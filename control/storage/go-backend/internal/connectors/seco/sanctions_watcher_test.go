package seco

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"net/http"
	"net/http/httptest"

	"tradeviewfusion/go-backend/internal/storage"
)

func TestParseSECOSanctionsJSON_Array(t *testing.T) {
	json := `["invalid", {"id": "s1", "name": "Entity A"}, {"id": "s2", "name": "Entity B"}]`
	got, err := parseSECOSanctionsJSON(bytes.NewReader([]byte(json)))
	if err != nil {
		t.Fatalf("parseSECOSanctionsJSON: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("expected 2 records (non-map items skipped), got %d", len(got))
	}
	if got[0]["id"] != "s1" || got[0]["name"] != "Entity A" {
		t.Fatalf("unexpected record 0: %v", got[0])
	}
}

func TestParseSECOSanctionsJSON_ObjectWithResults(t *testing.T) {
	json := `{"results":[{"id":"r1","name":"Entity R"}]}`
	got, err := parseSECOSanctionsJSON(bytes.NewReader([]byte(json)))
	if err != nil {
		t.Fatalf("parseSECOSanctionsJSON: %v", err)
	}
	if len(got) != 1 {
		t.Fatalf("expected 1 record, got %d", len(got))
	}
	if got[0]["id"] != "r1" {
		t.Fatalf("unexpected record: %v", got[0])
	}
}

func TestParseSECOSanctionsJSON_ObjectWithEntities(t *testing.T) {
	json := `{"entities":[{"id":"e1"}]}`
	got, err := parseSECOSanctionsJSON(bytes.NewReader([]byte(json)))
	if err != nil {
		t.Fatalf("parseSECOSanctionsJSON: %v", err)
	}
	if len(got) != 1 {
		t.Fatalf("expected 1 record, got %d", len(got))
	}
}

func TestParseSECOSanctionsJSON_EmptyArray(t *testing.T) {
	json := `[]`
	got, err := parseSECOSanctionsJSON(bytes.NewReader([]byte(json)))
	if err != nil {
		t.Fatalf("parseSECOSanctionsJSON: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("expected 0 records, got %d", len(got))
	}
}

func TestParseSECOSanctionsJSON_Invalid(t *testing.T) {
	_, err := parseSECOSanctionsJSON(bytes.NewReader([]byte("not json")))
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

func TestParseSECOSanctionsXML_MinimalWholeList(t *testing.T) {
	xmlPayload := `<?xml version="1.0" encoding="UTF-8"?>
<swiss-sanctions-list list-type="whole-list" date="2026-03-10">
  <target ssid="T1" sanctions-set-id="SS1">
    <individual sex="male"></individual>
    <identity ssid="I1" main="true">
      <name>
        <name-part order="1" name-part-type="given-name">John</name-part>
        <name-part order="2" name-part-type="family-name">Doe</name-part>
      </name>
    </identity>
  </target>
  <target ssid="T2" sanctions-set-id="SS1">
    <entity></entity>
    <identity ssid="I2" main="true">
      <name>
        <name-part order="1" name-part-type="whole-name">Example AG</name-part>
      </name>
    </identity>
  </target>
</swiss-sanctions-list>`
	got, err := parseSECOSanctionsJSON(bytes.NewReader([]byte(xmlPayload)))
	if err != nil {
		t.Fatalf("parseSECOSanctionsJSON(xml): %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("expected 2 records, got %d", len(got))
	}
	if got[0]["id"] != "T1" || got[0]["name"] != "John Doe" || got[0]["type"] != "individual" {
		t.Fatalf("unexpected first xml record: %v", got[0])
	}
	if got[1]["id"] != "T2" || got[1]["name"] != "Example AG" || got[1]["type"] != "entity" {
		t.Fatalf("unexpected second xml record: %v", got[1])
	}
}

func TestNewSanctionsWatcher(t *testing.T) {
	w := NewSanctionsWatcher("", nil)
	if w == nil {
		t.Fatal("expected non-nil watcher")
	}
}

func TestNewSanctionsWatcher_UsesEnvOverride(t *testing.T) {
	t.Setenv("SECO_SANCTIONS_URL", "https://example.com/seco.xml")
	w := NewSanctionsWatcher("", nil)
	if w == nil {
		t.Fatal("expected non-nil watcher")
	}
	if got := w.URL(); got != "https://example.com/seco.xml" {
		t.Fatalf("expected env url override, got %q", got)
	}
	client := w.HTTPClient()
	if client == nil {
		t.Fatal("expected http client")
	}
	if got := client.Timeout; got != 90*time.Second {
		t.Fatalf("expected 90s timeout, got %v", got)
	}
}

func TestNewSanctionsWatcher_DefaultsToOfficialThenFallback(t *testing.T) {
	w := NewSanctionsWatcher("", nil)
	if w == nil {
		t.Fatal("expected non-nil watcher")
	}
	if got := w.URL(); got != DefaultSECOOfficialURL {
		t.Fatalf("expected official default url, got %q", got)
	}
	urls := w.URLs()
	if len(urls) != 2 {
		t.Fatalf("expected 2 urls, got %d", len(urls))
	}
	if urls[0] != DefaultSECOOfficialURL || urls[1] != DefaultSECOFallbackURL {
		t.Fatalf("unexpected fallback chain: %#v", urls)
	}
}

func TestSanctionsWatcherRecordsSnapshotMetadataAndRawPayload(t *testing.T) {
	xmlPayload := `<?xml version="1.0" encoding="UTF-8"?>
<swiss-sanctions-list list-type="whole-list" date="2026-03-10">
  <target ssid="T1" sanctions-set-id="SS1">
    <entity></entity>
    <identity ssid="I1" main="true">
      <name>
        <name-part order="1" name-part-type="whole-name">Example AG</name-part>
      </name>
    </identity>
  </target>
</swiss-sanctions-list>`

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/xml")
		w.Header().Set("ETag", `"seco-etag"`)
		w.Header().Set("Last-Modified", "Thu, 12 Mar 2026 08:00:00 GMT")
		_, _ = w.Write([]byte(xmlPayload))
	}))
	t.Cleanup(server.Close)

	tempDir := t.TempDir()
	storePath := filepath.Join(tempDir, "state", "seco.json")
	t.Setenv("SECO_SANCTIONS_URL", server.URL)

	watcher := NewSanctionsWatcher(storePath, server.Client())
	if watcher == nil {
		t.Fatal("expected watcher")
	}

	result, err := watcher.CheckForUpdates(context.Background())
	if err != nil {
		t.Fatalf("check for updates: %v", err)
	}
	if result == nil || len(result.Added) != 1 {
		t.Fatalf("expected 1 added record, got %#v", result)
	}

	rawFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "raw", "seco", "*.xml"))
	if err != nil {
		t.Fatalf("glob raw files: %v", err)
	}
	if len(rawFiles) != 1 {
		t.Fatalf("expected 1 raw snapshot file, got %d", len(rawFiles))
	}

	rawPayload, err := os.ReadFile(rawFiles[0])
	if err != nil {
		t.Fatalf("read raw snapshot: %v", err)
	}
	if string(rawPayload) != xmlPayload {
		t.Fatalf("raw payload mismatch: %q", string(rawPayload))
	}

	snapshotID := rawFiles[0][len(rawFiles[0])-len(filepath.Base(rawFiles[0])):]
	snapshotID = snapshotID[:len(snapshotID)-len(filepath.Ext(snapshotID))]
	metaStore, err := storage.NewSQLiteMetadataStore(filepath.Join(tempDir, "state", "source-snapshots", "seco_meta.db"))
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
	if snapshot.SourceID != "seco" {
		t.Fatalf("source id = %q, want seco", snapshot.SourceID)
	}
	if snapshot.SourceClass != "file-snapshot" {
		t.Fatalf("source class = %q, want file-snapshot", snapshot.SourceClass)
	}
	if snapshot.ContentType != "application/xml" {
		t.Fatalf("content type = %q, want application/xml", snapshot.ContentType)
	}
	if snapshot.ObjectKey != filepath.ToSlash(filepath.Join("source-snapshots", "raw", "seco", filepath.Base(rawFiles[0]))) {
		t.Fatalf("object key = %q", snapshot.ObjectKey)
	}
	if snapshot.SnapshotStatus != storage.SourceSnapshotFetched {
		t.Fatalf("snapshot status = %q, want %q", snapshot.SnapshotStatus, storage.SourceSnapshotFetched)
	}
	if snapshot.DatasetName != "seco-sanctions" {
		t.Fatalf("dataset name = %q, want seco-sanctions", snapshot.DatasetName)
	}
	if snapshot.CadenceHint != "daily" {
		t.Fatalf("cadence hint = %q, want daily", snapshot.CadenceHint)
	}
	if snapshot.ParserVersion != "seco-sanctions-json-xml-v1" {
		t.Fatalf("parser version = %q", snapshot.ParserVersion)
	}
	if snapshot.SourceURL != server.URL {
		t.Fatalf("source url = %q, want %q", snapshot.SourceURL, server.URL)
	}
}
