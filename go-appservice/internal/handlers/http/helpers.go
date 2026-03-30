package http

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// writeJSON writes a JSON response with the given status code.
func writeJSON(w http.ResponseWriter, statusCode int, response any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(response)
}

// decodeJSONBody reads and decodes a JSON request body (max 1 MB).
func decodeJSONBody(r *http.Request, out any) error {
	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		return fmt.Errorf("read body: %w", err)
	}
	if len(body) == 0 {
		return nil
	}
	if err := json.Unmarshal(body, out); err != nil {
		return fmt.Errorf("decode json body: %w", err)
	}
	return nil
}

// clampInt returns value if within [min, max], otherwise fallback.
func clampInt(value, min, max, fallback int) int {
	if value < min || value > max {
		return fallback
	}
	return value
}
