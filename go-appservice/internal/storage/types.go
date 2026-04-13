package storage

import (
	"context"
	"errors"
	"time"
)

type ProviderKind string

const (
	ProviderFilesystem ProviderKind = "filesystem"
	ProviderS3         ProviderKind = "s3"
	ProviderSeaweedFS  ProviderKind = "seaweedfs"
)

type ArtifactStatus string

const (
	StatusPendingUpload ArtifactStatus = "pending_upload"
	StatusReady         ArtifactStatus = "ready"
	StatusUploadFailed  ArtifactStatus = "upload_failed"
)

// ArtifactMetadataStore is the closable MetadataStore alias used by the
// wiring layer so Close() is discoverable for graceful shutdown.
type ArtifactMetadataStore interface {
	MetadataStore
	Close() error
}

// MediaType categorises an artifact by its payload. Derived from content-type
// and/or filename extension via ClassifyMediaType.
type MediaType string

const (
	MediaTypeDocument MediaType = "document" // pdf, md, txt, html, docx, doc, odt, rtf
	MediaTypeImage    MediaType = "image"    // png, jpg, svg, webp, avif, gif, heic
	MediaTypeAudio    MediaType = "audio"    // mp3, wav, opus, m4a, flac, ogg
	MediaTypeVideo    MediaType = "video"    // mp4, webm, mkv, mov, avi, m4v
	MediaTypeData     MediaType = "data"     // csv, tsv, json, xlsx, xls, parquet, sqlite
	MediaTypeOther    MediaType = "other"    // fallback
)

type Action string

const (
	ActionUpload   Action = "upload"
	ActionDownload Action = "download"
)

var (
	ErrArtifactNotFound                = errors.New("artifact not found")
	ErrArtifactNotReady                = errors.New("artifact not ready")
	ErrArtifactUploadState             = errors.New("artifact not in uploadable state")
	ErrInvalidToken                    = errors.New("invalid signed token")
	ErrForbidden                       = errors.New("forbidden")
	ErrUnsupportedPipelineForArtifact  = errors.New("pipeline kind not supported for artifact-based trigger")
)

type Artifact struct {
	ID             string
	UserID         string    // exec-19: per-user isolation
	MediaType      MediaType // exec-19 Medium #4: stored, not derived per query
	ObjectKey      string
	Filename       string
	ContentType    string
	RetentionClass string
	Status         ArtifactStatus
	SizeBytes      int64
	SHA256Hex      string
	CreatedAt      time.Time
	UpdatedAt      time.Time
	ExpiresAt      time.Time

	DownloadToken string
}

type CreateArtifactInput struct {
	UserID         string
	Filename       string
	ContentType    string
	RetentionClass string
	ObjectKey      string
}

// FilesListQuery describes the filter set for listing artifacts.
// All fields are optional — zero values mean "no filter".
type FilesListQuery struct {
	UserID    string    // REQUIRED — enforced by handler, never empty here
	MediaType MediaType // filter by document|image|audio|video|data|other
	Status    string    // filter by artifact status (ready|pending_upload|upload_failed)
	Search    string    // filename substring (case-insensitive)
	Limit     int       // default 50, max 500
	Offset    int       // pagination offset
}

// FileRecord is the API representation of an artifact plus joined data
// (ingestion progress, media-specific metadata). Serialised to control-ui.
type FileRecord struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Type        MediaType `json:"type"`
	Extension   string    `json:"extension,omitempty"`
	ContentType string    `json:"content_type,omitempty"`
	Status      string    `json:"status"`
	SizeBytes   int64     `json:"size_bytes"`
	SHA256      string    `json:"sha256,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at,omitzero"`
	UserID      string    `json:"user_id,omitempty"`

	// Ingestion (joined from ingestion.jobs, nil if not ingested)
	Pipeline    string  `json:"pipeline,omitempty"`
	Progress    float64 `json:"progress,omitempty"`
	ChunksTotal int     `json:"chunks_total,omitempty"`
	ChunksDone  int     `json:"chunks_done,omitempty"`
	IngestError string  `json:"ingest_error,omitempty"`
}

// FilesListResult wraps a page of FileRecord with total + pagination info.
type FilesListResult struct {
	Items       []FileRecord `json:"items"`
	Total       int          `json:"total"`
	Limit       int          `json:"limit"`
	Offset      int          `json:"offset"`
	NextOffset  int          `json:"next_offset,omitempty"`
}

// FilesOverview is the aggregate summary for the control-ui Files tab header.
type FilesOverview struct {
	TotalFiles      int               `json:"total_files"`
	TotalBytes      int64             `json:"total_bytes"`
	IndexingPending int               `json:"indexing_pending"`
	IndexingFailed  int               `json:"indexing_failed"`
	ByType          map[MediaType]int `json:"by_type"`
	ByStatus        map[string]int    `json:"by_status"`
	RecentUploads   []FileRecord      `json:"recent_uploads"`
}

// UploadIntentInput describes the parameters for CreateUploadIntent.
// Filename and ContentType come from the browser File object; AutoIngest
// is a hint to immediately trigger the ingestion pipeline after mark-ready.
type UploadIntentInput struct {
	UserID         string
	Filename       string
	ContentType    string
	RetentionClass string
	SizeBytes      int64 // optional, for quota checks
	AutoIngest     bool  // whether mark-ready should auto-trigger ingestion
	// IngestPipeline is the kind to trigger if AutoIngest is true.
	// Empty = auto-detect from content type (documents → document pipeline,
	// audio → audio, etc.). Uses ingestion.PipelineKind from the connectors
	// package — we store as string here to avoid circular imports.
	IngestPipeline string
}

// UploadIntent bundles everything the client needs to perform a direct PUT
// to SeaweedFS: artifact metadata, signed PUT URL, TTL. After the browser
// completes the PUT, the client calls mark-ready with the artifact_id.
type UploadIntent struct {
	Artifact     Artifact  `json:"artifact"`
	UploadURL    string    `json:"upload_url"`
	UploadMethod string    `json:"upload_method"` // always "PUT"
	Token        string    `json:"token"`
	ExpiresAt    time.Time `json:"expires_at"`
	// AutoIngest echoes the input flag so the client knows whether to
	// follow up with a trigger call or rely on mark-ready to do it.
	AutoIngest     bool   `json:"auto_ingest,omitempty"`
	IngestPipeline string `json:"ingest_pipeline,omitempty"`
}

// MarkReadyResult describes the outcome of a mark-ready call. exec-19
// Review Fix #5: mark-ready may succeed (artifact.status = ready) but an
// optional auto-ingest trigger may fail — this must be distinguishable
// from a hard mark-ready failure. Handlers map MarkedReady=true +
// IngestError!=""  to HTTP 207 Multi-Status.
type MarkReadyResult struct {
	MarkedReady     bool   `json:"marked_ready"`
	IngestTriggered bool   `json:"ingest_triggered"`
	IngestJobID     string `json:"ingest_job_id,omitempty"`
	IngestError     string `json:"ingest_error,omitempty"`
}

type UploadResult struct {
	SizeBytes  int64
	SHA256Hex  string
	UploadedAt time.Time
}

// TokenClaims are the fields signed into an upload/download token. exec-19
// Stufe 3 Phase 2 (A): UserID is now part of the claims so that a leaked
// token cannot be redeemed by a different user. The handler extracts
// X-Actor-User-Id from the request and the signer binds it into the token.
// Verification checks both: (a) HMAC integrity, (b) claims.UserID matches
// the request's X-Actor-User-Id header.
type TokenClaims struct {
	ArtifactID string
	UserID     string // required, may be empty only for legacy-callsite fallback
	Action     Action
	ExpiresAt  time.Time
}

type SignedURL struct {
	Method    string
	URL       string
	Token     string
	ExpiresAt time.Time
}

type S3Config struct {
	Endpoint        string
	Region          string
	Bucket          string
	AccessKeyID     string
	SecretAccessKey string
	UsePathStyle    bool
	CreateBucket    bool
}

type MetadataStore interface {
	Create(artifact Artifact) error
	Get(id string) (Artifact, error)
	MarkUploaded(id string, result UploadResult) error

	// exec-19 Stufe 3: per-user listing
	ListByUser(query FilesListQuery) ([]Artifact, int, error)
	CountByStatus(userID string) (map[string]int, error)
	CountByMediaType(userID string) (map[MediaType]int, error)
	Delete(id string) error
}

// ObjectInfo describes an object as returned by an ObjectLister. It is the
// minimal subset needed for listing (Key, SizeBytes, LastModified, ETag) —
// body retrieval goes through ObjectStore.Get.
type ObjectInfo struct {
	Key          string
	SizeBytes    int64
	LastModified time.Time
	ETag         string
}

// ObjectLister is an optional capability a Provider may implement. The S3
// provider does, the filesystem provider doesn't (listing a user's tree on
// disk would be possible but is not currently needed). The FilesService
// discovers this via type assertion.
type ObjectLister interface {
	ListObjects(ctx context.Context, prefix string, maxKeys int) ([]ObjectInfo, error)
}

