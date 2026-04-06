package app

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

func TestNewServerFromEnv_WiresArtifactRoutes(t *testing.T) {
	baseDir := t.TempDir()

	t.Setenv("ARTIFACT_STORAGE_METADATA_DB_PATH", filepath.Join(baseDir, "artifacts.db"))
	t.Setenv("ARTIFACT_STORAGE_BASE_DIR", filepath.Join(baseDir, "objects"))
	t.Setenv("ARTIFACT_STORAGE_SIGNING_SECRET", "test-artifact-secret")
	t.Setenv("GCT_AUDIT_DB_ENABLED", "false")
	t.Setenv("AUTH_JWT_REVOCATION_AUDIT_DB_ENABLED", "false")

	server, err := NewServerFromEnv()
	if err != nil {
		t.Fatalf("new server from env: %v", err)
	}
	t.Cleanup(func() {
		if err := server.Close(); err != nil {
			t.Fatalf("close server resources: %v", err)
		}
	})

	req := httptest.NewRequest(http.MethodPost, "/api/v1/storage/artifacts/upload-url", bytes.NewBufferString(`{
		"filename":"report.pdf",
		"contentType":"application/pdf",
		"retentionClass":"analysis"
	}`))
	rec := httptest.NewRecorder()
	server.handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want %d, body=%s", rec.Code, http.StatusCreated, rec.Body.String())
	}

	var payload struct {
		Success bool `json:"success"`
		Data    struct {
			Artifact struct {
				ID string `json:"id"`
			} `json:"artifact"`
			Upload struct {
				Method string `json:"method"`
				URL    string `json:"url"`
			} `json:"upload"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if !payload.Success {
		t.Fatal("expected success response")
	}
	if payload.Data.Artifact.ID == "" {
		t.Fatal("expected artifact id")
	}
	if payload.Data.Upload.Method != http.MethodPut {
		t.Fatalf("upload method = %q, want PUT", payload.Data.Upload.Method)
	}
	if payload.Data.Upload.URL == "" {
		t.Fatal("expected signed upload url")
	}
}
