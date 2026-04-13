package storage

import (
	"strings"
	"testing"
	"time"
)

func TestSignerIssueAndVerify(t *testing.T) {
	t.Parallel()

	signer := NewSigner("test-secret")
	now := time.Unix(1_700_000_000, 0).UTC()

	token, err := signer.Issue(TokenClaims{
		ArtifactID: "art_123",
		Action:     ActionUpload,
		ExpiresAt:  now.Add(5 * time.Minute),
	}, now)
	if err != nil {
		t.Fatalf("issue token: %v", err)
	}

	claims, err := signer.Verify(token, now.Add(time.Minute))
	if err != nil {
		t.Fatalf("verify token: %v", err)
	}
	if claims.ArtifactID != "art_123" {
		t.Fatalf("artifact id = %q, want art_123", claims.ArtifactID)
	}
	if claims.Action != ActionUpload {
		t.Fatalf("action = %q, want %q", claims.Action, ActionUpload)
	}
}

func TestSignerRejectsTamperedOrExpiredToken(t *testing.T) {
	t.Parallel()

	signer := NewSigner("test-secret")
	now := time.Unix(1_700_000_000, 0).UTC()

	token, err := signer.Issue(TokenClaims{
		ArtifactID: "art_123",
		Action:     ActionDownload,
		ExpiresAt:  now.Add(time.Minute),
	}, now)
	if err != nil {
		t.Fatalf("issue token: %v", err)
	}

	if _, err := signer.Verify(token+"x", now.Add(30*time.Second)); err == nil {
		t.Fatal("expected tampered token verification to fail")
	}
	if _, err := signer.Verify(token, now.Add(2*time.Minute)); err == nil {
		t.Fatal("expected expired token verification to fail")
	}
}

func TestSignerWrongSecret(t *testing.T) {
	t.Parallel()

	signerA := NewSigner("secret-a")
	signerB := NewSigner("secret-b")
	now := time.Unix(1_700_000_000, 0).UTC()

	token, err := signerA.Issue(TokenClaims{
		ArtifactID: "art_x",
		Action:     ActionDownload,
		ExpiresAt:  now.Add(5 * time.Minute),
	}, now)
	if err != nil {
		t.Fatalf("issue: %v", err)
	}
	if _, err := signerB.Verify(token, now); err == nil {
		t.Fatal("token signed by secret-a must not verify under secret-b")
	}
}

func TestSignerRoundtripBothActions(t *testing.T) {
	t.Parallel()

	signer := NewSigner("test-secret")
	now := time.Unix(1_700_000_000, 0).UTC()

	for _, action := range []Action{ActionUpload, ActionDownload} {
		t.Run(string(action), func(t *testing.T) {
			token, err := signer.Issue(TokenClaims{
				ArtifactID: "art_roundtrip",
				UserID:     "alice",
				Action:     action,
				ExpiresAt:  now.Add(time.Minute),
			}, now)
			if err != nil {
				t.Fatalf("issue %s: %v", action, err)
			}
			claims, err := signer.Verify(token, now.Add(30*time.Second))
			if err != nil {
				t.Fatalf("verify %s: %v", action, err)
			}
			if claims.Action != action {
				t.Errorf("action = %q, want %q", claims.Action, action)
			}
			if claims.UserID != "alice" {
				t.Errorf("UserID = %q, want alice", claims.UserID)
			}
		})
	}
}

// TestSignerUserIDRoundtrip verifies the UserID survives a full Issue/Verify
// cycle — the core requirement for exec-19 Phase 2 (A).
func TestSignerUserIDRoundtrip(t *testing.T) {
	t.Parallel()

	signer := NewSigner("test-secret")
	now := time.Unix(1_700_000_000, 0).UTC()

	cases := []string{
		"alice",
		"@agent-trading:matrix.local",
		"user-with-dash",
		"UPPERCASE",
		"",   // legacy/anonymous — token with empty UserID must verify too
	}
	for _, uid := range cases {
		t.Run("uid="+uid, func(t *testing.T) {
			token, err := signer.Issue(TokenClaims{
				ArtifactID: "art_123",
				UserID:     uid,
				Action:     ActionUpload,
				ExpiresAt:  now.Add(time.Minute),
			}, now)
			if err != nil {
				t.Fatalf("issue with uid=%q: %v", uid, err)
			}
			claims, err := signer.Verify(token, now.Add(30*time.Second))
			if err != nil {
				t.Fatalf("verify: %v", err)
			}
			if claims.UserID != uid {
				t.Errorf("UserID = %q, want %q", claims.UserID, uid)
			}
		})
	}
}

// TestSignerUserIDTamperDetection — a token where the payload has been
// re-encoded with a different UserID must not verify (because the HMAC
// no longer matches the tampered payload). This is the primary defense
// against leaked-URL replay by a different user, since the HMAC is
// computed over the whole payload including UserID.
func TestSignerUserIDTamperDetection(t *testing.T) {
	t.Parallel()

	signer := NewSigner("test-secret")
	now := time.Unix(1_700_000_000, 0).UTC()

	tokenA, err := signer.Issue(TokenClaims{
		ArtifactID: "art_123",
		UserID:     "alice",
		Action:     ActionUpload,
		ExpiresAt:  now.Add(time.Minute),
	}, now)
	if err != nil {
		t.Fatalf("issue A: %v", err)
	}
	tokenB, err := signer.Issue(TokenClaims{
		ArtifactID: "art_123",
		UserID:     "bob",
		Action:     ActionUpload,
		ExpiresAt:  now.Add(time.Minute),
	}, now)
	if err != nil {
		t.Fatalf("issue B: %v", err)
	}
	// The two tokens differ in payload (different UserID) AND in signature
	// (because HMAC is computed over the payload).
	if tokenA == tokenB {
		t.Fatal("tokens with different UserID should produce different strings")
	}

	// Swap payload from A onto signature from B — must not verify.
	aParts := strings.Split(tokenA, ".")
	bParts := strings.Split(tokenB, ".")
	if len(aParts) != 2 || len(bParts) != 2 {
		t.Fatalf("unexpected token format")
	}
	hybrid := aParts[0] + "." + bParts[1]
	if _, err := signer.Verify(hybrid, now); err == nil {
		t.Error("hybrid A-payload + B-signature should not verify")
	}

	// Just to double-check: a correctly-signed token for alice still verifies.
	if claims, err := signer.Verify(tokenA, now); err != nil {
		t.Errorf("re-verify A: %v", err)
	} else if claims.UserID != "alice" {
		t.Errorf("re-verify A UserID = %q, want alice", claims.UserID)
	}
}
