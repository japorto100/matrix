package storage

import (
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

type PostgresMetadataStore struct {
	db *sql.DB
}

func NewPostgresMetadataStore(dsn string) (*PostgresMetadataStore, error) {
	trimmed := strings.TrimSpace(dsn)
	if trimmed == "" {
		return nil, fmt.Errorf("postgres metadata dsn required")
	}
	db, err := sql.Open("pgx", trimmed)
	if err != nil {
		return nil, fmt.Errorf("open postgres metadata db: %w", err)
	}
	store := &PostgresMetadataStore{db: db}
	if err := store.migrate(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return store, nil
}

func (s *PostgresMetadataStore) migrate() error {
	if s == nil || s.db == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	_, err := s.db.Exec(`
CREATE TABLE IF NOT EXISTS artifact_metadata (
	id TEXT PRIMARY KEY,
	object_key TEXT NOT NULL,
	filename TEXT NOT NULL,
	content_type TEXT NOT NULL,
	retention_class TEXT NOT NULL,
	status TEXT NOT NULL,
	size_bytes BIGINT NOT NULL DEFAULT 0,
	sha256_hex TEXT NOT NULL DEFAULT '',
	created_at TIMESTAMPTZ NOT NULL,
	updated_at TIMESTAMPTZ NOT NULL,
	expires_at TIMESTAMPTZ NOT NULL
)
`)
	if err != nil {
		return fmt.Errorf("migrate postgres metadata db: %w", err)
	}
	return nil
}

func (s *PostgresMetadataStore) Close() error {
	if s == nil || s.db == nil {
		return nil
	}
	if err := s.db.Close(); err != nil {
		return fmt.Errorf("close postgres metadata db: %w", err)
	}
	return nil
}

func (s *PostgresMetadataStore) Create(artifact Artifact) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	_, err := s.db.Exec(`
INSERT INTO artifact_metadata (
	id, object_key, filename, content_type, retention_class, status,
	size_bytes, sha256_hex, created_at, updated_at, expires_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
`,
		artifact.ID,
		artifact.ObjectKey,
		artifact.Filename,
		artifact.ContentType,
		artifact.RetentionClass,
		string(artifact.Status),
		artifact.SizeBytes,
		artifact.SHA256Hex,
		artifact.CreatedAt.UTC(),
		artifact.UpdatedAt.UTC(),
		artifact.ExpiresAt.UTC(),
	)
	if err != nil {
		return fmt.Errorf("insert artifact metadata: %w", err)
	}
	return nil
}

func (s *PostgresMetadataStore) Get(id string) (Artifact, error) {
	if s == nil || s.db == nil {
		return Artifact{}, fmt.Errorf("metadata store unavailable")
	}
	var row struct {
		ID             string
		ObjectKey      string
		Filename       string
		ContentType    string
		RetentionClass string
		Status         string
		SizeBytes      int64
		SHA256Hex      string
		CreatedAt      time.Time
		UpdatedAt      time.Time
		ExpiresAt      time.Time
	}
	err := s.db.QueryRow(`
SELECT id, object_key, filename, content_type, retention_class, status,
       size_bytes, sha256_hex, created_at, updated_at, expires_at
FROM artifact_metadata
WHERE id = $1
`, id).Scan(
		&row.ID,
		&row.ObjectKey,
		&row.Filename,
		&row.ContentType,
		&row.RetentionClass,
		&row.Status,
		&row.SizeBytes,
		&row.SHA256Hex,
		&row.CreatedAt,
		&row.UpdatedAt,
		&row.ExpiresAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Artifact{}, ErrArtifactNotFound
		}
		return Artifact{}, fmt.Errorf("query artifact metadata: %w", err)
	}
	return Artifact{
		ID:             row.ID,
		ObjectKey:      row.ObjectKey,
		Filename:       row.Filename,
		ContentType:    row.ContentType,
		RetentionClass: row.RetentionClass,
		Status:         ArtifactStatus(row.Status),
		SizeBytes:      row.SizeBytes,
		SHA256Hex:      row.SHA256Hex,
		CreatedAt:      row.CreatedAt.UTC(),
		UpdatedAt:      row.UpdatedAt.UTC(),
		ExpiresAt:      row.ExpiresAt.UTC(),
	}, nil
}

func (s *PostgresMetadataStore) MarkUploaded(id string, result UploadResult) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	res, err := s.db.Exec(`
UPDATE artifact_metadata
SET status = $1, size_bytes = $2, sha256_hex = $3, updated_at = $4
WHERE id = $5
`,
		string(StatusReady),
		result.SizeBytes,
		result.SHA256Hex,
		result.UploadedAt.UTC(),
		id,
	)
	if err != nil {
		return fmt.Errorf("mark artifact uploaded: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("artifact upload rows affected: %w", err)
	}
	if rows == 0 {
		return ErrArtifactNotFound
	}
	return nil
}
