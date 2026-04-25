package natsbridge

import (
	"encoding/json"
	"testing"
)

// These tests verify JSON serialization of the message types without
// requiring a live NATS connection. The Bridge itself needs NATS and is
// tested via integration (Cold-Start / devstack).

func TestInboundMessageSerialization(t *testing.T) {
	msg := InboundMessage{
		RoomID:        "!room:matrix.local",
		Sender:        "@user:matrix.local",
		Body:          "hello agent",
		EventID:       "$event123",
		ThreadID:      "$thread_root",
		TargetAgent:   "trading",
		IsThreadReply: true,
	}
	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var decoded InboundMessage
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if decoded.RoomID != msg.RoomID {
		t.Errorf("RoomID = %q, want %q", decoded.RoomID, msg.RoomID)
	}
	if decoded.Sender != msg.Sender {
		t.Errorf("Sender = %q", decoded.Sender)
	}
	if decoded.Body != msg.Body {
		t.Errorf("Body = %q", decoded.Body)
	}
	if decoded.ThreadID != msg.ThreadID {
		t.Errorf("ThreadID = %q", decoded.ThreadID)
	}
	if decoded.TargetAgent != msg.TargetAgent {
		t.Errorf("TargetAgent = %q", decoded.TargetAgent)
	}
	if !decoded.IsThreadReply {
		t.Error("IsThreadReply should be true")
	}
}

func TestReplyMessageSerialization(t *testing.T) {
	msg := ReplyMessage{
		RoomID:       "!room:matrix.local",
		AgentUserID:  "@agent-trading:matrix.local",
		Text:         "BTC is at 100k",
		IsStreaming:  false,
		ThreadRootID: "$thread_root",
	}
	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var decoded ReplyMessage
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if decoded.AgentUserID != msg.AgentUserID {
		t.Errorf("AgentUserID = %q", decoded.AgentUserID)
	}
	if decoded.Text != msg.Text {
		t.Errorf("Text = %q", decoded.Text)
	}
	if decoded.ThreadRootID != msg.ThreadRootID {
		t.Errorf("ThreadRootID = %q", decoded.ThreadRootID)
	}
}

func TestInboundMessageOmitsEmptyFields(t *testing.T) {
	msg := InboundMessage{
		RoomID:  "!room:local",
		Sender:  "@user:local",
		Body:    "hi",
		EventID: "$e1",
		// ThreadID, TargetAgent, IsThreadReply all zero
	}
	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	text := string(data)
	if contains(text, "thread_id") {
		t.Error("empty ThreadID should be omitted")
	}
	if contains(text, "target_agent") {
		t.Error("empty TargetAgent should be omitted")
	}
	if contains(text, "is_thread_reply") {
		t.Error("false IsThreadReply should be omitted")
	}
}

func TestSubjectAgentTokenNormalizesUnsafeNames(t *testing.T) {
	cases := map[string]string{
		"Research":                             "research",
		"@agent-Research.Bot:matrix.local":     "research-bot",
		"../../evil":                           "evil",
		"---":                                  "default",
		"agent-very_long_name_with/slashes...": "very_long_name_with-slashes",
	}
	for input, want := range cases {
		if got := SubjectAgentToken(input); got != want {
			t.Fatalf("SubjectAgentToken(%q) = %q, want %q", input, got, want)
		}
	}
}

func contains(s, sub string) bool {
	return len(s) > 0 && len(sub) > 0 && jsonContains(s, sub)
}

func jsonContains(s, key string) bool {
	return len(s) > 0 && len(key) > 0 && stringContains(s, `"`+key+`"`)
}

func stringContains(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
