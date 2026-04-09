package http

import (
	"io"
	"net/http"
	"strings"
)

// ControlProxyHandler reverse-proxies all /api/v1/control/* requests to the
// Python Agent Service (:8094).
//
// Pattern 1:1 identical to McpProxyHandler. Python agent exposes the full
// /api/v1/control/* route space via agent/control/router.py (54 routes across
// memory, episodes, kg, agents, permissions, skills, tools, sandbox, system,
// audit, sessions, mcp, a2a, overview, security, models).
//
// Slice 7: tutto kompletto frontend+backend wiring.
func ControlProxyHandler(agentBaseURL string) http.HandlerFunc {
	upstream := strings.TrimRight(agentBaseURL, "/")

	return func(w http.ResponseWriter, r *http.Request) {
		// Forward path + query string 1:1
		targetURL := upstream + r.URL.Path
		if r.URL.RawQuery != "" {
			targetURL += "?" + r.URL.RawQuery
		}

		upstreamReq, err := http.NewRequestWithContext(r.Context(), r.Method, targetURL, r.Body)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{
				"error": "control proxy: create request failed",
			})
			return
		}

		// Forward headers (except Host, set by http.Client automatically)
		for key, vals := range r.Header {
			if strings.EqualFold(key, "Host") {
				continue
			}
			for _, v := range vals {
				upstreamReq.Header.Add(key, v)
			}
		}

		resp, err := http.DefaultClient.Do(upstreamReq)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{
				"error": "python agent service unreachable: " + err.Error(),
			})
			return
		}
		defer func() { _ = resp.Body.Close() }()

		// Forward response headers
		for key, vals := range resp.Header {
			for _, v := range vals {
				w.Header().Add(key, v)
			}
		}
		w.WriteHeader(resp.StatusCode)
		_, _ = io.Copy(w, resp.Body)
	}
}
