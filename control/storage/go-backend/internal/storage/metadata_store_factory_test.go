package storage

import (
	"path/filepath"
	"testing"
)

func TestNewArtifactMetadataStoreSQLiteDefault(t *testing.T) {
	t.Parallel()

	store, err := NewArtifactMetadataStore("", filepath.Join(t.TempDir(), "artifacts.db"), "")
	if err != nil {
		t.Fatalf("new artifact metadata store: %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Fatalf("close store: %v", err)
		}
	})
}

func TestNewArtifactMetadataStorePostgresRequiresDSN(t *testing.T) {
	t.Parallel()

	_, err := NewArtifactMetadataStore("postgres", "", "")
	if err == nil {
		t.Fatal("expected postgres metadata store to require dsn")
	}
}
