package storage

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func NewObjectStoreFromEnv(ctx context.Context, filesystemBaseDir string) (ObjectStore, error) {
	provider := ProviderKind(strings.TrimSpace(os.Getenv("ARTIFACT_STORAGE_PROVIDER")))
	if provider == "" {
		provider = ProviderFilesystem
	}

	switch provider {
	case ProviderFilesystem:
		baseDir := strings.TrimSpace(os.Getenv("ARTIFACT_STORAGE_BASE_DIR"))
		if baseDir == "" {
			baseDir = strings.TrimSpace(filesystemBaseDir)
		}
		if baseDir == "" {
			return nil, fmt.Errorf("filesystem base dir required")
		}
		return NewFilesystemProvider(baseDir)
	case ProviderS3, ProviderSeaweedFS:
		return NewS3Provider(ctx, S3Config{
			Endpoint:        strings.TrimSpace(os.Getenv("ARTIFACT_STORAGE_S3_ENDPOINT")),
			Region:          defaultString(strings.TrimSpace(os.Getenv("ARTIFACT_STORAGE_S3_REGION")), "us-east-1"),
			Bucket:          strings.TrimSpace(os.Getenv("ARTIFACT_STORAGE_S3_BUCKET")),
			AccessKeyID:     strings.TrimSpace(os.Getenv("ARTIFACT_STORAGE_S3_ACCESS_KEY_ID")),
			SecretAccessKey: strings.TrimSpace(os.Getenv("ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY")),
			UsePathStyle:    boolEnv("ARTIFACT_STORAGE_S3_USE_PATH_STYLE", true),
			CreateBucket:    boolEnv("ARTIFACT_STORAGE_S3_CREATE_BUCKET", true),
		})
	default:
		return nil, fmt.Errorf("unsupported object store provider %q", provider)
	}
}

func defaultString(value, fallback string) string {
	if value != "" {
		return value
	}
	return fallback
}

func boolEnv(key string, fallback bool) bool {
	switch strings.ToLower(strings.TrimSpace(os.Getenv(key))) {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
}

func DefaultSnapshotFilesystemBaseDir(storePath string) string {
	if trimmed := strings.TrimSpace(storePath); trimmed != "" {
		return filepath.Dir(trimmed)
	}
	return ""
}
