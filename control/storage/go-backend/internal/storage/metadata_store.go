package storage

import (
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

type SQLiteMetadataStore struct {
	db *sql.DB
}

func NewSQLiteMetadataStore(path string) (*SQLiteMetadataStore, error) {
	trimmed := filepath.Clean(path)
	if trimmed == "." || trimmed == "" {
		return nil, fmt.Errorf("metadata db path required")
	}
	if err := os.MkdirAll(filepath.Dir(trimmed), 0o750); err != nil {
		return nil, fmt.Errorf("create metadata db dir: %w", err)
	}
	// URI DSN: busy_timeout is applied at connection level before any lock is
	// acquired, so journal_mode=WAL can retry on the first open instead of
	// returning SQLITE_BUSY immediately. WAL is persistent — once set on the
	// file, subsequent opens are no-ops. _txlock=immediate prevents deferred→
	// write upgrade failures that bypass busy_timeout.
	// TODO(postgres): replace with pgxpool when METADATA_STORE_DRIVER=postgres.
	dsn := "file:" + filepath.ToSlash(trimmed) +
		"?_pragma=busy_timeout(5000)" +
		"&_pragma=journal_mode(WAL)" +
		"&_pragma=synchronous(NORMAL)" +
		"&_txlock=immediate"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open metadata db: %w", err)
	}
	// Single writer connection — serialises writes at the Go layer so SQLite
	// never sees concurrent write attempts from the same process.
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	store := &SQLiteMetadataStore{db: db}
	if err := store.migrate(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return store, nil
}

func (s *SQLiteMetadataStore) migrate() error {
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
	size_bytes INTEGER NOT NULL DEFAULT 0,
	sha256_hex TEXT NOT NULL DEFAULT '',
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_snapshot_metadata (
	id TEXT PRIMARY KEY,
	source_id TEXT NOT NULL,
	source_class TEXT NOT NULL,
	fetch_mode TEXT NOT NULL,
	source_url TEXT NOT NULL,
	object_key TEXT NOT NULL,
	content_type TEXT NOT NULL,
	content_length INTEGER NOT NULL DEFAULT 0,
	sha256_hex TEXT NOT NULL DEFAULT '',
	etag TEXT NOT NULL DEFAULT '',
	last_modified TEXT NOT NULL DEFAULT '',
	parser_version TEXT NOT NULL DEFAULT '',
	snapshot_status TEXT NOT NULL,
	retention_class TEXT NOT NULL,
	cadence_hint TEXT NOT NULL DEFAULT '',
	dataset_name TEXT NOT NULL DEFAULT '',
	partition_key TEXT NOT NULL DEFAULT '',
	trace_id TEXT NOT NULL DEFAULT '',
	error_class TEXT NOT NULL DEFAULT '',
	fetched_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);
`)
	if err != nil {
		return fmt.Errorf("migrate metadata db: %w", err)
	}
	return nil
}

func (s *SQLiteMetadataStore) Close() error {
	if s == nil || s.db == nil {
		return nil
	}
	if err := s.db.Close(); err != nil {
		return fmt.Errorf("close sqlite metadata db: %w", err)
	}
	return nil
}

func (s *SQLiteMetadataStore) Create(artifact Artifact) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	_, err := s.db.Exec(`
INSERT INTO artifact_metadata (
	id, object_key, filename, content_type, retention_class, status,
	size_bytes, sha256_hex, created_at, updated_at, expires_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`,
		artifact.ID,
		artifact.ObjectKey,
		artifact.Filename,
		artifact.ContentType,
		artifact.RetentionClass,
		string(artifact.Status),
		artifact.SizeBytes,
		artifact.SHA256Hex,
		artifact.CreatedAt.UTC().Format(time.RFC3339Nano),
		artifact.UpdatedAt.UTC().Format(time.RFC3339Nano),
		artifact.ExpiresAt.UTC().Format(time.RFC3339Nano),
	)
	if err != nil {
		return fmt.Errorf("insert artifact metadata: %w", err)
	}
	return nil
}

func (s *SQLiteMetadataStore) Get(id string) (Artifact, error) {
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
		CreatedAt      string
		UpdatedAt      string
		ExpiresAt      string
	}
	err := s.db.QueryRow(`
SELECT id, object_key, filename, content_type, retention_class, status,
       size_bytes, sha256_hex, created_at, updated_at, expires_at
FROM artifact_metadata
WHERE id = ?
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
	createdAt, err := time.Parse(time.RFC3339Nano, row.CreatedAt)
	if err != nil {
		return Artifact{}, fmt.Errorf("parse created_at: %w", err)
	}
	updatedAt, err := time.Parse(time.RFC3339Nano, row.UpdatedAt)
	if err != nil {
		return Artifact{}, fmt.Errorf("parse updated_at: %w", err)
	}
	expiresAt, err := time.Parse(time.RFC3339Nano, row.ExpiresAt)
	if err != nil {
		return Artifact{}, fmt.Errorf("parse expires_at: %w", err)
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
		CreatedAt:      createdAt.UTC(),
		UpdatedAt:      updatedAt.UTC(),
		ExpiresAt:      expiresAt.UTC(),
	}, nil
}

func (s *SQLiteMetadataStore) MarkUploaded(id string, result UploadResult) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	res, err := s.db.Exec(`
UPDATE artifact_metadata
SET status = ?, size_bytes = ?, sha256_hex = ?, updated_at = ?
WHERE id = ?
`,
		string(StatusReady),
		result.SizeBytes,
		result.SHA256Hex,
		result.UploadedAt.UTC().Format(time.RFC3339Nano),
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

func (s *SQLiteMetadataStore) CreateSourceSnapshot(snapshot SourceSnapshot) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	_, err := s.db.Exec(`
INSERT INTO source_snapshot_metadata (
	id, source_id, source_class, fetch_mode, source_url, object_key, content_type,
	content_length, sha256_hex, etag, last_modified, parser_version,
	snapshot_status, retention_class, cadence_hint, dataset_name, partition_key,
	trace_id, error_class, fetched_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`,
		snapshot.ID,
		snapshot.SourceID,
		snapshot.SourceClass,
		snapshot.FetchMode,
		snapshot.SourceURL,
		snapshot.ObjectKey,
		snapshot.ContentType,
		snapshot.ContentLength,
		snapshot.SHA256Hex,
		snapshot.ETag,
		snapshot.LastModified,
		snapshot.ParserVersion,
		string(snapshot.SnapshotStatus),
		snapshot.RetentionClass,
		snapshot.CadenceHint,
		snapshot.DatasetName,
		snapshot.PartitionKey,
		snapshot.TraceID,
		snapshot.ErrorClass,
		snapshot.FetchedAt.UTC().Format(time.RFC3339Nano),
		snapshot.UpdatedAt.UTC().Format(time.RFC3339Nano),
	)
	if err != nil {
		return fmt.Errorf("insert source snapshot metadata: %w", err)
	}
	return nil
}

func (s *SQLiteMetadataStore) GetSourceSnapshot(id string) (SourceSnapshot, error) {
	if s == nil || s.db == nil {
		return SourceSnapshot{}, fmt.Errorf("metadata store unavailable")
	}
	var row struct {
		ID             string
		SourceID       string
		SourceClass    string
		FetchMode      string
		SourceURL      string
		ObjectKey      string
		ContentType    string
		ContentLength  int64
		SHA256Hex      string
		ETag           string
		LastModified   string
		ParserVersion  string
		SnapshotStatus string
		RetentionClass string
		CadenceHint    string
		DatasetName    string
		PartitionKey   string
		TraceID        string
		ErrorClass     string
		FetchedAt      string
		UpdatedAt      string
	}
	err := s.db.QueryRow(`
SELECT id, source_id, source_class, fetch_mode, source_url, object_key,
       content_type, content_length, sha256_hex, etag, last_modified,
       parser_version, snapshot_status, retention_class, cadence_hint,
       dataset_name, partition_key, trace_id, error_class, fetched_at, updated_at
FROM source_snapshot_metadata
WHERE id = ?
`, id).Scan(
		&row.ID,
		&row.SourceID,
		&row.SourceClass,
		&row.FetchMode,
		&row.SourceURL,
		&row.ObjectKey,
		&row.ContentType,
		&row.ContentLength,
		&row.SHA256Hex,
		&row.ETag,
		&row.LastModified,
		&row.ParserVersion,
		&row.SnapshotStatus,
		&row.RetentionClass,
		&row.CadenceHint,
		&row.DatasetName,
		&row.PartitionKey,
		&row.TraceID,
		&row.ErrorClass,
		&row.FetchedAt,
		&row.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return SourceSnapshot{}, ErrArtifactNotFound
		}
		return SourceSnapshot{}, fmt.Errorf("query source snapshot metadata: %w", err)
	}
	fetchedAt, err := time.Parse(time.RFC3339Nano, row.FetchedAt)
	if err != nil {
		return SourceSnapshot{}, fmt.Errorf("parse fetched_at: %w", err)
	}
	updatedAt, err := time.Parse(time.RFC3339Nano, row.UpdatedAt)
	if err != nil {
		return SourceSnapshot{}, fmt.Errorf("parse updated_at: %w", err)
	}
	return SourceSnapshot{
		ID:             row.ID,
		SourceID:       row.SourceID,
		SourceClass:    row.SourceClass,
		FetchMode:      row.FetchMode,
		SourceURL:      row.SourceURL,
		ObjectKey:      row.ObjectKey,
		ContentType:    row.ContentType,
		ContentLength:  row.ContentLength,
		SHA256Hex:      row.SHA256Hex,
		ETag:           row.ETag,
		LastModified:   row.LastModified,
		ParserVersion:  row.ParserVersion,
		SnapshotStatus: SourceSnapshotStatus(row.SnapshotStatus),
		RetentionClass: row.RetentionClass,
		CadenceHint:    row.CadenceHint,
		DatasetName:    row.DatasetName,
		PartitionKey:   row.PartitionKey,
		TraceID:        row.TraceID,
		ErrorClass:     row.ErrorClass,
		FetchedAt:      fetchedAt.UTC(),
		UpdatedAt:      updatedAt.UTC(),
	}, nil
}

func (s *SQLiteMetadataStore) MarkSourceSnapshotStatus(id string, status SourceSnapshotStatus, parserVersion, errorClass string, updatedAt time.Time) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	res, err := s.db.Exec(`
UPDATE source_snapshot_metadata
SET snapshot_status = ?, parser_version = ?, error_class = ?, updated_at = ?
WHERE id = ?
`,
		string(status),
		parserVersion,
		errorClass,
		updatedAt.UTC().Format(time.RFC3339Nano),
		id,
	)
	if err != nil {
		return fmt.Errorf("mark source snapshot status: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("source snapshot rows affected: %w", err)
	}
	if rows == 0 {
		return ErrArtifactNotFound
	}
	return nil
}

func (s *SQLiteMetadataStore) ListSourceSnapshots(sourceID string, status SourceSnapshotStatus, limit int) ([]SourceSnapshot, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("metadata store unavailable")
	}
	sourceID = strings.TrimSpace(sourceID)
	if sourceID == "" {
		return nil, fmt.Errorf("source id required")
	}
	if limit <= 0 {
		limit = 10
	}

	query := `
SELECT id, source_id, source_class, fetch_mode, source_url, object_key,
       content_type, content_length, sha256_hex, etag, last_modified,
       parser_version, snapshot_status, retention_class, cadence_hint,
       dataset_name, partition_key, trace_id, error_class, fetched_at, updated_at
FROM source_snapshot_metadata
WHERE source_id = ?`
	args := []any{sourceID}
	if status != "" {
		query += "\n  AND snapshot_status = ?"
		args = append(args, string(status))
	}
	query += "\nORDER BY fetched_at DESC, updated_at DESC\nLIMIT ?"
	args = append(args, limit)

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("list source snapshots: %w", err)
	}
	defer func() { _ = rows.Close() }()

	snapshots := make([]SourceSnapshot, 0, limit)
	for rows.Next() {
		snapshot, err := scanSourceSnapshot(rows)
		if err != nil {
			return nil, err
		}
		snapshots = append(snapshots, snapshot)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate source snapshots: %w", err)
	}
	return snapshots, nil
}

func (s *SQLiteMetadataStore) GetLatestSourceSnapshot(sourceID string, status SourceSnapshotStatus) (SourceSnapshot, error) {
	snapshots, err := s.ListSourceSnapshots(sourceID, status, 1)
	if err != nil {
		return SourceSnapshot{}, err
	}
	if len(snapshots) == 0 {
		return SourceSnapshot{}, ErrArtifactNotFound
	}
	return snapshots[0], nil
}

type sourceSnapshotScanner interface {
	Scan(dest ...any) error
}

func scanSourceSnapshot(scanner sourceSnapshotScanner) (SourceSnapshot, error) {
	var row struct {
		ID             string
		SourceID       string
		SourceClass    string
		FetchMode      string
		SourceURL      string
		ObjectKey      string
		ContentType    string
		ContentLength  int64
		SHA256Hex      string
		ETag           string
		LastModified   string
		ParserVersion  string
		SnapshotStatus string
		RetentionClass string
		CadenceHint    string
		DatasetName    string
		PartitionKey   string
		TraceID        string
		ErrorClass     string
		FetchedAt      string
		UpdatedAt      string
	}
	if err := scanner.Scan(
		&row.ID,
		&row.SourceID,
		&row.SourceClass,
		&row.FetchMode,
		&row.SourceURL,
		&row.ObjectKey,
		&row.ContentType,
		&row.ContentLength,
		&row.SHA256Hex,
		&row.ETag,
		&row.LastModified,
		&row.ParserVersion,
		&row.SnapshotStatus,
		&row.RetentionClass,
		&row.CadenceHint,
		&row.DatasetName,
		&row.PartitionKey,
		&row.TraceID,
		&row.ErrorClass,
		&row.FetchedAt,
		&row.UpdatedAt,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return SourceSnapshot{}, ErrArtifactNotFound
		}
		return SourceSnapshot{}, fmt.Errorf("scan source snapshot metadata: %w", err)
	}
	fetchedAt, err := time.Parse(time.RFC3339Nano, row.FetchedAt)
	if err != nil {
		return SourceSnapshot{}, fmt.Errorf("parse fetched_at: %w", err)
	}
	updatedAt, err := time.Parse(time.RFC3339Nano, row.UpdatedAt)
	if err != nil {
		return SourceSnapshot{}, fmt.Errorf("parse updated_at: %w", err)
	}
	return SourceSnapshot{
		ID:             row.ID,
		SourceID:       row.SourceID,
		SourceClass:    row.SourceClass,
		FetchMode:      row.FetchMode,
		SourceURL:      row.SourceURL,
		ObjectKey:      row.ObjectKey,
		ContentType:    row.ContentType,
		ContentLength:  row.ContentLength,
		SHA256Hex:      row.SHA256Hex,
		ETag:           row.ETag,
		LastModified:   row.LastModified,
		ParserVersion:  row.ParserVersion,
		SnapshotStatus: SourceSnapshotStatus(row.SnapshotStatus),
		RetentionClass: row.RetentionClass,
		CadenceHint:    row.CadenceHint,
		DatasetName:    row.DatasetName,
		PartitionKey:   row.PartitionKey,
		TraceID:        row.TraceID,
		ErrorClass:     row.ErrorClass,
		FetchedAt:      fetchedAt.UTC(),
		UpdatedAt:      updatedAt.UTC(),
	}, nil
}
