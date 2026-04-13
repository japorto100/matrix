package storage

import (
	"context"
	"errors"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Integration test — hits a real Postgres. Skips if HINDSIGHT_DB_URL is not
// set or the DB is unreachable. The devstack runs PG on :5433 with the
// hindsight_dev database, so `HINDSIGHT_DB_URL=postgresql://postgres@localhost:5433/hindsight_dev`
// is the default.
//
// Each test runs in its own transaction-free isolated user_id namespace so
// parallel test runs don't collide.
func testPostgresDSN(t *testing.T) string {
	t.Helper()
	dsn := strings.TrimSpace(os.Getenv("HINDSIGHT_DB_URL"))
	if dsn == "" {
		dsn = strings.TrimSpace(os.Getenv("POSTGRES_DSN"))
	}
	if dsn == "" {
		t.Skip("HINDSIGHT_DB_URL not set — skipping Postgres integration test")
	}
	// Quick ping so we don't spew obscure pgx errors when PG is down
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Skipf("Postgres unreachable (%s): %v", dsn, err)
	}
	defer pool.Close()
	if err := pool.Ping(ctx); err != nil {
		t.Skipf("Postgres ping failed: %v", err)
	}
	return dsn
}

func newTestStore(t *testing.T) *PostgresMetadataStore {
	t.Helper()
	dsn := testPostgresDSN(t)
	store, err := NewPostgresMetadataStore(dsn)
	if err != nil {
		t.Fatalf("NewPostgresMetadataStore: %v", err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return store
}

// cleanupUser wipes all artifact_metadata rows for a given user so tests are
// idempotent across re-runs.
func cleanupUser(t *testing.T, store *PostgresMetadataStore, userID string) {
	t.Helper()
	_, err := store.pool.Exec(context.Background(),
		`DELETE FROM storage.artifact_metadata WHERE user_id = $1`, userID)
	if err != nil {
		t.Fatalf("cleanup user %s: %v", userID, err)
	}
}

func testArtifact(userID, id, filename, contentType string, status ArtifactStatus) Artifact {
	now := time.Now().UTC().Truncate(time.Microsecond)
	return Artifact{
		ID:             id,
		UserID:         userID,
		ObjectKey:      "users/" + userID + "/2026/04/11/" + id,
		Filename:       filename,
		ContentType:    contentType,
		RetentionClass: "standard",
		Status:         status,
		SizeBytes:      1024,
		SHA256Hex:      "deadbeef",
		CreatedAt:      now,
		UpdatedAt:      now,
		ExpiresAt:      now.Add(24 * time.Hour),
	}
}

func TestPostgresStoreCreateAndGet(t *testing.T) {
	store := newTestStore(t)
	userID := "test-create-get"
	cleanupUser(t, store, userID)

	want := testArtifact(userID, "art_testcreate01", "hello.pdf", "application/pdf", StatusPendingUpload)
	if err := store.Create(want); err != nil {
		t.Fatalf("Create: %v", err)
	}

	got, err := store.Get(want.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.UserID != userID {
		t.Errorf("UserID = %q, want %q", got.UserID, userID)
	}
	if got.Filename != want.Filename {
		t.Errorf("Filename = %q, want %q", got.Filename, want.Filename)
	}
	if got.Status != want.Status {
		t.Errorf("Status = %q, want %q", got.Status, want.Status)
	}
	if got.SizeBytes != want.SizeBytes {
		t.Errorf("SizeBytes = %d, want %d", got.SizeBytes, want.SizeBytes)
	}
}

func TestPostgresStoreGetNotFound(t *testing.T) {
	store := newTestStore(t)
	_, err := store.Get("art_doesnotexist")
	if !errors.Is(err, ErrArtifactNotFound) {
		t.Errorf("Get(nonexistent) error = %v, want ErrArtifactNotFound", err)
	}
}

func TestPostgresStoreMarkUploaded(t *testing.T) {
	store := newTestStore(t)
	userID := "test-markuploaded"
	cleanupUser(t, store, userID)

	a := testArtifact(userID, "art_markup01", "foo.txt", "text/plain", StatusPendingUpload)
	if err := store.Create(a); err != nil {
		t.Fatalf("Create: %v", err)
	}
	err := store.MarkUploaded(a.ID, UploadResult{
		SizeBytes:  2048,
		SHA256Hex:  "cafebabe",
		UploadedAt: time.Now().UTC(),
	})
	if err != nil {
		t.Fatalf("MarkUploaded: %v", err)
	}
	got, err := store.Get(a.ID)
	if err != nil {
		t.Fatalf("Get after MarkUploaded: %v", err)
	}
	if got.Status != StatusReady {
		t.Errorf("Status = %q, want %q", got.Status, StatusReady)
	}
	if got.SizeBytes != 2048 {
		t.Errorf("SizeBytes = %d, want 2048", got.SizeBytes)
	}
	if got.SHA256Hex != "cafebabe" {
		t.Errorf("SHA256Hex = %q, want cafebabe", got.SHA256Hex)
	}
}

func TestPostgresStoreListByUser(t *testing.T) {
	store := newTestStore(t)
	userA := "test-list-userA"
	userB := "test-list-userB"
	cleanupUser(t, store, userA)
	cleanupUser(t, store, userB)

	// Insert 5 artifacts for userA, 2 for userB
	for i, f := range []string{"doc1.pdf", "song.mp3", "pic.png", "data.csv", "clip.mp4"} {
		a := testArtifact(userA, "art_A"+string(rune('0'+i)), f, "", StatusReady)
		// stagger created_at so ORDER BY created_at DESC is deterministic
		a.CreatedAt = a.CreatedAt.Add(time.Duration(i) * time.Second)
		if err := store.Create(a); err != nil {
			t.Fatalf("Create A%d: %v", i, err)
		}
	}
	for i, f := range []string{"other.txt", "b.pdf"} {
		a := testArtifact(userB, "art_B"+string(rune('0'+i)), f, "", StatusReady)
		if err := store.Create(a); err != nil {
			t.Fatalf("Create B%d: %v", i, err)
		}
	}

	// List userA — should see 5
	items, total, err := store.ListByUser(FilesListQuery{UserID: userA, Limit: 100})
	if err != nil {
		t.Fatalf("ListByUser(userA): %v", err)
	}
	if total != 5 {
		t.Errorf("total = %d, want 5", total)
	}
	if len(items) != 5 {
		t.Errorf("len(items) = %d, want 5", len(items))
	}
	for _, it := range items {
		if it.UserID != userA {
			t.Errorf("got artifact for user %q, want %q — cross-user leak!", it.UserID, userA)
		}
	}

	// List userB — should see 2
	items, total, err = store.ListByUser(FilesListQuery{UserID: userB, Limit: 100})
	if err != nil {
		t.Fatalf("ListByUser(userB): %v", err)
	}
	if total != 2 {
		t.Errorf("userB total = %d, want 2", total)
	}
	if len(items) != 2 {
		t.Errorf("userB len = %d, want 2", len(items))
	}

	// Search filter (filename ILIKE)
	items, _, err = store.ListByUser(FilesListQuery{UserID: userA, Search: "pdf", Limit: 100})
	if err != nil {
		t.Fatalf("ListByUser(search=pdf): %v", err)
	}
	if len(items) != 1 {
		t.Errorf("search=pdf len = %d, want 1", len(items))
	} else if items[0].Filename != "doc1.pdf" {
		t.Errorf("search=pdf got %q, want doc1.pdf", items[0].Filename)
	}

	// Empty user_id → error
	_, _, err = store.ListByUser(FilesListQuery{UserID: "", Limit: 10})
	if err == nil {
		t.Error("ListByUser(user_id=\"\") should error")
	}
}

func TestPostgresStoreCountByStatus(t *testing.T) {
	store := newTestStore(t)
	userID := "test-countstatus"
	cleanupUser(t, store, userID)

	specs := []struct {
		id     string
		status ArtifactStatus
	}{
		{"art_cs01", StatusReady},
		{"art_cs02", StatusReady},
		{"art_cs03", StatusReady},
		{"art_cs04", StatusPendingUpload},
		{"art_cs05", StatusUploadFailed},
	}
	for _, s := range specs {
		a := testArtifact(userID, s.id, s.id+".txt", "text/plain", s.status)
		if err := store.Create(a); err != nil {
			t.Fatalf("Create %s: %v", s.id, err)
		}
	}

	counts, err := store.CountByStatus(userID)
	if err != nil {
		t.Fatalf("CountByStatus: %v", err)
	}
	if counts[string(StatusReady)] != 3 {
		t.Errorf("ready = %d, want 3", counts[string(StatusReady)])
	}
	if counts[string(StatusPendingUpload)] != 1 {
		t.Errorf("pending = %d, want 1", counts[string(StatusPendingUpload)])
	}
	if counts[string(StatusUploadFailed)] != 1 {
		t.Errorf("failed = %d, want 1", counts[string(StatusUploadFailed)])
	}
}

func TestPostgresStoreCountByMediaType(t *testing.T) {
	store := newTestStore(t)
	userID := "test-countmedia"
	cleanupUser(t, store, userID)

	// 3 documents, 2 images, 1 audio — all ready
	specs := []struct {
		id          string
		filename    string
		contentType string
	}{
		{"mt1", "doc1.pdf", "application/pdf"},
		{"mt2", "doc2.pdf", "application/pdf"},
		{"mt3", "doc3.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
		{"mt4", "img1.png", "image/png"},
		{"mt5", "img2.jpg", "image/jpeg"},
		{"mt6", "song.mp3", "audio/mpeg"},
	}
	for _, s := range specs {
		a := testArtifact(userID, s.id, s.filename, s.contentType, StatusReady)
		// Clear MediaType so store.Create classifies from content_type/filename
		a.MediaType = ""
		if err := store.Create(a); err != nil {
			t.Fatalf("create %s: %v", s.id, err)
		}
	}

	counts, err := store.CountByMediaType(userID)
	if err != nil {
		t.Fatalf("CountByMediaType: %v", err)
	}
	if counts[MediaTypeDocument] != 3 {
		t.Errorf("document = %d, want 3", counts[MediaTypeDocument])
	}
	if counts[MediaTypeImage] != 2 {
		t.Errorf("image = %d, want 2", counts[MediaTypeImage])
	}
	if counts[MediaTypeAudio] != 1 {
		t.Errorf("audio = %d, want 1", counts[MediaTypeAudio])
	}
	// No video, no data, no other
	if counts[MediaTypeVideo] != 0 {
		t.Errorf("video = %d, want 0", counts[MediaTypeVideo])
	}
}

func TestPostgresStoreMediaTypeBackfill(t *testing.T) {
	// Simulates a pre-migration row by inserting with media_type = 'other'
	// manually, then re-running migrate() and checking the backfill fixed it.
	store := newTestStore(t)
	userID := "test-backfill"
	cleanupUser(t, store, userID)

	now := time.Now().UTC().Truncate(time.Microsecond)
	_, err := store.pool.Exec(context.Background(), `
INSERT INTO storage.artifact_metadata (
	id, user_id, media_type, object_key, filename, content_type, retention_class, status,
	size_bytes, sha256_hex, created_at, updated_at, expires_at
) VALUES ($1, $2, 'other', 'k/x.pdf', 'report.pdf', 'application/pdf', 'standard', 'ready', 0, '',
	$3, $3, $3)`, "bf_pdf01", userID, now)
	if err != nil {
		t.Fatalf("insert legacy row: %v", err)
	}

	// Force a re-run of migrate() including backfill
	if migErr := store.migrate(context.Background()); migErr != nil {
		t.Fatalf("re-migrate: %v", migErr)
	}

	// Now the row should have media_type = 'document'
	var mt string
	err = store.pool.QueryRow(context.Background(),
		`SELECT media_type FROM storage.artifact_metadata WHERE id = $1`, "bf_pdf01").Scan(&mt)
	if err != nil {
		t.Fatalf("verify backfill: %v", err)
	}
	if mt != "document" {
		t.Errorf("backfilled media_type = %q, want document", mt)
	}
}

func TestPostgresStoreDelete(t *testing.T) {
	store := newTestStore(t)
	userID := "test-delete"
	cleanupUser(t, store, userID)

	a := testArtifact(userID, "art_del01", "todelete.pdf", "application/pdf", StatusReady)
	if err := store.Create(a); err != nil {
		t.Fatalf("Create: %v", err)
	}

	if err := store.Delete(a.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := store.Get(a.ID); !errors.Is(err, ErrArtifactNotFound) {
		t.Errorf("after Delete, Get = %v, want ErrArtifactNotFound", err)
	}
	// Delete again → ErrArtifactNotFound
	if err := store.Delete(a.ID); !errors.Is(err, ErrArtifactNotFound) {
		t.Errorf("second Delete = %v, want ErrArtifactNotFound", err)
	}
}
