package http

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

// AgentAudioTranscribeHandler proxies POST /api/v1/audio/transcribe → Python agent STT.
func AgentAudioTranscribeHandler(agentServiceBaseURL string) http.HandlerFunc {
	return agentAudioProxyHandler(agentServiceBaseURL, "/api/v1/audio/transcribe")
}

// AgentAudioSynthesizeHandler proxies POST /api/v1/audio/synthesize → Python agent TTS.
func AgentAudioSynthesizeHandler(agentServiceBaseURL string) http.HandlerFunc {
	return agentAudioProxyHandler(agentServiceBaseURL, "/api/v1/audio/synthesize")
}

func agentAudioProxyHandler(agentServiceBaseURL string, upstreamPath string) http.HandlerFunc {
	baseURL := strings.TrimRight(strings.TrimSpace(agentServiceBaseURL), "/")
	if baseURL == "" {
		baseURL = "http://127.0.0.1:8094"
	}
	upstreamURL := baseURL + upstreamPath

	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}

		const maxBodyBytes = 25 << 20 // 25 MB
		body, err := io.ReadAll(io.LimitReader(r.Body, maxBodyBytes+1))
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("read body: %v", err)})
			return
		}
		if int64(len(body)) > maxBodyBytes {
			writeJSON(w, http.StatusRequestEntityTooLarge, map[string]string{"error": "request body exceeds 25 MB limit"})
			return
		}
		if !json.Valid(body) {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "request body is not valid JSON"})
			return
		}

		upstreamReq, err := http.NewRequestWithContext(r.Context(), http.MethodPost, upstreamURL, bytes.NewReader(body))
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": fmt.Sprintf("build upstream request: %v", err)})
			return
		}
		upstreamReq.Header.Set("Content-Type", "application/json")

		resp, err := agentChatHTTPClient.Do(upstreamReq)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("agent audio service unreachable: %v", err)})
			return
		}
		defer resp.Body.Close()

		// Forward Content-Type (audio/mpeg for TTS, application/json for STT)
		ct := resp.Header.Get("Content-Type")
		if ct != "" {
			w.Header().Set("Content-Type", ct)
		}
		w.WriteHeader(resp.StatusCode)
		io.Copy(w, resp.Body)
	}
}
