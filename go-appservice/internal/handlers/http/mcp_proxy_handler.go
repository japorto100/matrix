package http

import (
	"io"
	"net/http"
	"strings"
)

// McpProxyHandler reverse-proxies MCP Streamable HTTP requests to the Python MCP Server.
// Alle Requests unter /api/v1/mcp/ werden 1:1 an den upstream MCP Server weitergeleitet.
func McpProxyHandler(mcpBaseURL string) http.HandlerFunc {
	upstream := strings.TrimRight(mcpBaseURL, "/")

	return func(w http.ResponseWriter, r *http.Request) {
		// MCP Streamable HTTP: POST /mcp (messages), GET /mcp/sse (SSE stream)
		// Pfad nach /api/v1/mcp wird an upstream weitergeleitet
		mcpPath := strings.TrimPrefix(r.URL.Path, "/api/v1/mcp")
		if mcpPath == "" {
			mcpPath = "/"
		}
		targetURL := upstream + "/mcp" + mcpPath
		if r.URL.RawQuery != "" {
			targetURL += "?" + r.URL.RawQuery
		}

		// #nosec G107,G704 -- upstream is operator-configured (MCP_SERVICE_URL), not user-controlled;
		// only path/query forwarded, normalized by net/http before proxying.
		upstreamReq, err := http.NewRequestWithContext(r.Context(), r.Method, targetURL, r.Body)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "mcp proxy: create request failed"})
			return
		}

		// Headers durchreichen (Content-Type, Accept, etc.)
		for key, vals := range r.Header {
			for _, v := range vals {
				upstreamReq.Header.Add(key, v)
			}
		}

		// upstream bound to operator-configured MCP_SERVICE_URL, not user input.
		resp, err := http.DefaultClient.Do(upstreamReq) //nolint:gosec // trusted upstream
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "mcp server unreachable"})
			return
		}
		defer func() { _ = resp.Body.Close() }()

		// Response Headers durchreichen
		for key, vals := range resp.Header {
			for _, v := range vals {
				w.Header().Add(key, v)
			}
		}
		w.WriteHeader(resp.StatusCode)
		_, _ = io.Copy(w, resp.Body)
	}
}
