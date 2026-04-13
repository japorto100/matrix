package http

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAgentChatHandler_MethodNotAllowed(t *testing.T) {
	h := AgentChatHandler("http://localhost:9999")
	req := httptest.NewRequest(http.MethodGet, "/api/v1/agent/chat", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestAgentChatHandler_ProxiesSSEStream(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("upstream method = %q", r.Method)
		}
		ct := r.Header.Get("Content-Type")
		if ct != "application/json" {
			t.Errorf("Content-Type = %q", ct)
		}
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("data: {\"text\":\"hello\"}\n\n"))
	}))
	defer upstream.Close()

	h := AgentChatHandler(upstream.URL)
	body := `{"message":"hi","threadId":"t1"}`
	req := httptest.NewRequest(http.MethodPost, "/api/v1/agent/chat",
		strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if rec.Header().Get("Content-Type") != "text/event-stream" {
		t.Errorf("Content-Type = %q, want text/event-stream", rec.Header().Get("Content-Type"))
	}
	if !strings.Contains(rec.Body.String(), "hello") {
		t.Errorf("body = %q", rec.Body.String())
	}
}

func TestAgentChatHandler_InvalidJSON(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("upstream should not be called for invalid JSON")
	}))
	defer upstream.Close()

	h := AgentChatHandler(upstream.URL)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/agent/chat",
		strings.NewReader("not json"))
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", rec.Code)
	}
}

func TestAgentChatHandler_UpstreamError(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte(`{"error":"model overloaded"}`))
	}))
	defer upstream.Close()

	h := AgentChatHandler(upstream.URL)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/agent/chat",
		strings.NewReader(`{"message":"hi"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)
	// Phase 4 Fix A: upstream 500 is now forwarded as-is (not masked by SSE 200)
	if rec.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500 (forwarded from upstream after Fix A)", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "model overloaded") {
		t.Errorf("body should contain error: %q", rec.Body.String())
	}
}

func TestAgentApproveHandler_MethodNotAllowed(t *testing.T) {
	h := AgentApproveHandler()
	req := httptest.NewRequest(http.MethodGet, "/api/v1/agent/approve", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestAgentChatHandler_ForwardsRequestBody(t *testing.T) {
	var receivedBody string
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		receivedBody = string(b)
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: ok\n\n"))
	}))
	defer upstream.Close()

	h := AgentChatHandler(upstream.URL)
	body := `{"message":"test","model":"openrouter/anthropic/claude-sonnet-4-6","reasoningEffort":"high"}`
	req := httptest.NewRequest(http.MethodPost, "/api/v1/agent/chat", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)

	if !strings.Contains(receivedBody, "reasoningEffort") {
		t.Errorf("upstream body should contain reasoningEffort: %q", receivedBody)
	}
	if !strings.Contains(receivedBody, "claude-sonnet") {
		t.Errorf("upstream body should contain model: %q", receivedBody)
	}
}
