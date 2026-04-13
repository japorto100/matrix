package http

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestAgentAudioTranscribeHandler_ProxiesSuccess(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("upstream method = %q, want POST", r.Method)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"text":"hello world"}`))
	}))
	defer upstream.Close()

	h := AgentAudioTranscribeHandler(upstream.URL)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/audio/transcribe",
		strings.NewReader(`{"audio_base64":"dGVzdA==","mime_type":"audio/webm"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "hello world") {
		t.Errorf("body = %q", rec.Body.String())
	}
}

func TestAgentAudioSynthesizeHandler_ProxiesAudioResponse(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "audio/mpeg")
		_, _ = w.Write([]byte("fake-mp3-bytes"))
	}))
	defer upstream.Close()

	h := AgentAudioSynthesizeHandler(upstream.URL)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/audio/synthesize",
		strings.NewReader(`{"text":"hello","voice":"alloy"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h(rec, req)

	if rec.Code != 200 {
		t.Errorf("status = %d", rec.Code)
	}
	if rec.Header().Get("Content-Type") != "audio/mpeg" {
		t.Errorf("Content-Type = %q, want audio/mpeg", rec.Header().Get("Content-Type"))
	}
}

func TestAgentAudioHandler_MethodNotAllowed(t *testing.T) {
	h := AgentAudioTranscribeHandler("http://localhost:9999")
	req := httptest.NewRequest(http.MethodGet, "/api/v1/audio/transcribe", nil)
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestAgentAudioHandler_InvalidJSON(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("upstream should not be called for invalid JSON")
	}))
	defer upstream.Close()

	h := AgentAudioTranscribeHandler(upstream.URL)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/audio/transcribe",
		strings.NewReader("not json"))
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", rec.Code)
	}
}

func TestAgentAudioHandler_BodyTooLarge(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("should not be called")
	}))
	defer upstream.Close()

	h := AgentAudioTranscribeHandler(upstream.URL)
	bigBody := `{"audio_base64":"` + strings.Repeat("A", 26<<20) + `"}`
	req := httptest.NewRequest(http.MethodPost, "/api/v1/audio/transcribe",
		strings.NewReader(bigBody))
	rec := httptest.NewRecorder()
	h(rec, req)
	if rec.Code != http.StatusRequestEntityTooLarge {
		t.Errorf("status = %d, want 413", rec.Code)
	}
}
