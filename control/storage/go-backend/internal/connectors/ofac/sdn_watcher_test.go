package ofac

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

func TestParseSDNXML(t *testing.T) {
	xml := `<?xml version="1.0"?>
<sdnList>
  <sdnEntry>
    <uid>123</uid>
    <lastName>Doe</lastName>
    <sdnType>individual</sdnType>
  </sdnEntry>
  <sdnEntry>
    <uid>456</uid>
    <lastName>Acme Corp</lastName>
    <sdnType>entity</sdnType>
  </sdnEntry>
</sdnList>`
	got, err := parseSDNXML(bytes.NewReader([]byte(xml)))
	if err != nil {
		t.Fatalf("parseSDNXML: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(got))
	}
	if got[0]["uid"] != "123" || got[0]["lastName"] != "Doe" || got[0]["sdnType"] != "individual" {
		t.Fatalf("unexpected entry 0: %v", got[0])
	}
	if got[1]["uid"] != "456" || got[1]["lastName"] != "Acme Corp" {
		t.Fatalf("unexpected entry 1: %v", got[1])
	}
}

func TestParseSDNXML_Empty(t *testing.T) {
	xml := `<?xml version="1.0"?><sdnList></sdnList>`
	got, err := parseSDNXML(bytes.NewReader([]byte(xml)))
	if err != nil {
		t.Fatalf("parseSDNXML: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("expected 0 entries, got %d", len(got))
	}
}

func TestNewSDNWatcher(t *testing.T) {
	w := NewSDNWatcher("", nil)
	if w == nil {
		t.Fatal("expected non-nil watcher")
	}
}

func TestSDNWatcherRecordsSnapshotMetadataAndRawPayload(t *testing.T) {
	xmlPayload := `<?xml version="1.0"?>
<sdnList>
  <sdnEntry>
    <uid>123</uid>
    <lastName>Doe</lastName>
    <sdnType>individual</sdnType>
  </sdnEntry>
</sdnList>`

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/xml")
		w.Header().Set("ETag", `"ofac-etag"`)
		w.Header().Set("Last-Modified", "Thu, 12 Mar 2026 08:00:00 GMT")
		_, _ = w.Write([]byte(xmlPayload))
	}))
	t.Cleanup(server.Close)

	tempDir := t.TempDir()
	storePath := filepath.Join(tempDir, "state", "ofac.json")
	t.Setenv("OFAC_SDN_URL", server.URL)

	watcher := NewSDNWatcher(storePath, server.Client())
	result, err := watcher.CheckForUpdates(context.Background())
	if err != nil {
		t.Fatalf("check for updates: %v", err)
	}
	if result == nil || len(result.Added) != 1 {
		t.Fatalf("expected 1 added record, got %#v", result)
	}

	rawFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "raw", "ofac", "*.xml"))
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
	metaStore, err := storage.NewSQLiteMetadataStore(filepath.Join(tempDir, "state", "source-snapshots", "ofac_meta.db"))
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
	if snapshot.SourceID != "ofac" {
		t.Fatalf("source id = %q, want ofac", snapshot.SourceID)
	}
	if snapshot.DatasetName != "ofac-sdn" {
		t.Fatalf("dataset name = %q, want ofac-sdn", snapshot.DatasetName)
	}
	if snapshot.ParserVersion != "ofac-sdn-xml-v1" {
		t.Fatalf("parser version = %q", snapshot.ParserVersion)
	}
	if snapshot.ObjectKey != filepath.ToSlash(filepath.Join("source-snapshots", "raw", "ofac", filepath.Base(rawFiles[0]))) {
		t.Fatalf("object key = %q", snapshot.ObjectKey)
	}
	if snapshot.SnapshotStatus != storage.SourceSnapshotFetched {
		t.Fatalf("snapshot status = %q", snapshot.SnapshotStatus)
	}
}
