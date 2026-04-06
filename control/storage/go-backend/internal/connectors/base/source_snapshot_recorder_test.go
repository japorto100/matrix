package base

import (
	"bytes"
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"tradeviewfusion/go-backend/internal/storage"
)

func TestLocalSnapshotRecorderUsesConfiguredS3ObjectStore(t *testing.T) {
	var (
		mu      sync.Mutex
		buckets = map[string]map[string][]byte{}
	)

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := strings.TrimPrefix(r.URL.Path, "/")
		parts := strings.SplitN(path, "/", 2)
		if len(parts) == 0 || strings.TrimSpace(parts[0]) == "" {
			http.Error(w, "bucket required", http.StatusBadRequest)
			return
		}
		bucket := parts[0]
		key := ""
		if len(parts) == 2 {
			key = parts[1]
		}

		mu.Lock()
		defer mu.Unlock()

		switch r.Method {
		case http.MethodHead:
			if _, ok := buckets[bucket]; !ok {
				http.NotFound(w, r)
				return
			}
			w.WriteHeader(http.StatusOK)
		case http.MethodPut:
			if key == "" {
				if _, ok := buckets[bucket]; !ok {
					buckets[bucket] = map[string][]byte{}
				}
				w.WriteHeader(http.StatusOK)
				return
			}
			if _, ok := buckets[bucket]; !ok {
				http.NotFound(w, r)
				return
			}
			body, err := io.ReadAll(r.Body)
			if err != nil {
				t.Fatalf("read request body: %v", err)
			}
			buckets[bucket][key] = body
			w.WriteHeader(http.StatusOK)
		case http.MethodGet:
			bucketObjects, ok := buckets[bucket]
			if !ok {
				http.NotFound(w, r)
				return
			}
			body, ok := bucketObjects[key]
			if !ok {
				http.NotFound(w, r)
				return
			}
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write(body)
		default:
			http.Error(w, "unsupported method", http.StatusMethodNotAllowed)
		}
	}))
	t.Cleanup(server.Close)

	baseDir := t.TempDir()
	storePath := filepath.Join(baseDir, "state", "seco.json")
	t.Setenv("ARTIFACT_STORAGE_PROVIDER", "seaweedfs")
	t.Setenv("ARTIFACT_STORAGE_S3_ENDPOINT", server.URL)
	t.Setenv("ARTIFACT_STORAGE_S3_REGION", "us-east-1")
	t.Setenv("ARTIFACT_STORAGE_S3_BUCKET", "tradeview-artifacts")
	t.Setenv("ARTIFACT_STORAGE_S3_ACCESS_KEY_ID", "seaweedfs")
	t.Setenv("ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY", "seaweedfs-secret")
	t.Setenv("ARTIFACT_STORAGE_S3_USE_PATH_STYLE", "true")
	t.Setenv("ARTIFACT_STORAGE_S3_CREATE_BUCKET", "true")
	t.Setenv("ARTIFACT_STORAGE_BASE_DIR", filepath.Join(baseDir, "objects-not-used"))

	recorder := NewLocalSnapshotRecorder(storageAwareConfig(storePath))
	if recorder == nil {
		t.Fatal("expected recorder")
	}

	fetchedAt := time.Date(2026, time.March, 12, 11, 0, 0, 0, time.UTC)
	payload := []byte("<xml>hello</xml>")
	if err := recorder(context.Background(), FetchSnapshot{
		WatcherName:   "SECO_SANCTIONS",
		SourceURL:     "https://example.test/seco.xml",
		ContentType:   "application/xml",
		ContentLength: int64(len(payload)),
		SHA256Hex:     "abc123abc123abc123",
		FetchedAt:     fetchedAt,
		Payload:       payload,
	}); err != nil {
		t.Fatalf("record snapshot: %v", err)
	}

	// Per-source DB file: baseName is derived from storePath ("seco.json" → "seco"), so
	// the recorder writes to "seco_meta.db" (not the old shared "source_snapshots.db").
	metaStore, err := storage.NewSQLiteMetadataStore(filepath.Join(baseDir, "state", "source-snapshots", "seco_meta.db"))
	if err != nil {
		t.Fatalf("open metadata store: %v", err)
	}
	t.Cleanup(func() { _ = metaStore.Close() })

	snapshotID := LocalSnapshotID("seco", fetchedAt, "abc123abc123abc123")
	snapshot, err := metaStore.GetSourceSnapshot(snapshotID)
	if err != nil {
		t.Fatalf("get snapshot: %v", err)
	}
	if snapshot.ObjectKey == "" {
		t.Fatal("expected object key")
	}

	mu.Lock()
	stored := append([]byte(nil), buckets["tradeview-artifacts"][snapshot.ObjectKey]...)
	mu.Unlock()
	if !bytes.Equal(stored, payload) {
		t.Fatalf("stored payload mismatch: %q", string(stored))
	}
}

func storageAwareConfig(storePath string) LocalSnapshotRecorderConfig {
	return LocalSnapshotRecorderConfig{
		SourceID:      "seco",
		Subdir:        "seco",
		SourceClass:   "file-snapshot",
		FetchMode:     "conditional-poll",
		StorePath:     storePath,
		DatasetName:   "seco-sanctions",
		CadenceHint:   "daily",
		ParserVersion: "seco-sanctions-json-xml-v1",
	}
}
