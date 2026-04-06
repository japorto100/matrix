package appstate

import (
	"database/sql"
	"path/filepath"
	"testing"
	"time"
)

func assertTableExists(t *testing.T, db *sql.DB, tableName string) {
	t.Helper()
	var found string
	err := db.QueryRow(
		`SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?`,
		tableName,
	).Scan(&found)
	if err != nil {
		t.Fatalf("expected table %s to exist: %v", tableName, err)
	}
	if found != tableName {
		t.Fatalf("table lookup returned %q, want %q", found, tableName)
	}
}

func assertTableCount(t *testing.T, db *sql.DB, tableName string, expected int) {
	t.Helper()
	var count int
	if err := db.QueryRow(`SELECT COUNT(*) FROM ` + tableName).Scan(&count); err != nil {
		t.Fatalf("count rows in %s: %v", tableName, err)
	}
	if count != expected {
		t.Fatalf("%s row count = %d, want %d", tableName, count, expected)
	}
}

func TestSQLiteStoreMigratesAllCurrentGoOwnedTables(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	requiredTables := []string{
		"UserProfile",
		"LayoutPreference",
		"Watchlist",
		"WatchlistItem",
		"User",
		"UserConsent",
		"VerificationToken",
		"TotpDevice",
		"RecoveryCode",
		"Authenticator",
		"PriceAlertRecord",
		"PaperOrderRecord",
		"TradeJournalRecord",
	}
	for _, tableName := range requiredTables {
		assertTableExists(t, store.db, tableName)
	}
}

func TestPreferencesRoundTrip(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	saved, err := store.SavePreferences(Preferences{
		ProfileKey:      "paper-default",
		Favorites:       []string{"AAPL", "MSFT", "AAPL"},
		Layout:          LayoutTwoHorizontal,
		SidebarOpen:     true,
		ShowDrawingTool: true,
		DarkMode:        false,
	})
	if err != nil {
		t.Fatalf("save preferences: %v", err)
	}
	if len(saved.Favorites) != 2 {
		t.Fatalf("expected deduped favorites, got %+v", saved.Favorites)
	}

	got, err := store.GetPreferences("paper-default")
	if err != nil {
		t.Fatalf("get preferences: %v", err)
	}
	if got.Layout != LayoutTwoHorizontal {
		t.Fatalf("layout = %q, want %q", got.Layout, LayoutTwoHorizontal)
	}
	if len(got.Favorites) != 2 {
		t.Fatalf("favorites len = %d, want 2", len(got.Favorites))
	}
}

func TestUpdateUserRole(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	now := "2026-03-17T12:00:00Z"
	if _, seedErr := store.db.Exec(`
INSERT INTO User (id, email, name, role, createdAt, updatedAt) VALUES
('admin-1', 'admin@example.com', 'Admin', 'admin', ?, ?),
('user-1', 'user@example.com', 'User', 'viewer', ?, ?)
`, now, now, now, now); seedErr != nil {
		t.Fatalf("seed users: %v", seedErr)
	}

	updated, err := store.UpdateUserRole("admin-1", "user-1", "trader")
	if err != nil {
		t.Fatalf("update user role: %v", err)
	}
	if updated.Role != "trader" {
		t.Fatalf("role = %q, want trader", updated.Role)
	}
}

func TestUserLookupAndConsentRoundTrip(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	now := "2026-03-17T12:00:00Z"
	if _, seedErr := store.db.Exec(`
INSERT INTO User (id, email, name, role, createdAt, updatedAt)
VALUES ('user-2', 'consent@example.com', 'Consent User', 'viewer', ?, ?)
`, now, now); seedErr != nil {
		t.Fatalf("seed user: %v", seedErr)
	}

	user, err := store.GetUserByIDOrEmail("", "consent@example.com")
	if err != nil {
		t.Fatalf("get user by email: %v", err)
	}
	if user.ID != "user-2" {
		t.Fatalf("user id = %q, want user-2", user.ID)
	}

	consent, err := store.GetOrCreateUserConsent("user-2")
	if err != nil {
		t.Fatalf("get or create consent: %v", err)
	}
	if consent.LLMProcessing {
		t.Fatal("expected default llm consent false")
	}

	enable := true
	updated, err := store.UpdateUserConsent("user-2", &enable, nil, nil)
	if err != nil {
		t.Fatalf("update consent: %v", err)
	}
	if !updated.LLMProcessing {
		t.Fatal("expected llm consent true after update")
	}
}

func TestAuthStateHelpers(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	now := "2026-03-17T12:00:00Z"
	if _, seedErr := store.db.Exec(`
INSERT INTO User (id, email, username, name, role, passwordHash, createdAt, updatedAt)
VALUES ('auth-user', 'auth@example.com', 'auth-user', 'Auth User', 'viewer', 'scrypt$16384$8$1$CO7x4hQ9b_MhO7Jin0CeNQ$eToLrgrP0k5fYhF4m7HchPKM6m5AqLu6uf4fPrhCW3AF4LqFxy3rAKsvLKiVv7M5w8ABmIkfM7g3aQiPEEsdgA', ?, ?)
`, now, now); seedErr != nil {
		t.Fatalf("seed auth user: %v", seedErr)
	}

	if setupErr := store.CreateTOTPSetup("auth-user", "secret-value", []string{"RECOVERY1", "RECOVERY2"}); setupErr != nil {
		t.Fatalf("create totp setup: %v", setupErr)
	}
	match, err := store.FindRecoveryCodeByEmail("auth@example.com", "RECOVERY1")
	if err != nil {
		t.Fatalf("find recovery code: %v", err)
	}
	if match.UserID != "auth-user" {
		t.Fatalf("recovery match user = %q, want auth-user", match.UserID)
	}
	if deleteErr := store.DeleteRecoveryCode(match.CodeID); deleteErr != nil {
		t.Fatalf("delete recovery code: %v", deleteErr)
	}
	if _, lookupErr := store.FindRecoveryCodeByEmail("auth@example.com", "RECOVERY1"); lookupErr == nil {
		t.Fatal("expected deleted recovery code lookup to fail")
	}

	expiresAt := time.Date(2026, 3, 18, 12, 0, 0, 0, time.UTC)
	if createErr := store.CreateVerificationToken("auth@example.com", "token-1", expiresAt); createErr != nil {
		t.Fatalf("create verification token: %v", createErr)
	}
	valid, err := store.GetValidVerificationToken("auth@example.com", "token-1", time.Date(2026, 3, 17, 12, 0, 0, 0, time.UTC))
	if err != nil {
		t.Fatalf("get valid verification token: %v", err)
	}
	if !valid {
		t.Fatal("expected verification token to be valid")
	}
	if deleteErr := store.DeleteVerificationToken("auth@example.com", "token-1"); deleteErr != nil {
		t.Fatalf("delete verification token: %v", deleteErr)
	}
	valid, err = store.GetValidVerificationToken("auth@example.com", "token-1", time.Date(2026, 3, 17, 12, 0, 0, 0, time.UTC))
	if err != nil {
		t.Fatalf("get deleted verification token: %v", err)
	}
	if valid {
		t.Fatal("expected deleted verification token to be invalid")
	}
}

func TestPasskeyAuthenticatorRoundTrip(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	user, authenticators, err := store.GetOrCreateUserByEmail("passkey@example.com", "Passkey User", "viewer")
	if err != nil {
		t.Fatalf("get or create user by email: %v", err)
	}
	if user.ID == "" {
		t.Fatal("expected created user id")
	}
	if len(authenticators) != 0 {
		t.Fatalf("expected no authenticators initially, got %d", len(authenticators))
	}

	stored, err := store.UpsertAuthenticator(PasskeyAuthenticator{
		UserID:               user.ID,
		ProviderAccountID:    "cred-1",
		CredentialID:         "cred-1",
		CredentialPublicKey:  "public-key-1",
		Counter:              1,
		CredentialDeviceType: "singleDevice",
		CredentialBackedUp:   false,
		Transports:           []string{"internal", "usb"},
		Name:                 "Laptop Passkey",
	})
	if err != nil {
		t.Fatalf("upsert authenticator: %v", err)
	}
	if stored.ID == "" {
		t.Fatal("expected stored authenticator id")
	}

	loaded, owner, err := store.GetAuthenticatorByCredentialID("cred-1")
	if err != nil {
		t.Fatalf("get authenticator by credential id: %v", err)
	}
	if owner.ID != user.ID {
		t.Fatalf("owner id = %q, want %q", owner.ID, user.ID)
	}
	if loaded.CredentialID != "cred-1" {
		t.Fatalf("credential id = %q, want cred-1", loaded.CredentialID)
	}

	updated, err := store.UpdateAuthenticatorUsage("cred-1", 7, "multiDevice", true)
	if err != nil {
		t.Fatalf("update authenticator usage: %v", err)
	}
	if updated.Counter != 7 || !updated.CredentialBackedUp {
		t.Fatalf("unexpected updated authenticator: %+v", updated)
	}

	_, err = store.UpsertAuthenticator(PasskeyAuthenticator{
		UserID:               user.ID,
		ProviderAccountID:    "cred-2",
		CredentialID:         "cred-2",
		CredentialPublicKey:  "public-key-2",
		Counter:              0,
		CredentialDeviceType: "singleDevice",
		CredentialBackedUp:   false,
		Name:                 "Phone Passkey",
	})
	if err != nil {
		t.Fatalf("insert second authenticator: %v", err)
	}

	remaining, err := store.DeleteAuthenticatorForUser(user.ID, stored.ID)
	if err != nil {
		t.Fatalf("delete authenticator for user: %v", err)
	}
	if remaining != 1 {
		t.Fatalf("remaining authenticators = %d, want 1", remaining)
	}
}

func TestRegisterUserAndCredentialLookup(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	user, err := store.RegisterUser(
		"login@example.com",
		"login_user",
		"Login User",
		"viewer",
		"scrypt$16384$8$1$CO7x4hQ9b_MhO7Jin0CeNQ$eToLrgrP0k5fYhF4m7HchPKM6m5AqLu6uf4fPrhCW3AF4LqFxy3rAKsvLKiVv7M5w8ABmIkfM7g3aQiPEEsdgA",
		[]string{"REG1"},
	)
	if err != nil {
		t.Fatalf("register user: %v", err)
	}
	if user.ID == "" {
		t.Fatal("expected registered user id")
	}

	found, err := store.FindUserForCredentials("login@example.com")
	if err != nil {
		t.Fatalf("find by email: %v", err)
	}
	if found.ID != user.ID {
		t.Fatalf("found id = %q, want %q", found.ID, user.ID)
	}

	found, err = store.FindUserForCredentials("login_user")
	if err != nil {
		t.Fatalf("find by username: %v", err)
	}
	if found.ID != user.ID {
		t.Fatalf("found username id = %q, want %q", found.ID, user.ID)
	}

	hasTOTP, err := store.HasActiveTOTP(user.ID)
	if err != nil {
		t.Fatalf("has active totp: %v", err)
	}
	if hasTOTP {
		t.Fatal("expected no totp initially")
	}

	if setupErr := store.CreateTOTPSetup(user.ID, "secret", []string{"X1"}); setupErr != nil {
		t.Fatalf("create totp setup: %v", setupErr)
	}
	hasTOTP, err = store.HasActiveTOTP(user.ID)
	if err != nil {
		t.Fatalf("has active totp after setup: %v", err)
	}
	if !hasTOTP {
		t.Fatal("expected totp after setup")
	}
}

func TestOrdersAndAlertsRoundTrip(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	order, err := store.CreatePaperOrder("paper-default", "AAPL", "buy", "market", 2, 150, nil, nil)
	if err != nil {
		t.Fatalf("create paper order: %v", err)
	}
	if order.ID == "" {
		t.Fatal("expected order id")
	}
	orders, err := store.ListPaperOrders("paper-default", "")
	if err != nil {
		t.Fatalf("list paper orders: %v", err)
	}
	if len(orders) != 1 {
		t.Fatalf("orders len = %d, want 1", len(orders))
	}
	updatedOrder, found, err := store.UpdatePaperOrderStatus("paper-default", order.ID, "filled")
	if err != nil {
		t.Fatalf("update paper order status: %v", err)
	}
	if !found || updatedOrder.Status != "filled" {
		t.Fatalf("unexpected updated order: %+v found=%v", updatedOrder, found)
	}

	alert, err := store.CreatePriceAlert("paper-default", "AAPL", "above", 200, true, "watch breakout")
	if err != nil {
		t.Fatalf("create price alert: %v", err)
	}
	if alert.ID == "" {
		t.Fatal("expected alert id")
	}
	alerts, err := store.ListPriceAlerts("paper-default", "")
	if err != nil {
		t.Fatalf("list price alerts: %v", err)
	}
	if len(alerts) != 1 {
		t.Fatalf("alerts len = %d, want 1", len(alerts))
	}
	triggeredAt := time.Date(2026, 3, 17, 15, 4, 5, 0, time.UTC).Format(time.RFC3339Nano)
	message := "triggered"
	triggered := new(bool)
	*triggered = true
	updatedAlert, found, err := store.UpdatePriceAlert("paper-default", alert.ID, nil, triggered, &triggeredAt, &message)
	if err != nil {
		t.Fatalf("update price alert: %v", err)
	}
	if !found || !updatedAlert.Triggered {
		t.Fatalf("unexpected updated alert: %+v found=%v", updatedAlert, found)
	}
	deleted, err := store.DeletePriceAlert("paper-default", alert.ID)
	if err != nil {
		t.Fatalf("delete price alert: %v", err)
	}
	if !deleted {
		t.Fatal("expected alert to be deleted")
	}
}

func TestPortfolioSnapshotsAndAuditLogs(t *testing.T) {
	t.Parallel()

	store, err := NewSQLiteStore(filepath.Join(t.TempDir(), "backend.db"))
	if err != nil {
		t.Fatalf("new sqlite store: %v", err)
	}
	t.Cleanup(func() {
		if closeErr := store.Close(); closeErr != nil {
			t.Fatalf("close store: %v", closeErr)
		}
	})

	saved, err := store.SavePortfolioSnapshot("paper-default", "2026-03-19T12:00:00Z", `{"generatedAt":"2026-03-19T12:00:00Z","positions":[]}`)
	if err != nil {
		t.Fatalf("save portfolio snapshot: %v", err)
	}
	if saved.ID == "" {
		t.Fatal("expected snapshot id")
	}
	snapshots, err := store.ListPortfolioSnapshots("paper-default", 10)
	if err != nil {
		t.Fatalf("list portfolio snapshots: %v", err)
	}
	if len(snapshots) != 1 {
		t.Fatalf("snapshots len = %d, want 1", len(snapshots))
	}

	if err := store.WriteFileAuditLog(FileAuditLogRecord{
		Action:      "upload",
		ActionClass: "bounded-write",
		RequestID:   "req-file-1",
		Target:      "report.pdf",
		Status:      "ok",
	}); err != nil {
		t.Fatalf("write file audit log: %v", err)
	}
	if err := store.WriteControlAuditLog(ControlAuditLogRecord{
		Action:      "kill-session",
		ActionClass: "approval-write",
		RequestID:   "req-control-1",
		Target:      "session-1",
		Status:      "failed",
		ErrorCode:   "APPROVAL_REQUIRED",
	}); err != nil {
		t.Fatalf("write control audit log: %v", err)
	}

	assertTableCount(t, store.db, "FileAuditLog", 1)
	assertTableCount(t, store.db, "ControlAuditLog", 1)
}
