package http

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"matrix/go-appservice/internal/connectors/memory"
)

// ── KG Handlers ──────────────────────────────────────────────────────────────

func MemoryKGSeedHandler(client *memory.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		var req memory.KGSeedRequest
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("invalid request: %v", err)})
			return
		}
		status, body, err := client.PostKGSeed(r.Context(), req)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("kg seed failed: %v", err)})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

func MemoryKGQueryHandler(client *memory.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		var req memory.KGQueryRequest
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("invalid request: %v", err)})
			return
		}
		status, body, err := client.PostKGQuery(r.Context(), req)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("kg query failed: %v", err)})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

func MemoryKGNodesHandler(client *memory.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		nodeType := r.URL.Query().Get("type")
		status, body, err := client.GetKGNodes(r.Context(), nodeType)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("kg nodes failed: %v", err)})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

func MemoryKGSyncHandler(client *memory.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		status, body, err := client.GetKGSync(r.Context())
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("kg sync failed: %v", err)})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

// ── Episode Handlers ─────────────────────────────────────────────────────────

func MemoryEpisodePostHandler(client *memory.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		var req memory.EpisodeCreateRequest
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("invalid request: %v", err)})
			return
		}
		status, body, err := client.PostEpisode(r.Context(), req)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("episode create failed: %v", err)})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

func MemoryEpisodesGetHandler(client *memory.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		role := r.URL.Query().Get("role")
		limitStr := r.URL.Query().Get("limit")
		limit := 20
		if l, err := strconv.Atoi(limitStr); err == nil {
			limit = clampInt(l, 1, 100, 20)
		}
		status, body, err := client.GetEpisodes(r.Context(), role, limit)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("episodes get failed: %v", err)})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

// ── Vector Search Handler ────────────────────────────────────────────────────

func MemorySearchHandler(client *memory.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
			return
		}
		var req memory.VectorSearchRequest
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": fmt.Sprintf("invalid request: %v", err)})
			return
		}
		status, body, err := client.PostSearch(r.Context(), req)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": fmt.Sprintf("search failed: %v", err)})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

// ── Health Handler ───────────────────────────────────────────────────────────

func MemoryHealthHandler(client *memory.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		status, body, err := client.GetHealth(r.Context())
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "memory service unreachable"})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write(body)
	}
}

// suppress unused import warning
var _ = json.Marshal
