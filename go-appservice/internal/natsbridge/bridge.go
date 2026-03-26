// Package natsbridge verbindet Matrix-Events mit dem Python Agent via NATS.
package natsbridge

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"

	"github.com/nats-io/nats.go"
)

const (
	// SubjectInbound: Matrix-Nachricht → Python Agent
	SubjectInbound = "matrix.message.inbound"
	// SubjectReply: Python Agent-Antwort → Matrix-Raum
	SubjectReply = "matrix.message.reply"
)

// InboundMessage repräsentiert eine eingehende Matrix-Nachricht.
type InboundMessage struct {
	RoomID   string `json:"room_id"`
	Sender   string `json:"sender"`
	Body     string `json:"body"`
	EventID  string `json:"event_id"`
	ThreadID string `json:"thread_id,omitempty"`
}

// ReplyMessage repräsentiert eine Antwort vom Agent.
type ReplyMessage struct {
	RoomID      string `json:"room_id"`
	AgentUserID string `json:"agent_user_id"` // @agent-trading:matrix.local
	Text        string `json:"text"`
	IsStreaming bool   `json:"is_streaming"`
}

// Bridge verwaltet die NATS-Verbindung.
type Bridge struct {
	nc *nats.Conn
}

// New erstellt eine neue Bridge-Verbindung.
func New(natsURL string) (*Bridge, error) {
	nc, err := nats.Connect(natsURL,
		nats.Name("matrix-appservice"),
		nats.MaxReconnects(10),
		nats.ReconnectHandler(func(nc *nats.Conn) {
			slog.Info("NATS reconnected", "url", nc.ConnectedUrl())
		}),
		nats.DisconnectErrHandler(func(nc *nats.Conn, err error) {
			if err != nil {
				slog.Warn("NATS disconnected", "error", err)
			}
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("nats connect %s: %w", natsURL, err)
	}
	slog.Info("NATS connected", "url", natsURL)
	return &Bridge{nc: nc}, nil
}

// PublishInbound publiziert eine eingehende Matrix-Nachricht.
func (b *Bridge) PublishInbound(ctx context.Context, msg InboundMessage) error {
	data, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("marshal: %w", err)
	}
	if err := b.nc.Publish(SubjectInbound, data); err != nil {
		return fmt.Errorf("publish %s: %w", SubjectInbound, err)
	}
	slog.Debug("published matrix message to NATS",
		"room", msg.RoomID,
		"sender", msg.Sender,
		"subject", SubjectInbound,
	)
	return nil
}

// SubscribeReplies abonniert Agent-Antworten und ruft handler auf.
func (b *Bridge) SubscribeReplies(handler func(ReplyMessage)) (*nats.Subscription, error) {
	sub, err := b.nc.Subscribe(SubjectReply, func(msg *nats.Msg) {
		var reply ReplyMessage
		if err := json.Unmarshal(msg.Data, &reply); err != nil {
			slog.Error("unmarshal reply failed", "error", err)
			return
		}
		handler(reply)
	})
	if err != nil {
		return nil, fmt.Errorf("subscribe %s: %w", SubjectReply, err)
	}
	slog.Info("subscribed to agent replies", "subject", SubjectReply)
	return sub, nil
}

// Close schließt die NATS-Verbindung sauber.
func (b *Bridge) Close() {
	if err := b.nc.Drain(); err != nil {
		slog.Warn("NATS drain error", "error", err)
	}
}
