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
	"os"
	"strings"
	"time"

	"matrix/go-appservice/internal/app"
	"matrix/go-appservice/internal/config"
	"matrix/go-appservice/internal/connectors/agentservice"
	"matrix/go-appservice/internal/connectors/ingestion"
	memclient "matrix/go-appservice/internal/connectors/memory"
	"matrix/go-appservice/internal/crypto"
	agenthttp "matrix/go-appservice/internal/handlers/http"
	"matrix/go-appservice/internal/intent"
	"matrix/go-appservice/internal/natsbridge"
	"matrix/go-appservice/internal/storage"

	"github.com/jackc/pgx/v5/pgxpool"
	"maunium.net/go/mautrix"
	"maunium.net/go/mautrix/event"
	"maunium.net/go/mautrix/id"
)

// Server ist der HTTP-Server des Appservice.
type Server struct {
	cfg           *config.Config
	httpServer    *http.Server
	client        *mautrix.Client
	nats          *natsbridge.Bridge
	agent         *intent.AgentSender
	crypto        *crypto.Machine               // nil wenn E2EE deaktiviert
	artifactStore storage.ArtifactMetadataStore // nil wenn Artifact Storage deaktiviert

	// DB is the process-wide pgxpool shared between storage, scheduler
	// (River), and any future Postgres-backed subsystem. Created in
	// NewServer, closed in Stop(). exec-scheduler Lane P.
	DB *pgxpool.Pool

	// roomMembers trackt Raum-Mitglieder für Mention-Filter (DM vs. Gruppe).
	// Wird von handleMembership() aktualisiert, unabhängig von E2EE.
	roomMembers map[id.RoomID]map[id.UserID]bool
}

// NewServer erstellt und konfiguriert den Appservice-Server.
func NewServer(cfg *config.Config, natsBridge *natsbridge.Bridge) (*Server, error) {
	// Matrix Client für den Appservice-Bot
	client, err := mautrix.NewClient(cfg.HomeserverURL, id.UserID(cfg.BotUserID), cfg.ASToken)
	if err != nil {
		return nil, fmt.Errorf("matrix client: %w", err)
	}

	agentSender := intent.New(client, cfg.ServerName)

	// exec-scheduler Lane P: shared pgxpool for storage + River. Only
	// created when a PostgresDSN is configured. Legacy deployments without
	// Postgres (pure SQLite crypto store + no artifact storage) keep DB=nil.
	var sharedPool *pgxpool.Pool
	if strings.TrimSpace(cfg.PostgresDSN) != "" {
		pool, poolErr := app.NewSharedPgxPool(context.Background(), cfg.PostgresDSN)
		if poolErr != nil {
			return nil, fmt.Errorf("shared pgx pool: %w", poolErr)
		}
		sharedPool = pool
	}

	s := &Server{
		cfg:         cfg,
		client:      client,
		nats:        natsBridge,
		agent:       agentSender,
		DB:          sharedPool,
		roomMembers: make(map[id.RoomID]map[id.UserID]bool),
	}

	// E2EE initialisieren (nur wenn aktiviert)
	if cfg.E2EEEnabled {
		// exec-19 Stufe 2B: prefer Postgres (cfg.PostgresDSN) for crypto
		// store. Falls back to SQLite (MATRIX_CRYPTO_DB_PATH) if PG not set.
		m, err := crypto.New(context.Background(), client, cfg.PostgresDSN, cfg.CryptoDBPath, []byte(cfg.CryptoPickleKey), cfg.KeyBackupPassword, cfg.DeleteKeysAfterDecrypt)
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

	// ── MCP Server Proxy (exec-09) ──────────────────────────────────────────
	mux.HandleFunc("/api/v1/mcp/", agenthttp.McpProxyHandler(cfg.MCPServiceURL))

	// ── Control Surface Proxy (exec-15 Slice 7) ────────────────────────────
	// Forward all /api/v1/control/* requests to Python Agent Service (:8094).
	// Python side: agent/control/router.py exposes 54 routes (memory, episodes,
	// kg, agents, permissions, skills, tools, sandbox, system, audit, sessions,
	// mcp, a2a, overview, security, models).
	mux.HandleFunc("/api/v1/control/", agenthttp.ControlProxyHandler(cfg.AgentServiceURL))

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

	// ── Artifact Storage (exec-15 Slice 1, capability-based via signed URLs) ─
	// Adopted from tradeview-fusion main project. Optional: only mounted if
	// ARTIFACT_STORAGE_SIGNING_SECRET (or AUTH_SECRET fallback in dev) is set
	// AND ARTIFACT_STORAGE_PROVIDER is set. Failure during init is logged
	// but does NOT block server startup (matrix-bridge can run without storage).
	host := strings.TrimPrefix(strings.TrimPrefix(cfg.AppserviceURL, "http://"), "https://")
	if idx := strings.Index(host, ":"); idx > 0 {
		host = host[:idx]
	}
	if host == "" {
		host = "127.0.0.1"
	}
	var artifactCfg *app.ArtifactServiceConfig
	var artifactErr error
	if sharedPool != nil {
		artifactCfg, artifactErr = app.BuildArtifactService(host, cfg.AppservicePort, sharedPool)
	} else {
		artifactErr = fmt.Errorf("PostgresDSN not configured — artifact storage requires Postgres")
	}
	if artifactErr != nil {
		slog.Warn("Artifact Storage disabled — set ARTIFACT_STORAGE_* env vars to enable",
			"error", artifactErr)
	} else {
		s.artifactStore = artifactCfg.Store
		mux.HandleFunc("/api/v1/storage/artifacts/upload-url",
			agenthttp.ArtifactUploadURLHandler(artifactCfg.Service, artifactCfg.GatewayBaseURL))
		mux.HandleFunc("/api/v1/storage/artifacts/upload/",
			agenthttp.ArtifactUploadHandler(artifactCfg.Service))
		mux.HandleFunc("/api/v1/storage/artifacts/",
			agenthttp.ArtifactMetadataHandler(artifactCfg.Service))
		// #nosec G706 -- ENV values are operator-controlled, not user input.
		slog.Info("Artifact Storage active",
			"provider", os.Getenv("ARTIFACT_STORAGE_PROVIDER"),
			"gateway_base_url", artifactCfg.GatewayBaseURL)

		// ── Files API (exec-19 Stufe 3) ─────────────────────────────
		// High-level facade over the artifact store + SeaweedFS + Python
		// ingestion worker. Handler dispatches on sub-path; see
		// internal/handlers/http/files_handler.go.
		ingestionURL := envOrDefault("INGESTION_WORKER_URL", ingestion.DefaultBaseURL)
		ingestionClient := ingestion.NewClient(
			ingestionURL,
			10*time.Second,
			ingestion.WithSharedSecret(os.Getenv("INGESTION_WORKER_SHARED_SECRET")),
		)
		// Optional: if the artifact provider is S3/SeaweedFS it also implements
		// ObjectLister. We type-assert to discover the capability at wiring
		// time so the handler can surface orphan blobs.
		var lister storage.ObjectLister
		if objLister, ok := artifactCfg.Service.Provider().(storage.ObjectLister); ok {
			lister = objLister
		}
		filesService := storage.NewFilesService(storage.FilesServiceConfig{
			Store:                artifactCfg.Store,
			Lister:               lister,
			Ingestion:            ingestionClient,
			Artifact:             artifactCfg.Service,
			AllowLegacyOwnerless: boolEnv("FILES_ALLOW_LEGACY_OWNERLESS", false),
		})
		mux.HandleFunc("/api/v1/files",
			agenthttp.FilesListHandler(filesService))
		mux.HandleFunc("/api/v1/files/",
			agenthttp.FilesItemHandler(filesService, artifactCfg.GatewayBaseURL))
		slog.Info("Files API active",
			"ingestion_url", ingestionURL,
			"lister_enabled", lister != nil,
			"allow_legacy_ownerless", boolEnv("FILES_ALLOW_LEGACY_OWNERLESS", false),
		)
	}

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

// envOrDefault returns os.Getenv(key) or fallback if empty/whitespace.
func envOrDefault(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

// boolEnv parses common boolean forms from an env var, fallback otherwise.
func boolEnv(key string, fallback bool) bool {
	v := strings.ToLower(strings.TrimSpace(os.Getenv(key)))
	switch v {
	case "":
		return fallback
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
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

// Stop fährt den Server sauber herunter. Shutdown-Ordering (exec-scheduler Lane P):
//  1. Key backup export (E2EE)
//  2. Scheduler stop — drain in-flight River jobs (30s timeout) — Lane B adds this
//  3. HTTP server shutdown (stops accepting new requests, drains in-flight) — 5s timeout
//  4. Artifact metadata store close (no-op on pool — doesn't own it)
//  5. Shared pgxpool close — last, so nothing tries to query a dead pool
//
// NATS bridge is closed by defer in cmd/appservice/main.go (LIFO after Stop).
func (s *Server) Stop() {
	// C-8: Key Backup beim Shutdown exportieren
	if s.crypto != nil {
		if err := s.crypto.ExportKeyBackup(context.Background()); err != nil {
			slog.Warn("E2EE: key backup export on shutdown failed", "error", err)
		}
	}

	// HTTP shutdown: stops accepting new requests, waits up to 5s for in-flight.
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := s.httpServer.Shutdown(ctx); err != nil {
		slog.Warn("HTTP server shutdown error", "error", err)
	}

	// exec-15 Slice 1: close artifact metadata store. With a shared pool this
	// is a no-op on the pool — only releases internal references. Pool is
	// closed below after all pool consumers are done.
	if s.artifactStore != nil {
		if err := s.artifactStore.Close(); err != nil {
			slog.Warn("Artifact metadata store close failed", "error", err)
		}
	}

	// exec-scheduler Lane P: close shared pool last. Everything that uses it
	// (storage, scheduler, crypto if PG-backed) must be done by now.
	if s.DB != nil {
		s.DB.Close()
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
		// #nosec G706 -- slog emits structured fields (JSON), caller-supplied values escaped.
		slog.Error("decode transaction failed", "txn_id", txnID, "error", err)
		http.Error(w, `{"error":"bad request"}`, http.StatusBadRequest)
		return
	}

	// #nosec G706 -- slog structured logging, txnID is path param from Tuwunel AS txn.
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
			// C-8: Key Backup nach neuen Room Keys aktualisieren.
			// Detach cancellation but keep request values (trace IDs etc.).
			bgCtx := context.WithoutCancel(r.Context())
			go func() {
				if err := s.crypto.ExportKeyBackup(bgCtx); err != nil {
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
		slog.Info("user query: agent user exists", "user_id", userID) //nolint:gosec // structured slog field
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
// exec-05c HY-2: Bei AgentCapabilities="native" wird Ciphertext durchgereicht (Zukunft).
func (s *Server) handleEncrypted(ctx context.Context, ev *event.Event) {
	if s.crypto == nil {
		slog.Warn("E2EE disabled — encrypted event skipped (set MATRIX_E2EE_ENABLED=true to enable)",
			"room", ev.RoomID,
			"sender", ev.Sender,
		)
		return
	}

	// exec-05c HY-2: Conditional Decrypt basierend auf Agent-Capability
	// "gateway" (default) = Go entschlüsselt, Agent bekommt Klartext
	// "native" (Zukunft) = Ciphertext durchreichen, Agent entschlüsselt selbst
	if s.cfg.AgentCapabilities == "native" {
		slog.Debug("E2EE: native mode — forwarding ciphertext to agent (not implemented yet)",
			"room", ev.RoomID)
		// TODO: Ciphertext als InboundMessage mit encrypted=true Flag publizieren
		// Aktuell: Fallback auf Gateway-Decrypt
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

	// Mention-Filter: In Gruppenräumen nur Messages weiterleiten die den Agent betreffen.
	// DMs (≤2 Member) werden immer weitergeleitet.
	if s.cfg.MentionOnlyInGroups && !s.shouldForwardToAgent(ev.RoomID, content) {
		slog.Debug("message filtered (no agent mention in group room)",
			"room", ev.RoomID, "sender", ev.Sender)
		return
	}

	slog.Info("matrix message received",
		"room", ev.RoomID,
		"sender", ev.Sender,
		"body_len", len(content.Body),
	)

	// exec-05c C2: Target-Agent aus Mention extrahieren
	targetAgent := extractAgentName(content.Body, s.cfg.AgentPrefix)

	// exec-05c C4: Thread-Kontext erkennen
	threadID := ""
	isThreadReply := false
	if content.RelatesTo != nil && content.RelatesTo.Type == event.RelThread {
		threadID = content.RelatesTo.EventID.String()
		isThreadReply = true
	}

	// An Python Agent via NATS weiterleiten
	msg := natsbridge.InboundMessage{
		RoomID:        ev.RoomID.String(),
		Sender:        ev.Sender.String(),
		Body:          content.Body,
		EventID:       ev.ID.String(),
		ThreadID:      threadID,
		TargetAgent:   targetAgent,
		IsThreadReply: isThreadReply,
	}

	if err := s.nats.PublishInbound(ctx, msg); err != nil {
		slog.Error("NATS publish failed", "error", err, "room", ev.RoomID)

		agentName := targetAgent
		if agentName == "" {
			agentName = "trading"
		}
		fallbackID := id.UserID("@" + s.cfg.AgentPrefix + agentName + ":" + s.cfg.ServerName)
		_ = s.agent.SendText(ctx, fallbackID, ev.RoomID, "⚠️ Agent temporär nicht erreichbar.")
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

	// Raum-Mitglieder tracken (für Mention-Filter: DM vs. Gruppe)
	switch content.Membership {
	case event.MembershipJoin:
		if s.roomMembers[ev.RoomID] == nil {
			s.roomMembers[ev.RoomID] = make(map[id.UserID]bool)
		}
		s.roomMembers[ev.RoomID][memberUserID] = true
	case event.MembershipLeave, event.MembershipBan:
		delete(s.roomMembers[ev.RoomID], memberUserID)
	case event.MembershipInvite, event.MembershipKnock:
		// Noch kein Raum-Mitglied — kein Tracking nötig
	}

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

	// exec-05c C4: Thread-Reply Content aufbauen
	msgContent := &event.MessageEventContent{
		MsgType: event.MsgText,
		Body:    reply.Text,
	}
	if reply.ThreadRootID != "" {
		msgContent.RelatesTo = &event.RelatesTo{
			Type:    event.RelThread,
			EventID: id.EventID(reply.ThreadRootID),
		}
	}

	// E2EE: verschlüsseln wenn Raum verschlüsselt
	if s.crypto != nil {
		encrypted, err := s.crypto.StateStore.IsEncrypted(ctx, roomID)
		if err != nil {
			slog.Warn("E2EE: could not check room encryption", "room", roomID, "error", err)
		}
		if encrypted {
			if err := s.sendEncryptedReply(ctx, agentID, roomID, msgContent); err != nil {
				slog.Error("E2EE: send encrypted reply failed", "error", err, "room", roomID)
				return
			}
			return
		}
	}

	// Plaintext: Thread-Reply oder normale Nachricht
	if reply.ThreadRootID != "" {
		if err := s.agent.SendContent(ctx, agentID, roomID, event.EventMessage, msgContent); err != nil {
			slog.Error("send agent thread reply failed", "agent", agentID, "room", roomID, "thread", reply.ThreadRootID, "error", err)
		}
	} else {
		if err := s.agent.SendText(ctx, agentID, roomID, reply.Text); err != nil {
			slog.Error("send agent reply failed", "agent", agentID, "room", roomID, "error", err)
		}
	}
}

// sendEncryptedReply verschlüsselt und sendet eine Nachricht in einen E2EE-Raum.
func (s *Server) sendEncryptedReply(ctx context.Context, agentUserID id.UserID, roomID id.RoomID, msgContent *event.MessageEventContent) error {
	// D-1 Fix: Megolm-Session sicherstellen bevor wir verschlüsseln.
	// Ohne EnsureSession schlägt Encrypt fehl wenn keine outbound Session existiert.
	members := s.crypto.StateStore.GetMembers(roomID)
	if len(members) > 0 {
		if err := s.crypto.EnsureSession(ctx, roomID, members); err != nil {
			slog.Warn("E2EE: ensure session failed, trying encrypt anyway", "room", roomID, "error", err)
		}
	}

	content := event.Content{
		Parsed: msgContent,
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

// shouldForwardToAgent entscheidet ob eine Nachricht an den Agent weitergeleitet werden soll.
// DMs (≤2 Member): immer weiterleiten.
// Gruppenräume: nur bei @agent-Mention, Reply auf Agent, oder Trigger-Wörtern.
func (s *Server) shouldForwardToAgent(roomID id.RoomID, content *event.MessageEventContent) bool {
	// DM-Erkennung: Räume mit ≤2 Mitgliedern sind DMs → immer weiterleiten
	members := s.roomMembers[roomID]
	if len(members) <= 2 {
		return true
	}

	body := strings.ToLower(content.Body)
	prefix := "@" + s.cfg.AgentPrefix

	// @agent-* Mention im Body (z.B. "@agent-trading")
	if strings.Contains(strings.ToLower(content.Body), prefix) {
		return true
	}

	// Reply auf eine Agent-Message
	if content.RelatesTo != nil && content.RelatesTo.InReplyTo != nil {
		// Wir können den Sender der Reply-Target-Message nicht direkt prüfen,
		// aber das Vorhandensein einer Reply ist ein starker Indikator.
		// TODO: Event-ID lookup für exakte Prüfung
		return true
	}

	// Trigger-Wörter (wie in der ehemaligen Python Bridge)
	triggers := []string{"agent,", "hey agent", "bot,", "hey bot"}
	for _, t := range triggers {
		if strings.HasPrefix(body, t) {
			return true
		}
	}

	return false
}

// extractAgentName extrahiert den Agent-Namen aus einer @agent-* Mention.
// z.B. "@agent-trading:matrix.local analysiere BTC" → "trading"
// Wenn kein Agent mentioned wird, wird "" zurückgegeben.
func extractAgentName(body, agentPrefix string) string {
	lower := strings.ToLower(body)
	prefix := "@" + agentPrefix
	idx := strings.Index(lower, prefix)
	if idx < 0 {
		return ""
	}
	// Ab dem Prefix den Agent-Namen extrahieren (bis : oder Leerzeichen)
	rest := body[idx+len(prefix):]
	end := len(rest)
	for i, ch := range rest {
		if ch == ':' || ch == ' ' || ch == '\n' || ch == '\t' || ch == ',' {
			end = i
			break
		}
	}
	return strings.ToLower(rest[:end])
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
