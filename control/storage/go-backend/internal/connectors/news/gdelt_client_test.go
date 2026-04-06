package news

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"tradeviewfusion/go-backend/internal/storage"
)

func TestGDELTClientFetchRecordsSnapshotMetadataAndRawPayload(t *testing.T) {
	payload := map[string]any{
		"articles": []map[string]any{
			{
				"title":    "Oil markets jump",
				"url":      "https://example.com/oil",
				"seendate": "20260312T111500Z",
			},
		},
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("ETag", `"gdelt-etag"`)
		w.Header().Set("Last-Modified", "Thu, 12 Mar 2026 11:00:00 GMT")
		_ = json.NewEncoder(w).Encode(payload)
	}))
	t.Cleanup(server.Close)

	tempDir := t.TempDir()
	storePath := filepath.Join(tempDir, "state", "gdelt-news.json")
	t.Setenv("ARTIFACT_STORAGE_PROVIDER", "filesystem")
	t.Setenv("ARTIFACT_STORAGE_BASE_DIR", filepath.Join(tempDir, "state"))

	client := NewGDELTClient(GDELTClientConfig{
		BaseURL:           server.URL,
		RequestTimeout:    2 * time.Second,
		RequestRetries:    0,
		SnapshotStorePath: storePath,
	})

	items, err := client.Fetch(context.Background(), "oil", 10)
	if err != nil {
		t.Fatalf("fetch: %v", err)
	}
	if len(items) != 1 {
		t.Fatalf("expected 1 headline, got %d", len(items))
	}

	rawFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "raw", "gdelt-news", "*.json"))
	if err != nil {
		t.Fatalf("glob raw files: %v", err)
	}
	if len(rawFiles) != 1 {
		t.Fatalf("expected 1 raw snapshot file, got %d", len(rawFiles))
	}
	normalizedFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "normalized", "gdelt-news", "*.json"))
	if err != nil {
		t.Fatalf("glob normalized files: %v", err)
	}
	if len(normalizedFiles) != 1 {
		t.Fatalf("expected 1 normalized snapshot file, got %d", len(normalizedFiles))
	}
	rawPayload, err := os.ReadFile(rawFiles[0])
	if err != nil {
		t.Fatalf("read raw snapshot: %v", err)
	}
	if len(rawPayload) == 0 {
		t.Fatal("expected raw payload")
	}
	normalizedPayload, err := os.ReadFile(normalizedFiles[0])
	if err != nil {
		t.Fatalf("read normalized snapshot: %v", err)
	}
	if len(normalizedPayload) == 0 {
		t.Fatal("expected normalized payload")
	}

	snapshotID := filepath.Base(rawFiles[0])
	snapshotID = snapshotID[:len(snapshotID)-len(filepath.Ext(snapshotID))]
	metaStore, err := storage.NewSQLiteMetadataStore(filepath.Join(tempDir, "state", "source-snapshots", "gdelt-news_meta.db"))
	if err != nil {
		t.Fatalf("open snapshot metadata store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := metaStore.Close(); closeErr != nil {
			t.Fatalf("close snapshot metadata store: %v", closeErr)
		}
	})

	snapshot, err := metaStore.GetSourceSnapshot(snapshotID)
	if err != nil {
		t.Fatalf("get source snapshot: %v", err)
	}
	if snapshot.SourceID != "gdelt-news" {
		t.Fatalf("source id = %q, want gdelt-news", snapshot.SourceID)
	}
	if snapshot.SourceClass != "api-snapshot" {
		t.Fatalf("source class = %q, want api-snapshot", snapshot.SourceClass)
	}
	if snapshot.DatasetName != "gdelt-news" {
		t.Fatalf("dataset name = %q, want gdelt-news", snapshot.DatasetName)
	}
	if snapshot.CadenceHint != "hourly" {
		t.Fatalf("cadence hint = %q, want hourly", snapshot.CadenceHint)
	}
	if snapshot.ParserVersion != "gdelt-news-normalized-v1" {
		t.Fatalf("parser version = %q", snapshot.ParserVersion)
	}
	if snapshot.SnapshotStatus != storage.SourceSnapshotNormalized {
		t.Fatalf("snapshot status = %q", snapshot.SnapshotStatus)
	}
	if snapshot.ObjectKey != filepath.ToSlash(filepath.Join("source-snapshots", "raw", "gdelt-news", filepath.Base(rawFiles[0]))) {
		t.Fatalf("object key = %q", snapshot.ObjectKey)
	}
}
