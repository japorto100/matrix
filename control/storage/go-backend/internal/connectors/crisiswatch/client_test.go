package crisiswatch

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"sync/atomic"
	"testing"
	"time"

	"tradeviewfusion/go-backend/internal/storage"
)

func TestClientList_ParsesRSSItems(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/rss+xml")
		_, _ = w.Write([]byte(`<?xml version="1.0" encoding="UTF-8"?>
			<rss version="2.0">
				<channel>
					<item>
						<guid>cw-1</guid>
						<title>Ukraine monthly update</title>
						<link>https://example.org/cw-1</link>
						<description>Conflict trends in Europe.</description>
						<pubDate>Mon, 15 Feb 2026 12:00:00 +0000</pubDate>
					</item>
					<item>
						<guid>cw-2</guid>
						<title>Sahel security update</title>
						<link>https://example.org/cw-2</link>
						<description>Armed activity remains elevated.</description>
						<pubDate>Mon, 10 Feb 2026 12:00:00 +0000</pubDate>
					</item>
				</channel>
			</rss>`))
	}))
	defer server.Close()

	client := NewClient(Config{RSSURL: server.URL})
	items, err := client.List(context.Background(), 10, "", "")
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if len(items) != 2 {
		t.Fatalf("expected 2 items, got %d", len(items))
	}
	if items[0].ID != "cw-1" {
		t.Fatalf("expected id cw-1, got %q", items[0].ID)
	}
	if items[0].Region != "Europe" {
		t.Fatalf("expected inferred region Europe, got %q", items[0].Region)
	}
	if items[0].PublishedAt == "" {
		t.Fatal("expected publishedAt")
	}
}

func TestClientList_AppliesQueryAndRegionFilters(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/rss+xml")
		_, _ = w.Write([]byte(`<?xml version="1.0" encoding="UTF-8"?>
			<rss version="2.0">
				<channel>
					<item>
						<title>Ukraine monthly update</title>
						<link>https://example.org/ua</link>
						<description>Europe conflict digest.</description>
					</item>
					<item>
						<title>Sahel security update</title>
						<link>https://example.org/sahel</link>
						<description>Africa conflict digest.</description>
					</item>
				</channel>
			</rss>`))
	}))
	defer server.Close()

	client := NewClient(Config{RSSURL: server.URL})
	items, err := client.List(context.Background(), 10, "africa", "security")
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if len(items) != 1 {
		t.Fatalf("expected 1 item, got %d", len(items))
	}
	if items[0].URL != "https://example.org/sahel" {
		t.Fatalf("unexpected item url %q", items[0].URL)
	}
}

func TestClientList_MapsUpstreamStatus(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer server.Close()

	client := NewClient(Config{RSSURL: server.URL})
	_, err := client.List(context.Background(), 10, "", "")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestClientList_UsesTTLCache(t *testing.T) {
	t.Parallel()

	var calls int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		atomic.AddInt32(&calls, 1)
		w.Header().Set("Content-Type", "application/rss+xml")
		_, _ = w.Write([]byte(`<?xml version="1.0" encoding="UTF-8"?>
			<rss version="2.0">
				<channel>
					<item>
						<title>Cached item</title>
						<link>https://example.org/cache</link>
						<description>Europe digest.</description>
					</item>
				</channel>
			</rss>`))
	}))
	defer server.Close()

	client := NewClient(Config{
		RSSURL:   server.URL,
		CacheTTL: time.Hour,
	})

	if _, err := client.List(context.Background(), 10, "", ""); err != nil {
		t.Fatalf("first call failed: %v", err)
	}
	if _, err := client.List(context.Background(), 10, "", ""); err != nil {
		t.Fatalf("second call failed: %v", err)
	}

	if got := atomic.LoadInt32(&calls); got != 1 {
		t.Fatalf("expected 1 upstream call, got %d", got)
	}
}

func TestClientList_LoadsPersistedCache(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	cachePath := filepath.Join(dir, "crisiswatch-cache.json")

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/rss+xml")
		_, _ = w.Write([]byte(`<?xml version="1.0" encoding="UTF-8"?>
			<rss version="2.0">
				<channel>
					<item>
						<guid>persisted-1</guid>
						<title>Persisted item</title>
						<link>https://example.org/persisted</link>
						<description>Europe digest.</description>
					</item>
				</channel>
			</rss>`))
	}))
	client := NewClient(Config{
		RSSURL:      server.URL,
		CacheTTL:    time.Hour,
		PersistPath: cachePath,
	})
	if _, err := client.List(context.Background(), 10, "", ""); err != nil {
		server.Close()
		t.Fatalf("seed call failed: %v", err)
	}
	server.Close()

	clientFromDisk := NewClient(Config{
		RSSURL:      "http://127.0.0.1:0",
		CacheTTL:    time.Hour,
		PersistPath: cachePath,
	})
	items, err := clientFromDisk.List(context.Background(), 10, "", "")
	if err != nil {
		t.Fatalf("expected persisted fallback, got %v", err)
	}
	if len(items) != 1 {
		t.Fatalf("expected 1 persisted item, got %d", len(items))
	}
	if items[0].ID != "persisted-1" {
		t.Fatalf("unexpected persisted id %q", items[0].ID)
	}
}

func TestClientList_RecordsSnapshotMetadataAndRawPayload(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/rss+xml")
		w.Header().Set("ETag", `"crisiswatch-etag"`)
		w.Header().Set("Last-Modified", "Thu, 12 Mar 2026 11:00:00 GMT")
		_, _ = w.Write([]byte(`<?xml version="1.0" encoding="UTF-8"?>
			<rss version="2.0">
				<channel>
					<item>
						<guid>snapshot-1</guid>
						<title>Middle East monthly update</title>
						<link>https://example.org/snapshot-1</link>
						<description>Regional conflict digest.</description>
						<pubDate>Thu, 12 Mar 2026 11:15:00 +0000</pubDate>
					</item>
				</channel>
			</rss>`))
	}))
	defer server.Close()

	tempDir := t.TempDir()
	t.Setenv("ARTIFACT_STORAGE_PROVIDER", "filesystem")
	t.Setenv("ARTIFACT_STORAGE_BASE_DIR", filepath.Join(tempDir, "state"))

	client := NewClient(Config{
		RSSURL:            server.URL,
		CacheTTL:          time.Hour,
		SnapshotStorePath: filepath.Join(tempDir, "state", "crisiswatch.json"),
	})

	items, err := client.List(context.Background(), 10, "", "")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(items) != 1 {
		t.Fatalf("expected 1 item, got %d", len(items))
	}

	rawFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "raw", "crisiswatch", "*.xml"))
	if err != nil {
		t.Fatalf("glob raw files: %v", err)
	}
	if len(rawFiles) != 1 {
		t.Fatalf("expected 1 raw snapshot file, got %d", len(rawFiles))
	}
	normalizedFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "normalized", "crisiswatch", "*.json"))
	if err != nil {
		t.Fatalf("glob normalized files: %v", err)
	}
	if len(normalizedFiles) != 1 {
		t.Fatalf("expected 1 normalized snapshot file, got %d", len(normalizedFiles))
	}
	if rawPayload, readErr := os.ReadFile(rawFiles[0]); readErr != nil || len(rawPayload) == 0 {
		t.Fatalf("read raw payload: %v", readErr)
	}
	if normalizedPayload, readErr := os.ReadFile(normalizedFiles[0]); readErr != nil || len(normalizedPayload) == 0 {
		t.Fatalf("read normalized payload: %v", readErr)
	}

	snapshotID := filepath.Base(rawFiles[0])
	snapshotID = snapshotID[:len(snapshotID)-len(filepath.Ext(snapshotID))]
	metaStore, err := storage.NewSQLiteMetadataStore(filepath.Join(tempDir, "state", "source-snapshots", "crisiswatch_meta.db"))
	if err != nil {
		t.Fatalf("open metadata store: %v", err)
	}
	t.Cleanup(func() {
		_ = metaStore.Close()
	})

	snapshot, err := metaStore.GetSourceSnapshot(snapshotID)
	if err != nil {
		t.Fatalf("get snapshot: %v", err)
	}
	if snapshot.SourceID != "crisiswatch" {
		t.Fatalf("source id = %q", snapshot.SourceID)
	}
	if snapshot.SourceClass != "api-snapshot" {
		t.Fatalf("source class = %q", snapshot.SourceClass)
	}
	if snapshot.DatasetName != "crisiswatch-rss" {
		t.Fatalf("dataset name = %q", snapshot.DatasetName)
	}
	if snapshot.ParserVersion != "crisiswatch-normalized-v1" {
		t.Fatalf("parser version = %q", snapshot.ParserVersion)
	}
	if snapshot.SnapshotStatus != storage.SourceSnapshotNormalized {
		t.Fatalf("snapshot status = %q", snapshot.SnapshotStatus)
	}
}
