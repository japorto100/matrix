package ingestion

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// These tests are pure unit tests against an httptest server — they do not
// require the real Python ingestion worker on :8098 to be running.

func newTestServer(handler http.HandlerFunc) (*httptest.Server, *Client) {
	srv := httptest.NewServer(handler)
	client := NewClient(srv.URL, 2*time.Second)
	return srv, client
}

func TestListJobsSuccess(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			t.Errorf("method = %q, want GET", r.Method)
		}
		if r.URL.Path != "/jobs" {
			t.Errorf("path = %q, want /jobs", r.URL.Path)
		}
		q := r.URL.Query()
		if q.Get("limit") != "10" {
			t.Errorf("limit = %q, want 10", q.Get("limit"))
		}
		if q.Get("user_id") != "alice" {
			t.Errorf("user_id = %q, want alice", q.Get("user_id"))
		}
		if q.Get("status") != "done" {
			t.Errorf("status = %q, want done", q.Get("status"))
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"jobs": []map[string]any{
				{
					"id":           "job-1",
					"user_id":      "alice",
					"pipeline":     "document",
					"status":       "done",
					"progress":     1.0,
					"chunks_total": 10,
					"chunks_done":  10,
					"started_at":   "2026-04-11T12:00:00Z",
					"completed_at": "2026-04-11T12:00:05Z",
				},
				{
					"id":           "job-2",
					"user_id":      "alice",
					"pipeline":     "note",
					"status":       "done",
					"progress":     1.0,
					"started_at":   "2026-04-11T11:00:00Z",
					"completed_at": "2026-04-11T11:00:01Z",
				},
			},
			"total":    2,
			"has_more": false,
		})
	})
	defer srv.Close()

	jobs, total, hasMore, err := client.ListJobs(context.Background(), ListJobsQuery{
		Limit:  10,
		Status: "done",
		UserID: "alice",
	})
	if err != nil {
		t.Fatalf("ListJobs: %v", err)
	}
	if total != 2 {
		t.Errorf("total = %d, want 2", total)
	}
	if hasMore {
		t.Error("hasMore = true, want false")
	}
	if len(jobs) != 2 {
		t.Fatalf("len(jobs) = %d, want 2", len(jobs))
	}
	if jobs[0].ID != "job-1" {
		t.Errorf("jobs[0].ID = %q, want job-1", jobs[0].ID)
	}
	if jobs[0].Pipeline != "document" {
		t.Errorf("jobs[0].Pipeline = %q, want document", jobs[0].Pipeline)
	}
	if jobs[0].ChunksTotal != 10 {
		t.Errorf("jobs[0].ChunksTotal = %d, want 10", jobs[0].ChunksTotal)
	}
	if !jobs[0].StartedAt.Equal(time.Date(2026, 4, 11, 12, 0, 0, 0, time.UTC)) {
		t.Errorf("jobs[0].StartedAt = %v, want 2026-04-11T12:00:00Z", jobs[0].StartedAt)
	}
}

func TestListJobsEmpty(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"jobs": [], "total": 0, "has_more": false}`))
	})
	defer srv.Close()

	jobs, total, _, err := client.ListJobs(context.Background(), ListJobsQuery{UserID: "bob"})
	if err != nil {
		t.Fatalf("ListJobs: %v", err)
	}
	if total != 0 {
		t.Errorf("total = %d, want 0", total)
	}
	if len(jobs) != 0 {
		t.Errorf("len(jobs) = %d, want 0", len(jobs))
	}
}

func TestListJobsNoFilters(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		if q.Get("limit") != "" {
			t.Errorf("limit should not be set, got %q", q.Get("limit"))
		}
		if q.Get("user_id") != "" {
			t.Errorf("user_id should not be set, got %q", q.Get("user_id"))
		}
		_, _ = w.Write([]byte(`{"jobs": [], "total": 0, "has_more": false}`))
	})
	defer srv.Close()
	_, _, _, err := client.ListJobs(context.Background(), ListJobsQuery{})
	if err != nil {
		t.Fatalf("ListJobs no-filters: %v", err)
	}
}

func TestListJobs500Error(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"detail": "database connection failed"}`))
	})
	defer srv.Close()

	_, _, _, err := client.ListJobs(context.Background(), ListJobsQuery{UserID: "alice"})
	if err == nil {
		t.Fatal("ListJobs should have errored on 500")
	}
	if !strings.Contains(err.Error(), "status 500") {
		t.Errorf("error = %q, should mention 'status 500'", err.Error())
	}
}

func TestGetJobSuccess(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasPrefix(r.URL.Path, "/jobs/") {
			t.Errorf("path = %q, want /jobs/*", r.URL.Path)
		}
		if !strings.HasSuffix(r.URL.Path, "abc-123") {
			t.Errorf("path should end with abc-123, got %q", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{
			"id": "abc-123",
			"user_id": "alice",
			"pipeline": "document",
			"status": "done",
			"progress": 1.0,
			"started_at": "2026-04-11T12:00:00Z"
		}`))
	})
	defer srv.Close()

	job, err := client.GetJob(context.Background(), "abc-123")
	if err != nil {
		t.Fatalf("GetJob: %v", err)
	}
	if job == nil {
		t.Fatal("job is nil")
	}
	if job.ID != "abc-123" {
		t.Errorf("ID = %q, want abc-123", job.ID)
	}
	if job.Status != "done" {
		t.Errorf("Status = %q, want done", job.Status)
	}
}

func TestGetJobNotFound(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"detail": "job not found"}`))
	})
	defer srv.Close()

	_, err := client.GetJob(context.Background(), "doesnt-exist")
	if !errors.Is(err, ErrJobNotFound) {
		t.Errorf("err = %v, want ErrJobNotFound", err)
	}
}

func TestHealthOK(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			t.Errorf("path = %q, want /health", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{"status": "ok"}`))
	})
	defer srv.Close()
	if err := client.Health(context.Background()); err != nil {
		t.Errorf("Health = %v, want nil", err)
	}
}

func TestHealthDown(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	})
	defer srv.Close()
	err := client.Health(context.Background())
	if err == nil {
		t.Error("Health should have errored on 503")
	}
}

func TestHealthUnreachable(t *testing.T) {
	// Point at a port that nothing is listening on (0 is invalid, use 1 which
	// is reserved and almost always unreachable on Windows + Linux).
	client := NewClient("http://127.0.0.1:1", 500*time.Millisecond)
	err := client.Health(context.Background())
	if err == nil {
		t.Error("Health on unreachable port should error")
	}
}

// TestTriggerDocument_404EmptyBodyIsNotImplemented verifies the review
// Small #3 refinement: an empty 404 body (FastAPI default route-not-found)
// maps to ErrPipelineNotImplemented.
func TestTriggerDocument_404EmptyBodyIsNotImplemented(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	})
	defer srv.Close()

	_, err := client.TriggerDocument(context.Background(), DocumentIngestRequest{
		FileID: "f1",
		UserID: "alice",
	})
	if !errors.Is(err, ErrPipelineNotImplemented) {
		t.Errorf("err = %v, want ErrPipelineNotImplemented", err)
	}
}

// TestTriggerDocument_404FastAPIDefaultIsNotImplemented — FastAPI's default
// missing-route body is `{"detail":"Not Found"}`.
func TestTriggerDocument_404FastAPIDefaultIsNotImplemented(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"detail":"Not Found"}`))
	})
	defer srv.Close()

	_, err := client.TriggerDocument(context.Background(), DocumentIngestRequest{
		FileID: "f1",
		UserID: "alice",
	})
	if !errors.Is(err, ErrPipelineNotImplemented) {
		t.Errorf("err = %v, want ErrPipelineNotImplemented", err)
	}
}

// TestTriggerDocument_404ResourceSpecificIsNotMapped — a 404 with a resource-
// specific detail message is NOT route-level, must surface as a real error.
func TestTriggerDocument_404ResourceSpecificIsNotMapped(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"detail":"artifact f1 not found in S3 bucket"}`))
	})
	defer srv.Close()

	_, err := client.TriggerDocument(context.Background(), DocumentIngestRequest{
		FileID: "f1",
		UserID: "alice",
	})
	if err == nil {
		t.Fatal("expected error")
	}
	if errors.Is(err, ErrPipelineNotImplemented) {
		t.Errorf("resource 404 should not map to ErrPipelineNotImplemented: %v", err)
	}
}

// TestTriggerDocument_501IsNotImplemented — Python may return 501 explicitly
// for stub routes; the client must honour that.
func TestTriggerDocument_501IsNotImplemented(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotImplemented)
	})
	defer srv.Close()

	_, err := client.TriggerDocument(context.Background(), DocumentIngestRequest{
		FileID: "f1",
		UserID: "alice",
	})
	if !errors.Is(err, ErrPipelineNotImplemented) {
		t.Errorf("501 should map to ErrPipelineNotImplemented, got %v", err)
	}
}

// TestTriggerDocument_Success decodes the IngestResponse from a 200 body.
func TestTriggerDocument_Success(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %q, want POST", r.Method)
		}
		if r.URL.Path != "/ingest/document" {
			t.Errorf("path = %q, want /ingest/document", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{"job_id":"job-42","status":"pending"}`))
	})
	defer srv.Close()

	out, err := client.TriggerDocument(context.Background(), DocumentIngestRequest{
		FileID: "f1",
		UserID: "alice",
	})
	if err != nil {
		t.Fatalf("TriggerDocument: %v", err)
	}
	if out.JobID != "job-42" {
		t.Errorf("JobID = %q, want job-42", out.JobID)
	}
}

// TestTriggerDocument_ValidationErrors verifies required-field checks.
func TestTriggerDocument_ValidationErrors(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		t.Error("should not reach server when validation fails")
	})
	defer srv.Close()

	// Missing file_id
	if _, err := client.TriggerDocument(context.Background(), DocumentIngestRequest{UserID: "alice"}); err == nil {
		t.Error("missing file_id should error")
	}
	// Missing user_id
	if _, err := client.TriggerDocument(context.Background(), DocumentIngestRequest{FileID: "f1"}); err == nil {
		t.Error("missing user_id should error")
	}
}

// TestReindex routes to /ingest/document/{id}/reindex
func TestReindex(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasSuffix(r.URL.Path, "/reindex") {
			t.Errorf("path %q should end with /reindex", r.URL.Path)
		}
		if !strings.Contains(r.URL.Path, "/ingest/document/art-1/") {
			t.Errorf("path %q should contain /ingest/document/art-1/", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{"job_id":"job-new","status":"pending"}`))
	})
	defer srv.Close()

	out, err := client.Reindex(context.Background(), "art-1", DocumentIngestRequest{
		FileID: "art-1",
		UserID: "alice",
	})
	if err != nil {
		t.Fatalf("Reindex: %v", err)
	}
	if out.JobID != "job-new" {
		t.Errorf("JobID = %q, want job-new", out.JobID)
	}
}

// TestCancelJobIdempotent verifies that cancelling a gone job returns nil.
func TestCancelJobIdempotent(t *testing.T) {
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	})
	defer srv.Close()

	if err := client.CancelJob(context.Background(), "gone-job"); err != nil {
		t.Errorf("CancelJob on missing job should return nil, got %v", err)
	}
}

// ─── Fix #8 Shared-secret auth ─────────────────────────────────────

// TestSharedSecretHeaderSent — when WithSharedSecret is set, all requests
// carry the X-Service-Auth header.
func TestSharedSecretHeaderSent(t *testing.T) {
	const secret = "test-secret-32-hex"
	var observed []string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		observed = append(observed, r.Header.Get(SharedSecretHeader))
		_, _ = w.Write([]byte(`{"jobs": [], "total": 0, "has_more": false}`))
	}))
	defer srv.Close()

	client := NewClient(srv.URL, 2*time.Second, WithSharedSecret(secret))

	// Exercise every exposed method that hits the wire
	_, _, _, _ = client.ListJobs(context.Background(), ListJobsQuery{UserID: "alice"})
	_, _ = client.GetJob(context.Background(), "job-1")
	_ = client.Health(context.Background())
	_, _ = client.TriggerDocument(context.Background(), DocumentIngestRequest{FileID: "f1", UserID: "alice"})
	_ = client.CancelJob(context.Background(), "job-1")

	if len(observed) != 5 {
		t.Fatalf("observed calls = %d, want 5", len(observed))
	}
	for i, got := range observed {
		if got != secret {
			t.Errorf("call %d: header = %q, want %q", i, got, secret)
		}
	}
}

// TestSharedSecretHeaderOmittedInDevMode — empty secret → no header.
func TestSharedSecretHeaderOmittedInDevMode(t *testing.T) {
	var observed []string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		observed = append(observed, r.Header.Get(SharedSecretHeader))
		_, _ = w.Write([]byte(`{"jobs": [], "total": 0, "has_more": false}`))
	}))
	defer srv.Close()

	client := NewClient(srv.URL, 2*time.Second) // no WithSharedSecret

	_, _, _, _ = client.ListJobs(context.Background(), ListJobsQuery{UserID: "alice"})

	if len(observed) != 1 {
		t.Fatalf("observed = %d, want 1", len(observed))
	}
	if observed[0] != "" {
		t.Errorf("header = %q, want empty (dev mode)", observed[0])
	}
}

func TestCancelJobSuccess(t *testing.T) {
	var called bool
	srv, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %q, want POST", r.Method)
		}
		called = true
		w.WriteHeader(http.StatusOK)
	})
	defer srv.Close()

	if err := client.CancelJob(context.Background(), "job-1"); err != nil {
		t.Errorf("CancelJob: %v", err)
	}
	if !called {
		t.Error("server handler not reached")
	}
}

func TestNilClient(t *testing.T) {
	var c *Client
	if _, _, _, err := c.ListJobs(context.Background(), ListJobsQuery{}); err == nil {
		t.Error("nil client ListJobs should error")
	}
	if _, err := c.GetJob(context.Background(), "x"); err == nil {
		t.Error("nil client GetJob should error")
	}
	if err := c.Health(context.Background()); err == nil {
		t.Error("nil client Health should error")
	}
}
