package http

import (
	"context"
	"io"
	"net/http"
)

type agentToolProxyClient interface {
	Get(ctx context.Context, path string) (status int, body []byte, err error)
}

type agentMutationProxyClient interface {
	Post(ctx context.Context, path string, body []byte) (status int, respBody []byte, err error)
}

// AgentToolProxyHandler forwards GET requests to the agent service tool endpoints.
func AgentToolProxyHandler(client agentToolProxyClient, upstreamPath string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", http.MethodGet)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		if client == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "agent tool proxy unavailable"})
			return
		}
		// #46 tier-2 bug: forward the incoming query-string so upstream
		// handlers receive thread_id / model / etc. Without this,
		// CompressionIndicator queried the proxy without context and
		// upstream defaulted to window=200000 (claude-opus-4-5) instead
		// of the real model's window.
		path := upstreamPath
		if r.URL.RawQuery != "" {
			path = path + "?" + r.URL.RawQuery
		}
		status, body, err := client.Get(r.Context(), path)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "agent tool request failed"})
			return
		}
		if status <= 0 {
			status = http.StatusOK
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		// #nosec G705 -- body comes from the trusted upstream agent-service
		// (operator-configured via AGENT_SERVICE_URL), Content-Type is
		// explicitly application/json so there is no XSS vector.
		_, _ = w.Write(body)
	}
}

// AgentMutationProxyHandler forwards POST mutation requests to the agent service.
func AgentMutationProxyHandler(client agentMutationProxyClient, upstreamPath string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		if client == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "agent mutation proxy unavailable"})
			return
		}
		const maxBody = 16 << 10 // 16 KB
		body, err := io.ReadAll(io.LimitReader(r.Body, maxBody+1))
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "read body failed"})
			return
		}
		if int64(len(body)) > maxBody {
			writeJSON(w, http.StatusRequestEntityTooLarge, map[string]string{"error": "body exceeds 16 KB"})
			return
		}
		status, respBody, err := client.Post(r.Context(), upstreamPath, body)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "agent mutation request failed"})
			return
		}
		if status <= 0 {
			status = http.StatusOK
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(respBody)
	}
}
