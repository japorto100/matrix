package memory

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func newTestClient(handler http.HandlerFunc) (*httptest.Server, *Client) {
	srv := httptest.NewServer(handler)
	return srv, NewClient(srv.URL, 2*time.Second)
}

func TestPostKGSeedSuccess(t *testing.T) {
	var receivedBody string
	srv, client := newTestClient(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %q, want POST", r.Method)
		}
		if !strings.HasSuffix(r.URL.Path, "/kg/seed") {
			t.Errorf("path = %q", r.URL.Path)
		}
		b := make([]byte, 1024)
		n, _ := r.Body.Read(b)
		receivedBody = string(b[:n])
		_, _ = w.Write([]byte(`{"ok":true}`))
	})
	defer srv.Close()

	status, _, err := client.PostKGSeed(context.Background(), KGSeedRequest{Force: true})
	if err != nil {
		t.Fatalf("PostKGSeed: %v", err)
	}
	if status != 200 {
		t.Errorf("status = %d, want 200", status)
	}
	if !strings.Contains(receivedBody, `"force":true`) {
		t.Errorf("body = %q, want force:true", receivedBody)
	}
}

func TestPostKGQuerySuccess(t *testing.T) {
	srv, client := newTestClient(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"results": [{"id": "1", "text": "hi"}]}`))
	})
	defer srv.Close()

	status, body, err := client.PostKGQuery(context.Background(), KGQueryRequest{Query: "MATCH (n) RETURN n"})
	if err != nil {
		t.Fatalf("PostKGQuery: %v", err)
	}
	if status != 200 {
		t.Errorf("status = %d", status)
	}
	if !strings.Contains(string(body), "hi") {
		t.Errorf("body = %q", string(body))
	}
}

func TestGetKGNodesSuccess(t *testing.T) {
	srv, client := newTestClient(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			t.Errorf("method = %q, want GET", r.Method)
		}
		resp := KGNodesResponse{OK: true, Nodes: []map[string]any{{"id": "n1"}}, Total: 1}
		_ = json.NewEncoder(w).Encode(resp)
	})
	defer srv.Close()

	status, body, err := client.GetKGNodes(context.Background(), "")
	if err != nil {
		t.Fatalf("GetKGNodes: %v", err)
	}
	if status != 200 {
		t.Errorf("status = %d", status)
	}
	if !strings.Contains(string(body), "n1") {
		t.Errorf("body = %q", string(body))
	}
}

func TestDefaultBaseURL(t *testing.T) {
	c := NewClient("", 0)
	if c.baseURL != DefaultBaseURL {
		t.Errorf("baseURL = %q, want %q", c.baseURL, DefaultBaseURL)
	}
}

func TestURLTrailingSlashTrimmed(t *testing.T) {
	c := NewClient("http://localhost:8093/", 1*time.Second)
	if strings.HasSuffix(c.baseURL, "/") {
		t.Errorf("trailing slash not trimmed: %q", c.baseURL)
	}
}

func TestServerError(t *testing.T) {
	srv, client := newTestClient(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"error":"db down"}`))
	})
	defer srv.Close()

	status, _, err := client.PostKGSeed(context.Background(), KGSeedRequest{})
	if err != nil {
		t.Fatalf("PostKGSeed: %v (should return status, not error)", err)
	}
	if status != 500 {
		t.Errorf("status = %d, want 500", status)
	}
}
