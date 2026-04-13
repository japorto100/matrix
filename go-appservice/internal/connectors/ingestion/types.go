package ingestion

// PipelineKind identifies which Python ingestion pipeline to run.
//
// Current Python worker support (as of 11.04.2026):
//   - document: PDF/DOCX/MD/TXT/HTML via DocumentPipeline
//   - note:     plain text → chunked directly
//   - link:     URL fetch → document pipeline
//
// Future (stubs exist in Go but the Python worker returns 501 or 404
// until the corresponding pipeline is implemented):
//   - image:    OCR + vision model description → text chunks
//   - audio:    Whisper transcription → text chunks
//   - video:    Key-frame extraction + Whisper + scene description
//   - batch:    multi-file archive (zip/tar) → fan-out to per-file pipelines
//
// The Go client allows callers to request any of these. If the worker does
// not implement it, Trigger* returns ErrPipelineNotImplemented which the
// FilesService maps to HTTP 501. This keeps the API forward-compatible.
type PipelineKind string

const (
	PipelineDocument PipelineKind = "document"
	PipelineNote     PipelineKind = "note"
	PipelineLink     PipelineKind = "link"
	PipelineImage    PipelineKind = "image"
	PipelineAudio    PipelineKind = "audio"
	PipelineVideo    PipelineKind = "video"
	PipelineBatch    PipelineKind = "batch"
)

// IsImplemented reports whether the Python worker currently supports the
// pipeline. Helps callers decide whether to attempt a request vs. falling
// back to a metadata-only upload (no RAG indexing).
func (p PipelineKind) IsImplemented() bool {
	switch p {
	case PipelineDocument, PipelineNote, PipelineLink:
		return true
	case PipelineImage, PipelineAudio, PipelineVideo, PipelineBatch:
		return false // future, stubs in Go, 501 in Python
	default:
		return false
	}
}

// DocumentIngestRequest triggers /ingest/document on the worker. The
// file_id refers to an artifact_metadata row whose blob lives in S3.
type DocumentIngestRequest struct {
	FileID   string         `json:"file_id"`
	UserID   string         `json:"user_id"`
	Filename string         `json:"filename,omitempty"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// NoteIngestRequest triggers /ingest/note. Notes are inline text, not a
// file in S3 — file_id is optional.
type NoteIngestRequest struct {
	UserID   string         `json:"user_id"`
	Title    string         `json:"title,omitempty"`
	Content  string         `json:"content"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// LinkIngestRequest triggers /ingest/link. Python fetches the URL,
// extracts text, and runs the document pipeline.
type LinkIngestRequest struct {
	UserID   string         `json:"user_id"`
	URL      string         `json:"url"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// ImageIngestRequest — future, will trigger OCR + vision captioning.
type ImageIngestRequest struct {
	FileID   string         `json:"file_id"`
	UserID   string         `json:"user_id"`
	Filename string         `json:"filename,omitempty"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// AudioIngestRequest — future, will trigger Whisper transcription.
type AudioIngestRequest struct {
	FileID   string         `json:"file_id"`
	UserID   string         `json:"user_id"`
	Filename string         `json:"filename,omitempty"`
	Language string         `json:"language,omitempty"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// VideoIngestRequest — future, will trigger key-frame + Whisper.
type VideoIngestRequest struct {
	FileID   string         `json:"file_id"`
	UserID   string         `json:"user_id"`
	Filename string         `json:"filename,omitempty"`
	Language string         `json:"language,omitempty"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

// IngestResponse is the common body returned by /ingest/* endpoints.
// Python returns {job_id, status} on success, at minimum.
type IngestResponse struct {
	JobID  string `json:"job_id,omitempty"`
	Status string `json:"status,omitempty"`
}
