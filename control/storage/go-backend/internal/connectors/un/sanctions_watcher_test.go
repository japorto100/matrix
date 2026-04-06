package un

import (
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"tradeviewfusion/go-backend/internal/storage"
)

func TestParseUNSanctionsXML(t *testing.T) {
	xml := `<?xml version="1.0"?>
<CONSOLIDATED_LIST>
  <INDIVIDUALS>
    <INDIVIDUAL>
      <DATAID>QDi.001</DATAID>
      <FIRST_NAME>John</FIRST_NAME>
      <SECOND_NAME>Doe</SECOND_NAME>
    </INDIVIDUAL>
    <INDIVIDUAL>
      <DATAID>QDi.002</DATAID>
      <FIRST_NAME>Jane</FIRST_NAME>
    </INDIVIDUAL>
  </INDIVIDUALS>
  <ENTITIES>
    <ENTITY>
      <DATAID>QDe.001</DATAID>
      <NAME>Acme Corp</NAME>
    </ENTITY>
    <ENTITY>
      <DATAID>QDe.002</DATAID>
      <FIRST_NAME>Other Entity</FIRST_NAME>
    </ENTITY>
  </ENTITIES>
</CONSOLIDATED_LIST>`
	got, err := parseUNSanctionsXML(bytes.NewReader([]byte(xml)))
	if err != nil {
		t.Fatalf("parseUNSanctionsXML: %v", err)
	}
	if len(got) != 4 {
		t.Fatalf("expected 4 records, got %d", len(got))
	}
	// Individual with full name
	if got[0]["reference_number"] != "QDi.001" || got[0]["name"] != "John Doe" || got[0]["type"] != "individual" {
		t.Fatalf("unexpected record 0: %v", got[0])
	}
	// Individual with single name
	if got[1]["reference_number"] != "QDi.002" || got[1]["name"] != "Jane" {
		t.Fatalf("unexpected record 1: %v", got[1])
	}
	// Entity with NAME
	if got[2]["reference_number"] != "QDe.001" || got[2]["name"] != "Acme Corp" || got[2]["type"] != "entity" {
		t.Fatalf("unexpected record 2: %v", got[2])
	}
	// Entity with FIRST_NAME fallback
	if got[3]["reference_number"] != "QDe.002" || got[3]["name"] != "Other Entity" {
		t.Fatalf("unexpected record 3: %v", got[3])
	}
}

func TestParseUNSanctionsXML_Empty(t *testing.T) {
	xml := `<?xml version="1.0"?>
<CONSOLIDATED_LIST>
  <INDIVIDUALS/>
  <ENTITIES/>
</CONSOLIDATED_LIST>`
	got, err := parseUNSanctionsXML(bytes.NewReader([]byte(xml)))
	if err != nil {
		t.Fatalf("parseUNSanctionsXML: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("expected 0 records, got %d", len(got))
	}
}

func TestParseUNSanctionsXML_Invalid(t *testing.T) {
	_, err := parseUNSanctionsXML(bytes.NewReader([]byte("not xml")))
	if err == nil {
		t.Fatal("expected error for invalid XML")
	}
}

func TestNewSanctionsWatcher(t *testing.T) {
	w := NewSanctionsWatcher("", nil)
	if w == nil {
		t.Fatal("expected non-nil watcher")
	}
}

func TestGetEnv(t *testing.T) {
	key := "UN_SANCTIONS_TEST_KEY_UNUSED"
	if got := getEnv(key, "fallback"); got != "fallback" {
		t.Fatalf("expected fallback when env empty, got %q", got)
	}
	if got := getEnv(key, ""); got != "" {
		t.Fatalf("expected empty when both empty, got %q", got)
	}
	os.Setenv(key, "custom")
	defer os.Unsetenv(key)
	if got := getEnv(key, "fallback"); got != "custom" {
		t.Fatalf("expected env value when set, got %q", got)
	}
}

func TestSanctionsWatcherRecordsSnapshotMetadataAndRawPayload(t *testing.T) {
	xmlPayload := `<?xml version="1.0"?>
<CONSOLIDATED_LIST>
  <INDIVIDUALS>
    <INDIVIDUAL>
      <DATAID>QDi.001</DATAID>
      <FIRST_NAME>John</FIRST_NAME>
      <SECOND_NAME>Doe</SECOND_NAME>
    </INDIVIDUAL>
  </INDIVIDUALS>
  <ENTITIES/>
</CONSOLIDATED_LIST>`

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/xml")
		w.Header().Set("ETag", `"un-etag"`)
		w.Header().Set("Last-Modified", "Thu, 12 Mar 2026 08:00:00 GMT")
		_, _ = w.Write([]byte(xmlPayload))
	}))
	t.Cleanup(server.Close)

	tempDir := t.TempDir()
	storePath := filepath.Join(tempDir, "state", "un.json")
	t.Setenv("UN_SANCTIONS_URL", server.URL)

	watcher := NewSanctionsWatcher(storePath, server.Client())
	result, err := watcher.CheckForUpdates(context.Background())
	if err != nil {
		t.Fatalf("check for updates: %v", err)
	}
	if result == nil || len(result.Added) != 1 {
		t.Fatalf("expected 1 added record, got %#v", result)
	}

	rawFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "raw", "un", "*.xml"))
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
		t.Fatal("raw payload mismatch")
	}

	snapshotID := filepath.Base(rawFiles[0])
	snapshotID = snapshotID[:len(snapshotID)-len(filepath.Ext(snapshotID))]
	metaStore, err := storage.NewSQLiteMetadataStore(filepath.Join(tempDir, "state", "source-snapshots", "un_meta.db"))
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
	if snapshot.SourceID != "un-sanctions" {
		t.Fatalf("source id = %q, want un-sanctions", snapshot.SourceID)
	}
	if snapshot.DatasetName != "un-sanctions" {
		t.Fatalf("dataset name = %q, want un-sanctions", snapshot.DatasetName)
	}
	if snapshot.ParserVersion != "un-sanctions-xml-v1" {
		t.Fatalf("parser version = %q", snapshot.ParserVersion)
	}
	if snapshot.ObjectKey != filepath.ToSlash(filepath.Join("source-snapshots", "raw", "un", filepath.Base(rawFiles[0]))) {
		t.Fatalf("object key = %q", snapshot.ObjectKey)
	}
	if snapshot.SnapshotStatus != storage.SourceSnapshotFetched {
		t.Fatalf("snapshot status = %q", snapshot.SnapshotStatus)
	}
}
