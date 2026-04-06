package cftc

import (
	"archive/zip"
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"tradeviewfusion/go-backend/internal/storage"
)

func TestParseCOTCSV(t *testing.T) {
	csv := "market,position\nEURO FX,123\nUS TREASURY,456\n"
	items, err := parseCOTCSV(bytes.NewReader([]byte(csv)))
	if err != nil {
		t.Fatalf("parseCOTCSV: %v", err)
	}
	if len(items) != 3 {
		t.Fatalf("expected 3 rows including header, got %d", len(items))
	}
	firstRow, ok := items[1].([]string)
	if !ok {
		t.Fatalf("expected []string row, got %T", items[1])
	}
	if firstRow[0] != "EURO FX" || firstRow[1] != "123" {
		t.Fatalf("unexpected first data row: %v", firstRow)
	}
}

func TestNewCOTFetcher(t *testing.T) {
	fetcher := NewCOTFetcher("", &http.Client{Timeout: 2 * time.Second})
	if fetcher == nil {
		t.Fatal("expected non-nil fetcher")
	}
}

func TestNewCOTFetcher_UsesEnvOverride(t *testing.T) {
	t.Setenv("CFTC_COT_URL", "https://example.test/cftc.zip")
	fetcher := NewCOTFetcher("", &http.Client{Timeout: 2 * time.Second})
	if fetcher == nil {
		t.Fatal("expected non-nil fetcher")
	}
	if got := fetcher.URL(); got != "https://example.test/cftc.zip" {
		t.Fatalf("url = %q, want env override", got)
	}
}

func TestCOTFetcherRecordsSnapshotMetadataAndRawPayload(t *testing.T) {
	buf := new(bytes.Buffer)
	zipWriter := zip.NewWriter(buf)
	fileWriter, err := zipWriter.Create("cot.csv")
	if err != nil {
		t.Fatalf("create zip entry: %v", err)
	}
	csvPayload := "market,position\nEURO FX,123\n"
	if _, writeErr := fileWriter.Write([]byte(csvPayload)); writeErr != nil {
		t.Fatalf("write zip payload: %v", writeErr)
	}
	if closeErr := zipWriter.Close(); closeErr != nil {
		t.Fatalf("close zip writer: %v", closeErr)
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/zip")
		w.Header().Set("ETag", `"cftc-etag"`)
		w.Header().Set("Last-Modified", "Thu, 12 Mar 2026 06:00:00 GMT")
		_, _ = w.Write(buf.Bytes())
	}))
	t.Cleanup(server.Close)

	tempDir := t.TempDir()
	storePath := filepath.Join(tempDir, "state", "cftc.json")
	t.Setenv("CFTC_COT_URL", server.URL)

	fetcher := NewCOTFetcher(storePath, server.Client())
	items, err := fetcher.Fetch(context.Background())
	if err != nil {
		t.Fatalf("fetch: %v", err)
	}
	if len(items) != 2 {
		t.Fatalf("expected 2 csv rows including header, got %d", len(items))
	}

	rawFiles, err := filepath.Glob(filepath.Join(tempDir, "state", "source-snapshots", "raw", "cftc", "*.zip"))
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
	if !bytes.Equal(rawPayload, buf.Bytes()) {
		t.Fatal("raw zip payload mismatch")
	}

	snapshotID := filepath.Base(rawFiles[0])
	snapshotID = snapshotID[:len(snapshotID)-len(filepath.Ext(snapshotID))]
	metaStore, err := storage.NewSQLiteMetadataStore(filepath.Join(tempDir, "state", "source-snapshots", "cftc_meta.db"))
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
	if snapshot.SourceID != "cftc-cot" {
		t.Fatalf("source id = %q, want cftc-cot", snapshot.SourceID)
	}
	if snapshot.ContentType != "application/zip" {
		t.Fatalf("content type = %q, want application/zip", snapshot.ContentType)
	}
	if snapshot.DatasetName != "cftc-cot" {
		t.Fatalf("dataset name = %q, want cftc-cot", snapshot.DatasetName)
	}
	if snapshot.CadenceHint != "weekly" {
		t.Fatalf("cadence hint = %q, want weekly", snapshot.CadenceHint)
	}
	if snapshot.SnapshotStatus != storage.SourceSnapshotFetched {
		t.Fatalf("snapshot status = %q", snapshot.SnapshotStatus)
	}
}
