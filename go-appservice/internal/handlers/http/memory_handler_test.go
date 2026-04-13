package http

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"matrix/go-appservice/internal/connectors/memory"
)

func newMemoryTestClient(handler http.HandlerFunc) (*httptest.Server, *memory.Client) {
	srv := httptest.NewServer(handler)
	return srv, memory.NewClient(srv.URL, 2*time.Second)
}

func TestMemoryKGSeedHandler_Success(t *testing.T) {
	srv, client := newMemoryTestClient(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %q", r.Method)
		}
		_, _ = w.Write([]byte(`{"ok":true}`))
	})
	defer srv.Close()

	h := MemoryKGSeedHandler(client)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/memory/kg/seed",
		strings.NewReader(`{"force":true}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "ok") {
		t.Errorf("body = %q", rec.Body.String())
	}
}

func TestMemoryKGSeedHandler_MethodNotAllowed(t *testing.T) {
	srv, client := newMemoryTestClient(func(w http.ResponseWriter, r *http.Request) {})
	defer srv.Close()

	h := MemoryKGSeedHandler(client)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/memory/kg/seed", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestMemoryKGQueryHandler_Success(t *testing.T) {
	srv, client := newMemoryTestClient(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"results":[]}`))
	})
	defer srv.Close()

	h := MemoryKGQueryHandler(client)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/memory/kg/query",
		strings.NewReader(`{"query":"MATCH (n) RETURN n"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
}

func TestMemoryKGNodesHandler_Success(t *testing.T) {
	srv, client := newMemoryTestClient(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			t.Errorf("method = %q, want GET", r.Method)
		}
		_, _ = w.Write([]byte(`{"ok":true,"nodes":[],"total":0}`))
	})
	defer srv.Close()

	h := MemoryKGNodesHandler(client)
	req := httptest.NewRequest(http.MethodGet, "/api/v1/memory/kg/nodes", nil)
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
}

func TestMemorySearchHandler_Success(t *testing.T) {
	srv, client := newMemoryTestClient(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"results":[]}`))
	})
	defer srv.Close()

	h := MemorySearchHandler(client)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/memory/search",
		strings.NewReader(`{"query":"test","n_results":5}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
}
