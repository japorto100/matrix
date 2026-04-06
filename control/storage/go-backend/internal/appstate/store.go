package appstate

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

type LayoutMode string

const (
	LayoutSingle        LayoutMode = "single"
	LayoutTwoHorizontal LayoutMode = "two_horizontal"
	LayoutTwoVertical   LayoutMode = "two_vertical"
	LayoutFour          LayoutMode = "four"
)

type Preferences struct {
	ProfileKey      string
	Favorites       []string
	Layout          LayoutMode
	SidebarOpen     bool
	ShowDrawingTool bool
	DarkMode        bool
}

type UserRecord struct {
	ID           string
	Email        string
	Name         string
	Role         string
	PasswordHash string
	CreatedAt    string
	UpdatedAt    string
}

type PasskeyAuthenticator struct {
	ID                   string
	UserID               string
	ProviderAccountID    string
	CredentialID         string
	CredentialPublicKey  string
	Counter              int
	CredentialDeviceType string
	CredentialBackedUp   bool
	Transports           []string
	Name                 string
	CreatedAt            string
	LastUsedAt           string
}

type PaperOrderRecord struct {
	ID          string
	ProfileKey  string
	Symbol      string
	Side        string
	Type        string
	Quantity    float64
	EntryPrice  float64
	StopLoss    *float64
	TakeProfit  *float64
	Status      string
	FilledPrice *float64
	ExecutedAt  string
	CreatedAt   string
	UpdatedAt   string
}

type PriceAlertRecord struct {
	ID          string
	ProfileKey  string
	Symbol      string
	Condition   string
	TargetValue float64
	Enabled     bool
	Triggered   bool
	TriggeredAt string
	Message     string
	CreatedAt   string
	UpdatedAt   string
}

type TradeJournalRecord struct {
	ID            string
	ProfileKey    string
	Symbol        string
	OrderID       string
	Note          string
	Tags          []string
	ContextJSON   string
	ScreenshotURL string
	CreatedAt     string
	UpdatedAt     string
}

type PortfolioSnapshotRecord struct {
	ID           string
	ProfileKey   string
	GeneratedAt  string
	SnapshotJSON string
	CreatedAt    string
}

type FileAuditLogRecord struct {
	ID          string
	DocumentID  string
	Action      string
	ActionClass string
	ActorUserID string
	ActorRole   string
	RequestID   string
	Target      string
	Status      string
	ErrorCode   string
	ExpiresAt   string
	CreatedAt   string
}

type ControlAuditLogRecord struct {
	ID          string
	Action      string
	ActionClass string
	ActorUserID string
	ActorRole   string
	RequestID   string
	Target      string
	Status      string
	ErrorCode   string
	ExpiresAt   string
	CreatedAt   string
}

type Store struct {
	db *sql.DB
}

func NewSQLiteStore(path string) (*Store, error) {
	trimmed := filepath.Clean(strings.TrimSpace(path))
	if trimmed == "." || trimmed == "" {
		return nil, fmt.Errorf("app db path required")
	}
	if err := os.MkdirAll(filepath.Dir(trimmed), 0o750); err != nil {
		return nil, fmt.Errorf("create app db dir: %w", err)
	}
	db, err := sql.Open("sqlite", trimmed)
	if err != nil {
		return nil, fmt.Errorf("open app db: %w", err)
	}
	store := &Store{db: db}
	if err := store.migrate(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return store, nil
}

func (s *Store) Close() error {
	if s == nil || s.db == nil {
		return nil
	}
	if err := s.db.Close(); err != nil {
		return fmt.Errorf("close app db: %w", err)
	}
	return nil
}

func (s *Store) migrate() error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	_, err := s.db.Exec(`
CREATE TABLE IF NOT EXISTS UserProfile (
	id TEXT PRIMARY KEY,
	profileKey TEXT NOT NULL UNIQUE,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS LayoutPreference (
	id TEXT PRIMARY KEY,
	profileId TEXT NOT NULL UNIQUE,
	layoutMode TEXT NOT NULL DEFAULT 'single',
	sidebarOpen INTEGER NOT NULL DEFAULT 1,
	showDrawingTool INTEGER NOT NULL DEFAULT 0,
	darkMode INTEGER NOT NULL DEFAULT 1,
	updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Watchlist (
	id TEXT PRIMARY KEY,
	profileId TEXT NOT NULL,
	name TEXT NOT NULL,
	isDefault INTEGER NOT NULL DEFAULT 0,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_profile_name ON Watchlist(profileId, name);

CREATE TABLE IF NOT EXISTS WatchlistItem (
	id TEXT PRIMARY KEY,
	watchlistId TEXT NOT NULL,
	symbol TEXT NOT NULL,
	position INTEGER NOT NULL DEFAULT 0,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlistitem_watchlist_symbol ON WatchlistItem(watchlistId, symbol);

CREATE TABLE IF NOT EXISTS User (
	id TEXT PRIMARY KEY,
	username TEXT,
	email TEXT,
	name TEXT,
	role TEXT NOT NULL DEFAULT 'viewer',
	passwordHash TEXT,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_email_unique ON User(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_username_unique ON User(username);

CREATE TABLE IF NOT EXISTS UserConsent (
	id TEXT PRIMARY KEY,
	userId TEXT NOT NULL UNIQUE,
	llmProcessing INTEGER NOT NULL DEFAULT 0,
	analyticsEnabled INTEGER NOT NULL DEFAULT 0,
	marketingEnabled INTEGER NOT NULL DEFAULT 0,
	privacyVersion TEXT NOT NULL DEFAULT 'v1',
	consentedAt TEXT,
	withdrawnAt TEXT,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS VerificationToken (
	identifier TEXT NOT NULL,
	token TEXT NOT NULL,
	expires TEXT NOT NULL,
	PRIMARY KEY (identifier, token)
);
CREATE INDEX IF NOT EXISTS idx_verificationtoken_expires ON VerificationToken(expires);

CREATE TABLE IF NOT EXISTS TotpDevice (
	id TEXT PRIMARY KEY,
	userId TEXT NOT NULL,
	label TEXT NOT NULL,
	secretEnc TEXT NOT NULL,
	isPrimary INTEGER NOT NULL DEFAULT 0,
	lastUsedAt TEXT,
	revokedAt TEXT,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_totpdevice_user ON TotpDevice(userId);
CREATE INDEX IF NOT EXISTS idx_totpdevice_user_revoked ON TotpDevice(userId, revokedAt);

CREATE TABLE IF NOT EXISTS RecoveryCode (
	id TEXT PRIMARY KEY,
	userId TEXT NOT NULL,
	codeHash TEXT NOT NULL,
	usedAt TEXT,
	createdAt TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_recoverycode_user_hash ON RecoveryCode(userId, codeHash);
CREATE INDEX IF NOT EXISTS idx_recoverycode_user_used ON RecoveryCode(userId, usedAt);

CREATE TABLE IF NOT EXISTS Authenticator (
	id TEXT PRIMARY KEY,
	userId TEXT NOT NULL,
	providerAccountId TEXT NOT NULL UNIQUE,
	credentialID TEXT NOT NULL UNIQUE,
	credentialPublicKey TEXT NOT NULL,
	counter INTEGER NOT NULL DEFAULT 0,
	credentialDeviceType TEXT NOT NULL,
	credentialBackedUp INTEGER NOT NULL DEFAULT 0,
	transports TEXT,
	name TEXT,
	createdAt TEXT NOT NULL,
	lastUsedAt TEXT
);
CREATE INDEX IF NOT EXISTS idx_authenticator_user ON Authenticator(userId);

CREATE TABLE IF NOT EXISTS PriceAlertRecord (
	id TEXT PRIMARY KEY,
	profileId TEXT NOT NULL,
	symbol TEXT NOT NULL,
	condition TEXT NOT NULL,
	targetValue REAL NOT NULL,
	enabled INTEGER NOT NULL DEFAULT 1,
	triggered INTEGER NOT NULL DEFAULT 0,
	triggeredAt TEXT,
	message TEXT,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pricealert_profile ON PriceAlertRecord(profileId);
CREATE INDEX IF NOT EXISTS idx_pricealert_profile_symbol_enabled ON PriceAlertRecord(profileId, symbol, enabled);

CREATE TABLE IF NOT EXISTS PaperOrderRecord (
	id TEXT PRIMARY KEY,
	profileId TEXT NOT NULL,
	symbol TEXT NOT NULL,
	side TEXT NOT NULL,
	type TEXT NOT NULL,
	quantity REAL NOT NULL,
	entryPrice REAL NOT NULL,
	stopLoss REAL,
	takeProfit REAL,
	status TEXT NOT NULL DEFAULT 'open',
	filledPrice REAL,
	executedAt TEXT,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_paperorder_profile_symbol_status ON PaperOrderRecord(profileId, symbol, status);
CREATE INDEX IF NOT EXISTS idx_paperorder_symbol_status ON PaperOrderRecord(symbol, status);

CREATE TABLE IF NOT EXISTS TradeJournalRecord (
	id TEXT PRIMARY KEY,
	profileId TEXT NOT NULL,
	symbol TEXT NOT NULL,
	orderId TEXT,
	note TEXT NOT NULL,
	tags TEXT,
	context TEXT,
	screenshotUrl TEXT,
	createdAt TEXT NOT NULL,
	updatedAt TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tradejournal_profile_symbol_created ON TradeJournalRecord(profileId, symbol, createdAt);
CREATE INDEX IF NOT EXISTS idx_tradejournal_orderid ON TradeJournalRecord(orderId);

CREATE TABLE IF NOT EXISTS PortfolioSnapshotRecord (
	id TEXT PRIMARY KEY,
	profileId TEXT NOT NULL,
	generatedAt TEXT NOT NULL,
	snapshotJson TEXT NOT NULL,
	createdAt TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_portfoliosnapshot_profile_generated ON PortfolioSnapshotRecord(profileId, generatedAt);

CREATE TABLE IF NOT EXISTS FileAuditLog (
	id TEXT PRIMARY KEY,
	documentId TEXT,
	action TEXT NOT NULL,
	actionClass TEXT NOT NULL,
	actorUserId TEXT,
	actorRole TEXT,
	requestId TEXT NOT NULL,
	target TEXT NOT NULL,
	status TEXT NOT NULL DEFAULT 'ok',
	errorCode TEXT,
	expiresAt TEXT,
	createdAt TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fileaudit_document ON FileAuditLog(documentId);
CREATE INDEX IF NOT EXISTS idx_fileaudit_action_created ON FileAuditLog(action, createdAt);
CREATE INDEX IF NOT EXISTS idx_fileaudit_actor_created ON FileAuditLog(actorUserId, createdAt);

CREATE TABLE IF NOT EXISTS ControlAuditLog (
	id TEXT PRIMARY KEY,
	action TEXT NOT NULL,
	actionClass TEXT NOT NULL,
	actorUserId TEXT,
	actorRole TEXT,
	requestId TEXT NOT NULL,
	target TEXT NOT NULL,
	status TEXT NOT NULL DEFAULT 'ok',
	errorCode TEXT,
	expiresAt TEXT,
	createdAt TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_controlaudit_action_created ON ControlAuditLog(action, createdAt);
CREATE INDEX IF NOT EXISTS idx_controlaudit_actor_created ON ControlAuditLog(actorUserId, createdAt);
CREATE INDEX IF NOT EXISTS idx_controlaudit_target_created ON ControlAuditLog(target, createdAt);
`)
	if err != nil {
		return fmt.Errorf("migrate app db: %w", err)
	}
	if err := s.ensureColumn("User", "username", "TEXT"); err != nil {
		return err
	}
	if err := s.ensureColumn("User", "passwordHash", "TEXT"); err != nil {
		return err
	}
	return nil
}

func (s *Store) ensureColumn(tableName, columnName, columnDDL string) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	rows, err := s.db.Query("PRAGMA table_info(" + tableName + ")")
	if err != nil {
		return fmt.Errorf("inspect %s columns: %w", tableName, err)
	}
	defer func() { _ = rows.Close() }()
	for rows.Next() {
		var cid int
		var name, colType string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &colType, &notNull, &defaultValue, &pk); err != nil {
			return fmt.Errorf("scan %s columns: %w", tableName, err)
		}
		if strings.EqualFold(name, columnName) {
			return nil
		}
	}
	if err := rows.Err(); err != nil {
		return fmt.Errorf("iterate %s columns: %w", tableName, err)
	}
	if _, err := s.db.Exec(fmt.Sprintf("ALTER TABLE %s ADD COLUMN %s %s", tableName, columnName, columnDDL)); err != nil {
		return fmt.Errorf("add %s.%s column: %w", tableName, columnName, err)
	}
	return nil
}

func (s *Store) GetPreferences(profileKey string) (Preferences, error) {
	if s == nil || s.db == nil {
		return Preferences{}, fmt.Errorf("app db unavailable")
	}
	profileKey = strings.TrimSpace(profileKey)
	if profileKey == "" {
		return Preferences{}, fmt.Errorf("profileKey required")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return Preferences{}, err
	}
	prefs := Preferences{
		ProfileKey:      profileKey,
		Layout:          LayoutSingle,
		SidebarOpen:     true,
		ShowDrawingTool: false,
		DarkMode:        true,
		Favorites:       []string{},
	}
	var layoutMode string
	var sidebarOpen, showDrawingTool, darkMode int
	err = s.db.QueryRow(`
SELECT layoutMode, sidebarOpen, showDrawingTool, darkMode
FROM LayoutPreference
WHERE profileId = ?
`, profileID).Scan(&layoutMode, &sidebarOpen, &showDrawingTool, &darkMode)
	if err == nil {
		prefs.Layout = normalizeLayoutMode(layoutMode)
		prefs.SidebarOpen = sidebarOpen != 0
		prefs.ShowDrawingTool = showDrawingTool != 0
		prefs.DarkMode = darkMode != 0
	} else if !errors.Is(err, sql.ErrNoRows) {
		return Preferences{}, fmt.Errorf("read layout preference: %w", err)
	}
	rows, err := s.db.Query(`
SELECT wi.symbol
FROM Watchlist w
JOIN WatchlistItem wi ON wi.watchlistId = w.id
WHERE w.profileId = ? AND w.isDefault = 1
ORDER BY wi.position ASC
`, profileID)
	if err != nil {
		return Preferences{}, fmt.Errorf("read favorites: %w", err)
	}
	defer func() { _ = rows.Close() }()
	for rows.Next() {
		var symbol string
		if err := rows.Scan(&symbol); err != nil {
			return Preferences{}, fmt.Errorf("scan favorite: %w", err)
		}
		prefs.Favorites = append(prefs.Favorites, symbol)
	}
	if err := rows.Err(); err != nil {
		return Preferences{}, fmt.Errorf("iterate favorites: %w", err)
	}
	return prefs, nil
}

func (s *Store) SavePreferences(prefs Preferences) (Preferences, error) {
	if s == nil || s.db == nil {
		return Preferences{}, fmt.Errorf("app db unavailable")
	}
	profileKey := strings.TrimSpace(prefs.ProfileKey)
	if profileKey == "" {
		return Preferences{}, fmt.Errorf("profileKey required")
	}
	layout := normalizeLayoutMode(string(prefs.Layout))
	normalizedSymbols := dedupeSymbols(prefs.Favorites)
	tx, err := s.db.Begin()
	if err != nil {
		return Preferences{}, fmt.Errorf("begin preferences tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	profileID, err := ensureUserProfileTx(tx, profileKey)
	if err != nil {
		return Preferences{}, err
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	layoutID, err := existingIDTx(tx, `SELECT id FROM LayoutPreference WHERE profileId = ?`, profileID)
	if err != nil {
		return Preferences{}, fmt.Errorf("load layout preference: %w", err)
	}
	if layoutID == "" {
		layoutID = newID("layout")
		_, err = tx.Exec(`
INSERT INTO LayoutPreference (id, profileId, layoutMode, sidebarOpen, showDrawingTool, darkMode, updatedAt)
VALUES (?, ?, ?, ?, ?, ?, ?)
`, layoutID, profileID, string(layout), boolToInt(prefs.SidebarOpen), boolToInt(prefs.ShowDrawingTool), boolToInt(prefs.DarkMode), now)
	} else {
		_, err = tx.Exec(`
UPDATE LayoutPreference
SET layoutMode = ?, sidebarOpen = ?, showDrawingTool = ?, darkMode = ?, updatedAt = ?
WHERE profileId = ?
`, string(layout), boolToInt(prefs.SidebarOpen), boolToInt(prefs.ShowDrawingTool), boolToInt(prefs.DarkMode), now, profileID)
	}
	if err != nil {
		return Preferences{}, fmt.Errorf("upsert layout preference: %w", err)
	}
	watchlistID, err := existingIDTx(tx, `SELECT id FROM Watchlist WHERE profileId = ? AND isDefault = 1 LIMIT 1`, profileID)
	if err != nil {
		return Preferences{}, fmt.Errorf("load default watchlist: %w", err)
	}
	if watchlistID == "" {
		watchlistID = newID("watch")
		_, err = tx.Exec(`
INSERT INTO Watchlist (id, profileId, name, isDefault, createdAt, updatedAt)
VALUES (?, ?, ?, 1, ?, ?)
`, watchlistID, profileID, "Favorites", now, now)
		if err != nil {
			return Preferences{}, fmt.Errorf("create default watchlist: %w", err)
		}
	}
	if _, err := tx.Exec(`DELETE FROM WatchlistItem WHERE watchlistId = ?`, watchlistID); err != nil {
		return Preferences{}, fmt.Errorf("clear watchlist items: %w", err)
	}
	for index, symbol := range normalizedSymbols {
		_, err := tx.Exec(`
INSERT INTO WatchlistItem (id, watchlistId, symbol, position, createdAt, updatedAt)
VALUES (?, ?, ?, ?, ?, ?)
`, newID("wli"), watchlistID, symbol, index, now, now)
		if err != nil {
			return Preferences{}, fmt.Errorf("insert watchlist item: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return Preferences{}, fmt.Errorf("commit preferences tx: %w", err)
	}
	return Preferences{
		ProfileKey:      profileKey,
		Favorites:       normalizedSymbols,
		Layout:          layout,
		SidebarOpen:     prefs.SidebarOpen,
		ShowDrawingTool: prefs.ShowDrawingTool,
		DarkMode:        prefs.DarkMode,
	}, nil
}

func (s *Store) ListUsers(query string, limit int) ([]UserRecord, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("app db unavailable")
	}
	if limit <= 0 {
		limit = 100
	}
	if limit > 200 {
		limit = 200
	}
	q := strings.TrimSpace(query)
	var rows *sql.Rows
	var err error
	if q == "" {
		rows, err = s.db.Query(`
SELECT id, COALESCE(email, ''), COALESCE(name, ''), role, CAST(createdAt AS TEXT), CAST(updatedAt AS TEXT)
FROM User
ORDER BY createdAt DESC
LIMIT ?
`, limit)
	} else {
		like := "%" + q + "%"
		rows, err = s.db.Query(`
SELECT id, COALESCE(email, ''), COALESCE(name, ''), role, CAST(createdAt AS TEXT), CAST(updatedAt AS TEXT)
FROM User
WHERE email LIKE ? OR name LIKE ?
ORDER BY createdAt DESC
LIMIT ?
`, like, like, limit)
	}
	if err != nil {
		return nil, fmt.Errorf("list users: %w", err)
	}
	defer func() { _ = rows.Close() }()
	items := make([]UserRecord, 0, limit)
	for rows.Next() {
		var item UserRecord
		if err := rows.Scan(&item.ID, &item.Email, &item.Name, &item.Role, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan user: %w", err)
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate users: %w", err)
	}
	return items, nil
}

func (s *Store) UpdateUserRole(actorUserID, targetUserID, role string) (UserRecord, error) {
	if s == nil || s.db == nil {
		return UserRecord{}, fmt.Errorf("app db unavailable")
	}
	tx, err := s.db.Begin()
	if err != nil {
		return UserRecord{}, fmt.Errorf("begin user role tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	var target UserRecord
	err = tx.QueryRow(`
SELECT id, COALESCE(email, ''), COALESCE(name, ''), role, CAST(createdAt AS TEXT), CAST(updatedAt AS TEXT)
FROM User
WHERE id = ?
`, targetUserID).Scan(&target.ID, &target.Email, &target.Name, &target.Role, &target.CreatedAt, &target.UpdatedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return UserRecord{}, fmt.Errorf("user not found")
		}
		return UserRecord{}, fmt.Errorf("load target user: %w", err)
	}
	if actorUserID == target.ID && strings.EqualFold(target.Role, "admin") && !strings.EqualFold(role, "admin") {
		var otherAdmins int
		if err := tx.QueryRow(`SELECT COUNT(*) FROM User WHERE role = 'admin' AND id <> ?`, target.ID).Scan(&otherAdmins); err != nil {
			return UserRecord{}, fmt.Errorf("count admins: %w", err)
		}
		if otherAdmins < 1 {
			return UserRecord{}, fmt.Errorf("cannot remove the last admin role from your own account")
		}
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	if _, err := tx.Exec(`UPDATE User SET role = ?, updatedAt = ? WHERE id = ?`, role, now, target.ID); err != nil {
		return UserRecord{}, fmt.Errorf("update user role: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return UserRecord{}, fmt.Errorf("commit user role tx: %w", err)
	}
	target.Role = role
	target.UpdatedAt = now
	return target, nil
}

type ConsentRecord struct {
	LLMProcessing    bool
	AnalyticsEnabled bool
	MarketingEnabled bool
	PrivacyVersion   string
	ConsentedAt      string
	WithdrawnAt      string
}

func (s *Store) GetUserByIDOrEmail(userID, email string) (UserRecord, error) {
	if s == nil || s.db == nil {
		return UserRecord{}, fmt.Errorf("app db unavailable")
	}
	userID = strings.TrimSpace(userID)
	email = strings.TrimSpace(strings.ToLower(email))
	var row UserRecord
	var err error
	switch {
	case userID != "":
		err = s.db.QueryRow(`
SELECT id, COALESCE(email, ''), COALESCE(name, ''), role, COALESCE(passwordHash, ''), CAST(createdAt AS TEXT), CAST(updatedAt AS TEXT)
FROM User WHERE id = ?
`, userID).Scan(&row.ID, &row.Email, &row.Name, &row.Role, &row.PasswordHash, &row.CreatedAt, &row.UpdatedAt)
	case email != "":
		err = s.db.QueryRow(`
SELECT id, COALESCE(email, ''), COALESCE(name, ''), role, COALESCE(passwordHash, ''), CAST(createdAt AS TEXT), CAST(updatedAt AS TEXT)
FROM User WHERE email = ?
`, email).Scan(&row.ID, &row.Email, &row.Name, &row.Role, &row.PasswordHash, &row.CreatedAt, &row.UpdatedAt)
	default:
		return UserRecord{}, fmt.Errorf("user identity required")
	}
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return UserRecord{}, fmt.Errorf("user not found")
		}
		return UserRecord{}, fmt.Errorf("load user: %w", err)
	}
	return row, nil
}

func (s *Store) GetOrCreateUserConsent(userID string) (ConsentRecord, error) {
	if s == nil || s.db == nil {
		return ConsentRecord{}, fmt.Errorf("app db unavailable")
	}
	userID = strings.TrimSpace(userID)
	if userID == "" {
		return ConsentRecord{}, fmt.Errorf("user id required")
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	consentID, err := existingIDDB(s.db, `SELECT id FROM UserConsent WHERE userId = ?`, userID)
	if err != nil {
		return ConsentRecord{}, fmt.Errorf("load user consent id: %w", err)
	}
	if consentID == "" {
		if _, err := s.db.Exec(`
INSERT INTO UserConsent (id, userId, llmProcessing, analyticsEnabled, marketingEnabled, privacyVersion, createdAt, updatedAt)
VALUES (?, ?, 0, 0, 0, 'v1', ?, ?)
`, newID("cons"), userID, now, now); err != nil {
			return ConsentRecord{}, fmt.Errorf("create user consent: %w", err)
		}
	}
	return s.loadConsent(userID)
}

func (s *Store) UpdateUserConsent(userID string, llm, analytics, marketing *bool) (ConsentRecord, error) {
	current, err := s.GetOrCreateUserConsent(userID)
	if err != nil {
		return ConsentRecord{}, err
	}
	nextLLM := current.LLMProcessing
	if llm != nil {
		nextLLM = *llm
	}
	nextAnalytics := current.AnalyticsEnabled
	if analytics != nil {
		nextAnalytics = *analytics
	}
	nextMarketing := current.MarketingEnabled
	if marketing != nil {
		nextMarketing = *marketing
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	consentedAt := current.ConsentedAt
	if nextLLM || nextAnalytics || nextMarketing {
		if consentedAt == "" {
			consentedAt = now
		}
		current.WithdrawnAt = ""
	} else {
		current.WithdrawnAt = now
	}
	if _, err := s.db.Exec(`
UPDATE UserConsent
SET llmProcessing = ?, analyticsEnabled = ?, marketingEnabled = ?, consentedAt = ?, withdrawnAt = ?, updatedAt = ?
WHERE userId = ?
`, boolToInt(nextLLM), boolToInt(nextAnalytics), boolToInt(nextMarketing), nullIfEmpty(consentedAt), nullIfEmpty(current.WithdrawnAt), now, userID); err != nil {
		return ConsentRecord{}, fmt.Errorf("update user consent: %w", err)
	}
	return s.loadConsent(userID)
}

func (s *Store) loadConsent(userID string) (ConsentRecord, error) {
	var llm, analytics, marketing int
	var privacyVersion string
	var consentedAt, withdrawnAt sql.NullString
	err := s.db.QueryRow(`
SELECT llmProcessing, analyticsEnabled, marketingEnabled, privacyVersion, consentedAt, withdrawnAt
FROM UserConsent WHERE userId = ?
`, userID).Scan(&llm, &analytics, &marketing, &privacyVersion, &consentedAt, &withdrawnAt)
	if err != nil {
		return ConsentRecord{}, fmt.Errorf("load user consent: %w", err)
	}
	return ConsentRecord{
		LLMProcessing:    llm != 0,
		AnalyticsEnabled: analytics != 0,
		MarketingEnabled: marketing != 0,
		PrivacyVersion:   privacyVersion,
		ConsentedAt:      nullStringValue(consentedAt),
		WithdrawnAt:      nullStringValue(withdrawnAt),
	}, nil
}

func (s *Store) SetPasswordHash(userID, newHash string) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	res, err := s.db.Exec(`UPDATE User SET passwordHash = ?, updatedAt = ? WHERE id = ?`, newHash, now, userID)
	if err != nil {
		return fmt.Errorf("update password hash: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("password hash rows affected: %w", err)
	}
	if rows == 0 {
		return fmt.Errorf("user not found")
	}
	return nil
}

func (s *Store) CreateTOTPSetup(userID, secret string, recoveryCodes []string) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	tx, err := s.db.Begin()
	if err != nil {
		return fmt.Errorf("begin totp tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	now := time.Now().UTC().Format(time.RFC3339Nano)
	if _, err := tx.Exec(`DELETE FROM TotpDevice WHERE userId = ?`, userID); err != nil {
		return fmt.Errorf("clear existing totp devices: %w", err)
	}
	if _, err := tx.Exec(`DELETE FROM RecoveryCode WHERE userId = ?`, userID); err != nil {
		return fmt.Errorf("clear existing recovery codes: %w", err)
	}
	if _, err := tx.Exec(`
INSERT INTO TotpDevice (id, userId, label, secretEnc, isPrimary, createdAt, updatedAt)
VALUES (?, ?, ?, ?, 1, ?, ?)
`, newID("totp"), userID, "Primary Authenticator", secret, now, now); err != nil {
		return fmt.Errorf("insert totp device: %w", err)
	}
	for _, code := range recoveryCodes {
		if _, err := tx.Exec(`
INSERT INTO RecoveryCode (id, userId, codeHash, createdAt)
VALUES (?, ?, ?, ?)
`, newID("rc"), userID, strings.TrimSpace(strings.ToUpper(code)), now); err != nil {
			return fmt.Errorf("insert recovery code: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit totp tx: %w", err)
	}
	return nil
}

func (s *Store) CreateVerificationToken(identifier, token string, expiresAt time.Time) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	if _, err := s.db.Exec(`
INSERT INTO VerificationToken (identifier, token, expires)
VALUES (?, ?, ?)
`, strings.TrimSpace(strings.ToLower(identifier)), token, expiresAt.UTC().Format(time.RFC3339Nano)); err != nil {
		return fmt.Errorf("insert verification token: %w", err)
	}
	return nil
}

func (s *Store) GetValidVerificationToken(identifier, token string, now time.Time) (bool, error) {
	if s == nil || s.db == nil {
		return false, fmt.Errorf("app db unavailable")
	}
	var expires string
	err := s.db.QueryRow(`
SELECT expires FROM VerificationToken
WHERE identifier = ? AND token = ?
`, strings.TrimSpace(strings.ToLower(identifier)), token).Scan(&expires)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return false, nil
		}
		return false, fmt.Errorf("load verification token: %w", err)
	}
	parsed, err := time.Parse(time.RFC3339Nano, expires)
	if err != nil {
		return false, fmt.Errorf("parse verification token expiry: %w", err)
	}
	return parsed.After(now.UTC()), nil
}

func (s *Store) DeleteVerificationToken(identifier, token string) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	if _, err := s.db.Exec(`
DELETE FROM VerificationToken WHERE identifier = ? AND token = ?
`, strings.TrimSpace(strings.ToLower(identifier)), token); err != nil {
		return fmt.Errorf("delete verification token: %w", err)
	}
	return nil
}

type RecoveryMatch struct {
	UserID string
	CodeID string
}

func (s *Store) FindRecoveryCodeByEmail(email, recoveryCode string) (RecoveryMatch, error) {
	if s == nil || s.db == nil {
		return RecoveryMatch{}, fmt.Errorf("app db unavailable")
	}
	var match RecoveryMatch
	err := s.db.QueryRow(`
SELECT u.id, rc.id
FROM User u
JOIN RecoveryCode rc ON rc.userId = u.id
WHERE u.email = ? AND rc.codeHash = ?
LIMIT 1
`, strings.TrimSpace(strings.ToLower(email)), strings.TrimSpace(strings.ToUpper(recoveryCode))).Scan(&match.UserID, &match.CodeID)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return RecoveryMatch{}, fmt.Errorf("recovery code not found")
		}
		return RecoveryMatch{}, fmt.Errorf("load recovery code: %w", err)
	}
	return match, nil
}

func (s *Store) DeleteRecoveryCode(codeID string) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	if _, err := s.db.Exec(`DELETE FROM RecoveryCode WHERE id = ?`, codeID); err != nil {
		return fmt.Errorf("delete recovery code: %w", err)
	}
	return nil
}

func (s *Store) GetOrCreateUserByEmail(email, displayName, role string) (UserRecord, []PasskeyAuthenticator, error) {
	if s == nil || s.db == nil {
		return UserRecord{}, nil, fmt.Errorf("app db unavailable")
	}
	normalizedEmail := strings.TrimSpace(strings.ToLower(email))
	if normalizedEmail == "" {
		return UserRecord{}, nil, fmt.Errorf("email required")
	}
	user, err := s.GetUserByIDOrEmail("", normalizedEmail)
	if err != nil {
		if !strings.Contains(err.Error(), "user not found") {
			return UserRecord{}, nil, err
		}
		now := time.Now().UTC().Format(time.RFC3339Nano)
		user = UserRecord{
			ID:        newID("user"),
			Email:     normalizedEmail,
			Name:      strings.TrimSpace(displayName),
			Role:      normalizeRoleOrDefault(role),
			CreatedAt: now,
			UpdatedAt: now,
		}
		if user.Name == "" {
			user.Name = strings.Split(normalizedEmail, "@")[0]
		}
		if _, execErr := s.db.Exec(`
INSERT INTO User (id, email, name, role, createdAt, updatedAt)
VALUES (?, ?, ?, ?, ?, ?)
`, user.ID, user.Email, user.Name, user.Role, user.CreatedAt, user.UpdatedAt); execErr != nil {
			return UserRecord{}, nil, fmt.Errorf("create user by email: %w", execErr)
		}
	}
	authenticators, err := s.ListAuthenticatorsByUserID(user.ID)
	if err != nil {
		return UserRecord{}, nil, err
	}
	return user, authenticators, nil
}

func (s *Store) ListAuthenticatorsByUserID(userID string) ([]PasskeyAuthenticator, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("app db unavailable")
	}
	rows, err := s.db.Query(`
SELECT id, userId, providerAccountId, credentialID, credentialPublicKey, counter,
       credentialDeviceType, credentialBackedUp, COALESCE(transports, ''), COALESCE(name, ''),
       CAST(createdAt AS TEXT), COALESCE(CAST(lastUsedAt AS TEXT), '')
FROM Authenticator
WHERE userId = ?
ORDER BY CASE WHEN lastUsedAt IS NULL THEN 1 ELSE 0 END ASC, lastUsedAt DESC, createdAt DESC
`, userID)
	if err != nil {
		return nil, fmt.Errorf("list authenticators: %w", err)
	}
	defer func() { _ = rows.Close() }()
	items := make([]PasskeyAuthenticator, 0)
	for rows.Next() {
		var item PasskeyAuthenticator
		var backedUp int
		var transports string
		if err := rows.Scan(
			&item.ID,
			&item.UserID,
			&item.ProviderAccountID,
			&item.CredentialID,
			&item.CredentialPublicKey,
			&item.Counter,
			&item.CredentialDeviceType,
			&backedUp,
			&transports,
			&item.Name,
			&item.CreatedAt,
			&item.LastUsedAt,
		); err != nil {
			return nil, fmt.Errorf("scan authenticator: %w", err)
		}
		item.CredentialBackedUp = backedUp != 0
		item.Transports = splitCSV(transports)
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate authenticators: %w", err)
	}
	return items, nil
}

func (s *Store) UpsertAuthenticator(authenticator PasskeyAuthenticator) (PasskeyAuthenticator, error) {
	if s == nil || s.db == nil {
		return PasskeyAuthenticator{}, fmt.Errorf("app db unavailable")
	}
	authenticator.UserID = strings.TrimSpace(authenticator.UserID)
	authenticator.CredentialID = strings.TrimSpace(authenticator.CredentialID)
	authenticator.ProviderAccountID = strings.TrimSpace(authenticator.ProviderAccountID)
	authenticator.CredentialPublicKey = strings.TrimSpace(authenticator.CredentialPublicKey)
	if authenticator.UserID == "" || authenticator.CredentialID == "" || authenticator.CredentialPublicKey == "" {
		return PasskeyAuthenticator{}, fmt.Errorf("userId, credentialID and credentialPublicKey are required")
	}
	if authenticator.ProviderAccountID == "" {
		authenticator.ProviderAccountID = authenticator.CredentialID
	}
	if authenticator.ID == "" {
		authenticator.ID = newID("authn")
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	if authenticator.CreatedAt == "" {
		authenticator.CreatedAt = now
	}
	if authenticator.LastUsedAt == "" {
		authenticator.LastUsedAt = now
	}
	if _, err := s.db.Exec(`
INSERT INTO Authenticator (
	id, userId, providerAccountId, credentialID, credentialPublicKey, counter,
	credentialDeviceType, credentialBackedUp, transports, name, createdAt, lastUsedAt
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(credentialID) DO UPDATE SET
	userId = excluded.userId,
	providerAccountId = excluded.providerAccountId,
	credentialPublicKey = excluded.credentialPublicKey,
	counter = excluded.counter,
	credentialDeviceType = excluded.credentialDeviceType,
	credentialBackedUp = excluded.credentialBackedUp,
	transports = excluded.transports,
	name = COALESCE(excluded.name, Authenticator.name),
	lastUsedAt = excluded.lastUsedAt
`, authenticator.ID, authenticator.UserID, authenticator.ProviderAccountID, authenticator.CredentialID, authenticator.CredentialPublicKey, authenticator.Counter, authenticator.CredentialDeviceType, boolToInt(authenticator.CredentialBackedUp), joinCSV(authenticator.Transports), nullIfEmpty(authenticator.Name), authenticator.CreatedAt, nullIfEmpty(authenticator.LastUsedAt)); err != nil {
		return PasskeyAuthenticator{}, fmt.Errorf("upsert authenticator: %w", err)
	}
	stored, _, err := s.GetAuthenticatorByCredentialID(authenticator.CredentialID)
	if err != nil {
		return PasskeyAuthenticator{}, err
	}
	return stored, nil
}

func (s *Store) GetAuthenticatorByCredentialID(credentialID string) (PasskeyAuthenticator, UserRecord, error) {
	if s == nil || s.db == nil {
		return PasskeyAuthenticator{}, UserRecord{}, fmt.Errorf("app db unavailable")
	}
	var authn PasskeyAuthenticator
	var user UserRecord
	var backedUp int
	var transports string
	err := s.db.QueryRow(`
SELECT a.id, a.userId, a.providerAccountId, a.credentialID, a.credentialPublicKey, a.counter,
       a.credentialDeviceType, a.credentialBackedUp, COALESCE(a.transports, ''), COALESCE(a.name, ''),
       CAST(a.createdAt AS TEXT), COALESCE(CAST(a.lastUsedAt AS TEXT), ''),
       u.id, COALESCE(u.email, ''), COALESCE(u.name, ''), u.role, COALESCE(u.passwordHash, ''),
       CAST(u.createdAt AS TEXT), CAST(u.updatedAt AS TEXT)
FROM Authenticator a
JOIN User u ON u.id = a.userId
WHERE a.credentialID = ?
LIMIT 1
`, strings.TrimSpace(credentialID)).Scan(
		&authn.ID, &authn.UserID, &authn.ProviderAccountID, &authn.CredentialID, &authn.CredentialPublicKey,
		&authn.Counter, &authn.CredentialDeviceType, &backedUp, &transports, &authn.Name, &authn.CreatedAt,
		&authn.LastUsedAt, &user.ID, &user.Email, &user.Name, &user.Role, &user.PasswordHash, &user.CreatedAt, &user.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return PasskeyAuthenticator{}, UserRecord{}, fmt.Errorf("authenticator not found")
		}
		return PasskeyAuthenticator{}, UserRecord{}, fmt.Errorf("load authenticator: %w", err)
	}
	authn.CredentialBackedUp = backedUp != 0
	authn.Transports = splitCSV(transports)
	return authn, user, nil
}

func (s *Store) UpdateAuthenticatorUsage(credentialID string, counter int, deviceType string, backedUp bool) (PasskeyAuthenticator, error) {
	if s == nil || s.db == nil {
		return PasskeyAuthenticator{}, fmt.Errorf("app db unavailable")
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	res, err := s.db.Exec(`
UPDATE Authenticator
SET counter = ?, credentialDeviceType = ?, credentialBackedUp = ?, lastUsedAt = ?
WHERE credentialID = ?
`, counter, strings.TrimSpace(deviceType), boolToInt(backedUp), now, strings.TrimSpace(credentialID))
	if err != nil {
		return PasskeyAuthenticator{}, fmt.Errorf("update authenticator usage: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return PasskeyAuthenticator{}, fmt.Errorf("authenticator rows affected: %w", err)
	}
	if rows == 0 {
		return PasskeyAuthenticator{}, fmt.Errorf("authenticator not found")
	}
	authn, _, err := s.GetAuthenticatorByCredentialID(credentialID)
	if err != nil {
		return PasskeyAuthenticator{}, err
	}
	return authn, nil
}

func (s *Store) DeleteAuthenticatorForUser(userID, authenticatorID string) (int, error) {
	if s == nil || s.db == nil {
		return 0, fmt.Errorf("app db unavailable")
	}
	tx, err := s.db.Begin()
	if err != nil {
		return 0, fmt.Errorf("begin delete authenticator tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	var count int
	if countErr := tx.QueryRow(`SELECT COUNT(*) FROM Authenticator WHERE userId = ?`, userID).Scan(&count); countErr != nil {
		return 0, fmt.Errorf("count authenticators: %w", countErr)
	}
	if count <= 1 {
		return 0, fmt.Errorf("cannot remove last passkey")
	}
	res, err := tx.Exec(`DELETE FROM Authenticator WHERE id = ? AND userId = ?`, authenticatorID, userID)
	if err != nil {
		return 0, fmt.Errorf("delete authenticator: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return 0, fmt.Errorf("delete authenticator rows affected: %w", err)
	}
	if rows == 0 {
		return 0, fmt.Errorf("authenticator not found")
	}
	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit delete authenticator tx: %w", err)
	}
	return count - 1, nil
}

func (s *Store) FindUserForCredentials(identifier string) (UserRecord, error) {
	if s == nil || s.db == nil {
		return UserRecord{}, fmt.Errorf("app db unavailable")
	}
	trimmed := strings.TrimSpace(identifier)
	if trimmed == "" {
		return UserRecord{}, fmt.Errorf("identifier required")
	}
	normalized := strings.ToLower(trimmed)
	var row UserRecord
	err := s.db.QueryRow(`
SELECT id, COALESCE(email, ''), COALESCE(name, ''), role, COALESCE(passwordHash, ''), CAST(createdAt AS TEXT), CAST(updatedAt AS TEXT)
FROM User
WHERE LOWER(COALESCE(email, '')) = ? OR LOWER(COALESCE(username, '')) = ? OR name = ?
LIMIT 1
`, normalized, normalized, trimmed).Scan(&row.ID, &row.Email, &row.Name, &row.Role, &row.PasswordHash, &row.CreatedAt, &row.UpdatedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return UserRecord{}, fmt.Errorf("user not found")
		}
		return UserRecord{}, fmt.Errorf("find user for credentials: %w", err)
	}
	return row, nil
}

func (s *Store) RegisterUser(email, username, name, role, passwordHash string, recoveryCodes []string) (UserRecord, error) {
	if s == nil || s.db == nil {
		return UserRecord{}, fmt.Errorf("app db unavailable")
	}
	email = strings.TrimSpace(strings.ToLower(email))
	username = strings.TrimSpace(strings.ToLower(username))
	name = strings.TrimSpace(name)
	role = normalizeRoleOrDefault(role)
	passwordHash = strings.TrimSpace(passwordHash)
	if email == "" || username == "" || passwordHash == "" {
		return UserRecord{}, fmt.Errorf("email, username and passwordHash are required")
	}
	tx, err := s.db.Begin()
	if err != nil {
		return UserRecord{}, fmt.Errorf("begin register user tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	var existing string
	err = tx.QueryRow(`SELECT id FROM User WHERE email = ? LIMIT 1`, email).Scan(&existing)
	if err == nil {
		return UserRecord{}, fmt.Errorf("email already registered")
	}
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return UserRecord{}, fmt.Errorf("check existing email: %w", err)
	}
	err = tx.QueryRow(`SELECT id FROM User WHERE username = ? LIMIT 1`, username).Scan(&existing)
	if err == nil {
		return UserRecord{}, fmt.Errorf("username already taken")
	}
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return UserRecord{}, fmt.Errorf("check existing username: %w", err)
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	user := UserRecord{
		ID:           newID("user"),
		Email:        email,
		Name:         firstNonEmpty(name, username),
		Role:         role,
		PasswordHash: passwordHash,
		CreatedAt:    now,
		UpdatedAt:    now,
	}
	if _, err := tx.Exec(`
INSERT INTO User (id, username, email, name, role, passwordHash, createdAt, updatedAt)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
`, user.ID, username, user.Email, user.Name, user.Role, user.PasswordHash, user.CreatedAt, user.UpdatedAt); err != nil {
		return UserRecord{}, fmt.Errorf("insert user: %w", err)
	}
	for _, code := range recoveryCodes {
		trimmed := strings.TrimSpace(strings.ToUpper(code))
		if trimmed == "" {
			continue
		}
		if _, err := tx.Exec(`
INSERT INTO RecoveryCode (id, userId, codeHash, createdAt)
VALUES (?, ?, ?, ?)
`, newID("rc"), user.ID, trimmed, now); err != nil {
			return UserRecord{}, fmt.Errorf("insert recovery code: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return UserRecord{}, fmt.Errorf("commit register user tx: %w", err)
	}
	return user, nil
}

func (s *Store) HasActiveTOTP(userID string) (bool, error) {
	if s == nil || s.db == nil {
		return false, fmt.Errorf("app db unavailable")
	}
	var count int
	if err := s.db.QueryRow(`
SELECT COUNT(*) FROM TotpDevice WHERE userId = ? AND revokedAt IS NULL
`, strings.TrimSpace(userID)).Scan(&count); err != nil {
		return false, fmt.Errorf("count active totp devices: %w", err)
	}
	return count > 0, nil
}

func (s *Store) ListPaperOrders(profileKey string, symbol string) ([]PaperOrderRecord, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return nil, err
	}
	query := `
SELECT po.id, up.profileKey, po.symbol, po.side, po.type, po.quantity, po.entryPrice,
       po.stopLoss, po.takeProfit, po.status, po.filledPrice,
       COALESCE(CAST(po.executedAt AS TEXT), ''), CAST(po.createdAt AS TEXT), CAST(po.updatedAt AS TEXT)
FROM PaperOrderRecord po
JOIN UserProfile up ON up.id = po.profileId
WHERE po.profileId = ?
`
	args := []any{profileID}
	if strings.TrimSpace(symbol) != "" {
		query += " AND po.symbol = ?"
		args = append(args, strings.TrimSpace(symbol))
	}
	query += " ORDER BY po.createdAt DESC"
	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("list paper orders: %w", err)
	}
	defer func() { _ = rows.Close() }()
	items := make([]PaperOrderRecord, 0)
	for rows.Next() {
		var item PaperOrderRecord
		var stopLoss, takeProfit, filledPrice sql.NullFloat64
		if err := rows.Scan(&item.ID, &item.ProfileKey, &item.Symbol, &item.Side, &item.Type, &item.Quantity, &item.EntryPrice, &stopLoss, &takeProfit, &item.Status, &filledPrice, &item.ExecutedAt, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan paper order: %w", err)
		}
		item.StopLoss = nullFloatPointer(stopLoss)
		item.TakeProfit = nullFloatPointer(takeProfit)
		item.FilledPrice = nullFloatPointer(filledPrice)
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate paper orders: %w", err)
	}
	return items, nil
}

func (s *Store) CreatePaperOrder(profileKey, symbol, side, orderType string, quantity, entryPrice float64, stopLoss, takeProfit *float64) (PaperOrderRecord, error) {
	if s == nil || s.db == nil {
		return PaperOrderRecord{}, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return PaperOrderRecord{}, err
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	record := PaperOrderRecord{
		ID:         newID("po"),
		ProfileKey: profileKey,
		Symbol:     strings.TrimSpace(symbol),
		Side:       strings.TrimSpace(side),
		Type:       strings.TrimSpace(orderType),
		Quantity:   quantity,
		EntryPrice: entryPrice,
		StopLoss:   stopLoss,
		TakeProfit: takeProfit,
		Status:     "open",
		CreatedAt:  now,
		UpdatedAt:  now,
	}
	if _, err := s.db.Exec(`
INSERT INTO PaperOrderRecord (id, profileId, symbol, side, type, quantity, entryPrice, stopLoss, takeProfit, status, createdAt, updatedAt)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`, record.ID, profileID, record.Symbol, record.Side, record.Type, record.Quantity, record.EntryPrice, nullFloatValue(record.StopLoss), nullFloatValue(record.TakeProfit), record.Status, record.CreatedAt, record.UpdatedAt); err != nil {
		return PaperOrderRecord{}, fmt.Errorf("insert paper order: %w", err)
	}
	return record, nil
}

func (s *Store) UpdatePaperOrderStatus(profileKey, orderID, status string) (PaperOrderRecord, bool, error) {
	if s == nil || s.db == nil {
		return PaperOrderRecord{}, false, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return PaperOrderRecord{}, false, err
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	res, err := s.db.Exec(`
UPDATE PaperOrderRecord SET status = ?, updatedAt = ? WHERE id = ? AND profileId = ?
`, strings.TrimSpace(status), now, strings.TrimSpace(orderID), profileID)
	if err != nil {
		return PaperOrderRecord{}, false, fmt.Errorf("update paper order status: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return PaperOrderRecord{}, false, fmt.Errorf("paper order rows affected: %w", err)
	}
	if rows == 0 {
		return PaperOrderRecord{}, false, nil
	}
	items, err := s.ListPaperOrders(profileKey, "")
	if err != nil {
		return PaperOrderRecord{}, false, err
	}
	for _, item := range items {
		if item.ID == orderID {
			return item, true, nil
		}
	}
	return PaperOrderRecord{}, false, fmt.Errorf("updated paper order not found")
}

func (s *Store) ListPriceAlerts(profileKey string, symbol string) ([]PriceAlertRecord, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return nil, err
	}
	query := `
SELECT pa.id, up.profileKey, pa.symbol, pa.condition, pa.targetValue, pa.enabled, pa.triggered,
       COALESCE(CAST(pa.triggeredAt AS TEXT), ''), COALESCE(pa.message, ''), CAST(pa.createdAt AS TEXT), CAST(pa.updatedAt AS TEXT)
FROM PriceAlertRecord pa
JOIN UserProfile up ON up.id = pa.profileId
WHERE pa.profileId = ?
`
	args := []any{profileID}
	if strings.TrimSpace(symbol) != "" {
		query += " AND pa.symbol = ?"
		args = append(args, strings.TrimSpace(symbol))
	}
	query += " ORDER BY pa.createdAt DESC"
	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("list price alerts: %w", err)
	}
	defer func() { _ = rows.Close() }()
	items := make([]PriceAlertRecord, 0)
	for rows.Next() {
		var item PriceAlertRecord
		var enabled, triggered int
		if err := rows.Scan(&item.ID, &item.ProfileKey, &item.Symbol, &item.Condition, &item.TargetValue, &enabled, &triggered, &item.TriggeredAt, &item.Message, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan price alert: %w", err)
		}
		item.Enabled = enabled != 0
		item.Triggered = triggered != 0
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate price alerts: %w", err)
	}
	return items, nil
}

func (s *Store) CreatePriceAlert(profileKey, symbol, condition string, targetValue float64, enabled bool, message string) (PriceAlertRecord, error) {
	if s == nil || s.db == nil {
		return PriceAlertRecord{}, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return PriceAlertRecord{}, err
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	record := PriceAlertRecord{
		ID:          newID("alert"),
		ProfileKey:  profileKey,
		Symbol:      strings.TrimSpace(symbol),
		Condition:   strings.TrimSpace(condition),
		TargetValue: targetValue,
		Enabled:     enabled,
		Triggered:   false,
		Message:     strings.TrimSpace(message),
		CreatedAt:   now,
		UpdatedAt:   now,
	}
	if _, err := s.db.Exec(`
INSERT INTO PriceAlertRecord (id, profileId, symbol, condition, targetValue, enabled, triggered, message, createdAt, updatedAt)
VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
`, record.ID, profileID, record.Symbol, record.Condition, record.TargetValue, boolToInt(record.Enabled), nullIfEmpty(record.Message), record.CreatedAt, record.UpdatedAt); err != nil {
		return PriceAlertRecord{}, fmt.Errorf("insert price alert: %w", err)
	}
	return record, nil
}

func (s *Store) UpdatePriceAlert(profileKey, alertID string, enabled, triggered *bool, triggeredAt *string, message *string) (PriceAlertRecord, bool, error) {
	if s == nil || s.db == nil {
		return PriceAlertRecord{}, false, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return PriceAlertRecord{}, false, err
	}
	existing, found, err := s.getPriceAlertByProfile(alertID, profileID)
	if err != nil || !found {
		return PriceAlertRecord{}, found, err
	}
	if enabled != nil {
		existing.Enabled = *enabled
	}
	if triggered != nil {
		existing.Triggered = *triggered
	}
	if triggeredAt != nil {
		existing.TriggeredAt = strings.TrimSpace(*triggeredAt)
	}
	if message != nil {
		existing.Message = strings.TrimSpace(*message)
	}
	existing.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	if _, err := s.db.Exec(`
UPDATE PriceAlertRecord
SET enabled = ?, triggered = ?, triggeredAt = ?, message = ?, updatedAt = ?
WHERE id = ? AND profileId = ?
`, boolToInt(existing.Enabled), boolToInt(existing.Triggered), nullIfEmpty(existing.TriggeredAt), nullIfEmpty(existing.Message), existing.UpdatedAt, alertID, profileID); err != nil {
		return PriceAlertRecord{}, false, fmt.Errorf("update price alert: %w", err)
	}
	return existing, true, nil
}

func (s *Store) DeletePriceAlert(profileKey, alertID string) (bool, error) {
	if s == nil || s.db == nil {
		return false, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return false, err
	}
	res, err := s.db.Exec(`DELETE FROM PriceAlertRecord WHERE id = ? AND profileId = ?`, strings.TrimSpace(alertID), profileID)
	if err != nil {
		return false, fmt.Errorf("delete price alert: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("price alert rows affected: %w", err)
	}
	return rows > 0, nil
}

func (s *Store) ListTradeJournalEntries(profileKey, symbol string, limit int) ([]TradeJournalRecord, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("app db unavailable")
	}
	if limit <= 0 {
		limit = 100
	}
	if limit > 500 {
		limit = 500
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return nil, err
	}
	query := `
SELECT tj.id, up.profileKey, tj.symbol, COALESCE(tj.orderId, ''), tj.note, COALESCE(tj.tags, '[]'),
       COALESCE(tj.context, ''), COALESCE(tj.screenshotUrl, ''), CAST(tj.createdAt AS TEXT), CAST(tj.updatedAt AS TEXT)
FROM TradeJournalRecord tj
JOIN UserProfile up ON up.id = tj.profileId
WHERE tj.profileId = ?
`
	args := []any{profileID}
	if strings.TrimSpace(symbol) != "" {
		query += " AND tj.symbol = ?"
		args = append(args, strings.TrimSpace(symbol))
	}
	query += " ORDER BY tj.createdAt DESC LIMIT ?"
	args = append(args, limit)
	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("list trade journal: %w", err)
	}
	defer func() { _ = rows.Close() }()
	items := make([]TradeJournalRecord, 0)
	for rows.Next() {
		var item TradeJournalRecord
		var tagsJSON string
		if err := rows.Scan(&item.ID, &item.ProfileKey, &item.Symbol, &item.OrderID, &item.Note, &tagsJSON, &item.ContextJSON, &item.ScreenshotURL, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan trade journal: %w", err)
		}
		item.Tags = decodeStringSlice(tagsJSON)
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate trade journal: %w", err)
	}
	return items, nil
}

func (s *Store) CreateTradeJournalEntry(profileKey, symbol, orderID, note string, tags []string, contextJSON, screenshotURL string) (TradeJournalRecord, error) {
	if s == nil || s.db == nil {
		return TradeJournalRecord{}, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return TradeJournalRecord{}, err
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	record := TradeJournalRecord{
		ID:            newID("tj"),
		ProfileKey:    profileKey,
		Symbol:        strings.TrimSpace(symbol),
		OrderID:       strings.TrimSpace(orderID),
		Note:          note,
		Tags:          dedupeStrings(tags),
		ContextJSON:   strings.TrimSpace(contextJSON),
		ScreenshotURL: strings.TrimSpace(screenshotURL),
		CreatedAt:     now,
		UpdatedAt:     now,
	}
	if _, err := s.db.Exec(`
INSERT INTO TradeJournalRecord (id, profileId, symbol, orderId, note, tags, context, screenshotUrl, createdAt, updatedAt)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`, record.ID, profileID, record.Symbol, nullIfEmpty(record.OrderID), record.Note, encodeStringSlice(record.Tags), nullIfEmpty(record.ContextJSON), nullIfEmpty(record.ScreenshotURL), record.CreatedAt, record.UpdatedAt); err != nil {
		return TradeJournalRecord{}, fmt.Errorf("insert trade journal: %w", err)
	}
	return record, nil
}

func (s *Store) UpdateTradeJournalEntry(profileKey, entryID string, note *string, tags []string, hasTags bool, contextJSON *string, screenshotURL *string) (TradeJournalRecord, bool, error) {
	if s == nil || s.db == nil {
		return TradeJournalRecord{}, false, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return TradeJournalRecord{}, false, err
	}
	record, found, err := s.getTradeJournalEntry(profileID, entryID)
	if err != nil || !found {
		return TradeJournalRecord{}, found, err
	}
	if note != nil {
		record.Note = *note
	}
	if hasTags {
		record.Tags = dedupeStrings(tags)
	}
	if contextJSON != nil {
		record.ContextJSON = strings.TrimSpace(*contextJSON)
	}
	if screenshotURL != nil {
		record.ScreenshotURL = strings.TrimSpace(*screenshotURL)
	}
	record.UpdatedAt = time.Now().UTC().Format(time.RFC3339Nano)
	if _, err := s.db.Exec(`
UPDATE TradeJournalRecord
SET note = ?, tags = ?, context = ?, screenshotUrl = ?, updatedAt = ?
WHERE id = ? AND profileId = ?
`, record.Note, encodeStringSlice(record.Tags), nullIfEmpty(record.ContextJSON), nullIfEmpty(record.ScreenshotURL), record.UpdatedAt, entryID, profileID); err != nil {
		return TradeJournalRecord{}, false, fmt.Errorf("update trade journal: %w", err)
	}
	return record, true, nil
}

func (s *Store) DeleteTradeJournalEntry(profileKey, entryID string) (bool, error) {
	if s == nil || s.db == nil {
		return false, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return false, err
	}
	res, err := s.db.Exec(`DELETE FROM TradeJournalRecord WHERE id = ? AND profileId = ?`, strings.TrimSpace(entryID), profileID)
	if err != nil {
		return false, fmt.Errorf("delete trade journal: %w", err)
	}
	rows, err := res.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("trade journal rows affected: %w", err)
	}
	return rows > 0, nil
}

func (s *Store) ListPortfolioSnapshots(profileKey string, limit int) ([]PortfolioSnapshotRecord, error) {
	if s == nil || s.db == nil {
		return nil, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return nil, err
	}
	if limit <= 0 {
		limit = 50
	}
	rows, err := s.db.Query(`
SELECT ps.id, up.profileKey, CAST(ps.generatedAt AS TEXT), ps.snapshotJson, CAST(ps.createdAt AS TEXT)
FROM PortfolioSnapshotRecord ps
JOIN UserProfile up ON up.id = ps.profileId
WHERE ps.profileId = ?
ORDER BY ps.generatedAt DESC
LIMIT ?
`, profileID, limit)
	if err != nil {
		return nil, fmt.Errorf("query portfolio snapshots: %w", err)
	}
	defer func() { _ = rows.Close() }()
	items := make([]PortfolioSnapshotRecord, 0)
	for rows.Next() {
		var item PortfolioSnapshotRecord
		if err := rows.Scan(&item.ID, &item.ProfileKey, &item.GeneratedAt, &item.SnapshotJSON, &item.CreatedAt); err != nil {
			return nil, fmt.Errorf("scan portfolio snapshot: %w", err)
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate portfolio snapshots: %w", err)
	}
	return items, nil
}

func (s *Store) SavePortfolioSnapshot(profileKey, generatedAt, snapshotJSON string) (PortfolioSnapshotRecord, error) {
	if s == nil || s.db == nil {
		return PortfolioSnapshotRecord{}, fmt.Errorf("app db unavailable")
	}
	profileID, err := s.ensureUserProfile(profileKey)
	if err != nil {
		return PortfolioSnapshotRecord{}, err
	}
	now := time.Now().UTC().Format(time.RFC3339Nano)
	record := PortfolioSnapshotRecord{
		ID:           newID("ps"),
		ProfileKey:   strings.TrimSpace(profileKey),
		GeneratedAt:  firstNonEmpty(strings.TrimSpace(generatedAt), now),
		SnapshotJSON: strings.TrimSpace(snapshotJSON),
		CreatedAt:    now,
	}
	if record.SnapshotJSON == "" {
		record.SnapshotJSON = "{}"
	}
	if _, err := s.db.Exec(`
INSERT INTO PortfolioSnapshotRecord (id, profileId, generatedAt, snapshotJson, createdAt)
VALUES (?, ?, ?, ?, ?)
`, record.ID, profileID, record.GeneratedAt, record.SnapshotJSON, record.CreatedAt); err != nil {
		return PortfolioSnapshotRecord{}, fmt.Errorf("insert portfolio snapshot: %w", err)
	}
	return record, nil
}

func (s *Store) WriteFileAuditLog(record FileAuditLogRecord) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	_, err := s.db.Exec(`
INSERT INTO FileAuditLog (id, documentId, action, actionClass, actorUserId, actorRole, requestId, target, status, errorCode, expiresAt, createdAt)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`, firstNonEmpty(record.ID, newID("faudit")), nullIfEmpty(record.DocumentID), record.Action, record.ActionClass, nullIfEmpty(record.ActorUserID), nullIfEmpty(record.ActorRole), record.RequestID, record.Target, firstNonEmpty(record.Status, "ok"), nullIfEmpty(record.ErrorCode), nullIfEmpty(record.ExpiresAt), firstNonEmpty(record.CreatedAt, time.Now().UTC().Format(time.RFC3339Nano)))
	if err != nil {
		return fmt.Errorf("insert file audit log: %w", err)
	}
	return nil
}

func (s *Store) WriteControlAuditLog(record ControlAuditLogRecord) error {
	if s == nil || s.db == nil {
		return fmt.Errorf("app db unavailable")
	}
	_, err := s.db.Exec(`
INSERT INTO ControlAuditLog (id, action, actionClass, actorUserId, actorRole, requestId, target, status, errorCode, expiresAt, createdAt)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`, firstNonEmpty(record.ID, newID("caudit")), record.Action, record.ActionClass, nullIfEmpty(record.ActorUserID), nullIfEmpty(record.ActorRole), record.RequestID, record.Target, firstNonEmpty(record.Status, "ok"), nullIfEmpty(record.ErrorCode), nullIfEmpty(record.ExpiresAt), firstNonEmpty(record.CreatedAt, time.Now().UTC().Format(time.RFC3339Nano)))
	if err != nil {
		return fmt.Errorf("insert control audit log: %w", err)
	}
	return nil
}

func (s *Store) getTradeJournalEntry(profileID, entryID string) (TradeJournalRecord, bool, error) {
	var record TradeJournalRecord
	var tagsJSON string
	err := s.db.QueryRow(`
SELECT tj.id, up.profileKey, tj.symbol, COALESCE(tj.orderId, ''), tj.note, COALESCE(tj.tags, '[]'),
       COALESCE(tj.context, ''), COALESCE(tj.screenshotUrl, ''), CAST(tj.createdAt AS TEXT), CAST(tj.updatedAt AS TEXT)
FROM TradeJournalRecord tj
JOIN UserProfile up ON up.id = tj.profileId
WHERE tj.id = ? AND tj.profileId = ?
LIMIT 1
`, strings.TrimSpace(entryID), profileID).Scan(&record.ID, &record.ProfileKey, &record.Symbol, &record.OrderID, &record.Note, &tagsJSON, &record.ContextJSON, &record.ScreenshotURL, &record.CreatedAt, &record.UpdatedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return TradeJournalRecord{}, false, nil
		}
		return TradeJournalRecord{}, false, fmt.Errorf("load trade journal: %w", err)
	}
	record.Tags = decodeStringSlice(tagsJSON)
	return record, true, nil
}

func (s *Store) getPriceAlertByProfile(alertID, profileID string) (PriceAlertRecord, bool, error) {
	var record PriceAlertRecord
	var enabled, triggered int
	err := s.db.QueryRow(`
SELECT pa.id, up.profileKey, pa.symbol, pa.condition, pa.targetValue, pa.enabled, pa.triggered,
       COALESCE(CAST(pa.triggeredAt AS TEXT), ''), COALESCE(pa.message, ''), CAST(pa.createdAt AS TEXT), CAST(pa.updatedAt AS TEXT)
FROM PriceAlertRecord pa
JOIN UserProfile up ON up.id = pa.profileId
WHERE pa.id = ? AND pa.profileId = ?
LIMIT 1
`, strings.TrimSpace(alertID), profileID).Scan(&record.ID, &record.ProfileKey, &record.Symbol, &record.Condition, &record.TargetValue, &enabled, &triggered, &record.TriggeredAt, &record.Message, &record.CreatedAt, &record.UpdatedAt)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return PriceAlertRecord{}, false, nil
		}
		return PriceAlertRecord{}, false, fmt.Errorf("load price alert: %w", err)
	}
	record.Enabled = enabled != 0
	record.Triggered = triggered != 0
	return record, true, nil
}

func ensureUserProfileTx(tx *sql.Tx, profileKey string) (string, error) {
	existingID, err := existingIDTx(tx, `SELECT id FROM UserProfile WHERE profileKey = ?`, profileKey)
	if err != nil {
		return "", fmt.Errorf("load user profile: %w", err)
	}
	if existingID != "" {
		return existingID, nil
	}
	id := newID("prof")
	now := time.Now().UTC().Format(time.RFC3339Nano)
	if _, err := tx.Exec(`
INSERT INTO UserProfile (id, profileKey, createdAt, updatedAt)
VALUES (?, ?, ?, ?)
`, id, profileKey, now, now); err != nil {
		return "", fmt.Errorf("create user profile: %w", err)
	}
	return id, nil
}

func (s *Store) ensureUserProfile(profileKey string) (string, error) {
	tx, err := s.db.Begin()
	if err != nil {
		return "", fmt.Errorf("begin user profile tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	id, err := ensureUserProfileTx(tx, profileKey)
	if err != nil {
		return "", err
	}
	if err := tx.Commit(); err != nil {
		return "", fmt.Errorf("commit user profile tx: %w", err)
	}
	return id, nil
}

func existingIDTx(tx *sql.Tx, query string, arg string) (string, error) {
	var id string
	err := tx.QueryRow(query, arg).Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("load existing id tx: %w", err)
	}
	return id, nil
}

func existingIDDB(db *sql.DB, query string, arg string) (string, error) {
	var id string
	err := db.QueryRow(query, arg).Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", fmt.Errorf("load existing id db: %w", err)
	}
	return id, nil
}

func dedupeSymbols(input []string) []string {
	seen := make(map[string]struct{}, len(input))
	result := make([]string, 0, len(input))
	for _, symbol := range input {
		trimmed := strings.TrimSpace(symbol)
		if trimmed == "" {
			continue
		}
		if _, ok := seen[trimmed]; ok {
			continue
		}
		seen[trimmed] = struct{}{}
		result = append(result, trimmed)
	}
	return result
}

func normalizeLayoutMode(value string) LayoutMode {
	switch strings.TrimSpace(strings.ToLower(value)) {
	case "two_horizontal", "2h":
		return LayoutTwoHorizontal
	case "two_vertical", "2v":
		return LayoutTwoVertical
	case "four", "4":
		return LayoutFour
	default:
		return LayoutSingle
	}
}

func boolToInt(value bool) int {
	if value {
		return 1
	}
	return 0
}

func newID(prefix string) string {
	buf := make([]byte, 8)
	if _, err := rand.Read(buf); err != nil {
		return fmt.Sprintf("%s_%d", prefix, time.Now().UTC().UnixNano())
	}
	return prefix + "_" + hex.EncodeToString(buf)
}

func nullIfEmpty(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return value
}

func nullStringValue(value sql.NullString) string {
	if !value.Valid {
		return ""
	}
	return value.String
}

func joinCSV(values []string) any {
	if len(values) == 0 {
		return nil
	}
	filtered := make([]string, 0, len(values))
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed != "" {
			filtered = append(filtered, trimmed)
		}
	}
	if len(filtered) == 0 {
		return nil
	}
	return strings.Join(filtered, ",")
}

func splitCSV(value string) []string {
	if strings.TrimSpace(value) == "" {
		return []string{}
	}
	parts := strings.Split(value, ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed != "" {
			out = append(out, trimmed)
		}
	}
	return out
}

func normalizeRoleOrDefault(value string) string {
	switch strings.TrimSpace(strings.ToLower(value)) {
	case "admin":
		return "admin"
	case "analyst":
		return "analyst"
	case "trader":
		return "trader"
	default:
		return "viewer"
	}
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed != "" {
			return trimmed
		}
	}
	return ""
}

func nullFloatPointer(value sql.NullFloat64) *float64 {
	if !value.Valid {
		return nil
	}
	v := value.Float64
	return &v
}

func nullFloatValue(value *float64) any {
	if value == nil {
		return nil
	}
	return *value
}

func encodeStringSlice(values []string) string {
	bytes, err := json.Marshal(dedupeStrings(values))
	if err != nil {
		return "[]"
	}
	return string(bytes)
}

func decodeStringSlice(value string) []string {
	if strings.TrimSpace(value) == "" {
		return []string{}
	}
	var out []string
	if err := json.Unmarshal([]byte(value), &out); err != nil {
		return []string{}
	}
	return dedupeStrings(out)
}

func dedupeStrings(values []string) []string {
	seen := make(map[string]struct{}, len(values))
	out := make([]string, 0, len(values))
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" {
			continue
		}
		if _, ok := seen[trimmed]; ok {
			continue
		}
		seen[trimmed] = struct{}{}
		out = append(out, trimmed)
	}
	return out
}
