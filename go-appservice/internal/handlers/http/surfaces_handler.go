package http

import (
	"bytes"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ── Agent Surfaces (A2UI widget persistence, plan-v2 Phase-2 #31) ──────────
//
// Backs the client-side usePersistentSurface hook. Stores A2UI widget-specs
// per (user_id, surface_id) in the agent.agent_surfaces table. Idempotent
// upsert on PUT, last-write-wins. No optimistic concurrency at this phase
// (single-user writes are infrequent; SSE live-updates #32 are a separate
// channel). Actor identity is carried in the X-Actor-User-Id header set by
// the BFF (frontend_merger) — go-appservice is the trust boundary, so the
// header is taken at face value here.

type surfaceBody struct {
	SchemaVersion int             `json:"schema_version"`
	SurfaceJSON   json.RawMessage `json:"surface_json"`
}

type surfaceResponse struct {
	SchemaVersion int             `json:"schema_version"`
	SurfaceJSON   json.RawMessage `json:"surface_json"`
	UpdatedAt     string          `json:"updated_at"`
}

// SurfacesHandler returns a single handler that dispatches GET/PUT/DELETE
// on /api/v1/surfaces/{id}. The {id} is everything after the final slash
// (surface-ids are opaque strings chosen by the client, not numeric).
func SurfacesHandler(pool *pgxpool.Pool) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if pool == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "postgres not configured"})
			return
		}

		surfaceID := strings.TrimPrefix(r.URL.Path, "/api/v1/surfaces/")
		if surfaceID == "" || strings.Contains(surfaceID, "/") {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "surface_id required"})
			return
		}

		userID := strings.TrimSpace(r.Header.Get("X-Actor-User-Id"))
		if userID == "" {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "X-Actor-User-Id required"})
			return
		}

		switch r.Method {
		case http.MethodGet:
			loadSurface(w, r, pool, userID, surfaceID)
		case http.MethodPut:
			saveSurface(w, r, pool, userID, surfaceID)
		case http.MethodDelete:
			deleteSurface(w, r, pool, userID, surfaceID)
		default:
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		}
	}
}

func loadSurface(w http.ResponseWriter, r *http.Request, pool *pgxpool.Pool, userID, surfaceID string) {
	const q = `
		SELECT schema_version, surface_json, updated_at
		FROM agent.agent_surfaces
		WHERE user_id = $1 AND surface_id = $2
	`
	var (
		schemaVersion int
		surfaceJSON   []byte
		updatedAt     time.Time
	)
	row := pool.QueryRow(r.Context(), q, userID, surfaceID)
	if err := row.Scan(&schemaVersion, &surfaceJSON, &updatedAt); err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "surface not found"})
			return
		}
		// #nosec G706 -- slog structured key-value args, not printf formatting; no log-injection.
		slog.Error("surfaces: load query failed", "user_id", userID, "surface_id", surfaceID, "error", err)
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "db query failed"})
		return
	}
	writeJSON(w, http.StatusOK, surfaceResponse{
		SchemaVersion: schemaVersion,
		SurfaceJSON:   json.RawMessage(surfaceJSON),
		UpdatedAt:     updatedAt.UTC().Format(time.RFC3339Nano),
	})
}

func saveSurface(w http.ResponseWriter, r *http.Request, pool *pgxpool.Pool, userID, surfaceID string) {
	var body surfaceBody
	if err := decodeJSONBody(r, &body); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid json body"})
		return
	}
	if body.SchemaVersion <= 0 {
		body.SchemaVersion = 1
	}
	// {"surface_json": null} serializes to 4 bytes ("null") and would
	// otherwise pass the len-check. Reject explicitly so the caller
	// sees 400 instead of a silently-lost surface (postgres accepts
	// null::jsonb, so the row would write but read back as null and
	// the hook would discard it).
	if len(body.SurfaceJSON) == 0 || bytes.Equal(bytes.TrimSpace(body.SurfaceJSON), []byte("null")) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "surface_json required"})
		return
	}

	const q = `
		INSERT INTO agent.agent_surfaces (user_id, surface_id, schema_version, surface_json, updated_at)
		VALUES ($1, $2, $3, $4::jsonb, now())
		ON CONFLICT (user_id, surface_id) DO UPDATE
			SET schema_version = EXCLUDED.schema_version,
			    surface_json   = EXCLUDED.surface_json,
			    updated_at     = now()
		RETURNING updated_at
	`
	var updatedAt time.Time
	row := pool.QueryRow(r.Context(), q, userID, surfaceID, body.SchemaVersion, string(body.SurfaceJSON))
	if err := row.Scan(&updatedAt); err != nil {
		// #nosec G706 -- slog structured key-value args, not printf formatting; no log-injection.
		slog.Error("surfaces: upsert failed", "user_id", userID, "surface_id", surfaceID, "error", err)
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "db upsert failed"})
		return
	}
	writeJSON(w, http.StatusOK, surfaceResponse{
		SchemaVersion: body.SchemaVersion,
		SurfaceJSON:   body.SurfaceJSON,
		UpdatedAt:     updatedAt.UTC().Format(time.RFC3339Nano),
	})
}

func deleteSurface(w http.ResponseWriter, r *http.Request, pool *pgxpool.Pool, userID, surfaceID string) {
	const q = `DELETE FROM agent.agent_surfaces WHERE user_id = $1 AND surface_id = $2`
	tag, err := pool.Exec(r.Context(), q, userID, surfaceID)
	if err != nil {
		// #nosec G706 -- slog structured key-value args, not printf formatting; no log-injection.
		slog.Error("surfaces: delete failed", "user_id", userID, "surface_id", surfaceID, "error", err)
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "db delete failed"})
		return
	}
	if tag.RowsAffected() == 0 {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "surface not found"})
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
