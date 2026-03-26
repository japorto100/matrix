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

	"github.com/rs/zerolog"
	"go.mau.fi/util/dbutil"
	"maunium.net/go/mautrix"
	"maunium.net/go/mautrix/crypto"
	"maunium.net/go/mautrix/event"
	"maunium.net/go/mautrix/id"

	_ "modernc.org/sqlite" // Pure-Go SQLite Treiber (kein CGO, Windows-kompatibel)
)

// Machine kapselt OlmMachine (via goolm — Pure-Go, kein libolm) für den Appservice.
// Build-Tag: -tags goolm (= Go-Äquivalent zu Vodozemac)
type Machine struct {
	olm              *crypto.OlmMachine
	StateStore       *StateStore
	backupPath       string // C-8: Pfad für Megolm Key Backup Datei
	backupPassphrase string // C-8: Passphrase für verschlüsseltes Backup
}

// New initialisiert OlmMachine mit SQLite-Backend.
// dbPath: Pfad zur SQLite-Datei (wird erstellt falls nicht vorhanden).
// pickleKey: Schlüssel zum Verschlüsseln des Olm-Accounts in der DB.
func New(ctx context.Context, client *mautrix.Client, dbPath string, pickleKey []byte, keyBackupPassword string) (*Machine, error) {
	// Verzeichnis erstellen
	if err := os.MkdirAll(filepath.Dir(dbPath), 0o750); err != nil {
		return nil, fmt.Errorf("crypto db dir: %w", err)
	}

	// SQLite öffnen (modernc.org/sqlite registriert als "sqlite")
	rawDB, err := sql.Open("sqlite", dbPath+"?_foreign_keys=on&_txlock=immediate")
	if err != nil {
		return nil, fmt.Errorf("open crypto db %s: %w", dbPath, err)
	}
	rawDB.SetMaxOpenConns(1) // SQLite: nur eine Schreibverbindung

	db, err := dbutil.NewWithDB(rawDB, "sqlite3")
	if err != nil {
		return nil, fmt.Errorf("dbutil wrap: %w", err)
	}

	// SQLCryptoStore — Upgrade-Schema wird intern via db.Child() gehandhabt
	cryptoStore := crypto.NewSQLCryptoStore(
		db,
		dbutil.NoopLogger,      // kein separates DB-Log
		client.UserID.String(), // accountID = Bot User-ID
		"APPSERVICE",           // deviceID (statisch für Appservice)
		pickleKey,
	)

	stateStore := NewStateStore(client)

	// OlmMachine — zerolog.Nop() = kein separates Crypto-Log (slog übernimmt)
	zlog := zerolog.Nop()
	olmMachine := crypto.NewOlmMachine(client, &zlog, cryptoStore, stateStore)

	// C-3 / MSC4153: Wir senden Keys an alle Geräte unabhängig vom Trust-Level.
	// Das eigentliche MSC4153-Problem (Element X schickt uns keine Keys) löst
	// der Cross-Signing Bootstrap weiter unten.
	olmMachine.SendKeysMinTrust = id.TrustStateUnset

	if err := olmMachine.Load(ctx); err != nil {
		return nil, fmt.Errorf("olm machine load: %w", err)
	}

	backupPath := filepath.Join(filepath.Dir(dbPath), "megolm_keys_backup.bin")

	m := &Machine{
		olm:              olmMachine,
		StateStore:       stateStore,
		backupPath:       backupPath,
		backupPassphrase: keyBackupPassword,
	}

	// C-8: Megolm Key Backup importieren (falls vorhanden)
	if err := m.importKeyBackup(ctx); err != nil {
		slog.Warn("E2EE: key backup import failed", "error", err)
	}

	// Device-Keys beim Homeserver registrieren (einmalig / bei Bedarf)
	if err := olmMachine.ShareKeys(ctx, -1); err != nil {
		slog.Warn("E2EE: device key upload failed", "error", err)
	} else {
		slog.Info("E2EE: device keys uploaded")
	}

	// C-3 / MSC4153: Cross-Signing Bootstrap.
	// Damit Element X (IdentityBasedStrategy) unserem Bot-Gerät Room-Keys schickt,
	// muss das Bot-Device mit dem eigenen Self-Signing Key signiert sein.
	// Seeds werden in <dbDir>/cross_signing_seeds.json gespeichert.
	seedsPath := filepath.Join(filepath.Dir(dbPath), "cross_signing_seeds.json")
	if err := ensureCrossSigning(ctx, olmMachine, seedsPath); err != nil {
		// Nicht fatal — Bot kann weiter laufen, nur MSC4153 greift ggf. nicht
		slog.Warn("E2EE: cross-signing bootstrap failed", "error", err)
	}

	return m, nil
}

// ensureCrossSigning stellt sicher dass das Bot-Gerät Cross-Signing-Keys hat
// und mit dem eigenen Self-Signing Key signiert ist.
//
// Erster Start: generiert MSK/SSK/USK, lädt Signaturen hoch, speichert Seeds.
// Folgestarts: importiert Seeds aus Datei, signiert Gerät erneut (in-memory).
func ensureCrossSigning(ctx context.Context, mach *crypto.OlmMachine, seedsPath string) error {
	data, err := os.ReadFile(seedsPath)
	if err == nil {
		// Seeds vorhanden → importieren und Gerät erneut signieren
		var seeds crypto.CrossSigningSeeds
		err = json.Unmarshal(data, &seeds)
		if err != nil {
			return fmt.Errorf("cross-signing seeds parse: %w", err)
		}
		err = mach.ImportCrossSigningKeys(seeds)
		if err != nil {
			return fmt.Errorf("cross-signing import: %w", err)
		}
		// Signaturen auf dem Homeserver erneuern (in-memory Keys neu verknüpfen)
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

	// Erster Start: Keys generieren und hochladen
	// nil-Callback = kein UIA (Appservice-Token braucht kein Passwort)
	_, _, err = mach.GenerateAndUploadCrossSigningKeys(ctx, nil, "")
	if err != nil {
		return fmt.Errorf("cross-signing generate: %w", err)
	}

	// Eigenes Gerät mit SSK signieren
	if own := mach.OwnIdentity(); own != nil {
		err = mach.SignOwnDevice(ctx, own)
		if err != nil {
			return fmt.Errorf("cross-signing sign device: %w", err)
		}
	}
	// Eigenen Master Key mit Device Key signieren (gegenseitige Verankerung)
	err = mach.SignOwnMasterKey(ctx)
	if err != nil {
		return fmt.Errorf("cross-signing sign master key: %w", err)
	}

	// Seeds persistieren für Folgestarts
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

// ExportKeyBackup exportiert alle Megolm-Sessions in eine verschlüsselte Datei (C-8).
func (m *Machine) ExportKeyBackup(ctx context.Context) error {
	if m.backupPassphrase == "" {
		return nil // Kein Backup ohne Passphrase
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

// importKeyBackup importiert Megolm-Sessions aus einer verschlüsselten Backup-Datei (C-8).
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

// HandleToDevice verarbeitet ein To-Device-Event (Olm-Handshake, Megolm Room Keys).
func (m *Machine) HandleToDevice(ctx context.Context, ev *event.Event) {
	m.olm.HandleToDeviceEvent(ctx, ev)
}

// Decrypt entschlüsselt ein m.room.encrypted Event.
func (m *Machine) Decrypt(ctx context.Context, ev *event.Event) (*event.Event, error) {
	decrypted, err := m.olm.DecryptMegolmEvent(ctx, ev)
	if err != nil {
		return nil, fmt.Errorf("megolm decrypt (room=%s event=%s): %w", ev.RoomID, ev.ID, err)
	}
	slog.Debug("E2EE: event decrypted", "room", ev.RoomID, "event_id", ev.ID, "type", decrypted.Type.Type)
	return decrypted, nil
}

// Encrypt verschlüsselt ein Event für einen Raum.
func (m *Machine) Encrypt(ctx context.Context, roomID id.RoomID, eventType event.Type, content any) (*event.EncryptedEventContent, error) {
	encrypted, err := m.olm.EncryptMegolmEvent(ctx, roomID, eventType, content)
	if err != nil {
		return nil, fmt.Errorf("megolm encrypt (room=%s): %w", roomID, err)
	}
	return encrypted, nil
}

// EnsureSession teilt eine Megolm-Session mit allen Raum-Mitgliedern.
func (m *Machine) EnsureSession(ctx context.Context, roomID id.RoomID, members []id.UserID) error {
	if err := m.olm.ShareGroupSession(ctx, roomID, members); err != nil {
		return fmt.Errorf("share group session (room=%s): %w", roomID, err)
	}
	return nil
}
