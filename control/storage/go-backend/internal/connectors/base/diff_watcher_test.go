package base

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestDiffWatcherCheckForUpdatesCallsOnFetched(t *testing.T) {
	t.Parallel()

	payload := []byte(`[{"id":"row-1","name":"Row 1"}]`)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("ETag", `"etag-1"`)
		w.Header().Set("Last-Modified", "Thu, 12 Mar 2026 10:00:00 GMT")
		_, _ = w.Write(payload)
	}))
	t.Cleanup(server.Close)

	fetchedAt := time.Date(2026, time.March, 12, 10, 30, 0, 0, time.UTC)
	var snapshot FetchSnapshot
	watcher := NewDiffWatcher(DiffWatcherConfig{
		Name:    "TEST_WATCHER",
		URL:     server.URL,
		IDField: "id",
		ParseFunc: func(r io.Reader) ([]map[string]any, error) {
			return []map[string]any{{"id": "row-1", "name": "Row 1"}}, nil
		},
		OnFetched: func(_ context.Context, fetched FetchSnapshot) error {
			snapshot = fetched
			return nil
		},
		HTTPClient: server.Client(),
		NowFunc:    func() time.Time { return fetchedAt },
	})

	result, err := watcher.CheckForUpdates(context.Background())
	if err != nil {
		t.Fatalf("check for updates: %v", err)
	}
	if result == nil {
		t.Fatal("expected diff result")
	}
	if len(result.Added) != 1 {
		t.Fatalf("expected 1 added item, got %d", len(result.Added))
	}

	sum := sha256.Sum256(payload)
	if snapshot.WatcherName != "TEST_WATCHER" {
		t.Fatalf("watcher name = %q, want TEST_WATCHER", snapshot.WatcherName)
	}
	if snapshot.SourceURL != server.URL {
		t.Fatalf("source url = %q, want %q", snapshot.SourceURL, server.URL)
	}
	if snapshot.ContentType != "application/json" {
		t.Fatalf("content type = %q, want application/json", snapshot.ContentType)
	}
	if snapshot.ContentLength != int64(len(payload)) {
		t.Fatalf("content length = %d, want %d", snapshot.ContentLength, len(payload))
	}
	if snapshot.ETag != `"etag-1"` {
		t.Fatalf("etag = %q, want %q", snapshot.ETag, `"etag-1"`)
	}
	if snapshot.LastModified != "Thu, 12 Mar 2026 10:00:00 GMT" {
		t.Fatalf("last modified = %q", snapshot.LastModified)
	}
	if snapshot.SHA256Hex != hex.EncodeToString(sum[:]) {
		t.Fatalf("sha256 = %q, want %q", snapshot.SHA256Hex, hex.EncodeToString(sum[:]))
	}
	if !snapshot.FetchedAt.Equal(fetchedAt) {
		t.Fatalf("fetched at = %s, want %s", snapshot.FetchedAt, fetchedAt)
	}
	if string(snapshot.Payload) != string(payload) {
		t.Fatalf("payload = %q, want %q", string(snapshot.Payload), string(payload))
	}
}
