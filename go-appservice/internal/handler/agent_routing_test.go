package handler

import (
	"testing"

	"matrix/go-appservice/internal/config"

	"maunium.net/go/mautrix/id"
)

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

func TestTargetAgentForRoomUsesJoinedAgentMember(t *testing.T) {
	roomID := id.RoomID("!room:matrix.local")
	server := &Server{
		cfg: &config.Config{
			ServerName:  "matrix.local",
			AgentPrefix: "agent-",
		},
		roomMembers: map[id.RoomID]map[id.UserID]bool{
			roomID: {
				id.UserID("@alice:matrix.local"):       true,
				id.UserID("@agent-alice:matrix.local"): true,
			},
		},
	}

	if got := server.targetAgentForRoom(roomID); got != "alice" {
		t.Fatalf("targetAgentForRoom() = %q, want alice", got)
	}
}
