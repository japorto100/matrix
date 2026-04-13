package storage

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"matrix/go-appservice/internal/connectors/ingestion"
)

// These tests use an in-memory fake MetadataStore (no DB needed) plus an
// httptest server for the ingestion client. Pure unit tests — no devstack.

// ─── Fake MetadataStore ──────────────────────────────────────────────

type fakeMetadataStore struct {
	artifacts map[string]Artifact
	created   []string // in insertion order
}

func newFakeStore() *fakeMetadataStore {
	return &fakeMetadataStore{artifacts: make(map[string]Artifact)}
}

func (s *fakeMetadataStore) Create(a Artifact) error {
	s.artifacts[a.ID] = a
	s.created = append(s.created, a.ID)
	return nil
}

func (s *fakeMetadataStore) Get(id string) (Artifact, error) {
	a, ok := s.artifacts[id]
	if !ok {
		return Artifact{}, ErrArtifactNotFound
	}
	return a, nil
}

func (s *fakeMetadataStore) MarkUploaded(id string, r UploadResult) error {
	a, ok := s.artifacts[id]
	if !ok {
		return ErrArtifactNotFound
	}
	a.Status = StatusReady
	a.SizeBytes = r.SizeBytes
	a.SHA256Hex = r.SHA256Hex
	a.UpdatedAt = r.UploadedAt
	s.artifacts[id] = a
	return nil
}

func (s *fakeMetadataStore) ListByUser(q FilesListQuery) ([]Artifact, int, error) {
	var out []Artifact
	for _, id := range s.created {
		a := s.artifacts[id]
		if a.UserID != q.UserID {
			continue
		}
		if q.Status != "" && string(a.Status) != q.Status {
			continue
		}
		out = append(out, a)
	}
	total := len(out)
	// Apply offset + limit
	if q.Offset > 0 && q.Offset < len(out) {
		out = out[q.Offset:]
	} else if q.Offset >= len(out) {
		out = nil
	}
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}
	return out, total, nil
}

func (s *fakeMetadataStore) CountByStatus(userID string) (map[string]int, error) {
	counts := make(map[string]int)
	for _, id := range s.created {
		a := s.artifacts[id]
		if a.UserID == userID {
			counts[string(a.Status)]++
		}
	}
	return counts, nil
}

func (s *fakeMetadataStore) CountByMediaType(userID string) (map[MediaType]int, error) {
	counts := make(map[MediaType]int)
	for _, id := range s.created {
		a := s.artifacts[id]
		if a.UserID != userID {
			continue
		}
		mt := a.MediaType
		if mt == "" {
			mt = ClassifyMediaType(a.ContentType, a.Filename)
		}
		counts[mt]++
	}
	return counts, nil
}

func (s *fakeMetadataStore) Delete(id string) error {
	if _, ok := s.artifacts[id]; !ok {
		return ErrArtifactNotFound
	}
	delete(s.artifacts, id)
	for i, v := range s.created {
		if v == id {
			s.created = append(s.created[:i], s.created[i+1:]...)
			break
		}
	}
	return nil
}

// ─── Helpers ─────────────────────────────────────────────────────────

func makeArtifact(id, userID, filename, contentType string) Artifact {
	now := time.Now().UTC()
	return Artifact{
		ID:          id,
		UserID:      userID,
		Filename:    filename,
		ContentType: contentType,
		Status:      StatusReady,
		SizeBytes:   1024,
		CreatedAt:   now,
		UpdatedAt:   now,
	}
}

// ─── Tests ───────────────────────────────────────────────────────────

func TestFilesServiceListRequiresUserID(t *testing.T) {
	store := newFakeStore()
	svc := NewFilesService(FilesServiceConfig{Store: store})

	_, err := svc.List(context.Background(), FilesListQuery{})
	if !errors.Is(err, ErrForbidden) {
		t.Errorf("List with empty userID = %v, want ErrForbidden", err)
	}
}

func TestFilesServiceListCrossUserIsolation(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "a.pdf", "application/pdf"))
	_ = store.Create(makeArtifact("a2", "alice", "b.mp3", "audio/mpeg"))
	_ = store.Create(makeArtifact("b1", "bob", "c.txt", "text/plain"))

	svc := NewFilesService(FilesServiceConfig{Store: store})

	result, err := svc.List(context.Background(), FilesListQuery{UserID: "alice", Limit: 10})
	if err != nil {
		t.Fatalf("List alice: %v", err)
	}
	if result.Total != 2 {
		t.Errorf("alice total = %d, want 2", result.Total)
	}
	for _, r := range result.Items {
		if r.UserID != "alice" {
			t.Errorf("cross-user leak: got %q", r.UserID)
		}
	}

	result, err = svc.List(context.Background(), FilesListQuery{UserID: "bob", Limit: 10})
	if err != nil {
		t.Fatalf("List bob: %v", err)
	}
	if result.Total != 1 {
		t.Errorf("bob total = %d, want 1", result.Total)
	}
}

func TestFilesServiceListMediaTypeFilter(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))
	_ = store.Create(makeArtifact("a2", "alice", "song.mp3", "audio/mpeg"))
	_ = store.Create(makeArtifact("a3", "alice", "movie.mp4", "video/mp4"))
	_ = store.Create(makeArtifact("a4", "alice", "data.csv", "text/csv"))

	svc := NewFilesService(FilesServiceConfig{Store: store})

	cases := []struct {
		mediaType MediaType
		wantLen   int
	}{
		{MediaTypeDocument, 1},
		{MediaTypeAudio, 1},
		{MediaTypeVideo, 1},
		{MediaTypeData, 1},
		{MediaTypeImage, 0},
	}
	for _, tc := range cases {
		t.Run(string(tc.mediaType), func(t *testing.T) {
			result, err := svc.List(context.Background(), FilesListQuery{
				UserID:    "alice",
				MediaType: tc.mediaType,
				Limit:     100,
			})
			if err != nil {
				t.Fatalf("List %s: %v", tc.mediaType, err)
			}
			if len(result.Items) != tc.wantLen {
				t.Errorf("%s len = %d, want %d", tc.mediaType, len(result.Items), tc.wantLen)
			}
			for _, r := range result.Items {
				if r.Type != tc.mediaType {
					t.Errorf("got type %q, want %q", r.Type, tc.mediaType)
				}
			}
		})
	}
}

func TestFilesServiceListJoinsIngestionJobs(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))
	_ = store.Create(makeArtifact("a2", "alice", "song.mp3", "audio/mpeg"))

	// Fake ingestion worker that returns a job for a1 only
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{
			"jobs": [
				{
					"id": "job-1",
					"file_id": "a1",
					"user_id": "alice",
					"pipeline": "document",
					"status": "embedding",
					"progress": 0.6,
					"chunks_total": 100,
					"chunks_done": 60,
					"started_at": "2026-04-11T12:00:00Z"
				}
			],
			"total": 1,
			"has_more": false
		}`))
	}))
	defer srv.Close()

	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})
	result, err := svc.List(context.Background(), FilesListQuery{UserID: "alice", Limit: 10})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(result.Items) != 2 {
		t.Fatalf("len = %d, want 2", len(result.Items))
	}
	// Find a1 and verify job data is merged
	var a1, a2 *FileRecord
	for i := range result.Items {
		if result.Items[i].ID == "a1" {
			a1 = &result.Items[i]
		}
		if result.Items[i].ID == "a2" {
			a2 = &result.Items[i]
		}
	}
	if a1 == nil || a2 == nil {
		t.Fatalf("missing a1 or a2 in result")
	}
	if a1.Pipeline != "document" {
		t.Errorf("a1 Pipeline = %q, want document", a1.Pipeline)
	}
	if a1.ChunksTotal != 100 {
		t.Errorf("a1 ChunksTotal = %d, want 100", a1.ChunksTotal)
	}
	if a1.Status != "embedding" {
		t.Errorf("a1 Status = %q, want embedding (overridden from ready)", a1.Status)
	}
	// a2 has no joined job, should keep raw metadata status
	if a2.Pipeline != "" {
		t.Errorf("a2 Pipeline = %q, want empty", a2.Pipeline)
	}
	if a2.Status != "ready" {
		t.Errorf("a2 Status = %q, want ready", a2.Status)
	}
}

func TestFilesServiceListIngestionDownIsNonFatal(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))

	// Point ingestion at a dead port
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient("http://127.0.0.1:1", 200*time.Millisecond),
	})

	result, err := svc.List(context.Background(), FilesListQuery{UserID: "alice", Limit: 10})
	if err != nil {
		t.Fatalf("List should not fail when ingestion is down: %v", err)
	}
	if len(result.Items) != 1 {
		t.Errorf("len = %d, want 1 (metadata-only)", len(result.Items))
	}
	// Pipeline field should be empty because we couldn't fetch jobs
	if result.Items[0].Pipeline != "" {
		t.Errorf("Pipeline = %q, want empty", result.Items[0].Pipeline)
	}
}

func TestFilesServiceGetEnforcesOwnership(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))

	svc := NewFilesService(FilesServiceConfig{Store: store})

	// Alice: OK
	rec, err := svc.Get(context.Background(), "a1", "alice")
	if err != nil {
		t.Errorf("alice Get: %v", err)
	}
	if rec.ID != "a1" {
		t.Errorf("ID = %q, want a1", rec.ID)
	}

	// Bob: forbidden
	_, err = svc.Get(context.Background(), "a1", "bob")
	if !errors.Is(err, ErrForbidden) {
		t.Errorf("bob Get = %v, want ErrForbidden", err)
	}

	// Empty userID: forbidden
	_, err = svc.Get(context.Background(), "a1", "")
	if !errors.Is(err, ErrForbidden) {
		t.Errorf("empty-user Get = %v, want ErrForbidden", err)
	}

	// Non-existent: NotFound
	_, err = svc.Get(context.Background(), "nope", "alice")
	if !errors.Is(err, ErrArtifactNotFound) {
		t.Errorf("nonexistent Get = %v, want ErrArtifactNotFound", err)
	}
}

func TestFilesServiceOverviewCountsPerUser(t *testing.T) {
	store := newFakeStore()
	// Alice: 3 ready documents
	for i := range 3 {
		a := makeArtifact("a"+string(rune('1'+i)), "alice", "doc.pdf", "application/pdf")
		_ = store.Create(a)
	}
	// Alice: 1 pending
	pending := makeArtifact("ap", "alice", "song.mp3", "audio/mpeg")
	pending.Status = StatusPendingUpload
	_ = store.Create(pending)
	// Bob: 1 ready — must NOT leak into alice's overview
	_ = store.Create(makeArtifact("b1", "bob", "x.txt", "text/plain"))

	svc := NewFilesService(FilesServiceConfig{Store: store})

	ov, err := svc.Overview(context.Background(), "alice")
	if err != nil {
		t.Fatalf("Overview: %v", err)
	}
	if ov.TotalFiles != 4 {
		t.Errorf("TotalFiles = %d, want 4", ov.TotalFiles)
	}
	if ov.ByStatus["ready"] != 3 {
		t.Errorf("ByStatus[ready] = %d, want 3", ov.ByStatus["ready"])
	}
	if ov.ByStatus["pending_upload"] != 1 {
		t.Errorf("ByStatus[pending_upload] = %d, want 1", ov.ByStatus["pending_upload"])
	}
	// Bob's file must not appear
	for _, r := range ov.RecentUploads {
		if r.UserID == "bob" {
			t.Error("bob's file leaked into alice overview")
		}
	}
}

func TestFilesServiceDeleteEnforcesOwnership(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))

	svc := NewFilesService(FilesServiceConfig{Store: store})

	// Bob cannot delete alice's file
	if err := svc.Delete(context.Background(), "a1", "bob"); !errors.Is(err, ErrForbidden) {
		t.Errorf("bob Delete = %v, want ErrForbidden", err)
	}
	// a1 still exists
	if _, err := store.Get("a1"); err != nil {
		t.Errorf("a1 should still exist after forbidden delete: %v", err)
	}

	// Alice can delete
	if err := svc.Delete(context.Background(), "a1", "alice"); err != nil {
		t.Errorf("alice Delete: %v", err)
	}
	// a1 is gone
	if _, err := store.Get("a1"); !errors.Is(err, ErrArtifactNotFound) {
		t.Errorf("after delete, Get = %v, want ErrArtifactNotFound", err)
	}
}

// ─── Write-flow tests (exec-19 Stufe 3 Phase 3) ──────────────────────

// fakeIngestionHandler returns a test ingestion worker that records every
// POST /ingest/* call so tests can assert what was triggered.
type recordedCall struct {
	Path string
	Body string
}

func newRecordingIngestionServer(t *testing.T) (*httptest.Server, *[]recordedCall) {
	var calls []recordedCall
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body := ""
		if r.Body != nil {
			b, _ := io.ReadAll(r.Body)
			body = string(b)
		}
		calls = append(calls, recordedCall{Path: r.URL.Path, Body: body})
		// Default response: accepted, stub job-id
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"job_id": "job-stub", "status": "pending"}`))
	}))
	t.Cleanup(func() { srv.Close() })
	return srv, &calls
}

func TestFilesServiceTriggerIngestionByMediaType(t *testing.T) {
	store := newFakeStore()
	// Ready artifacts of each media type
	docA := makeArtifact("doc1", "alice", "report.pdf", "application/pdf")
	imgA := makeArtifact("img1", "alice", "photo.jpg", "image/jpeg")
	audA := makeArtifact("aud1", "alice", "song.mp3", "audio/mpeg")
	vidA := makeArtifact("vid1", "alice", "clip.mp4", "video/mp4")
	for _, a := range []Artifact{docA, imgA, audA, vidA} {
		_ = store.Create(a)
	}

	srv, calls := newRecordingIngestionServer(t)
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	cases := []struct {
		artifactID string
		wantPath   string
	}{
		{"doc1", "/ingest/document"},
		{"img1", "/ingest/image"},
		{"aud1", "/ingest/audio"},
		{"vid1", "/ingest/video"},
	}
	for _, tc := range cases {
		t.Run(tc.artifactID, func(t *testing.T) {
			_, err := svc.TriggerIngestion(context.Background(), tc.artifactID, "alice", "")
			if err != nil {
				t.Fatalf("TriggerIngestion %s: %v", tc.artifactID, err)
			}
		})
	}
	// Verify all four endpoints were called
	if len(*calls) != 4 {
		t.Fatalf("want 4 calls, got %d: %+v", len(*calls), *calls)
	}
	for i, tc := range cases {
		if (*calls)[i].Path != tc.wantPath {
			t.Errorf("call %d: path = %q, want %q", i, (*calls)[i].Path, tc.wantPath)
		}
	}
}

func TestFilesServiceTriggerIngestionOwnership(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))

	srv, _ := newRecordingIngestionServer(t)
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	// Bob cannot trigger ingestion on alice's file
	_, err := svc.TriggerIngestion(context.Background(), "a1", "bob", "")
	if !errors.Is(err, ErrForbidden) {
		t.Errorf("bob trigger = %v, want ErrForbidden", err)
	}
	// Empty user → forbidden
	_, err = svc.TriggerIngestion(context.Background(), "a1", "", "")
	if !errors.Is(err, ErrForbidden) {
		t.Errorf("empty trigger = %v, want ErrForbidden", err)
	}
}

func TestFilesServiceTriggerIngestionRequiresReady(t *testing.T) {
	store := newFakeStore()
	pending := makeArtifact("a1", "alice", "doc.pdf", "application/pdf")
	pending.Status = StatusPendingUpload
	_ = store.Create(pending)

	srv, _ := newRecordingIngestionServer(t)
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	_, err := svc.TriggerIngestion(context.Background(), "a1", "alice", "")
	if !errors.Is(err, ErrArtifactNotReady) {
		t.Errorf("trigger on pending = %v, want ErrArtifactNotReady", err)
	}
}

func TestFilesServiceReindexOwnership(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))

	srv, calls := newRecordingIngestionServer(t)
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	// Alice reindex → hits /ingest/document/a1/reindex
	_, err := svc.Reindex(context.Background(), "a1", "alice")
	if err != nil {
		t.Fatalf("alice reindex: %v", err)
	}
	if len(*calls) != 1 {
		t.Fatalf("want 1 call, got %d", len(*calls))
	}
	if (*calls)[0].Path != "/ingest/document/a1/reindex" {
		t.Errorf("path = %q, want /ingest/document/a1/reindex", (*calls)[0].Path)
	}

	// Bob reindex → forbidden, no additional call
	_, err = svc.Reindex(context.Background(), "a1", "bob")
	if !errors.Is(err, ErrForbidden) {
		t.Errorf("bob reindex = %v, want ErrForbidden", err)
	}
	if len(*calls) != 1 {
		t.Errorf("bob should not have triggered a call; calls=%d", len(*calls))
	}
}

func TestFilesServiceMarkReadyAutoIngest(t *testing.T) {
	store := newFakeStore()
	pending := makeArtifact("a1", "alice", "report.pdf", "application/pdf")
	pending.Status = StatusPendingUpload
	_ = store.Create(pending)

	srv, calls := newRecordingIngestionServer(t)
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	result, err := svc.MarkReady(context.Background(), "a1", "alice", UploadResult{
		SizeBytes: 4096,
		SHA256Hex: "deadbeef",
	}, true, "")
	if err != nil {
		t.Fatalf("MarkReady: %v", err)
	}
	// Structured result (exec-19 Fix #5)
	if !result.MarkedReady {
		t.Error("MarkedReady = false, want true")
	}
	if !result.IngestTriggered {
		t.Error("IngestTriggered = false, want true (auto-ingest succeeded)")
	}
	if result.IngestJobID != "job-stub" {
		t.Errorf("IngestJobID = %q, want job-stub", result.IngestJobID)
	}
	if result.IngestError != "" {
		t.Errorf("IngestError = %q, want empty", result.IngestError)
	}

	// Artifact should now be ready
	got, _ := store.Get("a1")
	if got.Status != StatusReady {
		t.Errorf("status = %q, want ready", got.Status)
	}
	if got.SizeBytes != 4096 {
		t.Errorf("size = %d, want 4096", got.SizeBytes)
	}

	// Ingestion should have been triggered with document pipeline
	if len(*calls) != 1 {
		t.Fatalf("ingestion calls = %d, want 1 (auto-ingest)", len(*calls))
	}
	if (*calls)[0].Path != "/ingest/document" {
		t.Errorf("path = %q, want /ingest/document", (*calls)[0].Path)
	}
}

// TestFilesServiceMarkReadyIngestFails — Fix #5: ingest trigger failure
// must NOT fail MarkReady. Structured result reports partial success.
func TestFilesServiceMarkReadyIngestFails(t *testing.T) {
	store := newFakeStore()
	pending := makeArtifact("a1", "alice", "report.pdf", "application/pdf")
	pending.Status = StatusPendingUpload
	_ = store.Create(pending)

	// Ingestion server returns 500 for all POSTs
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"detail": "db down"}`))
	}))
	defer srv.Close()

	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	result, err := svc.MarkReady(context.Background(), "a1", "alice", UploadResult{
		SizeBytes: 4096, SHA256Hex: "deadbeef",
	}, true, "")
	if err != nil {
		t.Fatalf("MarkReady should not hard-fail on ingest error: %v", err)
	}
	if !result.MarkedReady {
		t.Error("MarkedReady should be true even when ingest fails")
	}
	if result.IngestTriggered {
		t.Error("IngestTriggered should be false")
	}
	if result.IngestError == "" {
		t.Error("IngestError should be set")
	}
	// Metadata row IS ready even though ingestion failed
	got, _ := store.Get("a1")
	if got.Status != StatusReady {
		t.Errorf("status = %q, want ready (mark-ready succeeded despite ingest fail)", got.Status)
	}
}

func TestFilesServiceMarkReadyWithoutAutoIngest(t *testing.T) {
	store := newFakeStore()
	pending := makeArtifact("a1", "alice", "song.mp3", "audio/mpeg")
	pending.Status = StatusPendingUpload
	_ = store.Create(pending)

	srv, calls := newRecordingIngestionServer(t)
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	result, err := svc.MarkReady(context.Background(), "a1", "alice", UploadResult{
		SizeBytes: 2048,
		SHA256Hex: "cafebabe",
	}, false, "")
	if err != nil {
		t.Fatalf("MarkReady: %v", err)
	}
	if !result.MarkedReady {
		t.Error("MarkedReady should be true")
	}
	if result.IngestTriggered {
		t.Error("IngestTriggered should be false (autoIngest=false)")
	}
	// No ingestion call — user didn't opt in
	if len(*calls) != 0 {
		t.Errorf("ingestion calls = %d, want 0 (autoIngest=false)", len(*calls))
	}
}

func TestFilesServiceDeleteCancelsRunningJob(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))

	// Mock ingestion that returns an in-progress job for a1 and records cancel
	var cancelCalled bool
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/jobs" && r.Method == "GET":
			_, _ = w.Write([]byte(`{
				"jobs": [
					{"id": "job-1", "file_id": "a1", "user_id": "alice", "pipeline": "document", "status": "embedding", "progress": 0.5, "started_at": "2026-04-11T12:00:00Z"}
				],
				"total": 1, "has_more": false
			}`))
		case r.URL.Path == "/jobs/job-1/cancel" && r.Method == "POST":
			cancelCalled = true
			w.WriteHeader(http.StatusOK)
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer srv.Close()

	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})
	if err := svc.Delete(context.Background(), "a1", "alice"); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if !cancelCalled {
		t.Error("CancelJob was not called for in-flight job")
	}
}

// TestFilesServiceTriggerIngestionFutureMediaTypes verifies the forward-
// compatible stubs route correctly even when the Python worker returns 404
// (which the client maps to ErrPipelineNotImplemented).
func TestFilesServiceTriggerIngestionFutureMediaTypes(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("img1", "alice", "photo.jpg", "image/jpeg"))

	// Worker that returns 404 for /ingest/image (not yet implemented).
	// Empty body — isMissingRouteBody returns true → ErrPipelineNotImplemented.
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer srv.Close()

	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})
	_, err := svc.TriggerIngestion(context.Background(), "img1", "alice", "")
	if err == nil {
		t.Fatal("expected error for unimplemented pipeline")
	}
	if !errors.Is(err, ingestion.ErrPipelineNotImplemented) {
		t.Errorf("error = %v, want ErrPipelineNotImplemented", err)
	}
}

// TestFilesServiceTriggerIngestionArtifactNotFoundIsNotMappedToNotImplemented
// guards the review Small #3 fix: a 404 response with a specific "artifact
// not found" body must surface as a real error, not be swallowed as
// ErrPipelineNotImplemented.
func TestFilesServiceTriggerIngestionArtifactNotFoundIsNotMappedToNotImplemented(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("doc1", "alice", "report.pdf", "application/pdf"))

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		// Resource-specific 404, not a route-level one
		_, _ = w.Write([]byte(`{"detail": "artifact doc1 not found in S3"}`))
	}))
	defer srv.Close()

	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})
	_, err := svc.TriggerIngestion(context.Background(), "doc1", "alice", "")
	if err == nil {
		t.Fatal("expected error")
	}
	if errors.Is(err, ingestion.ErrPipelineNotImplemented) {
		t.Errorf("resource-level 404 was mistakenly mapped to ErrPipelineNotImplemented: %v", err)
	}
}

// TestFilesServiceMarkReadyDataFileSkipsAutoIngest guards the review Small
// #1 fix: Data files (sqlite, parquet, json) must NOT fall back to the
// document pipeline on auto-ingest. They are skipped silently and the user
// can trigger a specific pipeline later if they want.
func TestFilesServiceMarkReadyDataFileSkipsAutoIngest(t *testing.T) {
	store := newFakeStore()
	pending := makeArtifact("db1", "alice", "store.sqlite", "application/x-sqlite3")
	pending.Status = StatusPendingUpload
	_ = store.Create(pending)

	srv, calls := newRecordingIngestionServer(t)
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	result, err := svc.MarkReady(context.Background(), "db1", "alice", UploadResult{
		SizeBytes: 1024,
		SHA256Hex: "deadbeef",
	}, true, "") // autoIngest=true with empty pipeline
	if err != nil {
		t.Fatalf("MarkReady: %v", err)
	}
	if !result.MarkedReady {
		t.Error("MarkedReady should be true")
	}
	if result.IngestTriggered {
		t.Error("IngestTriggered should be false (data file auto-skipped)")
	}
	if result.IngestError != "" {
		t.Errorf("IngestError = %q, want empty (silent skip)", result.IngestError)
	}
	// Artifact should be ready, but NO ingestion call
	got, _ := store.Get("db1")
	if got.Status != StatusReady {
		t.Errorf("status = %q, want ready", got.Status)
	}
	if len(*calls) != 0 {
		t.Errorf("ingestion calls = %d, want 0 (data file skipped)", len(*calls))
	}
}

// TestFilesServiceTriggerIngestionNotePipelineRejected guards the review
// Small #2 fix: artifact-based trigger for non-artifact pipelines (note,
// link, batch) must return ErrUnsupportedPipelineForArtifact cleanly.
func TestFilesServiceTriggerIngestionNotePipelineRejected(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(makeArtifact("a1", "alice", "doc.pdf", "application/pdf"))

	srv, calls := newRecordingIngestionServer(t)
	svc := NewFilesService(FilesServiceConfig{
		Store:     store,
		Ingestion: ingestion.NewClient(srv.URL, 2*time.Second),
	})

	// Each non-artifact pipeline must be rejected
	for _, kind := range []string{"note", "link", "batch"} {
		t.Run(kind, func(t *testing.T) {
			_, err := svc.TriggerIngestion(context.Background(), "a1", "alice", kind)
			if !errors.Is(err, ErrUnsupportedPipelineForArtifact) {
				t.Errorf("pipeline=%s error = %v, want ErrUnsupportedPipelineForArtifact", kind, err)
			}
		})
	}
	// And no ingestion calls should have been made (rejected before dispatch)
	if len(*calls) != 0 {
		t.Errorf("ingestion calls = %d, want 0 (all rejected)", len(*calls))
	}
}

// ─── Fix #9 Legacy UserID feature flag ─────────────────────────────────

// fakeLegacyArtifact emulates a pre-exec-19 row with empty UserID.
func fakeLegacyArtifact(id, filename, contentType string) Artifact {
	a := makeArtifact(id, "", filename, contentType) // UserID=""
	return a
}

func TestFilesServiceLegacyOwnerlessDefaultForbidden(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(fakeLegacyArtifact("legacy1", "doc.pdf", "application/pdf"))

	// Default: AllowLegacyOwnerless = false
	svc := NewFilesService(FilesServiceConfig{Store: store})

	_, err := svc.Get(context.Background(), "legacy1", "alice")
	if !errors.Is(err, ErrForbidden) {
		t.Errorf("legacy artifact Get with flag=false = %v, want ErrForbidden", err)
	}
	if err := svc.Delete(context.Background(), "legacy1", "alice"); !errors.Is(err, ErrForbidden) {
		t.Errorf("legacy artifact Delete with flag=false = %v, want ErrForbidden", err)
	}
}

func TestFilesServiceLegacyOwnerlessAllowedWithFlag(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(fakeLegacyArtifact("legacy1", "doc.pdf", "application/pdf"))

	// Flag enabled (dev mode)
	svc := NewFilesService(FilesServiceConfig{
		Store:                store,
		AllowLegacyOwnerless: true,
	})

	rec, err := svc.Get(context.Background(), "legacy1", "alice")
	if err != nil {
		t.Errorf("legacy artifact Get with flag=true = %v, want success", err)
	}
	if rec != nil && rec.ID != "legacy1" {
		t.Errorf("rec.ID = %q, want legacy1", rec.ID)
	}
}

func TestFilesServiceLegacyEmptyRequestUserStillForbidden(t *testing.T) {
	store := newFakeStore()
	_ = store.Create(fakeLegacyArtifact("legacy1", "doc.pdf", "application/pdf"))

	// Even with flag, empty request userID is forbidden
	svc := NewFilesService(FilesServiceConfig{
		Store:                store,
		AllowLegacyOwnerless: true,
	})

	_, err := svc.Get(context.Background(), "legacy1", "")
	if !errors.Is(err, ErrForbidden) {
		t.Errorf("legacy artifact Get with empty request user = %v, want ErrForbidden", err)
	}
}

// ─── Fix #7 ObjectLister join (orphan S3 files) ────────────────────────

// fakeLister is a minimal ObjectLister for unit tests.
type fakeLister struct {
	objs map[string][]ObjectInfo // prefix → objects
}

func (l *fakeLister) ListObjects(_ context.Context, prefix string, _ int) ([]ObjectInfo, error) {
	return l.objs[prefix], nil
}

func TestFilesServiceListSurfacesOrphanS3Objects(t *testing.T) {
	store := newFakeStore()
	// alice has 1 known artifact with object_key matching S3 blob
	knownArtifact := Artifact{
		ID:          "a1",
		UserID:      "alice",
		MediaType:   MediaTypeDocument,
		ObjectKey:   "users/alice/2026/doc.pdf",
		Filename:    "doc.pdf",
		ContentType: "application/pdf",
		Status:      StatusReady,
		CreatedAt:   time.Now().UTC().Add(-1 * time.Hour),
		UpdatedAt:   time.Now().UTC().Add(-1 * time.Hour),
	}
	_ = store.Create(knownArtifact)

	// S3 has 3 objects: known + 2 orphans
	lister := &fakeLister{
		objs: map[string][]ObjectInfo{
			"users/alice/": {
				{Key: "users/alice/2026/doc.pdf", SizeBytes: 1024, LastModified: time.Now().UTC()},
				{Key: "users/alice/orphan/extra.jpg", SizeBytes: 2048, LastModified: time.Now().UTC()},
				{Key: "users/alice/ghost/audio.mp3", SizeBytes: 4096, LastModified: time.Now().UTC()},
			},
		},
	}

	svc := NewFilesService(FilesServiceConfig{
		Store:  store,
		Lister: lister,
	})
	result, err := svc.List(context.Background(), FilesListQuery{UserID: "alice", Limit: 100})
	if err != nil {
		t.Fatalf("List: %v", err)
	}

	// Expected: 1 known (a1) + 2 orphans = 3 total
	if len(result.Items) != 3 {
		t.Fatalf("len = %d, want 3 (1 known + 2 orphans). Items: %+v", len(result.Items), result.Items)
	}
	orphanCount := 0
	for _, item := range result.Items {
		if item.Status == "orphan" {
			orphanCount++
			if !strings.HasPrefix(item.ID, "orphan:") {
				t.Errorf("orphan ID should start with 'orphan:', got %q", item.ID)
			}
		}
	}
	if orphanCount != 2 {
		t.Errorf("orphan count = %d, want 2", orphanCount)
	}
}

func TestFilesServiceListOrphanRespectsMediaTypeFilter(t *testing.T) {
	store := newFakeStore()
	lister := &fakeLister{
		objs: map[string][]ObjectInfo{
			"users/alice/": {
				{Key: "users/alice/foo.mp3", SizeBytes: 1024, LastModified: time.Now().UTC()},
				{Key: "users/alice/bar.pdf", SizeBytes: 2048, LastModified: time.Now().UTC()},
				{Key: "users/alice/baz.png", SizeBytes: 4096, LastModified: time.Now().UTC()},
			},
		},
	}

	svc := NewFilesService(FilesServiceConfig{Store: store, Lister: lister})

	// Filter for audio only
	result, err := svc.List(context.Background(), FilesListQuery{
		UserID:    "alice",
		MediaType: MediaTypeAudio,
		Limit:     100,
	})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(result.Items) != 1 {
		t.Fatalf("len = %d, want 1 (only the mp3 orphan)", len(result.Items))
	}
	if result.Items[0].Type != MediaTypeAudio {
		t.Errorf("type = %q, want audio", result.Items[0].Type)
	}
}

func TestFilesServiceListSkipsOrphansIfNoLister(t *testing.T) {
	store := newFakeStore()
	// No lister configured — orphans should not appear
	svc := NewFilesService(FilesServiceConfig{Store: store})

	result, err := svc.List(context.Background(), FilesListQuery{UserID: "alice", Limit: 10})
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(result.Items) != 0 {
		t.Errorf("len = %d, want 0", len(result.Items))
	}
}
