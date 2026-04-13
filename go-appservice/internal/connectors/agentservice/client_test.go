package agentservice

import (
	"context"
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

func TestPostSuccess(t *testing.T) {
	srv, client := newTestClient(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %q, want POST", r.Method)
		}
		if r.Header.Get("Content-Type") != "application/json" {
			t.Errorf("Content-Type = %q", r.Header.Get("Content-Type"))
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"ok": true}`))
	})
	defer srv.Close()

	status, body, err := client.Post(context.Background(), "/test", []byte(`{"msg":"hi"}`))
	if err != nil {
		t.Fatalf("Post: %v", err)
	}
	if status != 200 {
		t.Errorf("status = %d, want 200", status)
	}
	if !strings.Contains(string(body), "ok") {
		t.Errorf("body = %q", string(body))
	}
}

func TestGetSuccess(t *testing.T) {
	srv, client := newTestClient(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			t.Errorf("method = %q, want GET", r.Method)
		}
		if r.URL.Path != "/health" {
			t.Errorf("path = %q", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})
	defer srv.Close()

	status, body, err := client.Get(context.Background(), "/health")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if status != 200 {
		t.Errorf("status = %d", status)
	}
	if !strings.Contains(string(body), "ok") {
		t.Errorf("body = %q", string(body))
	}
}

func TestDefaultBaseURL(t *testing.T) {
	c := NewClient("", 0)
	if c.baseURL != DefaultBaseURL {
		t.Errorf("baseURL = %q, want %q", c.baseURL, DefaultBaseURL)
	}
}

func TestNilClient(t *testing.T) {
	var c *Client
	if _, _, err := c.Post(context.Background(), "/x", nil); err == nil {
		t.Error("nil Post should error")
	}
	if _, _, err := c.Get(context.Background(), "/x"); err == nil {
		t.Error("nil Get should error")
	}
}

func TestURLNormalization(t *testing.T) {
	c := NewClient("http://localhost:8094/", 1*time.Second)
	if strings.HasSuffix(c.baseURL, "/") {
		t.Errorf("trailing slash not trimmed: %q", c.baseURL)
	}
}
