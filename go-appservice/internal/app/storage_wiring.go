// Package app contains application-level wiring for shared services.
//
// storage_wiring.go — Adopts the artifact storage stack from
// tradeview-fusion main project (1:1 helper functions). Provides:
//   - env helpers: envOr, intOr, boolOr, durationMsOr, isProductionRuntime
//   - artifact-specific helpers: artifactSigningSecretFromEnv,
//     artifactGatewayBaseURLFromEnv
//   - BuildArtifactService factory that constructs storage.Service +
//     metadata store from environment variables
//
// All ARTIFACT_STORAGE_* env vars are named identically to the main project
// for forward-compatibility (D12: capability-based access pattern).
package app

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"matrix/go-appservice/internal/storage"
)

// ArtifactServiceConfig holds the constructed service + its public base URL.
type ArtifactServiceConfig struct {
	Service        *storage.Service
	GatewayBaseURL string
	Store          storage.ArtifactMetadataStore // exposes Close() for graceful shutdown
}

// BuildArtifactService constructs the storage.Service from env variables.
// Returns (cfg, nil) on success or (nil, err) if init fails.
//
// Required:
//   - ARTIFACT_STORAGE_SIGNING_SECRET (or AUTH_SECRET fallback in dev)
//   - ARTIFACT_STORAGE_PROVIDER (filesystem | s3 | seaweedfs)
//   - For s3/seaweedfs: ARTIFACT_STORAGE_S3_ENDPOINT + BUCKET + ACCESS_KEY_ID + SECRET_ACCESS_KEY
//   - HINDSIGHT_DB_URL (or POSTGRES_DSN) — Postgres is the only metadata backend
//
// exec-19: the SQLite metadata store was removed in Phase 3 cleanup. The
// devstack always has Postgres running (required by Hindsight + Agent), so
// a SQLite fallback was dead weight.
func BuildArtifactService(host, port, postgresDSN string) (*ArtifactServiceConfig, error) {
	signingSecret := artifactSigningSecretFromEnv()
	if signingSecret == "" {
		return nil, fmt.Errorf("ARTIFACT_STORAGE_SIGNING_SECRET (or AUTH_SECRET fallback) required")
	}

	if strings.TrimSpace(postgresDSN) == "" {
		return nil, fmt.Errorf("PostgresDSN required (set HINDSIGHT_DB_URL, POSTGRES_URL, or DATABASE_URL)")
	}

	store, err := storage.NewPostgresMetadataStore(postgresDSN)
	if err != nil {
		return nil, fmt.Errorf("init artifact metadata store: %w", err)
	}

	provider := storage.ProviderKind(envOr("ARTIFACT_STORAGE_PROVIDER", string(storage.ProviderFilesystem)))

	svc, err := storage.NewService(storage.Config{
		Provider:      provider,
		BaseDir:       envOr("ARTIFACT_STORAGE_BASE_DIR", "data/storage/objects"),
		SigningSecret: signingSecret,
		TTL:           durationMsOr("ARTIFACT_STORAGE_SIGNED_URL_TTL_MS", 15*60*1000),
		Store:         store,
		S3: storage.S3Config{
			Endpoint:        envOr("ARTIFACT_STORAGE_S3_ENDPOINT", ""),
			Region:          envOr("ARTIFACT_STORAGE_S3_REGION", "us-east-1"),
			Bucket:          envOr("ARTIFACT_STORAGE_S3_BUCKET", ""),
			AccessKeyID:     envOr("ARTIFACT_STORAGE_S3_ACCESS_KEY_ID", ""),
			SecretAccessKey: envOr("ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY", ""),
			UsePathStyle:    boolOr("ARTIFACT_STORAGE_S3_USE_PATH_STYLE", true),
			CreateBucket:    boolOr("ARTIFACT_STORAGE_S3_CREATE_BUCKET", true),
		},
	})
	if err != nil {
		_ = store.Close()
		return nil, fmt.Errorf("init artifact storage service: %w", err)
	}

	return &ArtifactServiceConfig{
		Service:        svc,
		GatewayBaseURL: artifactGatewayBaseURLFromEnv(host, port),
		Store:          store,
	}, nil
}

// ── Env Helpers (1:1 from tradeview-fusion wiring.go) ─────────────────────

func envOr(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

func intOr(key string, fallback int) int {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func durationMsOr(key string, fallbackMs int) time.Duration {
	value := intOr(key, fallbackMs)
	if value < 1 {
		value = fallbackMs
	}
	return time.Duration(value) * time.Millisecond
}

func boolOr(key string, fallback bool) bool {
	value := strings.TrimSpace(strings.ToLower(os.Getenv(key)))
	if value == "" {
		return fallback
	}
	switch value {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
}

func isProductionRuntime() bool {
	for _, key := range []string{"APP_ENV", "ENVIRONMENT", "GO_ENV", "NODE_ENV"} {
		value := strings.TrimSpace(strings.ToLower(os.Getenv(key)))
		if value == "" {
			continue
		}
		if value == "prod" || value == "production" {
			return true
		}
	}
	return false
}

// artifactSigningSecretFromEnv looks up the signing secret in priority order.
// In development without any of these set, returns a fixed dev secret.
// In production, returns "" (caller must error).
func artifactSigningSecretFromEnv() string {
	candidates := []string{
		strings.TrimSpace(envOr("ARTIFACT_STORAGE_SIGNING_SECRET", "")),
		strings.TrimSpace(envOr("AUTH_JWT_SECRET", "")),
		strings.TrimSpace(envOr("AUTH_SECRET", "")),
		strings.TrimSpace(envOr("NEXTAUTH_SECRET", "")),
	}
	for _, candidate := range candidates {
		if candidate != "" {
			return candidate
		}
	}
	if !isProductionRuntime() {
		return "local-dev-artifact-signing-secret"
	}
	return ""
}

// artifactGatewayBaseURLFromEnv computes the public base URL for signed
// upload/download URLs. Falls back to http://<host>:<port> when no
// ARTIFACT_STORAGE_PUBLIC_BASE_URL is configured.
func artifactGatewayBaseURLFromEnv(host, port string) string {
	if configured := strings.TrimSpace(envOr("ARTIFACT_STORAGE_PUBLIC_BASE_URL", "")); configured != "" {
		return strings.TrimRight(configured, "/")
	}
	resolvedHost := strings.TrimSpace(host)
	if resolvedHost == "" || resolvedHost == "0.0.0.0" {
		resolvedHost = "127.0.0.1"
	}
	return fmt.Sprintf("http://%s:%s", resolvedHost, strings.TrimSpace(port))
}
