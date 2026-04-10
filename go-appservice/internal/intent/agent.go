// Package intent stellt Helfer für das Senden von Nachrichten als Agent bereit.
// Nutzt die mautrix-go Intent API: Nachrichten werden als @agent-*:domain gesendet.
package intent

import (
	"context"
	"fmt"
	"log/slog"

	"maunium.net/go/mautrix"
	"maunium.net/go/mautrix/event"
	"maunium.net/go/mautrix/id"
)

// AgentSender sendet Nachrichten als virtuelle Agent-User-IDs.
type AgentSender struct {
	client     *mautrix.Client
	serverName string
}

// New erstellt einen AgentSender.
func New(client *mautrix.Client, serverName string) *AgentSender {
	return &AgentSender{client: client, serverName: serverName}
}

// UserID gibt die Matrix-User-ID für einen Agent-Namen zurück.
// Beispiel: "trading" → "@agent-trading:matrix.local"
func (s *AgentSender) UserID(agentName string) id.UserID {
	return id.NewUserID(fmt.Sprintf("agent-%s", agentName), s.serverName)
}

// SendText sendet eine Text-Nachricht als Agent in einen Raum.
// Der Agent-Account wird automatisch erstellt wenn er noch nicht existiert.
func (s *AgentSender) SendText(ctx context.Context, agentUserID id.UserID, roomID id.RoomID, text string) error {
	// Als Agent-User senden via ?user_id= Query-Parameter (Appservice-Recht)
	reqURL := s.client.BuildClientURL("v3", "rooms", string(roomID), "send", "m.room.message", "")

	content := map[string]any{
		"msgtype": "m.text",
		"body":    text,
	}

	// Anfrage mit user_id Override (Appservice-Recht)
	_, err := s.client.MakeRequest(ctx, "PUT", reqURL+"?user_id="+string(agentUserID), content, nil)
	if err != nil {
		return fmt.Errorf("send text as %s: %w", agentUserID, err)
	}

	slog.Debug("message sent as agent",
		"agent", agentUserID,
		"room", roomID,
		"body_len", len(text),
	)
	return nil
}

// SendContent sendet ein Event mit beliebigem Content als Agent (exec-05c C4: Thread-Replies).
func (s *AgentSender) SendContent(ctx context.Context, agentUserID id.UserID, roomID id.RoomID, evType event.Type, content any) error {
	reqURL := s.client.BuildClientURL("v3", "rooms", string(roomID), "send", evType.Type, "")
	_, err := s.client.MakeRequest(ctx, "PUT", reqURL+"?user_id="+string(agentUserID), content, nil)
	if err != nil {
		return fmt.Errorf("send content as %s: %w", agentUserID, err)
	}
	slog.Debug("content sent as agent", "agent", agentUserID, "room", roomID, "type", evType.Type)
	return nil
}

// SetTyping sendet den Tipp-Indikator als Agent.
func (s *AgentSender) SetTyping(ctx context.Context, agentUserID id.UserID, roomID id.RoomID, typing bool) error {
	reqURL := s.client.BuildClientURL("v3", "rooms", string(roomID), "typing", string(agentUserID))

	body := map[string]any{
		"typing":  typing,
		"timeout": 30000,
	}

	_, err := s.client.MakeRequest(ctx, "PUT", reqURL+"?user_id="+string(agentUserID), body, nil)
	if err != nil {
		// Tipp-Fehler nicht kritisch — nur loggen
		slog.Warn("set typing failed", "agent", agentUserID, "error", err)
	}
	return nil //nolint:nilerr // typing failures are non-critical
}

// EnsureProfile setzt Display Name und Avatar für einen Agent (einmalig).
func (s *AgentSender) EnsureProfile(ctx context.Context, agentUserID id.UserID, displayName string) {
	reqURL := s.client.BuildClientURL("v3", "profile", string(agentUserID), "displayname")
	body := map[string]string{"displayname": displayName}
	if _, err := s.client.MakeRequest(ctx, "PUT", reqURL+"?user_id="+string(agentUserID), body, nil); err != nil {
		slog.Warn("set display name failed", "agent", agentUserID, "error", err)
	}
}

// JoinRoom lässt einen Agent-User einem Raum beitreten.
func (s *AgentSender) JoinRoom(ctx context.Context, agentUserID id.UserID, roomID id.RoomID) error {
	reqURL := s.client.BuildClientURL("v3", "join", string(roomID))
	_, err := s.client.MakeRequest(ctx, "POST", reqURL+"?user_id="+string(agentUserID), struct{}{}, nil)
	if err != nil {
		return fmt.Errorf("join room %s as %s: %w", roomID, agentUserID, err)
	}
	slog.Info("agent joined room", "agent", agentUserID, "room", roomID)
	return nil
}
