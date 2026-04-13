"""KeyVault — AES-256-GCM encryption for API keys at rest.

Cross-language compatible with Go internal/keyvault/ (identical byte format).
Format: 0x01 || 12-byte nonce || ciphertext || 16-byte GCM tag

ENV: KEY_ENCRYPTION_SECRET (64 hex chars = 32 bytes)
     KEY_VAULT_BACKEND (default: aesgcm)
"""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Prefix bytes for auto-detection during decrypt
_PREFIX_AESGCM = b"\x01"
_PREFIX_HPKE = b"\x02"  # reserved for future PQC backend

_NONCE_SIZE = 12  # AES-GCM standard nonce size


@runtime_checkable
class KeyVault(Protocol):
    """Pluggable encryption interface for secrets at rest."""

    def encrypt(self, plaintext: str) -> bytes: ...
    def decrypt(self, ciphertext: bytes) -> str: ...
    @property
    def backend(self) -> str: ...


class AESGCMVault:
    """AES-256-GCM encryption. Cross-language compatible with Go keyvault."""

    def __init__(self, secret_hex: str) -> None:
        if len(secret_hex) != 64:
            raise ValueError(
                "KEY_ENCRYPTION_SECRET must be 64 hex chars (32 bytes). "
                'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        self._key = bytes.fromhex(secret_hex)
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = os.urandom(_NONCE_SIZE)
        ct = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return _PREFIX_AESGCM + nonce + ct

    def decrypt(self, ciphertext: bytes) -> str:
        if not ciphertext:
            raise ValueError("Empty ciphertext")
        prefix = ciphertext[0:1]
        if prefix == _PREFIX_HPKE:
            raise NotImplementedError(
                "HPKE-MLKEM decrypt not yet implemented in Python. Use Go backend."
            )
        if prefix != _PREFIX_AESGCM:
            raise ValueError(f"Unknown encryption prefix: {prefix!r}")
        nonce = ciphertext[1 : 1 + _NONCE_SIZE]
        ct = ciphertext[1 + _NONCE_SIZE :]
        return self._aesgcm.decrypt(nonce, ct, None).decode("utf-8")

    @property
    def backend(self) -> str:
        return "aesgcm"


# Singleton
_vault: KeyVault | None = None


def get_vault() -> KeyVault:
    """Get or create the global KeyVault singleton from ENV."""
    global _vault
    if _vault is not None:
        return _vault

    secret = os.environ.get("KEY_ENCRYPTION_SECRET", "")
    if not secret:
        raise RuntimeError(
            "KEY_ENCRYPTION_SECRET not set. API key encryption requires this ENV var. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        )

    backend = os.environ.get("KEY_VAULT_BACKEND", "aesgcm")
    if backend == "aesgcm":
        _vault = AESGCMVault(secret)
    else:
        raise ValueError(f"Unknown KEY_VAULT_BACKEND: {backend}. Supported: aesgcm")

    return _vault
