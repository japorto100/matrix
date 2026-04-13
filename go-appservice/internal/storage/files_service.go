package storage

import (
	"context"
	"fmt"
	"log/slog"
	"sort"
	"strings"
	"time"

	"matrix/go-appservice/internal/connectors/ingestion"
)

// FilesService is the high-level orchestrator for the user-facing Files API
// (exec-19 Stufe 3). It joins three data sources for READ operations and
// delegates WRITE operations to the underlying storage.Service + Ingestion
// client for upload/download/trigger flows.
//
// READ (join):
//  1. MetadataStore — Postgres storage.artifact_metadata (authoritative)
//  2. ObjectLister  — SeaweedFS ListObjects (blobs outside the pipeline)
//  3. IngestionClient — Python ingestion worker :8098 (pipeline progress)
//
// WRITE (delegate):
//   - CreateUploadIntent  → Service.CreateArtifact + Service.IssueUploadURL
//   - MarkReady           → Service.MarkUploaded (after direct-PUT) +
//                           optional ingestion trigger
//   - IssueDownloadURL    → Service.IssueDownloadURL
//   - TriggerIngestion    → IngestionClient.Trigger{Document|Audio|...}
//   - Reindex             → IngestionClient.Reindex
//   - Delete              → Service.DeleteArtifact + optional job cancel
//
// Per-user isolation is enforced at every layer:
//   - MetadataStore.ListByUser filters SQL by user_id
//   - ObjectLister is called with prefix `users/{user_id}/`
//   - IngestionClient.ListJobs passes user_id as query param
//   - Every write method verifies artifact.UserID == requestUserID
//
// The service is stateless; safe to call from any goroutine.
type FilesService struct {
	store                MetadataStore
	lister               ObjectLister // optional, nil for filesystem provider
	ingestion            *ingestion.Client
	artifact             *Service // delegates for write flows (upload/download/delete)
	nowFunc              func() time.Time
	allowLegacyOwnerless bool // exec-19 Review Fix #9
}

type FilesServiceConfig struct {
	Store     MetadataStore
	Lister    ObjectLister      // may be nil
	Ingestion *ingestion.Client // may be nil (read/write fall back gracefully)
	Artifact  *Service          // may be nil (write methods error without it)
	NowFunc   func() time.Time

	// AllowLegacyOwnerless allows read/delete access to artifacts with an
	// empty UserID (pre-exec-19 Phase 2 rows). Default: false — such rows
	// are treated as forbidden, matching the production-safe stance.
	// Dev mode may set this true to keep working with pre-existing data.
	// exec-19 Review Fix #9.
	AllowLegacyOwnerless bool
}

func NewFilesService(cfg FilesServiceConfig) *FilesService {
	nowFunc := cfg.NowFunc
	if nowFunc == nil {
		nowFunc = func() time.Time { return time.Now().UTC() }
	}
	return &FilesService{
		store:                cfg.Store,
		lister:               cfg.Lister,
		ingestion:            cfg.Ingestion,
		artifact:             cfg.Artifact,
		nowFunc:              nowFunc,
		allowLegacyOwnerless: cfg.AllowLegacyOwnerless,
	}
}

// checkOwnership is the single authoritative ownership gate for FilesService.
// exec-19 Review Fix #6 (consolidation) + #9 (legacy flag) + #11 (warn log).
//
// Rules:
//  1. Request userID must be non-empty (ErrForbidden otherwise).
//  2. If artifact.UserID is non-empty and matches → allow.
//  3. If artifact.UserID is empty (legacy row) and AllowLegacyOwnerless is
//     true → allow, but log a warning so operators notice the stale row.
//  4. Otherwise → ErrForbidden.
func (s *FilesService) checkOwnership(ctx context.Context, artifact Artifact, userID, op string) error {
	if strings.TrimSpace(userID) == "" {
		slog.WarnContext(ctx, "files_service: empty user_id on write path",
			"op", op, "artifact_id", artifact.ID)
		return ErrForbidden
	}
	if artifact.UserID == "" {
		if !s.allowLegacyOwnerless {
			slog.WarnContext(ctx, "files_service: rejecting legacy owner-less artifact",
				"op", op, "artifact_id", artifact.ID, "request_user", userID)
			return ErrForbidden
		}
		slog.WarnContext(ctx, "files_service: allowing legacy owner-less artifact (AllowLegacyOwnerless=true)",
			"op", op, "artifact_id", artifact.ID, "request_user", userID)
		return nil
	}
	if artifact.UserID != userID {
		return ErrForbidden
	}
	return nil
}

// List returns a page of FileRecords for the given user, joined with
// ingestion job state if available. The MediaType filter is applied in Go
// after the SQL query (see metadata_store ListByUser for the rationale).
//
// exec-19 Review Fix #7: if an ObjectLister is configured, blobs in S3
// under the user's prefix that have no corresponding metadata row are also
// surfaced as "orphaned" FileRecords so operators can reconcile. Non-
// orphan paths still prefer the metadata row (authoritative for filename,
// content_type, status).
func (s *FilesService) List(ctx context.Context, query FilesListQuery) (*FilesListResult, error) {
	userID := strings.TrimSpace(query.UserID)
	if userID == "" {
		slog.WarnContext(ctx, "files_service: List called with empty user_id")
		return nil, ErrForbidden
	}
	limit := query.Limit
	if limit <= 0 {
		limit = 50
	}
	if limit > 500 {
		limit = 500
	}

	// 1. Query metadata store (authoritative source)
	artifacts, totalRaw, err := s.store.ListByUser(query)
	if err != nil {
		return nil, fmt.Errorf("list artifacts: %w", err)
	}

	// 2. Query ingestion worker (best-effort, failures don't break listing)
	jobsByFileID := make(map[string]*ingestion.Job)
	if s.ingestion != nil {
		jobs, _, _, jobsErr := s.ingestion.ListJobs(ctx, ingestion.ListJobsQuery{
			UserID: userID,
			Limit:  500, // over-fetch so we can join even if the user has many
		})
		if jobsErr == nil {
			for i := range jobs {
				job := &jobs[i]
				if job.FileID != "" {
					jobsByFileID[job.FileID] = job
				}
			}
		} else {
			slog.WarnContext(ctx, "files_service: ingestion ListJobs failed, serving metadata-only",
				"error", jobsErr)
		}
	}

	// 3. Build FileRecords with joined data
	records := make([]FileRecord, 0, len(artifacts))
	knownObjectKeys := make(map[string]struct{}, len(artifacts))
	for _, a := range artifacts {
		knownObjectKeys[a.ObjectKey] = struct{}{}
		rec := artifactToRecord(a)
		if job, ok := jobsByFileID[a.ID]; ok {
			applyJobToRecord(&rec, job)
		}
		// 4. Apply MediaType filter in-memory
		if query.MediaType != "" && rec.Type != query.MediaType {
			continue
		}
		records = append(records, rec)
	}

	// 5. Optional S3 listing — surface orphan blobs (in S3, not in metadata)
	// exec-19 Review Fix #7. Best-effort: if the listing fails we still
	// return the metadata-only set.
	if s.lister != nil {
		prefix := "users/" + userID + "/"
		objs, listErr := s.lister.ListObjects(ctx, prefix, 500)
		if listErr == nil {
			for _, obj := range objs {
				if _, known := knownObjectKeys[obj.Key]; known {
					continue
				}
				rec := orphanObjectToRecord(obj, userID)
				if query.MediaType != "" && rec.Type != query.MediaType {
					continue
				}
				records = append(records, rec)
			}
		} else {
			slog.WarnContext(ctx, "files_service: S3 ListObjects failed, orphans not surfaced",
				"error", listErr, "prefix", prefix)
		}
	}

	// 6. Re-sort by CreatedAt DESC (stable after in-memory filter + orphans)
	sort.SliceStable(records, func(i, j int) bool {
		return records[i].CreatedAt.After(records[j].CreatedAt)
	})

	// 7. Truncate to requested limit (ListByUser may have over-fetched 4x
	//    for MediaType filter headroom, plus orphans may push over the limit)
	nextOffset := 0
	if len(records) > limit {
		records = records[:limit]
		nextOffset = query.Offset + limit
	}

	// When MediaType is set, total is approximate (we don't know exactly how
	// many match without scanning all). Use the raw SQL count as upper bound.
	total := totalRaw
	if query.MediaType != "" {
		total = len(records) // best we can do without a full scan
	}

	return &FilesListResult{
		Items:      records,
		Total:      total,
		Limit:      limit,
		Offset:     query.Offset,
		NextOffset: nextOffset,
	}, nil
}

// orphanObjectToRecord builds a FileRecord from an S3 object that has no
// metadata row. Status is "orphan" to make it distinguishable in the UI.
// exec-19 Review Fix #7.
func orphanObjectToRecord(obj ObjectInfo, userID string) FileRecord {
	// Extract filename from the last path segment
	filename := obj.Key
	if idx := strings.LastIndex(filename, "/"); idx >= 0 {
		filename = filename[idx+1:]
	}
	return FileRecord{
		ID:        "orphan:" + obj.Key, // synthetic ID, cannot be used for metadata ops
		Name:      filename,
		Type:      ClassifyMediaType("", filename),
		Extension: FileExtension(filename),
		Status:    "orphan",
		SizeBytes: obj.SizeBytes,
		CreatedAt: obj.LastModified,
		UpdatedAt: obj.LastModified,
		UserID:    userID,
	}
}

// Overview aggregates user-level file statistics for the Files-Tab header.
// Uses native SQL aggregation (CountByStatus + CountByMediaType) so it
// scales to 10k+ files per user without fetching rows. Recent uploads is
// a separate small-limit query. Fixed 11.04.2026 (review Medium #4,
// Option A — media_type stored in DB).
func (s *FilesService) Overview(ctx context.Context, userID string) (*FilesOverview, error) {
	userID = strings.TrimSpace(userID)
	if userID == "" {
		return nil, ErrForbidden
	}
	byStatus, err := s.store.CountByStatus(userID)
	if err != nil {
		return nil, fmt.Errorf("count by status: %w", err)
	}
	byType, err := s.store.CountByMediaType(userID)
	if err != nil {
		return nil, fmt.Errorf("count by media_type: %w", err)
	}

	// Recent uploads: small page for the Files-Tab "last activity" strip.
	recent, _, err := s.store.ListByUser(FilesListQuery{
		UserID: userID,
		Limit:  10,
	})
	if err != nil {
		return nil, fmt.Errorf("list recent: %w", err)
	}
	recentRecords := make([]FileRecord, 0, len(recent))
	var totalBytes int64
	for _, a := range recent {
		recentRecords = append(recentRecords, artifactToRecord(a))
		totalBytes += a.SizeBytes
	}

	total := 0
	for _, c := range byStatus {
		total += c
	}

	return &FilesOverview{
		TotalFiles:      total,
		TotalBytes:      totalBytes,
		IndexingPending: byStatus["pending_upload"],
		IndexingFailed:  byStatus["upload_failed"],
		ByType:          byType,
		ByStatus:        byStatus,
		RecentUploads:   recentRecords,
	}, nil
}

// Get returns a single FileRecord for the given artifact, enforcing
// ownership. Returns ErrArtifactNotFound or ErrForbidden on access denial.
func (s *FilesService) Get(ctx context.Context, artifactID, userID string) (*FileRecord, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return nil, fmt.Errorf("get artifact %s: %w", artifactID, err)
	}
	if err := s.checkOwnership(ctx, artifact, userID, "Get"); err != nil {
		return nil, err
	}

	rec := artifactToRecord(artifact)

	// Join ingestion status (best-effort)
	if s.ingestion != nil {
		jobs, _, _, err := s.ingestion.ListJobs(ctx, ingestion.ListJobsQuery{
			UserID: userID,
			Limit:  100,
		})
		if err == nil {
			for i := range jobs {
				if jobs[i].FileID == artifactID {
					applyJobToRecord(&rec, &jobs[i])
					break
				}
			}
		}
	}

	return &rec, nil
}

// Delete removes the artifact's metadata row and object. Enforces ownership.
// Also attempts to cancel any in-flight ingestion job (best-effort, non-fatal
// if the ingestion worker is unreachable). Idempotent.
func (s *FilesService) Delete(ctx context.Context, artifactID, userID string) error {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return fmt.Errorf("get artifact %s: %w", artifactID, err)
	}
	if err := s.checkOwnership(ctx, artifact, userID, "Delete"); err != nil {
		return err
	}
	userID = strings.TrimSpace(userID)

	// Best-effort: cancel any running ingestion job for this file.
	if s.ingestion != nil {
		jobs, _, _, err := s.ingestion.ListJobs(ctx, ingestion.ListJobsQuery{
			UserID: userID,
			Limit:  100,
		})
		if err == nil {
			for _, job := range jobs {
				if job.FileID == artifactID && job.Status != "done" && job.Status != "failed" {
					_ = s.ingestion.CancelJob(ctx, job.ID)
				}
			}
		}
	}

	if s.artifact != nil {
		if err := s.artifact.DeleteArtifact(ctx, artifactID); err != nil {
			return fmt.Errorf("delete artifact %s: %w", artifactID, err)
		}
		return nil
	}
	if err := s.store.Delete(artifactID); err != nil {
		return fmt.Errorf("delete artifact %s: %w", artifactID, err)
	}
	return nil
}

// ─── Write flows (exec-19 Stufe 3 Phase 3) ──────────────────────────

// CreateUploadIntent creates an artifact_metadata row in pending_upload
// state and issues a signed PUT URL to SeaweedFS. The returned UploadIntent
// contains everything the browser needs for a direct PUT bypass of Go.
func (s *FilesService) CreateUploadIntent(ctx context.Context, input UploadIntentInput, gatewayBaseURL string) (*UploadIntent, error) {
	userID := strings.TrimSpace(input.UserID)
	if userID == "" {
		return nil, ErrForbidden
	}
	if s.artifact == nil {
		return nil, fmt.Errorf("files service has no underlying artifact service")
	}
	artifact, err := s.artifact.CreateArtifact(ctx, CreateArtifactInput{
		UserID:         userID,
		Filename:       input.Filename,
		ContentType:    input.ContentType,
		RetentionClass: input.RetentionClass,
	})
	if err != nil {
		return nil, fmt.Errorf("create artifact: %w", err)
	}
	signed, err := s.artifact.IssueUploadURL(artifact.ID, userID, gatewayBaseURL)
	if err != nil {
		return nil, fmt.Errorf("issue upload url: %w", err)
	}
	return &UploadIntent{
		Artifact:       artifact,
		UploadURL:      signed.URL,
		UploadMethod:   signed.Method,
		Token:          signed.Token,
		ExpiresAt:      signed.ExpiresAt,
		AutoIngest:     input.AutoIngest,
		IngestPipeline: input.IngestPipeline,
	}, nil
}

// MarkReady finalizes an upload after the browser has PUT the bytes
// directly to SeaweedFS. This is the Direct-PUT flow counterpart to
// Service.UploadArtifact (which is the Proxy-PUT flow).
//
// Returns a MarkReadyResult that distinguishes the mark-ready outcome
// from the (optional) auto-ingest outcome. exec-19 Review Fix #5.
//
// Flow:
//  1. Verify ownership
//  2. Verify status == pending_upload
//  3. Store.MarkUploaded → artifact.status = ready (hard failure if fails)
//  4. If autoIngest: dispatch to ingestion. Non-fatal if that fails —
//     MarkReadyResult.IngestError is set, caller can retry later.
func (s *FilesService) MarkReady(ctx context.Context, artifactID, userID string, result UploadResult, autoIngest bool, pipeline string) (*MarkReadyResult, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return nil, fmt.Errorf("get artifact %s: %w", artifactID, err)
	}
	if err := s.checkOwnership(ctx, artifact, userID, "MarkReady"); err != nil {
		return nil, err
	}
	if artifact.Status != StatusPendingUpload {
		return nil, ErrArtifactUploadState
	}
	if result.UploadedAt.IsZero() {
		result.UploadedAt = s.nowFunc().UTC()
	}
	if err := s.store.MarkUploaded(artifactID, result); err != nil {
		return nil, fmt.Errorf("mark uploaded: %w", err)
	}
	out := &MarkReadyResult{MarkedReady: true}
	if !autoIngest {
		return out, nil
	}
	// Reload artifact with updated state for ingestion request metadata
	updated, getErr := s.store.Get(artifactID)
	if getErr != nil {
		// Should not happen — we just wrote the row. Log + treat as
		// ingest failure so caller sees MarkedReady=true at least.
		slog.WarnContext(ctx, "files_service: post-mark-ready reload failed",
			"artifact_id", artifactID, "error", getErr)
		out.IngestError = getErr.Error()
		return out, nil
	}
	resp, ingErr := s.triggerIngestionForArtifactWithResponse(ctx, updated, pipeline)
	if ingErr != nil {
		slog.WarnContext(ctx, "files_service: auto-ingest trigger failed (mark-ready still succeeded)",
			"artifact_id", artifactID, "error", ingErr)
		out.IngestError = ingErr.Error()
		return out, nil
	}
	if resp != nil {
		out.IngestTriggered = true
		out.IngestJobID = resp.JobID
	}
	return out, nil
}

// IssueDownloadURL returns a fresh signed download URL for an owned artifact.
func (s *FilesService) IssueDownloadURL(ctx context.Context, artifactID, userID, gatewayBaseURL string) (*SignedURL, error) {
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return nil, fmt.Errorf("get artifact %s: %w", artifactID, err)
	}
	if ownErr := s.checkOwnership(ctx, artifact, userID, "IssueDownloadURL"); ownErr != nil {
		return nil, ownErr
	}
	if s.artifact == nil {
		return nil, fmt.Errorf("files service has no underlying artifact service")
	}
	signed, signErr := s.artifact.IssueDownloadURL(artifactID, userID, gatewayBaseURL)
	if signErr != nil {
		return nil, fmt.Errorf("issue download url: %w", signErr)
	}
	return &signed, nil
}

// TriggerIngestion dispatches to the right IngestionClient.Trigger* based on
// pipeline kind. Callers can use this either directly (explicit trigger) or
// via the AutoIngest flag on CreateUploadIntent → MarkReady chain.
//
// If pipeline is empty string, it is auto-detected from the artifact's
// MediaType (document/image/audio/video). Enforces ownership.
func (s *FilesService) TriggerIngestion(ctx context.Context, artifactID, userID, pipeline string) (*ingestion.IngestResponse, error) {
	if s.ingestion == nil {
		return nil, fmt.Errorf("ingestion client not configured")
	}
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return nil, fmt.Errorf("get artifact %s: %w", artifactID, err)
	}
	if err := s.checkOwnership(ctx, artifact, userID, "TriggerIngestion"); err != nil {
		return nil, err
	}
	if artifact.Status != StatusReady {
		return nil, ErrArtifactNotReady
	}
	kind := ingestion.PipelineKind(pipeline)
	if kind == "" {
		kind = pipelineForMediaType(ClassifyMediaType(artifact.ContentType, artifact.Filename))
	}
	return s.triggerKind(ctx, kind, artifact)
}

// Reindex re-runs the document pipeline for a previously-ingested file.
// Python cancels any existing job and starts a fresh run.
func (s *FilesService) Reindex(ctx context.Context, artifactID, userID string) (*ingestion.IngestResponse, error) {
	if s.ingestion == nil {
		return nil, fmt.Errorf("ingestion client not configured")
	}
	artifact, err := s.store.Get(artifactID)
	if err != nil {
		return nil, fmt.Errorf("get artifact %s: %w", artifactID, err)
	}
	if ownErr := s.checkOwnership(ctx, artifact, userID, "Reindex"); ownErr != nil {
		return nil, ownErr
	}
	// Use the artifact's owning user (which matches request after
	// checkOwnership) for the outgoing ingestion call. This preserves
	// ownership semantics when AllowLegacyOwnerless is in play: the
	// outgoing request carries the *request* user, not "".
	ownerUser := artifact.UserID
	if ownerUser == "" {
		ownerUser = strings.TrimSpace(userID)
	}
	resp, reindexErr := s.ingestion.Reindex(ctx, artifactID, ingestion.DocumentIngestRequest{
		FileID:   artifactID,
		UserID:   ownerUser,
		Filename: artifact.Filename,
	})
	if reindexErr != nil {
		return nil, fmt.Errorf("reindex %s: %w", artifactID, reindexErr)
	}
	return resp, nil
}

// triggerIngestionForArtifactWithResponse is an internal helper used by
// MarkReady when autoIngest is true. It classifies the media and dispatches.
// Returns (nil, nil) silently if the media type has no auto-ingest
// pipeline (Data/Other) — caller treats this as "no ingestion, no error".
func (s *FilesService) triggerIngestionForArtifactWithResponse(ctx context.Context, artifact Artifact, pipeline string) (*ingestion.IngestResponse, error) {
	if s.ingestion == nil {
		return nil, nil // no client → skip, caller treated as non-fatal
	}
	kind := ingestion.PipelineKind(pipeline)
	if kind == "" {
		kind = pipelineForMediaType(ClassifyMediaType(artifact.ContentType, artifact.Filename))
	}
	if kind == "" {
		return nil, nil // no auto-pipeline for this media type → skip silently
	}
	return s.triggerKind(ctx, kind, artifact)
}

// triggerKind routes to the right client method based on pipeline kind.
// Only artifact-based pipelines (document/image/audio/video) can be
// triggered this way. Note/Link/Batch have no artifact (note = inline text,
// link = URL, batch = ZIP/TAR fan-out) — callers must use the ingestion
// client directly with the corresponding request struct.
func (s *FilesService) triggerKind(ctx context.Context, kind ingestion.PipelineKind, artifact Artifact) (*ingestion.IngestResponse, error) {
	var resp *ingestion.IngestResponse
	var err error
	switch kind {
	case ingestion.PipelineDocument:
		resp, err = s.ingestion.TriggerDocument(ctx, ingestion.DocumentIngestRequest{
			FileID:   artifact.ID,
			UserID:   artifact.UserID,
			Filename: artifact.Filename,
		})
	case ingestion.PipelineImage:
		resp, err = s.ingestion.TriggerImage(ctx, ingestion.ImageIngestRequest{
			FileID:   artifact.ID,
			UserID:   artifact.UserID,
			Filename: artifact.Filename,
		})
	case ingestion.PipelineAudio:
		resp, err = s.ingestion.TriggerAudio(ctx, ingestion.AudioIngestRequest{
			FileID:   artifact.ID,
			UserID:   artifact.UserID,
			Filename: artifact.Filename,
		})
	case ingestion.PipelineVideo:
		resp, err = s.ingestion.TriggerVideo(ctx, ingestion.VideoIngestRequest{
			FileID:   artifact.ID,
			UserID:   artifact.UserID,
			Filename: artifact.Filename,
		})
	case ingestion.PipelineNote, ingestion.PipelineLink, ingestion.PipelineBatch:
		return nil, ErrUnsupportedPipelineForArtifact
	default:
		return nil, fmt.Errorf("unknown pipeline kind %q", kind)
	}
	if err != nil {
		return nil, fmt.Errorf("trigger %s: %w", kind, err)
	}
	return resp, nil
}

// pipelineForMediaType picks the appropriate ingestion pipeline for the
// auto-ingest path. Returns empty string for types with no sensible default
// (data files like SQLite, unknowns) — callers must skip rather than fall
// back to the document pipeline which would fail on non-text payloads.
// Fixed 11.04.2026 (review finding Small #1).
func pipelineForMediaType(mt MediaType) ingestion.PipelineKind {
	switch mt {
	case MediaTypeDocument:
		return ingestion.PipelineDocument
	case MediaTypeImage:
		return ingestion.PipelineImage
	case MediaTypeAudio:
		return ingestion.PipelineAudio
	case MediaTypeVideo:
		return ingestion.PipelineVideo
	case MediaTypeData, MediaTypeOther:
		return "" // no auto-pipeline — explicit user choice required
	default:
		return ""
	}
}

// ─── Helpers ────────────────────────────────────────────────────────────

func artifactToRecord(a Artifact) FileRecord {
	// Prefer the stored MediaType (set at Create time). Fall back to a
	// fresh classify for legacy rows where MediaType is empty or 'other'
	// due to a still-pending backfill.
	mt := a.MediaType
	if mt == "" || mt == MediaTypeOther {
		mt = ClassifyMediaType(a.ContentType, a.Filename)
	}
	return FileRecord{
		ID:          a.ID,
		Name:        a.Filename,
		Type:        mt,
		Extension:   FileExtension(a.Filename),
		ContentType: a.ContentType,
		Status:      string(a.Status),
		SizeBytes:   a.SizeBytes,
		SHA256:      a.SHA256Hex,
		CreatedAt:   a.CreatedAt,
		UpdatedAt:   a.UpdatedAt,
		UserID:      a.UserID,
	}
}

func applyJobToRecord(rec *FileRecord, job *ingestion.Job) {
	rec.Pipeline = job.Pipeline
	rec.Progress = job.Progress
	rec.ChunksTotal = job.ChunksTotal
	rec.ChunksDone = job.ChunksDone
	rec.IngestError = job.ErrorMessage
	// If the ingestion status is more specific than the raw artifact status
	// (e.g. "embedding" vs "ready"), we prefer ingestion for display.
	if job.Status != "" {
		rec.Status = job.Status
	}
}
