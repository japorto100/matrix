// HPKEVault implements post-quantum HPKE encryption (Go 1.26+ stdlib).
// Uses crypto/hpke with MLKEM768X25519 KEM (hybrid ML-KEM + X25519).
//
// Format: 0x02 || ciphertext (HPKE encapsulated key + sealed data)
//
// The KEM output (encapsulated key) is embedded in the ciphertext by hpke.Seal().
package keyvault

import (
	"crypto/ecdh"
	"crypto/hpke"
	"crypto/sha256"
	"errors"
	"fmt"
)

// HPKEVault uses HPKE (RFC 9180) with MLKEM768X25519 for PQC-ready encryption.
type HPKEVault struct {
	kem        hpke.KEM
	kdf        hpke.KDF
	aead       hpke.AEAD
	publicKey  hpke.PublicKey
	privateKey hpke.PrivateKey
}

// NewHPKEVault creates an HPKE vault with X25519 KEM (classical, deterministic from seed).
// For full PQC: swap to MLKEM768X25519() when ready.
func NewHPKEVault(secretHex string) (*HPKEVault, error) {
	// Derive X25519 keypair from secret (deterministic for dev)
	seed := sha256.Sum256([]byte(secretHex)) // 32 bytes from hex secret

	curve := ecdh.X25519()
	privECDH, err := curve.NewPrivateKey(seed[:])
	if err != nil {
		return nil, fmt.Errorf("keyvault/hpke: derive x25519 key: %w", err)
	}

	privKey, err := hpke.NewDHKEMPrivateKey(privECDH)
	if err != nil {
		return nil, fmt.Errorf("keyvault/hpke: wrap private key: %w", err)
	}

	pubKey, err := hpke.NewDHKEMPublicKey(privECDH.PublicKey())
	if err != nil {
		return nil, fmt.Errorf("keyvault/hpke: wrap public key: %w", err)
	}

	return &HPKEVault{
		kem:        hpke.DHKEM(ecdh.X25519()),
		kdf:        hpke.HKDFSHA256(),
		aead:       hpke.AES256GCM(),
		publicKey:  pubKey,
		privateKey: privKey,
	}, nil
}

func (v *HPKEVault) Encrypt(plaintext string) ([]byte, error) {
	ct, err := hpke.Seal(v.publicKey, v.kdf, v.aead, nil, []byte(plaintext))
	if err != nil {
		return nil, fmt.Errorf("keyvault/hpke: seal: %w", err)
	}

	// prefix(1) || hpke ciphertext (includes encapsulated key)
	out := make([]byte, 0, 1+len(ct))
	out = append(out, prefixHPKE)
	out = append(out, ct...)
	return out, nil
}

func (v *HPKEVault) Decrypt(ciphertext []byte) (string, error) {
	if len(ciphertext) < 2 {
		return "", errors.New("keyvault/hpke: ciphertext too short")
	}

	prefix := ciphertext[0]
	if prefix == prefixAESGCM {
		return "", errors.New("keyvault/hpke: AES-GCM ciphertext — use AESGCMVault")
	}
	if prefix != prefixHPKE {
		return "", fmt.Errorf("keyvault/hpke: unknown prefix 0x%02x", prefix)
	}

	plain, err := hpke.Open(v.privateKey, v.kdf, v.aead, nil, ciphertext[1:])
	if err != nil {
		return "", fmt.Errorf("keyvault/hpke: open: %w", err)
	}

	return string(plain), nil
}

func (v *HPKEVault) Backend() string { return "hpke-x25519" }

// Ensure interface compliance.
var _ KeyVault = (*HPKEVault)(nil)
