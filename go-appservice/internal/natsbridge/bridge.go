// Package natsbridge verbindet Matrix-Events mit dem Python Agent via NATS.
package natsbridge

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"regexp"
	"strings"

	"github.com/nats-io/nats.go"
)

const (
	// SubjectInbound: Matrix-Nachricht → Python Agent
	SubjectInbound = "matrix.message.inbound"
	// SubjectInboundAgentPrefix: agent-specific inbound routing.
	SubjectInboundAgentPrefix = SubjectInbound + ".agent."
	// SubjectReply: Python Agent-Antwort → Matrix-Raum
	SubjectReply = "matrix.message.reply"
)

var (
	natsSubjectUnsafe = regexp.MustCompile(`[^a-z0-9_-]+`)
	natsSubjectDashes = regexp.MustCompile(`-{2,}`)
)

// SubjectAgentToken normalisiert Agent-Namen fuer NATS-Subjects.
func SubjectAgentToken(agent string) string {
	value := strings.ToLower(strings.TrimSpace(agent))
	value = strings.TrimPrefix(value, "@")
	value = strings.TrimPrefix(value, "agent-")
	if idx := strings.Index(value, ":"); idx >= 0 {
		value = value[:idx]
	}
	value = natsSubjectUnsafe.ReplaceAllString(value, "-")
	value = natsSubjectDashes.ReplaceAllString(value, "-")
	value = strings.Trim(value, "-_")
	if len(value) > 64 {
		value = strings.Trim(value[:64], "-_")
	}
	if value == "" {
		return "default"
	}
	return value
}

// InboundMessage repräsentiert eine eingehende Matrix-Nachricht.
type InboundMessage struct {
	RoomID        string `json:"room_id"`
	Sender        string `json:"sender"`
	Body          string `json:"body"`
	EventID       string `json:"event_id"`
	ThreadID      string `json:"thread_id,omitempty"`       // exec-05c C4: Thread-Root Event-ID
	TargetAgent   string `json:"target_agent,omitempty"`    // exec-05c C2: z.B. "trading", "research"
	IsThreadReply bool   `json:"is_thread_reply,omitempty"` // exec-05c C4: true wenn Thread-Reply
}

// ReplyMessage repräsentiert eine Antwort vom Agent.
type ReplyMessage struct {
	RoomID       string `json:"room_id"`
	AgentUserID  string `json:"agent_user_id"` // @agent-trading:matrix.local
	Text         string `json:"text"`
	IsStreaming  bool   `json:"is_streaming"`
	ThreadRootID string `json:"thread_root_id,omitempty"` // exec-05c C4: Thread-Root Event-ID
}

// Bridge verwaltet die NATS-Verbindung.
type Bridge struct {
	nc             *nats.Conn
	subjectRouting bool // exec-05c: per-Agent Subject Routing
}

// New erstellt eine neue Bridge-Verbindung.
func New(natsURL string, subjectRouting bool) (*Bridge, error) {
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
	slog.Info("NATS connected", "url", natsURL, "subject_routing", subjectRouting)
	return &Bridge{nc: nc, subjectRouting: subjectRouting}, nil
}

// PublishInbound publiziert eine eingehende Matrix-Nachricht.
// Bei subjectRouting=true wird das Subject per Room partitioniert:
// matrix.message.inbound.room.<roomID> statt dem globalen Subject.
func (b *Bridge) PublishInbound(ctx context.Context, msg InboundMessage) error {
	data, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("marshal: %w", err)
	}

	subject := SubjectInbound
	if b.subjectRouting {
		// exec-05c C2: Agent-spezifisches Routing hat Vorrang vor Room-Routing
		if msg.TargetAgent != "" {
			subject = SubjectInboundAgentPrefix + SubjectAgentToken(msg.TargetAgent)
		} else if msg.RoomID != "" {
			subject = SubjectInbound + ".room." + msg.RoomID
		}
	}

	if err := b.nc.Publish(subject, data); err != nil {
		return fmt.Errorf("publish %s: %w", subject, err)
	}
	slog.Debug("published matrix message to NATS",
		"room", msg.RoomID,
		"sender", msg.Sender,
		"subject", subject,
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
