package crypto

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/rs/zerolog"
	"go.mau.fi/util/dbutil"
	"maunium.net/go/mautrix"
	"maunium.net/go/mautrix/crypto"
	"maunium.net/go/mautrix/event"
	"maunium.net/go/mautrix/id"

	_ "github.com/jackc/pgx/v5/stdlib" // exec-19 Stufe 2B: PG driver for mautrix-go
	_ "modernc.org/sqlite"             // Pure-Go SQLite (fallback when no PG URL)
)

// Machine kapselt OlmMachine (via goolm — Pure-Go, kein libolm) für den Appservice.
// Build-Tag: -tags goolm (= Go-Äquivalent zu Vodozemac)
//
// exec-19 Stufe 2B: supports both SQLite (MATRIX_CRYPTO_DB_PATH) and
// Postgres (MATRIX_CRYPTO_DB_URL). When both are set, Postgres wins.
// Postgres uses the `matrix_crypto` schema (created automatically).
type Machine struct {
	olm                    *crypto.OlmMachine
	StateStore             *StateStore
	backupPath             string
	backupPassphrase       string
	deleteKeysAfterDecrypt bool
}

// New initialises the OlmMachine.
//
//   - dbURL: Postgres DSN (preferred). If non-empty and starts with
//     "postgres://" or "postgresql://", Postgres is used with the
//     `matrix_crypto` schema. mautrix-go requires the database/sql
//     wrapper (pgx/v5/stdlib), not native pgxpool.
//   - dbPath: SQLite file path (fallback when dbURL is empty).
func New(ctx context.Context, client *mautrix.Client, dbURL, dbPath string, pickleKey []byte, keyBackupPassword string, deleteKeysAfterDecrypt bool) (*Machine, error) {
	rawDB, dialect, err := openCryptoDB(ctx, dbURL, dbPath)
	if err != nil {
		return nil, err
	}

	db, err := dbutil.NewWithDB(rawDB, dialect)
	if err != nil {
		return nil, fmt.Errorf("dbutil wrap: %w", err)
	}

	cryptoStore := crypto.NewSQLCryptoStore(
		db,
		dbutil.NoopLogger,
		client.UserID.String(),
		"APPSERVICE",
		pickleKey,
	)

	// Schema-Upgrade BEFORE Load — leere DB hat keine Tables.
	if err := cryptoStore.DB.Upgrade(ctx); err != nil {
		return nil, fmt.Errorf("crypto store schema upgrade: %w", err)
	}

	stateStore := NewStateStore(client)

	zlog := zerolog.Nop()
	olmMachine := crypto.NewOlmMachine(client, &zlog, cryptoStore, stateStore)
	olmMachine.SendKeysMinTrust = id.TrustStateUnset

	if err := olmMachine.Load(ctx); err != nil {
		return nil, fmt.Errorf("olm machine load: %w", err)
	}

	backupPath := filepath.Join(resolveBackupDir(dbURL, dbPath), "megolm_keys_backup.bin")

	m := &Machine{
		olm:                    olmMachine,
		StateStore:             stateStore,
		backupPath:             backupPath,
		backupPassphrase:       keyBackupPassword,
		deleteKeysAfterDecrypt: deleteKeysAfterDecrypt,
	}

	if err := m.importKeyBackup(ctx); err != nil {
		slog.Warn("E2EE: key backup import failed", "error", err)
	}

	if err := olmMachine.ShareKeys(ctx, -1); err != nil {
		slog.Warn("E2EE: device key upload failed", "error", err)
	} else {
		slog.Info("E2EE: device keys uploaded")
	}

	seedsPath := filepath.Join(resolveBackupDir(dbURL, dbPath), "cross_signing_seeds.json")
	if err := ensureCrossSigning(ctx, olmMachine, seedsPath); err != nil {
		slog.Warn("E2EE: cross-signing bootstrap failed", "error", err)
	}

	return m, nil
}

// openCryptoDB opens the appropriate database backend for the crypto store.
//
// exec-19 Stufe 2B: if dbURL starts with "postgres://" or "postgresql://",
// we use pgx/v5/stdlib (mautrix-go requires *sql.DB, not pgxpool).
// The `matrix_crypto` schema is created automatically.
// Otherwise falls back to SQLite at dbPath.
func openCryptoDB(ctx context.Context, dbURL, dbPath string) (*sql.DB, string, error) {
	dbURL = strings.TrimSpace(dbURL)

	if strings.HasPrefix(dbURL, "postgres://") || strings.HasPrefix(dbURL, "postgresql://") {
		slog.Info("E2EE: using Postgres crypto store", "url", redactDSN(dbURL))

		rawDB, err := sql.Open("pgx", dbURL)
		if err != nil {
			return nil, "", fmt.Errorf("open crypto postgres: %w", err)
		}
		// Create the dedicated schema so mautrix-go's tables don't
		// collide with Hindsight/Agent tables in public/*.
		if _, err := rawDB.ExecContext(ctx, "CREATE SCHEMA IF NOT EXISTS matrix_crypto"); err != nil {
			_ = rawDB.Close()
			return nil, "", fmt.Errorf("create matrix_crypto schema: %w", err)
		}
		// Set search_path so all subsequent CREATE TABLE / SELECT calls
		// from mautrix-go land in the matrix_crypto schema.
		if _, err := rawDB.ExecContext(ctx, "SET search_path TO matrix_crypto, public"); err != nil {
			_ = rawDB.Close()
			return nil, "", fmt.Errorf("set search_path: %w", err)
		}

		return rawDB, "postgres", nil
	}

	// SQLite fallback
	dbPath = strings.TrimSpace(dbPath)
	if dbPath == "" {
		dbPath = "./data/crypto.sqlite3"
	}
	if err := os.MkdirAll(filepath.Dir(dbPath), 0o750); err != nil {
		return nil, "", fmt.Errorf("crypto db dir: %w", err)
	}
	rawDB, err := sql.Open("sqlite", dbPath+"?_foreign_keys=on&_txlock=immediate")
	if err != nil {
		return nil, "", fmt.Errorf("open crypto sqlite %s: %w", dbPath, err)
	}
	rawDB.SetMaxOpenConns(1)

	slog.Info("E2EE: using SQLite crypto store", "path", dbPath)
	return rawDB, "sqlite3", nil
}

// resolveBackupDir determines the directory for key backup + cross-signing
// seeds. For SQLite this is the DB file's parent dir; for Postgres we use
// a conventional `./data/crypto/` directory.
func resolveBackupDir(dbURL, dbPath string) string {
	dbURL = strings.TrimSpace(dbURL)
	if strings.HasPrefix(dbURL, "postgres://") || strings.HasPrefix(dbURL, "postgresql://") {
		dir := "./data/crypto"
		_ = os.MkdirAll(dir, 0o750)
		return dir
	}
	return filepath.Dir(dbPath)
}

// redactDSN hides credentials from a Postgres DSN for logging.
func redactDSN(dsn string) string {
	if idx := strings.Index(dsn, "@"); idx > 0 {
		return "postgres://***@" + dsn[idx+1:]
	}
	return dsn
}

// ensureCrossSigning stellt sicher dass das Bot-Gerät Cross-Signing-Keys hat
// und mit dem eigenen Self-Signing Key signiert ist.
func ensureCrossSigning(ctx context.Context, mach *crypto.OlmMachine, seedsPath string) error {
	data, err := os.ReadFile(seedsPath)
	if err == nil {
		var seeds crypto.CrossSigningSeeds
		err = json.Unmarshal(data, &seeds)
		if err != nil {
			return fmt.Errorf("cross-signing seeds parse: %w", err)
		}
		err = mach.ImportCrossSigningKeys(seeds)
		if err != nil {
			return fmt.Errorf("cross-signing import: %w", err)
		}
		if own := mach.OwnIdentity(); own != nil {
			err = mach.SignOwnDevice(ctx, own)
			if err != nil {
				return fmt.Errorf("cross-signing sign device: %w", err)
			}
		}
		err = mach.SignOwnMasterKey(ctx)
		if err != nil {
			return fmt.Errorf("cross-signing sign master key: %w", err)
		}
		slog.Info("E2EE: cross-signing keys loaded from disk")
		return nil
	}
	if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("cross-signing seeds read: %w", err)
	}

	_, _, err = mach.GenerateAndUploadCrossSigningKeys(ctx, nil, "")
	if err != nil {
		return fmt.Errorf("cross-signing generate: %w", err)
	}

	if own := mach.OwnIdentity(); own != nil {
		err = mach.SignOwnDevice(ctx, own)
		if err != nil {
			return fmt.Errorf("cross-signing sign device: %w", err)
		}
	}
	err = mach.SignOwnMasterKey(ctx)
	if err != nil {
		return fmt.Errorf("cross-signing sign master key: %w", err)
	}

	seeds := mach.ExportCrossSigningKeys()
	seedsJSON, err := json.Marshal(seeds)
	if err != nil {
		return fmt.Errorf("cross-signing seeds marshal: %w", err)
	}
	if err := os.WriteFile(seedsPath, seedsJSON, 0o600); err != nil {
		return fmt.Errorf("cross-signing seeds write: %w", err)
	}
	slog.Info("E2EE: cross-signing keys generated and uploaded", "seeds_path", seedsPath)
	return nil
}

func (m *Machine) ExportKeyBackup(ctx context.Context) error {
	if m.backupPassphrase == "" {
		return nil
	}
	sessions, err := m.olm.CryptoStore.GetAllGroupSessions(ctx).AsList()
	if err != nil {
		return fmt.Errorf("get all sessions: %w", err)
	}
	if len(sessions) == 0 {
		slog.Debug("E2EE: no sessions to backup")
		return nil
	}
	data, err := crypto.ExportKeys(m.backupPassphrase, sessions)
	if err != nil {
		return fmt.Errorf("export keys: %w", err)
	}
	if err := os.WriteFile(m.backupPath, data, 0o600); err != nil {
		return fmt.Errorf("write key backup: %w", err)
	}
	slog.Info("E2EE: key backup exported", "sessions", len(sessions), "path", m.backupPath)
	return nil
}

func (m *Machine) importKeyBackup(ctx context.Context) error {
	if m.backupPassphrase == "" {
		return nil
	}
	data, err := os.ReadFile(m.backupPath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			slog.Debug("E2EE: no key backup file found, skipping import")
			return nil
		}
		return fmt.Errorf("read key backup: %w", err)
	}
	imported, total, err := m.olm.ImportKeys(ctx, m.backupPassphrase, data)
	if err != nil {
		return fmt.Errorf("import keys: %w", err)
	}
	slog.Info("E2EE: key backup imported", "imported", imported, "total", total, "path", m.backupPath)
	return nil
}

func (m *Machine) HandleToDevice(ctx context.Context, ev *event.Event) {
	m.olm.HandleToDeviceEvent(ctx, ev)
}

func (m *Machine) Decrypt(ctx context.Context, ev *event.Event) (*event.Event, error) {
	decrypted, err := m.olm.DecryptMegolmEvent(ctx, ev)
	if err != nil {
		return nil, fmt.Errorf("megolm decrypt (room=%s event=%s): %w", ev.RoomID, ev.ID, err)
	}
	slog.Debug("E2EE: event decrypted", "room", ev.RoomID, "event_id", ev.ID, "type", decrypted.Type.Type)

	if m.deleteKeysAfterDecrypt {
		if enc, ok := ev.Content.Parsed.(*event.EncryptedEventContent); ok {
			if err := m.olm.CryptoStore.RedactGroupSession(ctx, ev.RoomID, enc.SessionID, "forward_secrecy"); err != nil {
				slog.Warn("E2EE: key redaction after decrypt failed", "room", ev.RoomID, "session", enc.SessionID, "error", err)
			} else {
				slog.Info("E2EE: key redacted after decrypt (Forward Secrecy)", "room", ev.RoomID, "session", enc.SessionID)
			}
		}
	}

	return decrypted, nil
}

func (m *Machine) Encrypt(ctx context.Context, roomID id.RoomID, eventType event.Type, content any) (*event.EncryptedEventContent, error) {
	encrypted, err := m.olm.EncryptMegolmEvent(ctx, roomID, eventType, content)
	if err != nil {
		return nil, fmt.Errorf("megolm encrypt (room=%s): %w", roomID, err)
	}
	return encrypted, nil
}

// EnsureSession teilt eine Megolm-Session mit allen Raum-Mitgliedern.
// Vor dem Session-Share werden Device-Keys aller Mitglieder force-refreshed
// als Workaround fuer tuwunel#377 (device_lists.changed fehlt in /sync).
func (m *Machine) EnsureSession(ctx context.Context, roomID id.RoomID, members []id.UserID) error {
	if _, err := m.olm.FetchKeys(ctx, members, true); err != nil {
		slog.Warn("E2EE: pre-session key fetch failed (tuwunel#377 workaround)", "room", roomID, "error", err)
	}
	if err := m.olm.ShareGroupSession(ctx, roomID, members); err != nil {
		return fmt.Errorf("share group session (room=%s): %w", roomID, err)
	}
	return nil
}
