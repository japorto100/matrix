package http

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// defaultChatHTTPClient is used when no custom client is injected. 5 min
// timeout because LLM streams can run for minutes.
var defaultChatHTTPClient = &http.Client{
	Timeout: 5 * time.Minute,
}

type agentAttachment struct {
	Base64   string `json:"base64"`
	MimeType string `json:"mime_type"`
	Name     string `json:"name"`
}

type browserToolDef struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"input_schema"`
}

type agentChatRequestBody struct {
	Message         string            `json:"message"`
	ThreadID        string            `json:"threadId,omitempty"`
	AgentID         string            `json:"agentId,omitempty"`
	Context         string            `json:"context,omitempty"`
	Model           string            `json:"model,omitempty"`
	Attachments     []agentAttachment `json:"attachments,omitempty"`
	ReasoningEffort string            `json:"reasoningEffort,omitempty"`
	BrowserTools    []browserToolDef  `json:"browserTools,omitempty"`
}

type agentApproveRequest struct {
	ToolCallID string `json:"toolCallId"`
	Decision   string `json:"decision"`
	ThreadID   string `json:"threadId"`
}

// AgentChatHandler proxies SSE streaming chat to the Python agent service.
// Sets Vercel AI Data Stream Protocol headers for ai SDK v6 compatibility.
// Phase 4 Fix C: optional httpClient parameter for testability.
func AgentChatHandler(agentServiceBaseURL string, httpClient ...*http.Client) http.HandlerFunc {
	baseURL := strings.TrimRight(strings.TrimSpace(agentServiceBaseURL), "/")
	if baseURL == "" {
		baseURL = "http://127.0.0.1:8094"
	}
	upstreamURL := baseURL + "/api/v1/agent/chat"
	client := defaultChatHTTPClient
	if len(httpClient) > 0 && httpClient[0] != nil {
		client = httpClient[0]
	}

	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}

		var req agentChatRequestBody
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("invalid request: %v", err)})
			return
		}
		if strings.TrimSpace(req.Message) == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "message is required"})
			return
		}

		// Re-encode for upstream
		upstreamBody, err := json.Marshal(req)
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "encode failed"})
			return
		}

		upstreamReq, err := http.NewRequestWithContext(r.Context(), http.MethodPost, upstreamURL, bytes.NewReader(upstreamBody))
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": fmt.Sprintf("build upstream request: %v", err)})
			return
		}
		upstreamReq.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(upstreamReq)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("agent service unreachable: %v", err)})
			return
		}
		defer func() { _ = resp.Body.Close() }()

		// Phase 4 Fix A: check upstream status BEFORE setting SSE headers.
		// If upstream returned an error (non-2xx), forward it as a regular
		// JSON error response instead of starting an SSE stream that would
		// mislead the client into thinking the connection is healthy.
		if resp.StatusCode >= 400 {
			body, _ := io.ReadAll(resp.Body)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(resp.StatusCode)
			_, _ = w.Write(body)
			return
		}

		// Vercel AI Data Stream Protocol — ai SDK v6 parst diesen Header
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")
		w.Header().Set("X-Vercel-AI-UI-Message-Stream", "v1")

		flusher, ok := w.(http.Flusher)
		if !ok {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "streaming not supported"})
			return
		}

		// Stream response chunk-by-chunk
		buf := make([]byte, 4096)
		for {
			n, readErr := resp.Body.Read(buf)
			if n > 0 {
				_, writeErr := w.Write(buf[:n])
				if writeErr != nil {
					return
				}
				flusher.Flush()
			}
			if readErr != nil {
				if readErr != io.EOF {
					_, _ = fmt.Fprintf(w, "event: error\ndata: {\"errorText\": \"stream interrupted\"}\n\n")
					flusher.Flush()
				}
				return
			}
		}
	}
}

// AgentApproveHandler handles POST /api/v1/agent/approve.
func AgentApproveHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		var req agentApproveRequest
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("invalid request: %v", err)})
			return
		}
		if req.ToolCallID == "" || (req.Decision != "approve" && req.Decision != "deny") {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "toolCallId and decision (approve|deny) required"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"ok": true, "toolCallId": req.ToolCallID, "decision": req.Decision})
	}
}
