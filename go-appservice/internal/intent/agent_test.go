package intent

import (
	"testing"

	"maunium.net/go/mautrix/id"
)

func TestUserIDGeneration(t *testing.T) {
	sender := New(nil, "matrix.local")

	cases := []struct {
		agent string
		want  id.UserID
	}{
		{"trading", "@agent-trading:matrix.local"},
		{"research", "@agent-research:matrix.local"},
		{"chat", "@agent-chat:matrix.local"},
		{" Agent-Research/Lead ", "@agent-research-lead:matrix.local"},
	}
	for _, tc := range cases {
		got := sender.UserID(tc.agent)
		if got != tc.want {
			t.Errorf("UserID(%q) = %q, want %q", tc.agent, got, tc.want)
		}
	}
}

func TestSanitizeAgentName(t *testing.T) {
	cases := []struct {
		name string
		want string
	}{
		{"trading", "trading"},
		{"@agent-Research.Bot:matrix.local", "research-bot"},
		{" research/slash dot.name ", "research-slash-dot-name"},
		{"../../evil", "evil"},
		{"", "default"},
		{"---", "default"},
	}

	for _, tc := range cases {
		got := SanitizeAgentName(tc.name)
		if got != tc.want {
			t.Errorf("SanitizeAgentName(%q) = %q, want %q", tc.name, got, tc.want)
		}
	}
}

func TestUserIDServerName(t *testing.T) {
	sender := New(nil, "custom.server")
	got := sender.UserID("bot")
	if got != "@agent-bot:custom.server" {
		t.Errorf("UserID = %q, want @agent-bot:custom.server", got)
	}
}
