package acled

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"tradeviewfusion/go-backend/internal/connectors/gct"
	"tradeviewfusion/go-backend/internal/storage"
)

func TestClientFetchEvents_WithBearerToken(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/acled/read" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if got := r.Header.Get("Authorization"); got != "Bearer token-123" {
			t.Fatalf("expected bearer token auth, got: %q", got)
		}
		query := r.URL.Query()
		if query.Get("_format") != "json" {
			t.Fatalf("expected _format=json, got %q", query.Get("_format"))
		}
		if query.Get("country") != "Ukraine" {
			t.Fatalf("expected country filter, got %q", query.Get("country"))
		}
		if query.Get("region") != "Eastern Europe" {
			t.Fatalf("expected region filter, got %q", query.Get("region"))
		}
		if query.Get("event_type") != "Battles" {
			t.Fatalf("expected event_type filter, got %q", query.Get("event_type"))
		}
		if query.Get("sub_event_type") != "Armed clash" {
			t.Fatalf("expected sub_event_type filter, got %q", query.Get("sub_event_type"))
		}
		if query.Get("event_date") != "2026-01-01|2026-01-31" {
			t.Fatalf("expected date range, got %q", query.Get("event_date"))
		}
		if query.Get("event_date_where") != "BETWEEN" {
			t.Fatalf("expected BETWEEN filter, got %q", query.Get("event_date_where"))
		}
		if query.Get("limit") != "25" {
			t.Fatalf("expected limit=25, got %q", query.Get("limit"))
		}
		if query.Get("fields") == "" {
			t.Fatal("expected selected fields")
		}

		_ = json.NewEncoder(w).Encode(map[string]any{
			"status": 200,
			"data": []map[string]any{
				{
					"event_id_cnty":  "UKR123",
					"event_date":     "2026-01-10",
					"country":        "Ukraine",
					"region":         "Eastern Europe",
					"event_type":     "Battles",
					"sub_event_type": "Armed clash",
					"actor1":         "Actor A",
					"actor2":         "Actor B",
					"fatalities":     "3",
					"location":       "Kyiv",
					"latitude":       "50.4501",
					"longitude":      "30.5234",
					"source":         "Example Source",
					"notes":          "Example note",
				},
			},
		})
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:  server.URL,
		APIToken: "token-123",
	})

	events, err := client.FetchEvents(context.Background(), Query{
		Country:      "Ukraine",
		Region:       "Eastern Europe",
		EventType:    "Battles",
		SubEventType: "Armed clash",
		StartDate:    "2026-01-01",
		EndDate:      "2026-01-31",
		Limit:        25,
	})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if len(events) != 1 {
		t.Fatalf("expected exactly one event, got %d", len(events))
	}
	if events[0].ID != "UKR123" {
		t.Fatalf("expected id UKR123, got %s", events[0].ID)
	}
	if events[0].Fatalities != 3 {
		t.Fatalf("expected fatalities=3, got %d", events[0].Fatalities)
	}
	if events[0].Region != "Eastern Europe" {
		t.Fatalf("expected region Eastern Europe, got %s", events[0].Region)
	}
}

func TestClientFetchEvents_WithLegacyCredentials(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		query := r.URL.Query()
		if query.Get("email") != "ops@example.com" {
			t.Fatalf("expected email credential, got %q", query.Get("email"))
		}
		if query.Get("key") != "legacy-key" {
			t.Fatalf("expected key credential, got %q", query.Get("key"))
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"status": 200,
			"data":   []map[string]any{},
		})
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:   server.URL,
		Email:     "ops@example.com",
		AccessKey: "legacy-key",
	})

	_, err := client.FetchEvents(context.Background(), Query{Limit: 5})
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestClientFetchEvents_RequiresAuthentication(t *testing.T) {
	t.Parallel()

	client := NewClient(Config{
		BaseURL: "https://acleddata.com/api",
	})

	_, err := client.FetchEvents(context.Background(), Query{Limit: 5})
	if err == nil {
		t.Fatal("expected auth error, got nil")
	}

	var requestErr *gct.RequestError
	if !errors.As(err, &requestErr) {
		t.Fatalf("expected request error, got %T", err)
	}
	if requestErr.StatusCode != http.StatusUnauthorized {
		t.Fatalf("expected status 401, got %d", requestErr.StatusCode)
	}
}

func TestClientFetchEvents_UsesMockWithoutCredentialsWhenEnabled(t *testing.T) {
	t.Parallel()

	client := NewClient(Config{
		BaseURL:     "http://127.0.0.1:1",
		MockEnabled: true,
	})

	events, err := client.FetchEvents(context.Background(), Query{
		Country:      "USA",
		Region:       "Americas",
		EventType:    "Battles",
		SubEventType: "Armed clash",
		Limit:        5,
	})
	if err != nil {
		t.Fatalf("expected no error with mock enabled, got %v", err)
	}
	if len(events) == 0 {
		t.Fatal("expected mocked events, got none")
	}
	if events[0].Source != "mock:acled" {
		t.Fatalf("expected mock source, got %q", events[0].Source)
	}
	if events[0].Country != "USA" {
		t.Fatalf("expected query country in mock payload, got %q", events[0].Country)
	}
}

func TestClientFetchEvents_UsesMockFixtureFileWhenConfigured(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	fixture := filepath.Join(dir, "acled-events.json")
	if err := os.WriteFile(
		fixture,
		[]byte(`{"events":[{"id":"fixture-1","eventDate":"2026-03-02","country":"Germany","region":"Europe","eventType":"Strategic developments","subEventType":"Policy signal","fatalities":0,"location":"Berlin","latitude":52.52,"longitude":13.405,"source":"mock:acled:file","notes":"fixture event"}]}`),
		0o600,
	); err != nil {
		t.Fatalf("write fixture: %v", err)
	}

	client := NewClient(Config{
		BaseURL:      "http://127.0.0.1:1",
		MockEnabled:  true,
		MockDataPath: fixture,
	})

	events, err := client.FetchEvents(context.Background(), Query{Limit: 5})
	if err != nil {
		t.Fatalf("expected no error with fixture mock, got %v", err)
	}
	if len(events) != 1 {
		t.Fatalf("expected one fixture event, got %d", len(events))
	}
	if events[0].ID != "fixture-1" {
		t.Fatalf("expected fixture id, got %q", events[0].ID)
	}
	if events[0].Source != "mock:acled:file" {
		t.Fatalf("expected fixture source, got %q", events[0].Source)
	}
}

func TestClientFetchEvents_MapsUpstreamStatus(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer server.Close()

	client := NewClient(Config{
		BaseURL:  server.URL,
		APIToken: "token-123",
	})

	_, err := client.FetchEvents(context.Background(), Query{Limit: 5})
	if err == nil {
		t.Fatal("expected error, got nil")
	}

	var requestErr *gct.RequestError
	if !errors.As(err, &requestErr) {
		t.Fatalf("expected request error, got %T", err)
	}
	if requestErr.StatusCode != http.StatusServiceUnavailable {
		t.Fatalf("expected status 503, got %d", requestErr.StatusCode)
	}
}

func TestClientFetchEvents_RecordsSnapshotMetadataAndRawPayload(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("ETag", `"acled-etag"`)
		w.Header().Set("Last-Modified", "Thu, 12 Mar 2026 11:00:00 GMT")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"status": 200,
			"data": []map[string]any{
				{
					"event_id_cnty":  "ACLED-1",
					"event_date":     "2026-03-12",
					"country":        "Ukraine",
					"region":         "Eastern Europe",
					"event_type":     "Battles",
					"sub_event_type": "Armed clash",
					"actor1":         "Actor A",
					"actor2":         "Actor B",
					"fatalities":     2,
					"location":       "Kyiv",
					"latitude":       50.45,
					"longitude":      30.52,
					"source":         "example",
					"notes":          "snapshot test",
				},
			},
		})
	}))
	defer server.Close()

	tempDir := t.TempDir()
	t.Setenv("ARTIFACT_STORAGE_PROVIDER", "filesystem")
	t.Setenv("ARTIFACT_STORAGE_BASE_DIR", filepath.Join(tempDir, "state"))

	client := NewClient(Config{
		BaseURL:           server.URL,
		APIToken:          "token-123",
		SnapshotStorePath: filepath.Join(tempDir, "state", "acled.json"),
	})

	events, err := client.FetchEvents(context.Background(), Query{Country: "Ukraine", Limit: 10})
	if err != nil {
		t.Fatalf("fetch events: %v", err)
	}
	if len(events) != 1 {
		t.Fatalf("expected 1 event, got %d", len(events))
	}

	rawFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "raw", "acled", "*.json"))
	if err != nil {
		t.Fatalf("glob raw files: %v", err)
	}
	if len(rawFiles) != 1 {
		t.Fatalf("expected 1 raw snapshot file, got %d", len(rawFiles))
	}
	normalizedFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "normalized", "acled", "*.json"))
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
	metaStore, err := storage.NewSQLiteMetadataStore(filepath.Join(tempDir, "state", "source-snapshots", "acled_meta.db"))
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
	if snapshot.SourceID != "acled" {
		t.Fatalf("source id = %q", snapshot.SourceID)
	}
	if snapshot.SourceClass != "api-snapshot" {
		t.Fatalf("source class = %q", snapshot.SourceClass)
	}
	if snapshot.DatasetName != "acled-events" {
		t.Fatalf("dataset name = %q", snapshot.DatasetName)
	}
	if snapshot.ParserVersion != "acled-events-normalized-v1" {
		t.Fatalf("parser version = %q", snapshot.ParserVersion)
	}
	if snapshot.SnapshotStatus != storage.SourceSnapshotNormalized {
		t.Fatalf("snapshot status = %q", snapshot.SnapshotStatus)
	}
}
