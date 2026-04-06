package base

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"tradeviewfusion/go-backend/internal/storage"
)

type LocalSnapshotRecorderConfig struct {
	SourceID      string
	Subdir        string
	SourceClass   string
	FetchMode     string
	StorePath     string
	DatasetName   string
	CadenceHint   string
	ParserVersion string
}

func NewLocalSnapshotRecorder(cfg LocalSnapshotRecorderConfig) func(context.Context, FetchSnapshot) error {
	basePath := strings.TrimSpace(cfg.StorePath)
	if basePath == "" {
		return nil
	}
	sourceID := strings.TrimSpace(cfg.SourceID)
	subdir := strings.TrimSpace(cfg.Subdir)
	if sourceID == "" {
		sourceID = subdir
	}
	if sourceID == "" {
		return nil
	}
	if subdir == "" {
		subdir = sourceID
	}
	rootDir := filepath.Dir(basePath)
	metaDir := filepath.Join(rootDir, "source-snapshots")
	baseName := strings.TrimSuffix(filepath.Base(basePath), filepath.Ext(filepath.Base(basePath)))
	dbPath := filepath.Join(metaDir, baseName+"_meta.db")
	objectStore, err := storage.NewObjectStoreFromEnv(context.Background(), storage.DefaultSnapshotFilesystemBaseDir(basePath))
	if err != nil {
		return nil
	}

	return func(_ context.Context, fetched FetchSnapshot) error {
		store, err := storage.NewSQLiteMetadataStore(dbPath)
		if err != nil {
			return fmt.Errorf("open snapshot metadata store: %w", err)
		}
		defer func() { _ = store.Close() }()

		snapshotID := LocalSnapshotID(sourceID, fetched.FetchedAt, fetched.SHA256Hex)
		filename := SnapshotFilename(snapshotID, fetched.ContentType, fetched.SourceURL)
		objectKey := filepath.ToSlash(filepath.Join("source-snapshots", "raw", filepath.FromSlash(subdir), filename))
		if err := ensureSnapshotParentDir(rootDir, objectKey); err != nil {
			return err
		}
		if _, err := objectStore.Put(context.Background(), objectKey, bytes.NewReader(fetched.Payload)); err != nil {
			return fmt.Errorf("write raw snapshot object: %w", err)
		}
		return store.CreateSourceSnapshot(storage.SourceSnapshot{
			ID:             snapshotID,
			SourceID:       sourceID,
			SourceClass:    defaultString(cfg.SourceClass, "file-snapshot"),
			FetchMode:      defaultString(cfg.FetchMode, "conditional-poll"),
			SourceURL:      fetched.SourceURL,
			ObjectKey:      objectKey,
			ContentType:    NormalizeSnapshotContentType(fetched.ContentType),
			ContentLength:  fetched.ContentLength,
			SHA256Hex:      fetched.SHA256Hex,
			ETag:           fetched.ETag,
			LastModified:   fetched.LastModified,
			ParserVersion:  strings.TrimSpace(cfg.ParserVersion),
			SnapshotStatus: storage.SourceSnapshotFetched,
			RetentionClass: "snapshot",
			CadenceHint:    strings.TrimSpace(cfg.CadenceHint),
			DatasetName:    strings.TrimSpace(cfg.DatasetName),
			PartitionKey:   fetched.FetchedAt.UTC().Format("2006-01-02"),
			FetchedAt:      fetched.FetchedAt.UTC(),
			UpdatedAt:      fetched.FetchedAt.UTC(),
		})
	}
}

func NewLocalSnapshotNormalizer(cfg LocalSnapshotRecorderConfig) func(context.Context, string, []byte, time.Time) error {
	basePath := strings.TrimSpace(cfg.StorePath)
	if basePath == "" {
		return nil
	}
	sourceID := strings.TrimSpace(cfg.SourceID)
	subdir := strings.TrimSpace(cfg.Subdir)
	if sourceID == "" {
		sourceID = subdir
	}
	if sourceID == "" {
		return nil
	}
	if subdir == "" {
		subdir = sourceID
	}
	rootDir := filepath.Dir(basePath)
	metaDir := filepath.Join(rootDir, "source-snapshots")
	baseName := strings.TrimSuffix(filepath.Base(basePath), filepath.Ext(filepath.Base(basePath)))
	dbPath := filepath.Join(metaDir, baseName+"_meta.db")
	objectStore, err := storage.NewObjectStoreFromEnv(context.Background(), storage.DefaultSnapshotFilesystemBaseDir(basePath))
	if err != nil {
		return nil
	}

	return func(_ context.Context, snapshotID string, payload []byte, updatedAt time.Time) error {
		normalizedAt := updatedAt.UTC()
		if strings.TrimSpace(snapshotID) == "" {
			return fmt.Errorf("normalize snapshot: snapshot id required")
		}
		store, err := storage.NewSQLiteMetadataStore(dbPath)
		if err != nil {
			return fmt.Errorf("open snapshot metadata store: %w", err)
		}
		defer func() { _ = store.Close() }()

		objectKey := filepath.ToSlash(filepath.Join("source-snapshots", "normalized", filepath.FromSlash(subdir), snapshotID+".json"))
		if err := ensureSnapshotParentDir(rootDir, objectKey); err != nil {
			return err
		}
		if _, err := objectStore.Put(context.Background(), objectKey, bytes.NewReader(payload)); err != nil {
			return fmt.Errorf("write normalized snapshot object: %w", err)
		}
		if err := store.MarkSourceSnapshotStatus(snapshotID, storage.SourceSnapshotNormalized, strings.TrimSpace(cfg.ParserVersion), "", normalizedAt); err != nil {
			return fmt.Errorf("mark normalized snapshot status: %w", err)
		}
		return nil
	}
}

func ensureSnapshotParentDir(rootDir, objectKey string) error {
	provider := storage.ProviderKind(strings.TrimSpace(os.Getenv("ARTIFACT_STORAGE_PROVIDER")))
	if provider != "" && provider != storage.ProviderFilesystem {
		return nil
	}
	rawPath := filepath.Join(rootDir, filepath.FromSlash(objectKey))
	if err := os.MkdirAll(filepath.Dir(rawPath), 0o750); err != nil {
		return fmt.Errorf("create raw snapshot dir: %w", err)
	}
	return nil
}

func LocalSnapshotID(sourceID string, fetchedAt time.Time, sha string) string {
	prefix := sha
	if len(prefix) > 12 {
		prefix = prefix[:12]
	}
	return fmt.Sprintf("%s_%s_%s", strings.TrimSpace(sourceID), fetchedAt.UTC().Format("20060102T150405Z"), prefix)
}

func SnapshotFilename(snapshotID, contentType, sourceURL string) string {
	normalizedURL := strings.ToLower(strings.TrimSpace(sourceURL))
	switch {
	case strings.Contains(contentType, "xml"), strings.HasSuffix(normalizedURL, ".xml"):
		return snapshotID + ".xml"
	case strings.Contains(contentType, "json"), strings.HasSuffix(normalizedURL, ".json"):
		return snapshotID + ".json"
	case strings.Contains(contentType, "zip"), strings.HasSuffix(normalizedURL, ".zip"):
		return snapshotID + ".zip"
	case strings.Contains(contentType, "gzip"), strings.HasSuffix(normalizedURL, ".gz"):
		return snapshotID + ".gz"
	case strings.Contains(contentType, "csv"), strings.HasSuffix(normalizedURL, ".csv"):
		return snapshotID + ".csv"
	default:
		return snapshotID + ".bin"
	}
}

func NormalizeSnapshotContentType(contentType string) string {
	if trimmed := strings.TrimSpace(contentType); trimmed != "" {
		return trimmed
	}
	return "application/octet-stream"
}

func defaultString(value, fallback string) string {
	if trimmed := strings.TrimSpace(value); trimmed != "" {
		return trimmed
	}
	return fallback
}
