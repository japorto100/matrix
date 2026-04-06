package http

import (
	"crypto/subtle"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"golang.org/x/crypto/scrypt"
	"golang.org/x/text/unicode/norm"
	"tradeviewfusion/go-backend/internal/appstate"
)

type appStateStore interface {
	GetPreferences(profileKey string) (appstate.Preferences, error)
	SavePreferences(prefs appstate.Preferences) (appstate.Preferences, error)
	ListUsers(query string, limit int) ([]appstate.UserRecord, error)
	UpdateUserRole(actorUserID, targetUserID, role string) (appstate.UserRecord, error)
	GetUserByIDOrEmail(userID, email string) (appstate.UserRecord, error)
	GetOrCreateUserConsent(userID string) (appstate.ConsentRecord, error)
	UpdateUserConsent(userID string, llm, analytics, marketing *bool) (appstate.ConsentRecord, error)
	SetPasswordHash(userID, newHash string) error
	CreateTOTPSetup(userID, secret string, recoveryCodes []string) error
	CreateVerificationToken(identifier, token string, expiresAt time.Time) error
	GetValidVerificationToken(identifier, token string, now time.Time) (bool, error)
	DeleteVerificationToken(identifier, token string) error
	FindRecoveryCodeByEmail(email, recoveryCode string) (appstate.RecoveryMatch, error)
	DeleteRecoveryCode(codeID string) error
	GetOrCreateUserByEmail(email, displayName, role string) (appstate.UserRecord, []appstate.PasskeyAuthenticator, error)
	ListAuthenticatorsByUserID(userID string) ([]appstate.PasskeyAuthenticator, error)
	UpsertAuthenticator(authenticator appstate.PasskeyAuthenticator) (appstate.PasskeyAuthenticator, error)
	GetAuthenticatorByCredentialID(credentialID string) (appstate.PasskeyAuthenticator, appstate.UserRecord, error)
	UpdateAuthenticatorUsage(credentialID string, counter int, deviceType string, backedUp bool) (appstate.PasskeyAuthenticator, error)
	DeleteAuthenticatorForUser(userID, authenticatorID string) (int, error)
	FindUserForCredentials(identifier string) (appstate.UserRecord, error)
	RegisterUser(email, username, name, role, passwordHash string, recoveryCodes []string) (appstate.UserRecord, error)
	HasActiveTOTP(userID string) (bool, error)
	ListPaperOrders(profileKey string, symbol string) ([]appstate.PaperOrderRecord, error)
	CreatePaperOrder(profileKey, symbol, side, orderType string, quantity, entryPrice float64, stopLoss, takeProfit *float64) (appstate.PaperOrderRecord, error)
	UpdatePaperOrderStatus(profileKey, orderID, status string) (appstate.PaperOrderRecord, bool, error)
	ListPriceAlerts(profileKey string, symbol string) ([]appstate.PriceAlertRecord, error)
	CreatePriceAlert(profileKey, symbol, condition string, targetValue float64, enabled bool, message string) (appstate.PriceAlertRecord, error)
	UpdatePriceAlert(profileKey, alertID string, enabled, triggered *bool, triggeredAt *string, message *string) (appstate.PriceAlertRecord, bool, error)
	DeletePriceAlert(profileKey, alertID string) (bool, error)
	ListTradeJournalEntries(profileKey, symbol string, limit int) ([]appstate.TradeJournalRecord, error)
	CreateTradeJournalEntry(profileKey, symbol, orderID, note string, tags []string, contextJSON, screenshotURL string) (appstate.TradeJournalRecord, error)
	UpdateTradeJournalEntry(profileKey, entryID string, note *string, tags []string, hasTags bool, contextJSON *string, screenshotURL *string) (appstate.TradeJournalRecord, bool, error)
	DeleteTradeJournalEntry(profileKey, entryID string) (bool, error)
	ListPortfolioSnapshots(profileKey string, limit int) ([]appstate.PortfolioSnapshotRecord, error)
	SavePortfolioSnapshot(profileKey, generatedAt, snapshotJSON string) (appstate.PortfolioSnapshotRecord, error)
	WriteFileAuditLog(record appstate.FileAuditLogRecord) error
	WriteControlAuditLog(record appstate.ControlAuditLogRecord) error
}

type preferencesRequest struct {
	ProfileKey      string   `json:"profileKey"`
	Favorites       []string `json:"favorites"`
	Layout          string   `json:"layout"`
	SidebarOpen     *bool    `json:"sidebarOpen"`
	ShowDrawingTool *bool    `json:"showDrawingTool"`
	DarkMode        *bool    `json:"darkMode"`
}

func FusionPreferencesHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		switch r.Method {
		case http.MethodGet:
			profileKey := strings.TrimSpace(r.URL.Query().Get("profileKey"))
			if profileKey == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "profileKey is required", "reason": "MISSING_PROFILE_KEY"})
				return
			}
			prefs, err := store.GetPreferences(profileKey)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": "Failed to load preferences", "reason": "PREFERENCES_LOAD_FAILED"})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"success": true,
				"preferences": map[string]any{
					"profileKey":      prefs.ProfileKey,
					"favorites":       prefs.Favorites,
					"layout":          fromDBLayoutMode(string(prefs.Layout)),
					"sidebarOpen":     prefs.SidebarOpen,
					"showDrawingTool": prefs.ShowDrawingTool,
					"darkMode":        prefs.DarkMode,
				},
			})
		case http.MethodPut:
			var req preferencesRequest
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid JSON body", "reason": "INVALID_JSON_BODY"})
				return
			}
			if strings.TrimSpace(req.ProfileKey) == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "profileKey is required", "reason": "MISSING_PROFILE_KEY"})
				return
			}
			prefs, err := store.SavePreferences(appstate.Preferences{
				ProfileKey:      strings.TrimSpace(req.ProfileKey),
				Favorites:       req.Favorites,
				Layout:          appstate.LayoutMode(toDBLayoutMode(req.Layout)),
				SidebarOpen:     boolOrDefault(req.SidebarOpen, true),
				ShowDrawingTool: boolOrDefault(req.ShowDrawingTool, false),
				DarkMode:        boolOrDefault(req.DarkMode, true),
			})
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": "Failed to save preferences", "reason": "PREFERENCES_SAVE_FAILED"})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"success": true,
				"preferences": map[string]any{
					"profileKey":      prefs.ProfileKey,
					"favorites":       prefs.Favorites,
					"layout":          fromDBLayoutMode(string(prefs.Layout)),
					"sidebarOpen":     prefs.SidebarOpen,
					"showDrawingTool": prefs.ShowDrawingTool,
					"darkMode":        prefs.DarkMode,
				},
			})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPut}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func AdminUsersHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		actorID := strings.TrimSpace(r.Header.Get("X-Auth-User-Id"))
		actorEmail := strings.TrimSpace(r.Header.Get("X-Auth-User-Email"))
		actorRole := normalizeRole(strings.TrimSpace(r.Header.Get("X-Auth-User-Role")))
		if actorRole != "admin" {
			writeJSON(w, http.StatusForbidden, map[string]any{"error": "forbidden"})
			return
		}
		switch r.Method {
		case http.MethodGet:
			query := strings.TrimSpace(r.URL.Query().Get("q"))
			limitRaw, _ := strconv.Atoi(strings.TrimSpace(r.URL.Query().Get("limit")))
			users, err := store.ListUsers(query, limitRaw)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": "failed to list users"})
				return
			}
			items := make([]map[string]any, 0, len(users))
			for _, user := range users {
				items = append(items, map[string]any{
					"id":        user.ID,
					"email":     emptyToNil(user.Email),
					"name":      emptyToNil(user.Name),
					"role":      normalizeRole(user.Role),
					"createdAt": user.CreatedAt,
					"updatedAt": user.UpdatedAt,
				})
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"actor": map[string]any{
					"id":    actorID,
					"email": emptyToNil(actorEmail),
					"role":  actorRole,
				},
				"total": len(items),
				"items": items,
			})
		case http.MethodPatch:
			var req struct {
				UserID string `json:"userId"`
				Role   string `json:"role"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			userID := strings.TrimSpace(req.UserID)
			role := normalizeRole(req.Role)
			if userID == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "userId is required"})
				return
			}
			if role == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "role must be one of viewer|analyst|trader|admin"})
				return
			}
			updated, err := store.UpdateUserRole(actorID, userID, role)
			if err != nil {
				status := http.StatusBadGateway
				message := err.Error()
				if strings.Contains(message, "user not found") {
					status = http.StatusNotFound
				} else if strings.Contains(message, "cannot remove the last admin role") {
					status = http.StatusConflict
				}
				writeJSON(w, status, map[string]any{"error": message})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"updated": map[string]any{
					"id":        updated.ID,
					"email":     emptyToNil(updated.Email),
					"name":      emptyToNil(updated.Name),
					"role":      normalizeRole(updated.Role),
					"updatedAt": updated.UpdatedAt,
				},
			})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPatch}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func CurrentUserHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		if r.Method != http.MethodGet {
			w.Header().Set("Allow", http.MethodGet)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
			return
		}
		userID := strings.TrimSpace(r.Header.Get("X-Auth-User-Id"))
		email := strings.TrimSpace(r.Header.Get("X-Auth-User-Email"))
		user, err := store.GetUserByIDOrEmail(userID, email)
		if err != nil {
			status := http.StatusBadGateway
			if strings.Contains(err.Error(), "user not found") {
				status = http.StatusNotFound
			}
			writeJSON(w, status, map[string]any{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"user": map[string]any{
				"id":    user.ID,
				"email": emptyToNil(user.Email),
				"role":  normalizeRole(user.Role),
			},
		})
	}
}

func AuthConsentHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		userID := strings.TrimSpace(r.Header.Get("X-Auth-User-Id"))
		if userID == "" {
			writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "unauthorized"})
			return
		}
		switch r.Method {
		case http.MethodGet:
			consent, err := store.GetOrCreateUserConsent(userID)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"consent": map[string]any{
					"llmProcessing":    consent.LLMProcessing,
					"analyticsEnabled": consent.AnalyticsEnabled,
					"marketingEnabled": consent.MarketingEnabled,
					"privacyVersion":   consent.PrivacyVersion,
					"consentedAt":      emptyToNil(consent.ConsentedAt),
					"withdrawnAt":      emptyToNil(consent.WithdrawnAt),
				},
			})
		case http.MethodPatch:
			var req struct {
				LLMProcessing    *bool `json:"llmProcessing"`
				AnalyticsEnabled *bool `json:"analyticsEnabled"`
				MarketingEnabled *bool `json:"marketingEnabled"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			consent, err := store.UpdateUserConsent(userID, req.LLMProcessing, req.AnalyticsEnabled, req.MarketingEnabled)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"consent": map[string]any{
					"llmProcessing":    consent.LLMProcessing,
					"analyticsEnabled": consent.AnalyticsEnabled,
					"marketingEnabled": consent.MarketingEnabled,
					"privacyVersion":   consent.PrivacyVersion,
					"consentedAt":      emptyToNil(consent.ConsentedAt),
					"withdrawnAt":      emptyToNil(consent.WithdrawnAt),
				},
			})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPatch}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func AuthActionsHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		action := strings.TrimSpace(strings.TrimPrefix(r.URL.Path, "/api/v1/auth/actions/"))
		if action == "" {
			writeJSON(w, http.StatusNotFound, map[string]any{"error": "auth action not found"})
			return
		}
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
			return
		}
		switch action {
		case "totp-enable":
			handleAuthTOTPEnable(store, w, r)
		case "password-change":
			handleAuthPasswordChange(store, w, r)
		case "password-recovery-request":
			handleAuthPasswordRecoveryRequest(store, w, r)
		case "password-recovery-reset":
			handleAuthPasswordRecoveryReset(store, w, r)
		case "password-recovery-code":
			handleAuthPasswordRecoveryCode(store, w, r)
		default:
			writeJSON(w, http.StatusNotFound, map[string]any{"error": "auth action not found"})
		}
	}
}

func handleAuthTOTPEnable(store appStateStore, w http.ResponseWriter, r *http.Request) {
	userID := strings.TrimSpace(r.Header.Get("X-Auth-User-Id"))
	if userID == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "unauthorized"})
		return
	}
	var req struct {
		Secret        string   `json:"secret"`
		RecoveryCodes []string `json:"recoveryCodes"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	if strings.TrimSpace(req.Secret) == "" || len(req.RecoveryCodes) == 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "secret and recoveryCodes are required"})
		return
	}
	if err := store.CreateTOTPSetup(userID, req.Secret, req.RecoveryCodes); err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true})
}

func handleAuthPasswordChange(store appStateStore, w http.ResponseWriter, r *http.Request) {
	userID := strings.TrimSpace(r.Header.Get("X-Auth-User-Id"))
	if userID == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "unauthorized"})
		return
	}
	var req struct {
		CurrentPassword string `json:"currentPassword"`
		NewHash         string `json:"newHash"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	if strings.TrimSpace(req.CurrentPassword) == "" || strings.TrimSpace(req.NewHash) == "" {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "currentPassword and newHash are required"})
		return
	}
	user, err := store.GetUserByIDOrEmail(userID, "")
	if err != nil {
		status := http.StatusBadGateway
		if strings.Contains(err.Error(), "user not found") {
			status = http.StatusNotFound
		}
		writeJSON(w, status, map[string]any{"error": err.Error()})
		return
	}
	if strings.TrimSpace(user.PasswordHash) == "" {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "Primary authentication method is not password-based."})
		return
	}
	valid, err := verifyEncodedPassword(req.CurrentPassword, user.PasswordHash)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	if !valid {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "Invalid current password."})
		return
	}
	if err := store.SetPasswordHash(user.ID, req.NewHash); err != nil {
		status := http.StatusBadGateway
		if strings.Contains(err.Error(), "user not found") {
			status = http.StatusNotFound
		}
		writeJSON(w, status, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true})
}

func handleAuthPasswordRecoveryRequest(store appStateStore, w http.ResponseWriter, r *http.Request) {
	var req struct {
		Identifier string `json:"identifier"`
		Token      string `json:"token"`
		ExpiresAt  string `json:"expiresAt"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	user, err := store.GetUserByIDOrEmail("", req.Identifier)
	if err != nil {
		if strings.Contains(err.Error(), "user not found") {
			writeJSON(w, http.StatusOK, map[string]any{"success": true})
			return
		}
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	expiresAt, err := time.Parse(time.RFC3339Nano, strings.TrimSpace(req.ExpiresAt))
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "expiresAt must be RFC3339"})
		return
	}
	if err := store.CreateVerificationToken(req.Identifier, req.Token, expiresAt); err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "userId": user.ID})
}

func handleAuthPasswordRecoveryReset(store appStateStore, w http.ResponseWriter, r *http.Request) {
	var req struct {
		Email   string `json:"email"`
		Token   string `json:"token"`
		NewHash string `json:"newHash"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	valid, err := store.GetValidVerificationToken(req.Email, req.Token, time.Now().UTC())
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	if !valid {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "Expired or invalid token."})
		return
	}
	user, err := store.GetUserByIDOrEmail("", req.Email)
	if err != nil {
		writeJSON(w, http.StatusNotFound, map[string]any{"error": "user not found"})
		return
	}
	if err := store.SetPasswordHash(user.ID, req.NewHash); err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	_ = store.DeleteVerificationToken(req.Email, req.Token)
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "userId": user.ID})
}

func handleAuthPasswordRecoveryCode(store appStateStore, w http.ResponseWriter, r *http.Request) {
	var req struct {
		Email        string `json:"email"`
		RecoveryCode string `json:"recoveryCode"`
		NewHash      string `json:"newHash"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	match, err := store.FindRecoveryCodeByEmail(req.Email, req.RecoveryCode)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "Invalid or already used recovery code."})
		return
	}
	if err := store.SetPasswordHash(match.UserID, req.NewHash); err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	_ = store.DeleteRecoveryCode(match.CodeID)
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "userId": match.UserID})
}

func AuthPasskeysHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		action := strings.TrimSpace(strings.TrimPrefix(r.URL.Path, "/api/v1/auth/passkeys/"))
		if action == "" {
			writeJSON(w, http.StatusNotFound, map[string]any{"error": "passkey action not found"})
			return
		}
		switch action {
		case "registration-context":
			handlePasskeyRegistrationContext(store, w, r)
		case "registration-verify":
			handlePasskeyRegistrationPersist(store, w, r)
		case "authentication-context":
			handlePasskeyAuthenticationContext(store, w, r)
		case "credential-record":
			handlePasskeyCredentialRecord(store, w, r)
		case "authentication-verify":
			handlePasskeyAuthenticationPersist(store, w, r)
		case "devices":
			handlePasskeyDevices(store, w, r)
		default:
			writeJSON(w, http.StatusNotFound, map[string]any{"error": "passkey action not found"})
		}
	}
}

func AuthOwnerHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		action := strings.TrimSpace(strings.TrimPrefix(r.URL.Path, "/api/v1/auth/owner/"))
		if action == "" {
			writeJSON(w, http.StatusNotFound, map[string]any{"error": "auth owner action not found"})
			return
		}
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
			return
		}
		switch action {
		case "authorize":
			handleAuthOwnerAuthorize(store, w, r)
		case "register":
			handleAuthOwnerRegister(store, w, r)
		case "user-security":
			handleAuthOwnerUserSecurity(store, w, r)
		default:
			writeJSON(w, http.StatusNotFound, map[string]any{"error": "auth owner action not found"})
		}
	}
}

func FusionOrdersHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		switch r.Method {
		case http.MethodGet:
			profileKey := strings.TrimSpace(r.URL.Query().Get("profileKey"))
			if profileKey == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "profileKey is required", "reason": "MISSING_PROFILE_KEY"})
				return
			}
			orders, err := store.ListPaperOrders(profileKey, strings.TrimSpace(r.URL.Query().Get("symbol")))
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "orders": serializeOrders(orders)})
		case http.MethodPost:
			var req struct {
				ProfileKey string   `json:"profileKey"`
				Symbol     string   `json:"symbol"`
				Side       string   `json:"side"`
				Type       string   `json:"type"`
				Quantity   float64  `json:"quantity"`
				EntryPrice float64  `json:"entryPrice"`
				StopLoss   *float64 `json:"stopLoss"`
				TakeProfit *float64 `json:"takeProfit"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			order, err := store.CreatePaperOrder(req.ProfileKey, req.Symbol, req.Side, req.Type, req.Quantity, req.EntryPrice, req.StopLoss, req.TakeProfit)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusCreated, map[string]any{"success": true, "order": serializeOrder(order)})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPost}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func FusionOrderDetailHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		if r.Method != http.MethodPatch {
			w.Header().Set("Allow", http.MethodPatch)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
			return
		}
		orderID := strings.TrimSpace(strings.TrimPrefix(r.URL.Path, "/api/v1/fusion/orders/"))
		if orderID == "" {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "orderId is required"})
			return
		}
		var req struct {
			ProfileKey string `json:"profileKey"`
			Status     string `json:"status"`
		}
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
			return
		}
		order, found, err := store.UpdatePaperOrderStatus(req.ProfileKey, orderID, req.Status)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
			return
		}
		if !found {
			writeJSON(w, http.StatusNotFound, map[string]any{"error": "order not found"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "order": serializeOrder(order)})
	}
}

func FusionAlertsHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		switch r.Method {
		case http.MethodGet:
			profileKey := strings.TrimSpace(r.URL.Query().Get("profileKey"))
			if profileKey == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "profileKey is required", "reason": "MISSING_PROFILE_KEY"})
				return
			}
			alerts, err := store.ListPriceAlerts(profileKey, strings.TrimSpace(r.URL.Query().Get("symbol")))
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "alerts": serializeAlerts(alerts)})
		case http.MethodPost:
			var req struct {
				ProfileKey  string  `json:"profileKey"`
				Symbol      string  `json:"symbol"`
				Condition   string  `json:"condition"`
				TargetValue float64 `json:"targetValue"`
				Message     string  `json:"message"`
				Enabled     *bool   `json:"enabled"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			alert, err := store.CreatePriceAlert(req.ProfileKey, req.Symbol, req.Condition, req.TargetValue, boolOrDefault(req.Enabled, true), req.Message)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusCreated, map[string]any{"success": true, "alert": serializeAlert(alert)})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPost}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func FusionAlertDetailHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		alertID := strings.TrimSpace(strings.TrimPrefix(r.URL.Path, "/api/v1/fusion/alerts/"))
		if alertID == "" {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "alertId is required"})
			return
		}
		switch r.Method {
		case http.MethodPatch:
			var req struct {
				ProfileKey  string  `json:"profileKey"`
				Enabled     *bool   `json:"enabled"`
				Triggered   *bool   `json:"triggered"`
				TriggeredAt *string `json:"triggeredAt"`
				Message     *string `json:"message"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			alert, found, err := store.UpdatePriceAlert(req.ProfileKey, alertID, req.Enabled, req.Triggered, req.TriggeredAt, req.Message)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			if !found {
				writeJSON(w, http.StatusNotFound, map[string]any{"error": "alert not found"})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "alert": serializeAlert(alert)})
		case http.MethodDelete:
			profileKey := strings.TrimSpace(r.URL.Query().Get("profileKey"))
			if profileKey == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "profileKey is required", "reason": "MISSING_PROFILE_KEY"})
				return
			}
			deleted, err := store.DeletePriceAlert(profileKey, alertID)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			if !deleted {
				writeJSON(w, http.StatusNotFound, map[string]any{"error": "alert not found"})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodPatch, http.MethodDelete}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func FusionTradeJournalHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		switch r.Method {
		case http.MethodGet:
			profileKey := strings.TrimSpace(r.URL.Query().Get("profileKey"))
			if profileKey == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "profileKey is required", "reason": "MISSING_PROFILE_KEY"})
				return
			}
			limit, _ := strconv.Atoi(strings.TrimSpace(r.URL.Query().Get("limit")))
			entries, err := store.ListTradeJournalEntries(profileKey, strings.TrimSpace(r.URL.Query().Get("symbol")), limit)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "entries": serializeTradeJournalEntries(entries)})
		case http.MethodPost:
			var req struct {
				ProfileKey    string         `json:"profileKey"`
				Symbol        string         `json:"symbol"`
				OrderID       string         `json:"orderId"`
				Note          string         `json:"note"`
				Tags          []string       `json:"tags"`
				Context       map[string]any `json:"context"`
				ScreenshotURL string         `json:"screenshotUrl"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			contextJSON := ""
			if len(req.Context) > 0 {
				encoded, err := json.Marshal(req.Context)
				if err != nil {
					writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid context payload"})
					return
				}
				contextJSON = string(encoded)
			}
			entry, err := store.CreateTradeJournalEntry(req.ProfileKey, req.Symbol, req.OrderID, req.Note, req.Tags, contextJSON, req.ScreenshotURL)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusCreated, map[string]any{"success": true, "entry": serializeTradeJournalEntry(entry)})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPost}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func FusionTradeJournalDetailHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		entryID := strings.TrimSpace(strings.TrimPrefix(r.URL.Path, "/api/v1/fusion/trade-journal/"))
		if entryID == "" {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "entryId is required"})
			return
		}
		switch r.Method {
		case http.MethodPatch:
			var req struct {
				ProfileKey    string          `json:"profileKey"`
				Note          *string         `json:"note"`
				Tags          []string        `json:"tags"`
				Context       json.RawMessage `json:"context"`
				ScreenshotURL *string         `json:"screenshotUrl"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			hasTags := req.Tags != nil
			var contextJSON *string
			if len(req.Context) > 0 {
				contextValue := string(req.Context)
				contextJSON = &contextValue
			}
			entry, found, err := store.UpdateTradeJournalEntry(req.ProfileKey, entryID, req.Note, req.Tags, hasTags, contextJSON, req.ScreenshotURL)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			if !found {
				writeJSON(w, http.StatusNotFound, map[string]any{"error": "entry not found"})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "entry": serializeTradeJournalEntry(entry)})
		case http.MethodDelete:
			var req struct {
				ProfileKey string `json:"profileKey"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			deleted, err := store.DeleteTradeJournalEntry(req.ProfileKey, entryID)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			if !deleted {
				writeJSON(w, http.StatusNotFound, map[string]any{"error": "entry not found"})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodPatch, http.MethodDelete}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func FusionPortfolioHistoryHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		switch r.Method {
		case http.MethodGet:
			profileKey := strings.TrimSpace(r.URL.Query().Get("profileKey"))
			if profileKey == "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "profileKey is required", "reason": "MISSING_PROFILE_KEY"})
				return
			}
			limit, _ := strconv.Atoi(strings.TrimSpace(r.URL.Query().Get("limit")))
			items, err := store.ListPortfolioSnapshots(profileKey, limit)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "entries": serializePortfolioSnapshots(items)})
		case http.MethodPost:
			var req struct {
				ProfileKey  string          `json:"profileKey"`
				GeneratedAt string          `json:"generatedAt"`
				Snapshot    json.RawMessage `json:"snapshot"`
			}
			if err := decodeJSONBody(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
				return
			}
			snapshotJSON := strings.TrimSpace(string(req.Snapshot))
			if snapshotJSON == "" {
				snapshotJSON = "{}"
			}
			entry, err := store.SavePortfolioSnapshot(req.ProfileKey, req.GeneratedAt, snapshotJSON)
			if err != nil {
				writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
				return
			}
			writeJSON(w, http.StatusCreated, map[string]any{"success": true, "entry": serializePortfolioSnapshot(entry)})
		default:
			w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPost}, ", "))
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		}
	}
}

func FileAuditLogHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
			return
		}
		var req struct {
			DocumentID  string `json:"documentId"`
			Action      string `json:"action"`
			ActionClass string `json:"actionClass"`
			ActorUserID string `json:"actorUserId"`
			ActorRole   string `json:"actorRole"`
			RequestID   string `json:"requestId"`
			Target      string `json:"target"`
			Status      string `json:"status"`
			ErrorCode   string `json:"errorCode"`
			ExpiresAt   string `json:"expiresAt"`
		}
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
			return
		}
		if err := store.WriteFileAuditLog(appstate.FileAuditLogRecord{
			DocumentID:  req.DocumentID,
			Action:      req.Action,
			ActionClass: req.ActionClass,
			ActorUserID: req.ActorUserID,
			ActorRole:   req.ActorRole,
			RequestID:   req.RequestID,
			Target:      req.Target,
			Status:      req.Status,
			ErrorCode:   req.ErrorCode,
			ExpiresAt:   req.ExpiresAt,
		}); err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusCreated, map[string]any{"success": true})
	}
}

func ControlAuditLogHandler(store appStateStore) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if store == nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"error": "app state store unavailable"})
			return
		}
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
			return
		}
		var req struct {
			Action      string `json:"action"`
			ActionClass string `json:"actionClass"`
			ActorUserID string `json:"actorUserId"`
			ActorRole   string `json:"actorRole"`
			RequestID   string `json:"requestId"`
			Target      string `json:"target"`
			Status      string `json:"status"`
			ErrorCode   string `json:"errorCode"`
			ExpiresAt   string `json:"expiresAt"`
		}
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
			return
		}
		if err := store.WriteControlAuditLog(appstate.ControlAuditLogRecord{
			Action:      req.Action,
			ActionClass: req.ActionClass,
			ActorUserID: req.ActorUserID,
			ActorRole:   req.ActorRole,
			RequestID:   req.RequestID,
			Target:      req.Target,
			Status:      req.Status,
			ErrorCode:   req.ErrorCode,
			ExpiresAt:   req.ExpiresAt,
		}); err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusCreated, map[string]any{"success": true})
	}
}

func handlePasskeyRegistrationContext(store appStateStore, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		return
	}
	var req struct {
		Email       string `json:"email"`
		DisplayName string `json:"displayName"`
		Role        string `json:"role"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	user, authenticators, err := store.GetOrCreateUserByEmail(req.Email, req.DisplayName, req.Role)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"user": map[string]any{
			"id":    user.ID,
			"email": emptyToNil(user.Email),
			"name":  emptyToNil(user.Name),
			"role":  normalizeRole(user.Role),
		},
		"authenticators": serializeAuthenticators(authenticators),
	})
}

func handlePasskeyRegistrationPersist(store appStateStore, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		return
	}
	var req struct {
		UserID               string   `json:"userId"`
		ProviderAccountID    string   `json:"providerAccountId"`
		CredentialID         string   `json:"credentialId"`
		CredentialPublicKey  string   `json:"credentialPublicKey"`
		Counter              int      `json:"counter"`
		CredentialDeviceType string   `json:"credentialDeviceType"`
		CredentialBackedUp   bool     `json:"credentialBackedUp"`
		Transports           []string `json:"transports"`
		Name                 string   `json:"name"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	authn, err := store.UpsertAuthenticator(appstate.PasskeyAuthenticator{
		UserID:               req.UserID,
		ProviderAccountID:    req.ProviderAccountID,
		CredentialID:         req.CredentialID,
		CredentialPublicKey:  req.CredentialPublicKey,
		Counter:              req.Counter,
		CredentialDeviceType: req.CredentialDeviceType,
		CredentialBackedUp:   req.CredentialBackedUp,
		Transports:           req.Transports,
		Name:                 req.Name,
	})
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"authenticator": serializeAuthenticator(authn)})
}

func handlePasskeyAuthenticationContext(store appStateStore, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		return
	}
	var req struct {
		Email string `json:"email"`
	}
	if err := decodeJSONBody(r, &req); err != nil && !errors.Is(err, io.EOF) {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	email := strings.TrimSpace(strings.ToLower(req.Email))
	if email == "" {
		writeJSON(w, http.StatusOK, map[string]any{
			"user":           nil,
			"authenticators": []map[string]any{},
		})
		return
	}
	user, err := store.GetUserByIDOrEmail("", email)
	if err != nil {
		if strings.Contains(err.Error(), "user not found") {
			writeJSON(w, http.StatusOK, map[string]any{
				"user":           nil,
				"authenticators": []map[string]any{},
			})
			return
		}
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	authenticators, err := store.ListAuthenticatorsByUserID(user.ID)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"user": map[string]any{
			"id":    user.ID,
			"email": emptyToNil(user.Email),
			"name":  emptyToNil(user.Name),
			"role":  normalizeRole(user.Role),
		},
		"authenticators": serializeAuthenticators(authenticators),
	})
}

func handlePasskeyAuthenticationPersist(store appStateStore, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		return
	}
	var req struct {
		CredentialID         string `json:"credentialId"`
		Counter              int    `json:"counter"`
		CredentialDeviceType string `json:"credentialDeviceType"`
		CredentialBackedUp   bool   `json:"credentialBackedUp"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	authn, err := store.UpdateAuthenticatorUsage(req.CredentialID, req.Counter, req.CredentialDeviceType, req.CredentialBackedUp)
	if err != nil {
		status := http.StatusBadGateway
		if strings.Contains(err.Error(), "authenticator not found") {
			status = http.StatusNotFound
		}
		writeJSON(w, status, map[string]any{"error": err.Error()})
		return
	}
	_, user, err := store.GetAuthenticatorByCredentialID(req.CredentialID)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"authenticator": serializeAuthenticator(authn),
		"user": map[string]any{
			"id":    user.ID,
			"email": emptyToNil(user.Email),
			"role":  normalizeRole(user.Role),
		},
	})
}

func handlePasskeyCredentialRecord(store appStateStore, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
		return
	}
	var req struct {
		CredentialID string `json:"credentialId"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	authn, user, err := store.GetAuthenticatorByCredentialID(req.CredentialID)
	if err != nil {
		status := http.StatusBadGateway
		if strings.Contains(err.Error(), "authenticator not found") {
			status = http.StatusNotFound
		}
		writeJSON(w, status, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"authenticator": serializeAuthenticator(authn),
		"user": map[string]any{
			"id":    user.ID,
			"email": emptyToNil(user.Email),
			"role":  normalizeRole(user.Role),
		},
		"credentialPublicKey": authn.CredentialPublicKey,
	})
}

func handlePasskeyDevices(store appStateStore, w http.ResponseWriter, r *http.Request) {
	userID := strings.TrimSpace(r.Header.Get("X-Auth-User-Id"))
	email := strings.TrimSpace(strings.ToLower(r.Header.Get("X-Auth-User-Email")))
	if userID == "" && email == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "unauthorized"})
		return
	}
	user, err := store.GetUserByIDOrEmail(userID, email)
	if err != nil {
		status := http.StatusBadGateway
		if strings.Contains(err.Error(), "user not found") {
			status = http.StatusNotFound
		}
		writeJSON(w, status, map[string]any{"error": err.Error()})
		return
	}
	switch r.Method {
	case http.MethodGet:
		authenticators, err := store.ListAuthenticatorsByUserID(user.ID)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"user": map[string]any{
				"id":    user.ID,
				"email": emptyToNil(user.Email),
				"role":  normalizeRole(user.Role),
			},
			"items": serializeAuthenticators(authenticators),
			"total": len(authenticators),
		})
	case http.MethodDelete:
		var req struct {
			AuthenticatorID string `json:"authenticatorId"`
		}
		if err := decodeJSONBody(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
			return
		}
		remaining, err := store.DeleteAuthenticatorForUser(user.ID, req.AuthenticatorID)
		if err != nil {
			status := http.StatusBadGateway
			message := err.Error()
			if strings.Contains(message, "authenticator not found") {
				status = http.StatusNotFound
			} else if strings.Contains(message, "cannot remove last passkey") {
				status = http.StatusConflict
			}
			writeJSON(w, status, map[string]any{"error": message})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"deleted":         true,
			"authenticatorId": req.AuthenticatorID,
			"remaining":       remaining,
		})
	default:
		w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodDelete}, ", "))
		writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"error": "method not allowed"})
	}
}

func handleAuthOwnerAuthorize(store appStateStore, w http.ResponseWriter, r *http.Request) {
	var req struct {
		Identifier string `json:"identifier"`
		Password   string `json:"password"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	user, err := store.FindUserForCredentials(req.Identifier)
	if err != nil {
		if strings.Contains(err.Error(), "user not found") {
			writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "invalid credentials"})
			return
		}
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	if strings.TrimSpace(user.PasswordHash) == "" {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "Primary authentication method is not password-based."})
		return
	}
	valid, err := verifyEncodedPassword(req.Password, user.PasswordHash)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	if !valid {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "invalid credentials"})
		return
	}
	hasTOTP, err := store.HasActiveTOTP(user.ID)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"user": map[string]any{
			"id":    user.ID,
			"email": emptyToNil(user.Email),
			"name":  emptyToNil(user.Name),
			"role":  normalizeRole(user.Role),
		},
		"hasTOTP": hasTOTP,
	})
}

func handleAuthOwnerRegister(store appStateStore, w http.ResponseWriter, r *http.Request) {
	var req struct {
		Email         string   `json:"email"`
		Username      string   `json:"username"`
		Name          string   `json:"name"`
		Role          string   `json:"role"`
		PasswordHash  string   `json:"passwordHash"`
		RecoveryCodes []string `json:"recoveryCodes"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	user, err := store.RegisterUser(req.Email, req.Username, req.Name, req.Role, req.PasswordHash, req.RecoveryCodes)
	if err != nil {
		status := http.StatusBadGateway
		message := err.Error()
		if strings.Contains(message, "already registered") || strings.Contains(message, "already taken") {
			status = http.StatusConflict
		} else if strings.Contains(message, "required") {
			status = http.StatusBadRequest
		}
		writeJSON(w, status, map[string]any{"error": message})
		return
	}
	writeJSON(w, http.StatusCreated, map[string]any{
		"user": map[string]any{
			"id":        user.ID,
			"email":     emptyToNil(user.Email),
			"name":      emptyToNil(user.Name),
			"role":      normalizeRole(user.Role),
			"createdAt": user.CreatedAt,
		},
	})
}

func handleAuthOwnerUserSecurity(store appStateStore, w http.ResponseWriter, r *http.Request) {
	var req struct {
		UserID string `json:"userId"`
	}
	if err := decodeJSONBody(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json body"})
		return
	}
	hasTOTP, err := store.HasActiveTOTP(req.UserID)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"hasTOTP": hasTOTP})
}

func fromDBLayoutMode(value string) string {
	switch strings.TrimSpace(strings.ToLower(value)) {
	case "two_horizontal":
		return "2h"
	case "two_vertical":
		return "2v"
	case "four":
		return "4"
	default:
		return "single"
	}
}

func toDBLayoutMode(value string) string {
	switch strings.TrimSpace(strings.ToLower(value)) {
	case "2h":
		return "two_horizontal"
	case "2v":
		return "two_vertical"
	case "4":
		return "four"
	default:
		return "single"
	}
}

func boolOrDefault(value *bool, fallback bool) bool {
	if value == nil {
		return fallback
	}
	return *value
}

func normalizeRole(value string) string {
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

func emptyToNil(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return value
}

func serializeAuthenticators(items []appstate.PasskeyAuthenticator) []map[string]any {
	out := make([]map[string]any, 0, len(items))
	for _, item := range items {
		out = append(out, serializeAuthenticator(item))
	}
	return out
}

func serializeAuthenticator(item appstate.PasskeyAuthenticator) map[string]any {
	return map[string]any{
		"id":           item.ID,
		"name":         emptyToNil(item.Name),
		"credentialId": item.CredentialID,
		"deviceType":   item.CredentialDeviceType,
		"backedUp":     item.CredentialBackedUp,
		"counter":      item.Counter,
		"transports":   item.Transports,
		"createdAt":    item.CreatedAt,
		"lastUsedAt":   emptyToNil(item.LastUsedAt),
	}
}

func serializeOrders(items []appstate.PaperOrderRecord) []map[string]any {
	out := make([]map[string]any, 0, len(items))
	for _, item := range items {
		out = append(out, serializeOrder(item))
	}
	return out
}

func serializeOrder(item appstate.PaperOrderRecord) map[string]any {
	return map[string]any{
		"id":          item.ID,
		"profileKey":  item.ProfileKey,
		"symbol":      item.Symbol,
		"side":        item.Side,
		"type":        item.Type,
		"quantity":    item.Quantity,
		"entryPrice":  item.EntryPrice,
		"stopLoss":    item.StopLoss,
		"takeProfit":  item.TakeProfit,
		"status":      item.Status,
		"filledPrice": item.FilledPrice,
		"executedAt":  emptyToNil(item.ExecutedAt),
		"createdAt":   item.CreatedAt,
		"updatedAt":   item.UpdatedAt,
	}
}

func serializeAlerts(items []appstate.PriceAlertRecord) []map[string]any {
	out := make([]map[string]any, 0, len(items))
	for _, item := range items {
		out = append(out, serializeAlert(item))
	}
	return out
}

func serializeAlert(item appstate.PriceAlertRecord) map[string]any {
	var triggeredAt any
	if strings.TrimSpace(item.TriggeredAt) != "" {
		if parsed, err := time.Parse(time.RFC3339Nano, item.TriggeredAt); err == nil {
			triggeredAt = parsed.UnixMilli()
		}
	}
	var createdAt any
	if parsed, err := time.Parse(time.RFC3339Nano, item.CreatedAt); err == nil {
		createdAt = parsed.UnixMilli()
	} else {
		createdAt = item.CreatedAt
	}
	return map[string]any{
		"id":          item.ID,
		"symbol":      item.Symbol,
		"condition":   item.Condition,
		"targetValue": item.TargetValue,
		"enabled":     item.Enabled,
		"triggered":   item.Triggered,
		"triggeredAt": triggeredAt,
		"createdAt":   createdAt,
		"message":     emptyToNil(item.Message),
	}
}

func serializeTradeJournalEntries(items []appstate.TradeJournalRecord) []map[string]any {
	out := make([]map[string]any, 0, len(items))
	for _, item := range items {
		out = append(out, serializeTradeJournalEntry(item))
	}
	return out
}

func serializeTradeJournalEntry(item appstate.TradeJournalRecord) map[string]any {
	var context any
	if strings.TrimSpace(item.ContextJSON) != "" {
		var decoded map[string]any
		if err := json.Unmarshal([]byte(item.ContextJSON), &decoded); err == nil {
			context = decoded
		}
	}
	return map[string]any{
		"id":            item.ID,
		"profileKey":    item.ProfileKey,
		"symbol":        item.Symbol,
		"orderId":       emptyToNil(item.OrderID),
		"note":          item.Note,
		"tags":          item.Tags,
		"context":       context,
		"screenshotUrl": emptyToNil(item.ScreenshotURL),
		"createdAt":     item.CreatedAt,
		"updatedAt":     item.UpdatedAt,
	}
}

func serializePortfolioSnapshots(items []appstate.PortfolioSnapshotRecord) []map[string]any {
	out := make([]map[string]any, 0, len(items))
	for _, item := range items {
		out = append(out, serializePortfolioSnapshot(item))
	}
	return out
}

func serializePortfolioSnapshot(item appstate.PortfolioSnapshotRecord) map[string]any {
	var snapshot any
	if strings.TrimSpace(item.SnapshotJSON) != "" {
		var decoded any
		if err := json.Unmarshal([]byte(item.SnapshotJSON), &decoded); err == nil {
			snapshot = decoded
		}
	}
	return map[string]any{
		"id":          item.ID,
		"profileKey":  item.ProfileKey,
		"generatedAt": item.GeneratedAt,
		"snapshot":    snapshot,
		"createdAt":   item.CreatedAt,
	}
}

func verifyEncodedPassword(password, encodedHash string) (bool, error) {
	parts := strings.Split(encodedHash, "$")
	if len(parts) != 6 {
		return false, nil
	}
	if parts[0] != "scrypt" {
		return false, nil
	}
	n, err := strconv.Atoi(parts[1])
	if err != nil {
		return false, nil
	}
	r, err := strconv.Atoi(parts[2])
	if err != nil {
		return false, nil
	}
	p, err := strconv.Atoi(parts[3])
	if err != nil {
		return false, nil
	}
	salt, err := base64.RawURLEncoding.DecodeString(parts[4])
	if err != nil || len(salt) == 0 {
		return false, nil
	}
	expected, err := base64.RawURLEncoding.DecodeString(parts[5])
	if err != nil || len(expected) == 0 {
		return false, nil
	}
	actual, err := scrypt.Key([]byte(norm.NFKC.String(password)), salt, n, r, p, len(expected))
	if err != nil {
		return false, fmt.Errorf("derive password hash: %w", err)
	}
	if len(actual) != len(expected) {
		return false, nil
	}
	return subtle.ConstantTimeCompare(actual, expected) == 1, nil
}
