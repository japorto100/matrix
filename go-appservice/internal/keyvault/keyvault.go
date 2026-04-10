// Package keyvault provides pluggable encryption for secrets at rest.
// Cross-language compatible with Python agent/security/key_vault.py.
//
// Byte format:  prefix(1) || nonce(12) || ciphertext || tag(16)
// Prefix 0x01 = AES-256-GCM, 0x02 = HPKE-MLKEM (reserved).
package keyvault

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
)

const (
	prefixAESGCM byte = 0x01
	prefixHPKE   byte = 0x02 // reserved for HPKE-MLKEM backend
	nonceSize         = 12
)

// KeyVault encrypts and decrypts secrets at rest.
type KeyVault interface {
	Encrypt(plaintext string) ([]byte, error)
	Decrypt(ciphertext []byte) (string, error)
	Backend() string
}

// AESGCMVault implements AES-256-GCM encryption.
// Compatible with Python AESGCMVault (identical byte format).
type AESGCMVault struct {
	gcm cipher.AEAD
}

// NewAESGCMVault creates a vault from a 32-byte key (64 hex chars).
func NewAESGCMVault(secretHex string) (*AESGCMVault, error) {
	key, err := hex.DecodeString(secretHex)
	if err != nil {
		return nil, fmt.Errorf("keyvault: invalid hex secret: %w", err)
	}
	if len(key) != 32 {
		return nil, fmt.Errorf("keyvault: secret must be 32 bytes (64 hex chars), got %d", len(key))
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("keyvault: aes cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("keyvault: gcm: %w", err)
	}

	return &AESGCMVault{gcm: gcm}, nil
}

func (v *AESGCMVault) Encrypt(plaintext string) ([]byte, error) {
	nonce := make([]byte, nonceSize)
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("keyvault: nonce: %w", err)
	}

	ct := v.gcm.Seal(nil, nonce, []byte(plaintext), nil)

	// prefix(1) || nonce(12) || ciphertext+tag
	out := make([]byte, 0, 1+nonceSize+len(ct))
	out = append(out, prefixAESGCM)
	out = append(out, nonce...)
	out = append(out, ct...)
	return out, nil
}

func (v *AESGCMVault) Decrypt(ciphertext []byte) (string, error) {
	if len(ciphertext) < 1+nonceSize+v.gcm.Overhead() {
		return "", errors.New("keyvault: ciphertext too short")
	}

	prefix := ciphertext[0]
	if prefix == prefixHPKE {
		return "", errors.New("keyvault: HPKE-MLKEM ciphertext — use HPKEVault to decrypt")
	}
	if prefix != prefixAESGCM {
		return "", fmt.Errorf("keyvault: unknown prefix 0x%02x", prefix)
	}

	nonce := ciphertext[1 : 1+nonceSize]
	ct := ciphertext[1+nonceSize:]

	plain, err := v.gcm.Open(nil, nonce, ct, nil)
	if err != nil {
		return "", fmt.Errorf("keyvault: decrypt: %w", err)
	}

	return string(plain), nil
}

func (v *AESGCMVault) Backend() string { return "aesgcm" }

// NewKeyVault creates the appropriate vault based on backend name.
func NewKeyVault(backend, secretHex string) (KeyVault, error) {
	switch backend {
	case "aesgcm", "":
		return NewAESGCMVault(secretHex)
	case "hpke-mlkem":
		return NewHPKEVault(secretHex)
	default:
		return nil, fmt.Errorf("keyvault: unknown backend %q (supported: aesgcm, hpke-mlkem)", backend)
	}
}
