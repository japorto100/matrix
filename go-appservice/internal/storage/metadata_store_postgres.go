package storage

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// PostgresMetadataStore uses native pgxpool (no database/sql wrapper).
// Rationale: native pgx gives us jsonb/uuid/tstzrange without marshaling,
// context-aware queries, row-to-struct scanning, and better tracing.
// Methods that don't accept a ctx use a background context internally to
// stay compatible with the MetadataStore interface. New methods added in
// exec-19 Stufe 3 (ListByUser, CountByStatus, Delete) also use background
// context — handler layer sets per-request context inside the Service when
// we wire that through in exec-18.
type PostgresMetadataStore struct {
	pool *pgxpool.Pool
}

// artifactRow mirrors artifact_metadata columns for pgx.RowToStructByName.
// pgx matches by lowercased struct field name, so ObjectKey→object_key via
// the db tag. time.Time binds directly to TIMESTAMPTZ with native pgx.
type artifactRow struct {
	ID             string    `db:"id"`
	UserID         string    `db:"user_id"`
	MediaType      string    `db:"media_type"`
	ObjectKey      string    `db:"object_key"`
	Filename       string    `db:"filename"`
	ContentType    string    `db:"content_type"`
	RetentionClass string    `db:"retention_class"`
	Status         string    `db:"status"`
	SizeBytes      int64     `db:"size_bytes"`
	SHA256Hex      string    `db:"sha256_hex"`
	CreatedAt      time.Time `db:"created_at"`
	UpdatedAt      time.Time `db:"updated_at"`
	ExpiresAt      time.Time `db:"expires_at"`
}

func (r artifactRow) toArtifact() Artifact {
	return Artifact{
		ID:             r.ID,
		UserID:         r.UserID,
		MediaType:      MediaType(r.MediaType),
		ObjectKey:      r.ObjectKey,
		Filename:       r.Filename,
		ContentType:    r.ContentType,
		RetentionClass: r.RetentionClass,
		Status:         ArtifactStatus(r.Status),
		SizeBytes:      r.SizeBytes,
		SHA256Hex:      r.SHA256Hex,
		CreatedAt:      r.CreatedAt.UTC(),
		UpdatedAt:      r.UpdatedAt.UTC(),
		ExpiresAt:      r.ExpiresAt.UTC(),
	}
}

// artifactSelectCols is the ordered column list used everywhere we fetch
// artifacts so pgx.RowToStructByName matches fields by name.
const artifactSelectCols = `id, user_id, media_type, object_key, filename, content_type,
retention_class, status, size_bytes, sha256_hex, created_at, updated_at, expires_at`

func NewPostgresMetadataStore(dsn string) (*PostgresMetadataStore, error) {
	trimmed := strings.TrimSpace(dsn)
	if trimmed == "" {
		return nil, fmt.Errorf("postgres metadata dsn required")
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, trimmed)
	if err != nil {
		return nil, fmt.Errorf("create pgx pool: %w", err)
	}
	store := &PostgresMetadataStore{pool: pool}
	if err := store.migrate(ctx); err != nil {
		pool.Close()
		return nil, err
	}
	return store, nil
}

func (s *PostgresMetadataStore) migrate(ctx context.Context) error {
	if s == nil || s.pool == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	// exec-19 Stufe 3: the table lives in a dedicated `storage` schema so it
	// does not visually collide with Python-owned tables in `public` (Hindsight)
	// or `agent` / `ingestion` schemas. See specs/17-schema-ownership.md for the
	// service/schema mapping.
	if _, err := s.pool.Exec(ctx, `CREATE SCHEMA IF NOT EXISTS storage`); err != nil {
		return fmt.Errorf("create storage schema: %w", err)
	}
	// One-time migration: move the table from public to storage if it was
	// previously created by an earlier migrate() run. ALTER TABLE SET SCHEMA
	// moves the table with all its indexes and constraints intact.
	if _, err := s.pool.Exec(ctx, `
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'artifact_metadata'
  ) THEN
    EXECUTE 'ALTER TABLE public.artifact_metadata SET SCHEMA storage';
  END IF;
END $$;`); err != nil {
		return fmt.Errorf("move artifact_metadata to storage schema: %w", err)
	}
	// Create the table if this is a fresh install.
	if _, err := s.pool.Exec(ctx, `
CREATE TABLE IF NOT EXISTS storage.artifact_metadata (
	id TEXT PRIMARY KEY,
	user_id TEXT NOT NULL DEFAULT '',
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
)`); err != nil {
		return fmt.Errorf("create storage.artifact_metadata: %w", err)
	}
	// Add user_id column for pre-existing databases (from earlier revisions
	// that didn't have it). Idempotent.
	if _, err := s.pool.Exec(ctx, `
ALTER TABLE storage.artifact_metadata
	ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT ''`); err != nil {
		return fmt.Errorf("add user_id column: %w", err)
	}
	// exec-19 review Medium #4: media_type column for exact overview counts
	// without full-table fetch+classify on every call.
	if _, err := s.pool.Exec(ctx, `
ALTER TABLE storage.artifact_metadata
	ADD COLUMN IF NOT EXISTS media_type TEXT NOT NULL DEFAULT 'other'`); err != nil {
		return fmt.Errorf("add media_type column: %w", err)
	}
	if _, err := s.pool.Exec(ctx, `
CREATE INDEX IF NOT EXISTS idx_artifact_metadata_user_created
	ON storage.artifact_metadata (user_id, created_at DESC)`); err != nil {
		return fmt.Errorf("create user index: %w", err)
	}
	if _, err := s.pool.Exec(ctx, `
CREATE INDEX IF NOT EXISTS idx_artifact_metadata_user_status
	ON storage.artifact_metadata (user_id, status)`); err != nil {
		return fmt.Errorf("create status index: %w", err)
	}
	if _, err := s.pool.Exec(ctx, `
CREATE INDEX IF NOT EXISTS idx_artifact_metadata_user_media_type
	ON storage.artifact_metadata (user_id, media_type)`); err != nil {
		return fmt.Errorf("create media_type index: %w", err)
	}
	// Backfill: classify any rows that were inserted before this column
	// existed (media_type default = 'other'). Idempotent — re-running
	// updates nothing if every row already has a non-default classification.
	if err := s.backfillMediaType(ctx); err != nil {
		return fmt.Errorf("backfill media_type: %w", err)
	}
	return nil
}

// backfillMediaType walks rows with media_type='other' and re-classifies
// them from content_type + filename. Called once per startup; idempotent
// because only 'other' rows are touched and re-running against already
// classified rows is a no-op.
func (s *PostgresMetadataStore) backfillMediaType(ctx context.Context) error {
	rows, err := s.pool.Query(ctx, `
SELECT id, content_type, filename
FROM storage.artifact_metadata
WHERE media_type = 'other'`)
	if err != nil {
		return fmt.Errorf("select rows for backfill: %w", err)
	}
	type toUpdate struct {
		ID          string
		ContentType string
		Filename    string
	}
	var pending []toUpdate
	for rows.Next() {
		var t toUpdate
		if err := rows.Scan(&t.ID, &t.ContentType, &t.Filename); err != nil {
			rows.Close()
			return fmt.Errorf("scan backfill row: %w", err)
		}
		pending = append(pending, t)
	}
	rows.Close()
	if err := rows.Err(); err != nil {
		return fmt.Errorf("iterate backfill rows: %w", err)
	}
	for _, t := range pending {
		mt := ClassifyMediaType(t.ContentType, t.Filename)
		if mt == MediaTypeOther {
			continue // genuinely "other", leave as-is
		}
		if _, err := s.pool.Exec(ctx,
			`UPDATE storage.artifact_metadata SET media_type = $1 WHERE id = $2`,
			string(mt), t.ID); err != nil {
			return fmt.Errorf("update row %s: %w", t.ID, err)
		}
	}
	return nil
}

func (s *PostgresMetadataStore) Close() error {
	if s != nil && s.pool != nil {
		s.pool.Close()
	}
	return nil
}

func (s *PostgresMetadataStore) Create(artifact Artifact) error {
	if s == nil || s.pool == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	// If the caller hasn't set MediaType, classify it from content-type +
	// filename. The Service.CreateArtifact path sets it explicitly; fakes
	// in tests may not.
	mediaType := artifact.MediaType
	if mediaType == "" {
		mediaType = ClassifyMediaType(artifact.ContentType, artifact.Filename)
	}
	_, err := s.pool.Exec(context.Background(), `
INSERT INTO storage.artifact_metadata (
	id, user_id, media_type, object_key, filename, content_type, retention_class, status,
	size_bytes, sha256_hex, created_at, updated_at, expires_at
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)`,
		artifact.ID,
		artifact.UserID,
		string(mediaType),
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

// CountByMediaType returns an exact histogram of media_type -> count for
// one user via SQL aggregation (no full-table fetch). exec-19 review
// Medium #4.
func (s *PostgresMetadataStore) CountByMediaType(userID string) (map[MediaType]int, error) {
	if s == nil || s.pool == nil {
		return nil, fmt.Errorf("metadata store unavailable")
	}
	userID = strings.TrimSpace(userID)
	if userID == "" {
		return nil, fmt.Errorf("user_id required")
	}
	rows, err := s.pool.Query(context.Background(), `
SELECT media_type, COUNT(*)
FROM storage.artifact_metadata
WHERE user_id = $1
GROUP BY media_type`, userID)
	if err != nil {
		return nil, fmt.Errorf("count by media_type: %w", err)
	}
	defer rows.Close()
	out := make(map[MediaType]int)
	for rows.Next() {
		var mt string
		var count int
		if scanErr := rows.Scan(&mt, &count); scanErr != nil {
			return nil, fmt.Errorf("scan media_type row: %w", scanErr)
		}
		out[MediaType(mt)] = count
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate media_type rows: %w", err)
	}
	return out, nil
}

func (s *PostgresMetadataStore) Get(id string) (Artifact, error) {
	if s == nil || s.pool == nil {
		return Artifact{}, fmt.Errorf("metadata store unavailable")
	}
	ctx := context.Background()
	rows, err := s.pool.Query(ctx,
		`SELECT `+artifactSelectCols+` FROM storage.artifact_metadata WHERE id = $1`, id)
	if err != nil {
		return Artifact{}, fmt.Errorf("query artifact metadata: %w", err)
	}
	row, err := pgx.CollectOneRow(rows, pgx.RowToStructByName[artifactRow])
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return Artifact{}, ErrArtifactNotFound
		}
		return Artifact{}, fmt.Errorf("scan artifact metadata: %w", err)
	}
	return row.toArtifact(), nil
}

func (s *PostgresMetadataStore) MarkUploaded(id string, result UploadResult) error {
	if s == nil || s.pool == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	tag, err := s.pool.Exec(context.Background(), `
UPDATE storage.artifact_metadata
SET status = $1, size_bytes = $2, sha256_hex = $3, updated_at = $4
WHERE id = $5`,
		string(StatusReady),
		result.SizeBytes,
		result.SHA256Hex,
		result.UploadedAt.UTC(),
		id,
	)
	if err != nil {
		return fmt.Errorf("mark artifact uploaded: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return ErrArtifactNotFound
	}
	return nil
}

// ListByUser implements exec-19 Stufe 3 per-user listing. Returns
// (items, total, error) where total is the unfiltered count matching the
// SQL-expressible filters (MediaType is applied in Go by the caller).
func (s *PostgresMetadataStore) ListByUser(query FilesListQuery) ([]Artifact, int, error) {
	if s == nil || s.pool == nil {
		return nil, 0, fmt.Errorf("metadata store unavailable")
	}
	userID := strings.TrimSpace(query.UserID)
	if userID == "" {
		return nil, 0, fmt.Errorf("user_id required")
	}
	limit := query.Limit
	if limit <= 0 {
		limit = 50
	}
	if limit > 500 {
		limit = 500
	}
	offset := max(query.Offset, 0)

	conditions := []string{"user_id = $1"}
	args := []any{userID}
	idx := 2
	if strings.TrimSpace(query.Status) != "" {
		conditions = append(conditions, fmt.Sprintf("status = $%d", idx))
		args = append(args, query.Status)
		idx++
	}
	if strings.TrimSpace(query.Search) != "" {
		conditions = append(conditions, fmt.Sprintf("filename ILIKE $%d", idx))
		args = append(args, "%"+query.Search+"%")
		idx++
	}
	where := "WHERE " + strings.Join(conditions, " AND ")

	// MediaType is derived from content_type + filename so we can't filter in
	// SQL. Over-fetch by 4x and let the caller truncate — good enough for
	// typical user libraries.
	sqlLimit := limit
	if query.MediaType != "" && query.MediaType != MediaTypeOther {
		sqlLimit = limit * 4
	}

	ctx := context.Background()
	var total int
	countSQL := fmt.Sprintf("SELECT COUNT(*) FROM storage.artifact_metadata %s", where)
	if err := s.pool.QueryRow(ctx, countSQL, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("count artifacts: %w", err)
	}

	listSQL := fmt.Sprintf(`
SELECT %s
FROM storage.artifact_metadata
%s
ORDER BY created_at DESC
LIMIT $%d OFFSET $%d`, artifactSelectCols, where, idx, idx+1)
	args = append(args, sqlLimit, offset)

	rows, err := s.pool.Query(ctx, listSQL, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("list artifacts: %w", err)
	}
	collected, err := pgx.CollectRows(rows, pgx.RowToStructByName[artifactRow])
	if err != nil {
		return nil, 0, fmt.Errorf("collect artifact rows: %w", err)
	}
	result := make([]Artifact, 0, len(collected))
	for _, r := range collected {
		result = append(result, r.toArtifact())
	}
	return result, total, nil
}

// CountByStatus returns a histogram of status -> count for one user.
func (s *PostgresMetadataStore) CountByStatus(userID string) (map[string]int, error) {
	if s == nil || s.pool == nil {
		return nil, fmt.Errorf("metadata store unavailable")
	}
	userID = strings.TrimSpace(userID)
	if userID == "" {
		return nil, fmt.Errorf("user_id required")
	}
	ctx := context.Background()
	rows, err := s.pool.Query(ctx, `
SELECT status, COUNT(*)
FROM storage.artifact_metadata
WHERE user_id = $1
GROUP BY status`, userID)
	if err != nil {
		return nil, fmt.Errorf("count by status: %w", err)
	}
	defer rows.Close()
	out := make(map[string]int)
	for rows.Next() {
		var status string
		var count int
		if scanErr := rows.Scan(&status, &count); scanErr != nil {
			return nil, fmt.Errorf("scan status row: %w", scanErr)
		}
		out[status] = count
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate status rows: %w", err)
	}
	return out, nil
}

// Delete removes an artifact metadata row.
func (s *PostgresMetadataStore) Delete(id string) error {
	if s == nil || s.pool == nil {
		return fmt.Errorf("metadata store unavailable")
	}
	tag, err := s.pool.Exec(context.Background(),
		`DELETE FROM storage.artifact_metadata WHERE id = $1`, id)
	if err != nil {
		return fmt.Errorf("delete artifact: %w", err)
	}
	if tag.RowsAffected() == 0 {
		return ErrArtifactNotFound
	}
	return nil
}
