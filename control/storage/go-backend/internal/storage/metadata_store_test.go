package storage

import (
	"path/filepath"
	"testing"
	"time"
)

func TestSQLiteMetadataStoreCreateGetAndComplete(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteMetadataStore(filepath.Join(t.TempDir(), "artifacts.db"))
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	createdAt := time.Unix(1_700_000_000, 0).UTC()
	artifact := Artifact{
		ID:             "art_123",
		ObjectKey:      "analysis/report.pdf",
		Filename:       "report.pdf",
		ContentType:    "application/pdf",
		RetentionClass: "analysis",
		Status:         StatusPendingUpload,
		CreatedAt:      createdAt,
		UpdatedAt:      createdAt,
		ExpiresAt:      createdAt.Add(15 * time.Minute),
	}

	if createErr := store.Create(artifact); createErr != nil {
		t.Fatalf("create artifact: %v", createErr)
	}

	got, err := store.Get("art_123")
	if err != nil {
		t.Fatalf("get artifact: %v", err)
	}
	if got.ObjectKey != artifact.ObjectKey {
		t.Fatalf("object key = %q, want %q", got.ObjectKey, artifact.ObjectKey)
	}

	if uploadErr := store.MarkUploaded("art_123", UploadResult{
		SizeBytes:  12,
		SHA256Hex:  "abc123",
		UploadedAt: createdAt.Add(time.Minute),
	}); uploadErr != nil {
		t.Fatalf("mark uploaded: %v", uploadErr)
	}

	got, err = store.Get("art_123")
	if err != nil {
		t.Fatalf("get uploaded artifact: %v", err)
	}
	if got.Status != StatusReady {
		t.Fatalf("status = %q, want %q", got.Status, StatusReady)
	}
	if got.SHA256Hex != "abc123" {
		t.Fatalf("sha256 = %q, want abc123", got.SHA256Hex)
	}
	if got.SizeBytes != 12 {
		t.Fatalf("size = %d, want 12", got.SizeBytes)
	}
}

func TestSQLiteMetadataStoreCreateGetAndUpdateSourceSnapshot(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteMetadataStore(filepath.Join(t.TempDir(), "snapshots.db"))
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	fetchedAt := time.Unix(1_700_100_000, 0).UTC()
	snapshot := SourceSnapshot{
		ID:             "snap_123",
		SourceID:       "seco",
		SourceClass:    "file-snapshot",
		FetchMode:      "conditional-poll",
		SourceURL:      "https://example.test/seco.xml",
		ObjectKey:      "sources/seco/2026/03/12/snap_123.xml",
		ContentType:    "application/xml",
		ContentLength:  2048,
		SHA256Hex:      "deadbeef",
		ETag:           "etag-1",
		LastModified:   "Wed, 12 Mar 2026 08:00:00 GMT",
		ParserVersion:  "v1",
		SnapshotStatus: SourceSnapshotFetched,
		RetentionClass: "snapshot",
		CadenceHint:    "daily",
		DatasetName:    "seco-sanctions",
		PartitionKey:   "2026-03-12",
		TraceID:        "trace-123",
		FetchedAt:      fetchedAt,
		UpdatedAt:      fetchedAt,
	}

	if createErr := store.CreateSourceSnapshot(snapshot); createErr != nil {
		t.Fatalf("create source snapshot: %v", createErr)
	}

	got, err := store.GetSourceSnapshot(snapshot.ID)
	if err != nil {
		t.Fatalf("get source snapshot: %v", err)
	}
	if got.SourceID != snapshot.SourceID {
		t.Fatalf("source id = %q, want %q", got.SourceID, snapshot.SourceID)
	}
	if got.ObjectKey != snapshot.ObjectKey {
		t.Fatalf("object key = %q, want %q", got.ObjectKey, snapshot.ObjectKey)
	}
	if got.SnapshotStatus != SourceSnapshotFetched {
		t.Fatalf("status = %q, want %q", got.SnapshotStatus, SourceSnapshotFetched)
	}

	updatedAt := fetchedAt.Add(5 * time.Minute)
	if markErr := store.MarkSourceSnapshotStatus(snapshot.ID, SourceSnapshotNormalized, "v2", "", updatedAt); markErr != nil {
		t.Fatalf("mark source snapshot status: %v", markErr)
	}

	got, err = store.GetSourceSnapshot(snapshot.ID)
	if err != nil {
		t.Fatalf("get updated source snapshot: %v", err)
	}
	if got.SnapshotStatus != SourceSnapshotNormalized {
		t.Fatalf("status = %q, want %q", got.SnapshotStatus, SourceSnapshotNormalized)
	}
	if got.ParserVersion != "v2" {
		t.Fatalf("parser version = %q, want v2", got.ParserVersion)
	}
	if !got.UpdatedAt.Equal(updatedAt) {
		t.Fatalf("updatedAt = %s, want %s", got.UpdatedAt, updatedAt)
	}
}

func TestSQLiteMetadataStoreListAndGetLatestSourceSnapshots(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteMetadataStore(filepath.Join(t.TempDir(), "snapshots-list.db"))
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	baseTime := time.Unix(1_700_200_000, 0).UTC()
	snapshots := []SourceSnapshot{
		{
			ID:             "snap_old",
			SourceID:       "acled",
			SourceClass:    "api-snapshot",
			FetchMode:      "poll",
			SourceURL:      "https://example.test/acled?window=1",
			ObjectKey:      "source-snapshots/raw/acled/snap_old.json",
			ContentType:    "application/json",
			ContentLength:  100,
			SHA256Hex:      "old",
			ParserVersion:  "v1",
			SnapshotStatus: SourceSnapshotFetched,
			RetentionClass: "snapshot",
			FetchedAt:      baseTime,
			UpdatedAt:      baseTime,
		},
		{
			ID:             "snap_new",
			SourceID:       "acled",
			SourceClass:    "api-snapshot",
			FetchMode:      "poll",
			SourceURL:      "https://example.test/acled?window=2",
			ObjectKey:      "source-snapshots/normalized/acled/snap_new.json",
			ContentType:    "application/json",
			ContentLength:  120,
			SHA256Hex:      "new",
			ParserVersion:  "v2",
			SnapshotStatus: SourceSnapshotNormalized,
			RetentionClass: "snapshot",
			FetchedAt:      baseTime.Add(time.Minute),
			UpdatedAt:      baseTime.Add(time.Minute),
		},
	}

	for _, snapshot := range snapshots {
		if createErr := store.CreateSourceSnapshot(snapshot); createErr != nil {
			t.Fatalf("create source snapshot %s: %v", snapshot.ID, createErr)
		}
	}

	listed, err := store.ListSourceSnapshots("acled", "", 10)
	if err != nil {
		t.Fatalf("list source snapshots: %v", err)
	}
	if len(listed) != 2 {
		t.Fatalf("expected 2 snapshots, got %d", len(listed))
	}
	if listed[0].ID != "snap_new" {
		t.Fatalf("expected newest snapshot first, got %q", listed[0].ID)
	}

	normalized, err := store.ListSourceSnapshots("acled", SourceSnapshotNormalized, 10)
	if err != nil {
		t.Fatalf("list normalized source snapshots: %v", err)
	}
	if len(normalized) != 1 || normalized[0].ID != "snap_new" {
		t.Fatalf("expected only normalized snapshot, got %+v", normalized)
	}

	latest, err := store.GetLatestSourceSnapshot("acled", SourceSnapshotNormalized)
	if err != nil {
		t.Fatalf("get latest source snapshot: %v", err)
	}
	if latest.ID != "snap_new" {
		t.Fatalf("expected latest normalized snapshot snap_new, got %q", latest.ID)
	}
}
