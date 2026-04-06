package storage

import (
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
