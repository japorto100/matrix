package keyvault

import (
	"crypto/rand"
	"encoding/hex"
	"strings"
	"testing"
)

// randomHexSecret generates a fresh 32-byte (64 hex char) secret per test.
func randomHexSecret(t *testing.T) string {
	t.Helper()
	key := make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		t.Fatalf("random key: %v", err)
	}
	return hex.EncodeToString(key)
}

// ─── AES-256-GCM ────────────────────────────────────────────────────

func TestAESGCMRoundtrip(t *testing.T) {
	secret := randomHexSecret(t)
	vault, err := NewAESGCMVault(secret)
	if err != nil {
		t.Fatalf("NewAESGCMVault: %v", err)
	}
	if vault.Backend() != "aesgcm" {
		t.Errorf("Backend = %q, want aesgcm", vault.Backend())
	}

	cases := []string{
		"hello world",
		"",
		"unicode: äöü 日本語 emoji 🎉",
		strings.Repeat("a", 10000),
		"sk-or-v1-d2aa14c92162107cc150a45e811eac2fd917617e",
	}
	for _, plain := range cases {
		ct, err := vault.Encrypt(plain)
		if err != nil {
			t.Fatalf("Encrypt(%q): %v", plain[:min(len(plain), 20)], err)
		}
		if ct[0] != prefixAESGCM {
			t.Errorf("prefix = 0x%02x, want 0x%02x", ct[0], prefixAESGCM)
		}
		got, err := vault.Decrypt(ct)
		if err != nil {
			t.Fatalf("Decrypt: %v", err)
		}
		if got != plain {
			t.Errorf("roundtrip failed: got %q, want %q", got[:min(len(got), 50)], plain[:min(len(plain), 50)])
		}
	}
}

func TestAESGCMTamperDetection(t *testing.T) {
	vault, _ := NewAESGCMVault(randomHexSecret(t))
	ct, _ := vault.Encrypt("secret data")

	// Flip a byte in the ciphertext body
	tampered := make([]byte, len(ct))
	copy(tampered, ct)
	tampered[len(tampered)-3] ^= 0xFF

	if _, err := vault.Decrypt(tampered); err == nil {
		t.Error("Decrypt(tampered) should fail")
	}
}

func TestAESGCMTooShort(t *testing.T) {
	vault, _ := NewAESGCMVault(randomHexSecret(t))
	if _, err := vault.Decrypt([]byte{prefixAESGCM, 1, 2}); err == nil {
		t.Error("Decrypt(too short) should fail")
	}
}

func TestAESGCMWrongPrefix(t *testing.T) {
	vault, _ := NewAESGCMVault(randomHexSecret(t))
	ct, _ := vault.Encrypt("test")
	ct[0] = 0xFF
	_, err := vault.Decrypt(ct)
	if err == nil {
		t.Error("Decrypt with wrong prefix should fail")
	}
	if !strings.Contains(err.Error(), "unknown prefix") {
		t.Errorf("error = %q, want 'unknown prefix'", err.Error())
	}
}

func TestAESGCMCrossVaultDecryptRejected(t *testing.T) {
	vault, _ := NewAESGCMVault(randomHexSecret(t))
	ct, _ := vault.Encrypt("test")
	ct[0] = prefixHPKE
	_, err := vault.Decrypt(ct)
	if err == nil || !strings.Contains(err.Error(), "HPKE") {
		t.Errorf("AES vault decrypting HPKE-prefixed data: err = %v", err)
	}
}

func TestAESGCMDifferentKeyCannotDecrypt(t *testing.T) {
	vault1, _ := NewAESGCMVault(randomHexSecret(t))
	vault2, _ := NewAESGCMVault(randomHexSecret(t))
	ct, _ := vault1.Encrypt("secret")
	if _, err := vault2.Decrypt(ct); err == nil {
		t.Error("different key should fail decryption")
	}
}

func TestAESGCMInvalidSecretHex(t *testing.T) {
	if _, err := NewAESGCMVault("not-hex"); err == nil {
		t.Error("non-hex secret should fail")
	}
	if _, err := NewAESGCMVault("aabb"); err == nil {
		t.Error("too-short secret should fail")
	}
	if _, err := NewAESGCMVault(strings.Repeat("aa", 33)); err == nil {
		t.Error("too-long secret should fail")
	}
}

func TestAESGCMNonceUniqueness(t *testing.T) {
	vault, _ := NewAESGCMVault(randomHexSecret(t))
	ct1, _ := vault.Encrypt("same")
	ct2, _ := vault.Encrypt("same")
	if string(ct1) == string(ct2) {
		t.Error("two encryptions of same plaintext must produce different ciphertext (unique nonce)")
	}
}

// ─── HPKE ────────────────────────────────────────────────────────────

func TestHPKERoundtrip(t *testing.T) {
	vault, err := NewHPKEVault(randomHexSecret(t))
	if err != nil {
		t.Fatalf("NewHPKEVault: %v", err)
	}
	if vault.Backend() != "hpke-x25519" {
		t.Errorf("Backend = %q, want hpke-x25519", vault.Backend())
	}

	cases := []string{"hello", "", "unicode 🔐", strings.Repeat("x", 5000)}
	for _, plain := range cases {
		ct, err := vault.Encrypt(plain)
		if err != nil {
			t.Fatalf("Encrypt: %v", err)
		}
		if ct[0] != prefixHPKE {
			t.Errorf("prefix = 0x%02x, want 0x%02x", ct[0], prefixHPKE)
		}
		got, err := vault.Decrypt(ct)
		if err != nil {
			t.Fatalf("Decrypt: %v", err)
		}
		if got != plain {
			t.Errorf("roundtrip: got %q, want %q", got[:min(len(got), 50)], plain[:min(len(plain), 50)])
		}
	}
}

func TestHPKECrossVaultDecryptRejected(t *testing.T) {
	vault, _ := NewHPKEVault(randomHexSecret(t))
	ct, _ := vault.Encrypt("test")
	ct[0] = prefixAESGCM
	_, err := vault.Decrypt(ct)
	if err == nil || !strings.Contains(err.Error(), "AES-GCM") {
		t.Errorf("HPKE vault decrypting AES-prefixed data: err = %v", err)
	}
}

func TestHPKEDifferentKeyCannotDecrypt(t *testing.T) {
	vault1, _ := NewHPKEVault(randomHexSecret(t))
	vault2, _ := NewHPKEVault(randomHexSecret(t))
	ct, _ := vault1.Encrypt("secret")
	if _, err := vault2.Decrypt(ct); err == nil {
		t.Error("different HPKE key should fail decryption")
	}
}

func TestHPKETooShort(t *testing.T) {
	vault, _ := NewHPKEVault(randomHexSecret(t))
	if _, err := vault.Decrypt([]byte{prefixHPKE}); err == nil {
		t.Error("Decrypt(too short) should fail")
	}
}

// ─── NewKeyVault factory ─────────────────────────────────────────────

func TestNewKeyVaultFactory(t *testing.T) {
	secret := randomHexSecret(t)

	aes, err := NewKeyVault("aesgcm", secret)
	if err != nil {
		t.Fatalf("aesgcm: %v", err)
	}
	if aes.Backend() != "aesgcm" {
		t.Errorf("aesgcm backend = %q", aes.Backend())
	}

	hpk, err := NewKeyVault("hpke-mlkem", secret)
	if err != nil {
		t.Fatalf("hpke-mlkem: %v", err)
	}
	if hpk.Backend() != "hpke-x25519" {
		t.Errorf("hpke backend = %q", hpk.Backend())
	}

	defVault, err := NewKeyVault("", secret)
	if err != nil {
		t.Fatalf("default: %v", err)
	}
	if defVault.Backend() != "aesgcm" {
		t.Errorf("default backend = %q, want aesgcm", defVault.Backend())
	}

	if _, err := NewKeyVault("unknown", secret); err == nil {
		t.Error("unknown backend should fail")
	}
}

// ─── Cross-backend compatibility ─────────────────────────────────────

func TestAESCannotDecryptHPKE(t *testing.T) {
	secret := randomHexSecret(t)
	aesVault, _ := NewAESGCMVault(secret)
	hpkeVault, _ := NewHPKEVault(secret)

	hpkeCT, _ := hpkeVault.Encrypt("hpke-encrypted")
	_, err := aesVault.Decrypt(hpkeCT)
	if err == nil {
		t.Error("AES should not decrypt HPKE ciphertext")
	}

	aesCT, _ := aesVault.Encrypt("aes-encrypted")
	_, err = hpkeVault.Decrypt(aesCT)
	if err == nil {
		t.Error("HPKE should not decrypt AES ciphertext")
	}
}
