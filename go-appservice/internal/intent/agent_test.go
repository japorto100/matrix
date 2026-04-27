package intent

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"maunium.net/go/mautrix"
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

func TestSendTextUsesTransactionIDAndEscapedUserID(t *testing.T) {
	var gotPath string
	var gotUserID string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotUserID = r.URL.Query().Get("user_id")
		_ = json.NewEncoder(w).Encode(map[string]string{"event_id": "$ok"})
	}))
	defer srv.Close()

	client, err := mautrix.NewClient(srv.URL, "@appservice-bot:matrix.local", "as-token")
	if err != nil {
		t.Fatalf("NewClient: %v", err)
	}
	sender := New(client, "matrix.local")

	err = sender.SendText(
		context.Background(),
		"@agent-alice:matrix.local",
		"!room:matrix.local",
		"hello",
	)
	if err != nil {
		t.Fatalf("SendText: %v", err)
	}

	if !strings.Contains(gotPath, "/send/m.room.message/") {
		t.Fatalf("path %q does not contain send route", gotPath)
	}
	if strings.HasSuffix(gotPath, "/send/m.room.message/") {
		t.Fatalf("path %q is missing transaction id", gotPath)
	}
	if gotUserID != "@agent-alice:matrix.local" {
		t.Fatalf("user_id = %q", gotUserID)
	}
}
