// Package ingestion is a thin HTTP client for the Python ingestion worker
// running on port 8098. It is used by go-appservice to query ingestion job
// state for the Files API (exec-19 Stufe 3).
//
// The worker has its own FastAPI app (python-backend/ingestion/worker.py);
// we only need read-access to `GET /jobs` for Files-Tab listing and
// `GET /jobs/{id}` for per-artifact detail. Write operations (POST
// /ingest/*) happen from Python callers or from control-ui BFF directly,
// not from go-appservice.
package ingestion

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const DefaultBaseURL = "http://127.0.0.1:8098"

// SharedSecretHeader is the HTTP header name used for service-to-service
// authentication to the Python ingestion worker. exec-19 Stufe 3 Review
// Fix #8. Empty secret in dev mode means the header is omitted and the
// worker accepts unauthenticated calls.
const SharedSecretHeader = "X-Service-Auth" //nolint:gosec // header NAME, not a credential

// Client is a stateless HTTP client. Cheap to construct.
type Client struct {
	baseURL      string
	sharedSecret string
	httpClient   *http.Client
}

// NewClient constructs a client. The sharedSecret is sent in the
// X-Service-Auth header for every request; pass "" to disable (dev only).
func NewClient(baseURL string, timeout time.Duration, opts ...Option) *Client {
	base := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if base == "" {
		base = DefaultBaseURL
	}
	if timeout <= 0 {
		timeout = 3 * time.Second
	}
	c := &Client{
		baseURL:    base,
		httpClient: &http.Client{Timeout: timeout},
	}
	for _, opt := range opts {
		opt(c)
	}
	return c
}

// Option configures a Client.
type Option func(*Client)

// WithSharedSecret sets the shared secret sent in the X-Service-Auth
// header. See SharedSecretHeader. exec-19 Review Fix #8.
func WithSharedSecret(secret string) Option {
	return func(c *Client) { c.sharedSecret = strings.TrimSpace(secret) }
}

// applyAuth adds the X-Service-Auth header if a shared secret is configured.
func (c *Client) applyAuth(req *http.Request) {
	if c.sharedSecret != "" {
		req.Header.Set(SharedSecretHeader, c.sharedSecret)
	}
}

// Job mirrors the dict returned by the Python worker's `/jobs` endpoint.
// Field names match python-backend/ingestion/tracking/jobs.py list_recent().
// Fields are optional ("omitempty") because the worker may omit some in the
// response (e.g. an in-progress job has no completed_at).
type Job struct {
	ID           string    `json:"id"`
	FileID       string    `json:"file_id,omitempty"`
	UserID       string    `json:"user_id"`
	Pipeline     string    `json:"pipeline"`
	Status       string    `json:"status"`
	Progress     float64   `json:"progress,omitempty"`
	ChunksTotal  int       `json:"chunks_total,omitempty"`
	ChunksDone   int       `json:"chunks_done,omitempty"`
	ErrorMessage string    `json:"error_message,omitempty"`
	DocumentHash string    `json:"document_hash,omitempty"`
	StartedAt    time.Time `json:"started_at"`
	CompletedAt  time.Time `json:"completed_at,omitzero"`
}

// ListJobsQuery is the query-param bundle for GET /jobs.
type ListJobsQuery struct {
	Limit    int    // 1..500, default 50
	Pipeline string // document|note|link|batch
	Status   string // pending|done|failed|...
	UserID   string
}

type listJobsResponse struct {
	Jobs    []Job `json:"jobs"`
	Total   int   `json:"total"`
	HasMore bool  `json:"has_more"`
}

// ListJobs queries the worker for jobs matching the filter. Returns the jobs
// slice, the total reported, a has_more flag, and any transport error.
//
// The worker only returns the most recent N jobs ordered by started_at DESC.
// The caller is responsible for pagination via Limit. If the worker is
// unreachable, ListJobs returns an error — the FilesService treats that as
// "ingestion metadata unavailable" and still serves file listings from the
// metadata store alone.
func (c *Client) ListJobs(ctx context.Context, q ListJobsQuery) ([]Job, int, bool, error) {
	if c == nil {
		return nil, 0, false, fmt.Errorf("ingestion client is nil")
	}
	params := url.Values{}
	if q.Limit > 0 {
		params.Set("limit", fmt.Sprintf("%d", q.Limit))
	}
	if strings.TrimSpace(q.Pipeline) != "" {
		params.Set("pipeline", q.Pipeline)
	}
	if strings.TrimSpace(q.Status) != "" {
		params.Set("status", q.Status)
	}
	if strings.TrimSpace(q.UserID) != "" {
		params.Set("user_id", q.UserID)
	}
	u := c.baseURL + "/jobs"
	if encoded := params.Encode(); encoded != "" {
		u += "?" + encoded
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return nil, 0, false, fmt.Errorf("ingestion list_jobs request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	c.applyAuth(req)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, 0, false, fmt.Errorf("ingestion list_jobs transport: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, 0, false, fmt.Errorf("ingestion list_jobs status %d: %s",
			resp.StatusCode, string(body))
	}
	var out listJobsResponse
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, 0, false, fmt.Errorf("ingestion list_jobs decode: %w", err)
	}
	return out.Jobs, out.Total, out.HasMore, nil
}

// GetJob fetches a single job by ID. Returns ErrJobNotFound on 404.
func (c *Client) GetJob(ctx context.Context, jobID string) (*Job, error) {
	if c == nil {
		return nil, fmt.Errorf("ingestion client is nil")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		c.baseURL+"/jobs/"+url.PathEscape(jobID), nil)
	if err != nil {
		return nil, fmt.Errorf("ingestion get_job request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	c.applyAuth(req)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ingestion get_job transport: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode == http.StatusNotFound {
		return nil, ErrJobNotFound
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("ingestion get_job status %d: %s",
			resp.StatusCode, string(body))
	}
	var job Job
	if err := json.Unmarshal(body, &job); err != nil {
		return nil, fmt.Errorf("ingestion get_job decode: %w", err)
	}
	return &job, nil
}

// Health pings the worker's /health endpoint. Returns nil if reachable and
// healthy, error otherwise. Used by FilesService to decide whether to
// include ingestion metadata in the join.
func (c *Client) Health(ctx context.Context) error {
	if c == nil {
		return fmt.Errorf("ingestion client is nil")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/health", nil)
	if err != nil {
		return fmt.Errorf("ingestion health request: %w", err)
	}
	c.applyAuth(req)
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("ingestion health transport: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("ingestion health status %d", resp.StatusCode)
	}
	return nil
}

// ─── Write / Trigger methods (exec-19 Stufe 3 Phase 3) ───────────────

// postJSON posts a JSON body to the given path, decoding the response into
// `out` if provided. Returns ErrPipelineNotImplemented on 501, surfaces
// other error statuses as a formatted error with body excerpt.
func (c *Client) postJSON(ctx context.Context, path string, payload, out any) error {
	if c == nil {
		return fmt.Errorf("ingestion client is nil")
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal %s body: %w", path, err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.baseURL+path, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("ingestion POST %s: %w", path, err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	c.applyAuth(req)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("ingestion POST %s transport: %w", path, err)
	}
	defer func() { _ = resp.Body.Close() }()
	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode == http.StatusNotImplemented {
		return ErrPipelineNotImplemented
	}
	// FastAPI returns 404 for both (a) missing route and (b) artifact not
	// found. We only map to ErrPipelineNotImplemented for (a) — detected by
	// an empty body or a FastAPI-default "Not Found" body that does not
	// mention a specific resource. Otherwise it's a real 404 (artifact gone)
	// which surfaces as a normal error. Fixed 11.04.2026 (review Small #3).
	if resp.StatusCode == http.StatusNotFound && strings.Contains(path, "/ingest/") {
		if isMissingRouteBody(respBody) {
			return ErrPipelineNotImplemented
		}
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("ingestion POST %s status %d: %s",
			path, resp.StatusCode, string(respBody))
	}
	if out != nil && len(respBody) > 0 {
		if err := json.Unmarshal(respBody, out); err != nil {
			return fmt.Errorf("ingestion POST %s decode: %w", path, err)
		}
	}
	return nil
}

// isMissingRouteBody heuristically detects whether a 404 response from the
// Python worker indicates a missing route (pipeline not implemented) vs a
// missing resource (artifact not found).
//
// FastAPI's default "route not found" body is `{"detail": "Not Found"}`.
// Our worker's "artifact not found" body is `{"detail": "job not found"}`
// or similar — specific to the resource.
func isMissingRouteBody(body []byte) bool {
	if len(body) == 0 {
		return true
	}
	text := strings.ToLower(string(body))
	// Exact FastAPI default — missing route
	if strings.Contains(text, `"detail":"not found"`) ||
		strings.Contains(text, `"detail": "not found"`) {
		return true
	}
	// Our explicit "not implemented" marker
	if strings.Contains(text, "not implemented") {
		return true
	}
	// Anything else (e.g. "job not found", "artifact not found") is a
	// resource-level 404, not a route-level one.
	return false
}

// TriggerDocument starts a document ingestion job for a pre-uploaded
// artifact. The file must already exist in SeaweedFS under its object key.
func (c *Client) TriggerDocument(ctx context.Context, req DocumentIngestRequest) (*IngestResponse, error) {
	if strings.TrimSpace(req.FileID) == "" || strings.TrimSpace(req.UserID) == "" {
		return nil, fmt.Errorf("file_id and user_id required")
	}
	var out IngestResponse
	if err := c.postJSON(ctx, "/ingest/document", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// TriggerNote runs the note pipeline (inline text, no S3 file).
func (c *Client) TriggerNote(ctx context.Context, req NoteIngestRequest) (*IngestResponse, error) {
	if strings.TrimSpace(req.UserID) == "" || strings.TrimSpace(req.Content) == "" {
		return nil, fmt.Errorf("user_id and content required")
	}
	var out IngestResponse
	if err := c.postJSON(ctx, "/ingest/note", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// TriggerLink fetches an external URL and runs the document pipeline over
// the extracted text.
func (c *Client) TriggerLink(ctx context.Context, req LinkIngestRequest) (*IngestResponse, error) {
	if strings.TrimSpace(req.UserID) == "" || strings.TrimSpace(req.URL) == "" {
		return nil, fmt.Errorf("user_id and url required")
	}
	var out IngestResponse
	if err := c.postJSON(ctx, "/ingest/link", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// TriggerImage — forward-compatible stub. Returns ErrPipelineNotImplemented
// until the Python worker implements /ingest/image.
func (c *Client) TriggerImage(ctx context.Context, req ImageIngestRequest) (*IngestResponse, error) {
	if strings.TrimSpace(req.FileID) == "" || strings.TrimSpace(req.UserID) == "" {
		return nil, fmt.Errorf("file_id and user_id required")
	}
	var out IngestResponse
	if err := c.postJSON(ctx, "/ingest/image", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// TriggerAudio — forward-compatible stub. Will run Whisper transcription
// once the Python worker implements /ingest/audio.
func (c *Client) TriggerAudio(ctx context.Context, req AudioIngestRequest) (*IngestResponse, error) {
	if strings.TrimSpace(req.FileID) == "" || strings.TrimSpace(req.UserID) == "" {
		return nil, fmt.Errorf("file_id and user_id required")
	}
	var out IngestResponse
	if err := c.postJSON(ctx, "/ingest/audio", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// TriggerVideo — forward-compatible stub. Key-frame extraction + Whisper.
func (c *Client) TriggerVideo(ctx context.Context, req VideoIngestRequest) (*IngestResponse, error) {
	if strings.TrimSpace(req.FileID) == "" || strings.TrimSpace(req.UserID) == "" {
		return nil, fmt.Errorf("file_id and user_id required")
	}
	var out IngestResponse
	if err := c.postJSON(ctx, "/ingest/video", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Reindex triggers a smart re-ingestion of an existing document.
// Python's /ingest/document/{file_id}/reindex accepts a DocumentIngestRequest
// body (for updated metadata) and re-runs the pipeline.
func (c *Client) Reindex(ctx context.Context, fileID string, req DocumentIngestRequest) (*IngestResponse, error) {
	if strings.TrimSpace(fileID) == "" {
		return nil, fmt.Errorf("file_id required")
	}
	var out IngestResponse
	path := "/ingest/document/" + url.PathEscape(fileID) + "/reindex"
	if err := c.postJSON(ctx, path, req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// CancelJob marks a running job as cancelled on the worker side. This is
// called by FilesService.Delete to stop any in-flight pipeline before
// removing the artifact. Returns nil if the job is already gone (idempotent).
func (c *Client) CancelJob(ctx context.Context, jobID string) error {
	if c == nil {
		return fmt.Errorf("ingestion client is nil")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.baseURL+"/jobs/"+url.PathEscape(jobID)+"/cancel", nil)
	if err != nil {
		return fmt.Errorf("cancel job request: %w", err)
	}
	c.applyAuth(req)
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("cancel job transport: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode == http.StatusNotFound {
		return nil // already gone, idempotent
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("cancel job status %d: %s", resp.StatusCode, string(body))
	}
	return nil
}
