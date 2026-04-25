package handler

import "testing"

func TestExtractAgentNameSanitizesMention(t *testing.T) {
	cases := []struct {
		body string
		want string
	}{
		{"@agent-trading check BTC", "trading"},
		{"hello @agent-Research.Bot:matrix.local", "research-bot"},
		{"@agent-../../evil run", "evil"},
		{"no mention", ""},
	}

	for _, tc := range cases {
		got := extractAgentName(tc.body, "agent-")
		if got != tc.want {
			t.Errorf("extractAgentName(%q) = %q, want %q", tc.body, got, tc.want)
		}
	}
}
