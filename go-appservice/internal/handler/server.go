// Package handler implementiert den HTTP-Server des Appservice.
// Tuwunel schickt Matrix-Events via HTTP-POST an /_matrix/app/v1/transactions/{txnID}.
package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"strings"
	"time"

	"matrix/go-appservice/internal/config"
	"matrix/go-appservice/internal/connectors/agentservice"
	memclient "matrix/go-appservice/internal/connectors/memory"
	"matrix/go-appservice/internal/crypto"
	agenthttp "matrix/go-appservice/internal/handlers/http"
	"matrix/go-appservice/internal/intent"
	"matrix/go-appservice/internal/natsbridge"

	"maunium.net/go/mautrix"
	"maunium.net/go/mautrix/event"
	"maunium.net/go/mautrix/id"
)

// Server ist der HTTP-Server des Appservice.
type Server struct {
	cfg        *config.Config
	httpServer *http.Server
	client     *mautrix.Client
	nats       *natsbridge.Bridge
	agent      *intent.AgentSender
	crypto     *crypto.Machine // nil wenn E2EE deaktiviert
}

// NewServer erstellt und konfiguriert den Appservice-Server.
func NewServer(cfg *config.Config, natsBridge *natsbridge.Bridge) (*Server, error) {
	// Matrix Client für den Appservice-Bot
	client, err := mautrix.NewClient(cfg.HomeserverURL, id.UserID(cfg.BotUserID), cfg.ASToken)
	if err != nil {
		return nil, fmt.Errorf("matrix client: %w", err)
	}

	agentSender := intent.New(client, cfg.ServerName)

	s := &Server{
		cfg:    cfg,
		client: client,
		nats:   natsBridge,
		agent:  agentSender,
	}

	// E2EE initialisieren (nur wenn aktiviert)
	if cfg.E2EEEnabled {
		m, err := crypto.New(context.Background(), client, cfg.CryptoDBPath, []byte(cfg.CryptoPickleKey), cfg.KeyBackupPassword)
		if err != nil {
			return nil, fmt.Errorf("crypto init: %w", err)
		}
		s.crypto = m
		slog.Info("E2EE activated (Option C: Go handles crypto)")
	} else {
		slog.Info("E2EE disabled (MATRIX_E2EE_ENABLED=false) — encrypted events will be skipped")
	}

	// ── Clients für Agent + Memory Service ──────────────────────────────────
	agentClient := agentservice.NewClient(cfg.AgentServiceURL, 5*time.Second)
	memoryClient := memclient.NewClient(cfg.MemoryServiceURL, 5*time.Second)

	mux := http.NewServeMux()

	// ── Matrix Appservice Protocol ──────────────────────────────────────────
	mux.HandleFunc("PUT /_matrix/app/v1/transactions/{txnID}", s.handleTransaction)
	mux.HandleFunc("GET /_matrix/app/v1/users/{userID}", s.handleUserQuery)
	mux.HandleFunc("GET /health", s.handleHealth)

	// ── Agent Chat (SSE Proxy → Python Agent) ───────────────────────────────
	mux.HandleFunc("/api/v1/agent/chat", agenthttp.AgentChatHandler(cfg.AgentServiceURL))
	mux.HandleFunc("/api/v1/agent/approve", agenthttp.AgentApproveHandler())

	// ── Agent Tool Proxies ──────────────────────────────────────────────────
	mux.HandleFunc("/api/v1/agent/tools/chart-state", agenthttp.AgentToolProxyHandler(agentClient, "/api/v1/agent/tools/chart-state"))
	mux.HandleFunc("/api/v1/agent/tools/portfolio-summary", agenthttp.AgentToolProxyHandler(agentClient, "/api/v1/agent/tools/portfolio-summary"))
	mux.HandleFunc("/api/v1/agent/tools/set_chart_state", agenthttp.AgentMutationProxyHandler(agentClient, "/api/v1/agent/tools/set_chart_state"))

	// ── Audio STT/TTS Proxy ─────────────────────────────────────────────────
	mux.HandleFunc("/api/v1/audio/transcribe", agenthttp.AgentAudioTranscribeHandler(cfg.AgentServiceURL))
	mux.HandleFunc("/api/v1/audio/synthesize", agenthttp.AgentAudioSynthesizeHandler(cfg.AgentServiceURL))

	// ── Memory Service Proxy ────────────────────────────────────────────────
	mux.HandleFunc("/api/v1/memory/kg/seed", agenthttp.MemoryKGSeedHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/kg/query", agenthttp.MemoryKGQueryHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/kg/nodes", agenthttp.MemoryKGNodesHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/kg/sync", agenthttp.MemoryKGSyncHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/episode", agenthttp.MemoryEpisodePostHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/episodes", agenthttp.MemoryEpisodesGetHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/search", agenthttp.MemorySearchHandler(memoryClient))
	mux.HandleFunc("/api/v1/memory/health", agenthttp.MemoryHealthHandler(memoryClient))

	s.httpServer = &http.Server{
		Addr:         ":" + cfg.AppservicePort,
		Handler:      s.hsTokenMiddleware(mux),
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		BaseContext:  func(_ net.Listener) context.Context { return context.Background() },
	}

	// NATS Reply-Subscription: Agent-Antworten in Matrix-Räume senden
	if _, err := natsBridge.SubscribeReplies(s.handleAgentReply); err != nil {
		return nil, fmt.Errorf("nats subscribe: %w", err)
	}

	return s, nil
}

// Start startet den HTTP-Server.
func (s *Server) Start(ctx context.Context) error {
	go func() {
		slog.Info("Appservice HTTP server listening", "addr", s.httpServer.Addr)
		if err := s.httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("HTTP server error", "error", err)
		}
	}()
	return nil
}

// Stop fährt den Server sauber herunter.
func (s *Server) Stop() {
	// C-8: Key Backup beim Shutdown exportieren
	if s.crypto != nil {
		if err := s.crypto.ExportKeyBackup(context.Background()); err != nil {
			slog.Warn("E2EE: key backup export on shutdown failed", "error", err)
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := s.httpServer.Shutdown(ctx); err != nil {
		slog.Warn("HTTP server shutdown error", "error", err)
	}
}

// hsTokenMiddleware verifiziert den HS-Token von Tuwunel.
func (s *Server) hsTokenMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Health-Check ohne Auth
		if r.URL.Path == "/health" {
			next.ServeHTTP(w, r)
			return
		}

		token := r.URL.Query().Get("access_token")
		if token == "" {
			// Bearer Token aus Header
			auth := r.Header.Get("Authorization")
			token = strings.TrimPrefix(auth, "Bearer ")
		}

		if token != s.cfg.HSToken {
			http.Error(w, `{"errcode":"M_FORBIDDEN"}`, http.StatusForbidden)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// transactionBody repräsentiert den Body eines Appservice-Transactions.
// Enthält Raum-Events (events) und To-Device-Events (to_device) nach MSC2409.
type transactionBody struct {
	Events   []*event.Event `json:"events"`
	ToDevice *struct {
		Events []*event.Event `json:"events"`
	} `json:"to_device"`
	// Älteres MSC2409 Prefix-Format (Fallback)
	ToDeviceLegacy *struct {
		Events []*event.Event `json:"events"`
	} `json:"de.sorunome.msc2409.to_device"`
}

// handleTransaction empfängt Events vom Homeserver.
func (s *Server) handleTransaction(w http.ResponseWriter, r *http.Request) {
	txnID := r.PathValue("txnID")

	var txn transactionBody
	if err := json.NewDecoder(r.Body).Decode(&txn); err != nil {
		slog.Error("decode transaction failed", "txn_id", txnID, "error", err)
		http.Error(w, `{"error":"bad request"}`, http.StatusBadRequest)
		return
	}

	slog.Debug("transaction received",
		"txn_id", txnID,
		"event_count", len(txn.Events),
	)

	// To-Device Events zuerst verarbeiten (liefern Room Keys für Entschlüsselung)
	if s.crypto != nil {
		toDeviceEvents := txn.toDeviceEvents()
		for _, ev := range toDeviceEvents {
			s.crypto.HandleToDevice(r.Context(), ev)
		}
		if len(toDeviceEvents) > 0 {
			slog.Debug("E2EE: to-device events processed", "count", len(toDeviceEvents))
			// C-8: Key Backup nach neuen Room Keys aktualisieren
			go func() {
				if err := s.crypto.ExportKeyBackup(context.Background()); err != nil {
					slog.Warn("E2EE: key backup export failed", "error", err)
				}
			}()
		}
	}

	// Raum-Events verarbeiten
	for _, ev := range txn.Events {
		s.processEvent(r.Context(), ev)
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("{}"))
}

// toDeviceEvents gibt alle To-Device-Events aus beiden Formaten zurück.
func (t *transactionBody) toDeviceEvents() []*event.Event {
	if t.ToDevice != nil {
		return t.ToDevice.Events
	}
	if t.ToDeviceLegacy != nil {
		return t.ToDeviceLegacy.Events
	}
	return nil
}

// handleUserQuery antwortet auf User-Existenz-Abfragen vom Homeserver.
func (s *Server) handleUserQuery(w http.ResponseWriter, r *http.Request) {
	userID := r.PathValue("userID")
	if isAgentUser(userID, s.cfg.ServerName, s.cfg.AgentPrefix) {
		slog.Info("user query: agent user exists", "user_id", userID)
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("{}"))
		return
	}
	http.Error(w, `{"errcode":"M_NOT_FOUND"}`, http.StatusNotFound)
}

// handleHealth gibt den Status des Appservice zurück.
func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	e2eeStatus := "disabled"
	if s.crypto != nil {
		e2eeStatus = "enabled"
	}
	w.Header().Set("Content-Type", "application/json")
	_, _ = fmt.Fprintf(w, `{"status":"ok","service":"matrix-appservice","e2ee":%q}`, e2eeStatus)
}

// processEvent verarbeitet ein einzelnes Matrix-Event.
func (s *Server) processEvent(ctx context.Context, ev *event.Event) {
	switch ev.Type {
	case event.EventEncrypted:
		s.handleEncrypted(ctx, ev)
	case event.EventMessage:
		s.handleMessage(ctx, ev)
	case event.StateMember:
		s.handleMembership(ctx, ev)
	case event.StateEncryption:
		s.handleEncryptionState(ev)
	default:
		slog.Debug("unhandled event type", "type", ev.Type.Type, "room", ev.RoomID)
	}
}

// handleEncrypted verarbeitet verschlüsselte Events.
// Bei aktiviertem E2EE: entschlüsseln und als normales Event weiterverarbeiten.
// Bei deaktiviertem E2EE: Warnung loggen und überspringen.
func (s *Server) handleEncrypted(ctx context.Context, ev *event.Event) {
	if s.crypto == nil {
		slog.Warn("E2EE disabled — encrypted event skipped (set MATRIX_E2EE_ENABLED=true to enable)",
			"room", ev.RoomID,
			"sender", ev.Sender,
		)
		return
	}

	decrypted, err := s.crypto.Decrypt(ctx, ev)
	if err != nil {
		slog.Warn("E2EE: decryption failed (room key not yet received?)",
			"room", ev.RoomID,
			"sender", ev.Sender,
			"error", err,
		)
		return
	}

	// Als entschlüsseltes Event weiterverarbeiten
	s.processEvent(ctx, decrypted)
}

// handleEncryptionState aktualisiert den E2EE-Status-Cache wenn ein Raum E2EE aktiviert.
func (s *Server) handleEncryptionState(ev *event.Event) {
	if s.crypto != nil {
		s.crypto.StateStore.SetEncrypted(ev.RoomID, true)
	}
	slog.Info("room encryption enabled", "room", ev.RoomID)
}

// handleMessage verarbeitet eingehende Text-Nachrichten.
func (s *Server) handleMessage(ctx context.Context, ev *event.Event) {
	content, ok := ev.Content.Parsed.(*event.MessageEventContent)
	if !ok {
		if err := ev.Content.ParseRaw(event.EventMessage); err != nil {
			return
		}
		content, ok = ev.Content.Parsed.(*event.MessageEventContent)
		if !ok {
			return
		}
	}

	if content.MsgType != event.MsgText {
		return
	}

	// Eigene Agent-Nachrichten ignorieren (Endlosschleife verhindern)
	if isAgentUser(ev.Sender.String(), s.cfg.ServerName, s.cfg.AgentPrefix) {
		return
	}

	slog.Info("matrix message received",
		"room", ev.RoomID,
		"sender", ev.Sender,
		"body_len", len(content.Body),
	)

	// An Python Agent via NATS weiterleiten
	msg := natsbridge.InboundMessage{
		RoomID:   ev.RoomID.String(),
		Sender:   ev.Sender.String(),
		Body:     content.Body,
		EventID:  ev.ID.String(),
		ThreadID: ev.RoomID.String(),
	}

	if err := s.nats.PublishInbound(ctx, msg); err != nil {
		slog.Error("NATS publish failed", "error", err, "room", ev.RoomID)

		defaultAgentID := id.UserID("@" + s.cfg.AgentPrefix + "trading:" + s.cfg.ServerName)
		_ = s.agent.SendText(ctx, defaultAgentID, ev.RoomID, "⚠️ Agent temporär nicht erreichbar.")
	}
}

// handleMembership verarbeitet Membership-Events (Einladungen, Beitritte, Austritte).
func (s *Server) handleMembership(ctx context.Context, ev *event.Event) {
	content, ok := ev.Content.Parsed.(*event.MemberEventContent)
	if !ok {
		if err := ev.Content.ParseRaw(event.StateMember); err != nil {
			return
		}
		content, ok = ev.Content.Parsed.(*event.MemberEventContent)
		if !ok {
			return
		}
	}

	memberUserID := id.UserID(ev.GetStateKey())

	// E2EE StateStore aktuell halten
	if s.crypto != nil {
		switch content.Membership {
		case event.MembershipJoin:
			s.crypto.StateStore.AddMember(ev.RoomID, memberUserID)
		case event.MembershipLeave, event.MembershipBan:
			s.crypto.StateStore.RemoveMember(ev.RoomID, memberUserID)
		case event.MembershipInvite, event.MembershipKnock:
			// Noch kein Raum-Mitglied — kein StateStore Update nötig
		}
	}

	// Einladung an Agent-User → automatisch annehmen
	if content.Membership == event.MembershipInvite {
		stateKey := ev.GetStateKey()
		if isAgentUser(stateKey, s.cfg.ServerName, s.cfg.AgentPrefix) {
			agentID := id.UserID(stateKey)
			if err := s.agent.JoinRoom(ctx, agentID, ev.RoomID); err != nil {
				slog.Error("auto-join failed", "agent", agentID, "room", ev.RoomID, "error", err)
			}
		}
	}
}

// handleAgentReply sendet eine Agent-Antwort in den Matrix-Raum.
func (s *Server) handleAgentReply(reply natsbridge.ReplyMessage) {
	ctx := context.Background()
	agentID := id.UserID(reply.AgentUserID)
	if reply.AgentUserID == "" {
		agentID = id.UserID("@" + s.cfg.AgentPrefix + "trading:" + s.cfg.ServerName)
	}

	roomID := id.RoomID(reply.RoomID)

	// E2EE: verschlüsseln wenn Raum verschlüsselt
	if s.crypto != nil {
		encrypted, err := s.crypto.StateStore.IsEncrypted(ctx, roomID)
		if err != nil {
			slog.Warn("E2EE: could not check room encryption", "room", roomID, "error", err)
		}
		if encrypted {
			if err := s.sendEncryptedReply(ctx, agentID, roomID, reply.Text); err != nil {
				slog.Error("E2EE: send encrypted reply failed", "error", err, "room", roomID)
				// Kein Plaintext-Fallback — würde E2EE umgehen
				return
			}
			return
		}
	}

	if err := s.agent.SendText(ctx, agentID, roomID, reply.Text); err != nil {
		slog.Error("send agent reply failed",
			"agent", agentID,
			"room", roomID,
			"error", err,
		)
	}
}

// sendEncryptedReply verschlüsselt und sendet eine Nachricht in einen E2EE-Raum.
func (s *Server) sendEncryptedReply(ctx context.Context, agentUserID id.UserID, roomID id.RoomID, text string) error {
	// D-1 Fix: Megolm-Session sicherstellen bevor wir verschlüsseln.
	// Ohne EnsureSession schlägt Encrypt fehl wenn keine outbound Session existiert.
	members := s.crypto.StateStore.GetMembers(roomID)
	if len(members) > 0 {
		if err := s.crypto.EnsureSession(ctx, roomID, members); err != nil {
			slog.Warn("E2EE: ensure session failed, trying encrypt anyway", "room", roomID, "error", err)
		}
	}

	content := event.Content{
		Parsed: &event.MessageEventContent{
			MsgType: event.MsgText,
			Body:    text,
		},
	}

	encrypted, err := s.crypto.Encrypt(ctx, roomID, event.EventMessage, content)
	if err != nil {
		return fmt.Errorf("encrypt: %w", err)
	}

	// C-10 / MSC4381: sender_key und device_id NICHT senden (Privacy, deprecated).
	// Empfänger identifiziert den Sender über die Megolm-Session selbst.
	encContent := map[string]any{
		"algorithm":  encrypted.Algorithm,
		"session_id": encrypted.SessionID,
		"ciphertext": encrypted.Ciphertext,
	}

	reqURL := s.client.BuildClientURL("v3", "rooms", string(roomID), "send", "m.room.encrypted", "")
	if _, err := s.client.MakeRequest(ctx, "PUT", reqURL+"?user_id="+string(agentUserID), encContent, nil); err != nil {
		return fmt.Errorf("send encrypted event: %w", err)
	}

	slog.Debug("E2EE: encrypted message sent", "agent", agentUserID, "room", roomID)
	return nil
}

// isAgentUser prüft ob eine User-ID aus dem Agent-Namespace kommt.
func isAgentUser(userID, serverName, agentPrefix string) bool {
	parts := strings.SplitN(userID, ":", 2)
	if len(parts) != 2 {
		return false
	}
	localpart := strings.TrimPrefix(parts[0], "@")
	return strings.HasPrefix(localpart, agentPrefix) && parts[1] == serverName
}
