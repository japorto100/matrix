package storage

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

type Signer struct {
	secret []byte
}

func NewSigner(secret string) *Signer {
	return &Signer{secret: []byte(secret)}
}

func (s *Signer) Issue(claims TokenClaims, now time.Time) (string, error) {
	if s == nil || len(s.secret) == 0 {
		return "", fmt.Errorf("signer secret missing")
	}
	if claims.ArtifactID == "" || claims.Action == "" {
		return "", fmt.Errorf("token claims incomplete")
	}
	if claims.ExpiresAt.IsZero() || !claims.ExpiresAt.After(now) {
		return "", fmt.Errorf("token expiry invalid")
	}

	payload, err := json.Marshal(struct {
		ArtifactID string `json:"artifactId"`
		Action     Action `json:"action"`
		ExpUnix    int64  `json:"expUnix"`
	}{
		ArtifactID: claims.ArtifactID,
		Action:     claims.Action,
		ExpUnix:    claims.ExpiresAt.UTC().Unix(),
	})
	if err != nil {
		return "", fmt.Errorf("marshal token payload: %w", err)
	}

	payloadPart := base64.RawURLEncoding.EncodeToString(payload)
	sig := s.sign(payloadPart)
	return payloadPart + "." + sig, nil
}

func (s *Signer) Verify(token string, now time.Time) (TokenClaims, error) {
	if s == nil || len(s.secret) == 0 {
		return TokenClaims{}, ErrInvalidToken
	}
	parts := strings.Split(token, ".")
	if len(parts) != 2 {
		return TokenClaims{}, ErrInvalidToken
	}
	if !hmac.Equal([]byte(parts[1]), []byte(s.sign(parts[0]))) {
		return TokenClaims{}, ErrInvalidToken
	}

	payload, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return TokenClaims{}, ErrInvalidToken
	}
	var decoded struct {
		ArtifactID string `json:"artifactId"`
		Action     Action `json:"action"`
		ExpUnix    int64  `json:"expUnix"`
	}
	if err := json.Unmarshal(payload, &decoded); err != nil {
		return TokenClaims{}, ErrInvalidToken
	}
	claims := TokenClaims{
		ArtifactID: decoded.ArtifactID,
		Action:     decoded.Action,
		ExpiresAt:  time.Unix(decoded.ExpUnix, 0).UTC(),
	}
	if claims.ArtifactID == "" || claims.Action == "" || claims.ExpiresAt.IsZero() || now.After(claims.ExpiresAt) {
		return TokenClaims{}, ErrInvalidToken
	}
	return claims, nil
}

func (s *Signer) sign(payload string) string {
	mac := hmac.New(sha256.New, s.secret)
	_, _ = mac.Write([]byte(payload))
	return base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
}
