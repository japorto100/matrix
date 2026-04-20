"""Tier-1 regex-based secret redaction for matrix (exec-security §1.2 Tier-1).

**What this is:**
Enterprise-adapted port of ``_ref/hermes-agent/agent/redact.py`` — 35 API-key
prefix patterns + 8 pattern-classes for ENV-assignments, JSON-fields,
Authorization headers, Telegram bot-tokens, private-key PEM blocks, DB
connection strings, JWT tokens, Discord mentions, and E.164 phone numbers.

Tier-1 design constraints:

* **Pure CPU, sync-safe** — patterns compiled at import time; no I/O,
  no asyncio, no DB. Safe to call from ``PostgresSpanProcessor.on_end``
  which runs synchronously (see exec-17 §2.5).
* **Snapshot-at-import** — ``MATRIX_REDACT_SECRETS`` env-var is read once
  and cached. Runtime env mutations (e.g. prompt-injected
  ``export MATRIX_REDACT_SECRETS=false``) cannot disable redaction.
* **Short-token full-mask** — tokens < 18 chars become ``***``;
  longer tokens preserve first-6 + last-4 chars for debuggability.

Tier-2 async DB-backed custom patterns (migration 023 + redact_consumer.py)
extends the static set — not in this module.

**Enterprise adaptations from hermes-original:**

1. Env-var renamed ``HERMES_REDACT_SECRETS`` → ``MATRIX_REDACT_SECRETS``.
2. New API ``redact_span_event(event: dict) -> dict`` — walks span-event
   JSONB trees recursively. Primary hook-point for exec-17 §2.5.
3. Every call tracks a ``RedactionResult`` with ``count`` so callers can
   emit the ``audit.redaction_count`` span-attribute for observability.
4. ``redact_dict`` helper for general dict-payload redaction (used by
   trajectory/exporter.py before JSONL serialization).

Cross-refs:
* ``exec-security.md §1`` — design, admin-bypass policy, SOTA-2026 research.
* ``exec-17.md §2.5`` — hook-points in PostgresSpanProcessor + trajectory.
* ``_ref/hermes-agent/agent/redact.py`` — upstream pattern-set.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "RedactionResult",
    "redact_sensitive_text",
    "redact_dict",
    "redact_span_event",
    "RedactingFormatter",
    "is_redaction_enabled",
]


# Snapshot at import time so runtime env mutations (e.g. LLM-generated
# ``export MATRIX_REDACT_SECRETS=false``) cannot disable redaction mid-session.
_REDACT_ENABLED: bool = os.getenv("MATRIX_REDACT_SECRETS", "").lower() not in (
    "0",
    "false",
    "no",
    "off",
)


def is_redaction_enabled() -> bool:
    """Module-level accessor so callers can check the flag without reaching
    into module-state. Useful for tests and for skipping instrumentation
    work when redaction is off in dev."""
    return _REDACT_ENABLED


# Known API key prefixes -- match the prefix + contiguous token chars.
# Ported 1:1 from hermes (battle-tested in production).
_PREFIX_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{10,}",           # OpenAI / OpenRouter / Anthropic (sk-ant-*)
    r"ghp_[A-Za-z0-9]{10,}",            # GitHub PAT (classic)
    r"github_pat_[A-Za-z0-9_]{10,}",    # GitHub PAT (fine-grained)
    r"gho_[A-Za-z0-9]{10,}",            # GitHub OAuth access token
    r"ghu_[A-Za-z0-9]{10,}",            # GitHub user-to-server token
    r"ghs_[A-Za-z0-9]{10,}",            # GitHub server-to-server token
    r"ghr_[A-Za-z0-9]{10,}",            # GitHub refresh token
    r"xox[baprs]-[A-Za-z0-9-]{10,}",    # Slack tokens
    r"AIza[A-Za-z0-9_-]{30,}",          # Google API keys
    r"pplx-[A-Za-z0-9]{10,}",           # Perplexity
    r"fal_[A-Za-z0-9_-]{10,}",          # Fal.ai
    r"fc-[A-Za-z0-9]{10,}",             # Firecrawl
    r"bb_live_[A-Za-z0-9_-]{10,}",      # BrowserBase
    r"gAAAA[A-Za-z0-9_=-]{20,}",        # Codex encrypted tokens
    r"AKIA[A-Z0-9]{16}",                # AWS Access Key ID
    r"sk_live_[A-Za-z0-9]{10,}",        # Stripe secret key (live)
    r"sk_test_[A-Za-z0-9]{10,}",        # Stripe secret key (test)
    r"rk_live_[A-Za-z0-9]{10,}",        # Stripe restricted key
    r"SG\.[A-Za-z0-9_-]{10,}",          # SendGrid API key
    r"hf_[A-Za-z0-9]{10,}",             # HuggingFace token
    r"r8_[A-Za-z0-9]{10,}",             # Replicate API token
    r"npm_[A-Za-z0-9]{10,}",            # npm access token
    r"pypi-[A-Za-z0-9_-]{10,}",         # PyPI API token
    r"dop_v1_[A-Za-z0-9]{10,}",         # DigitalOcean PAT
    r"doo_v1_[A-Za-z0-9]{10,}",         # DigitalOcean OAuth
    r"am_[A-Za-z0-9_-]{10,}",           # AgentMail API key
    r"sk_[A-Za-z0-9_]{10,}",            # ElevenLabs TTS key (sk_ underscore, not sk- dash)
    r"tvly-[A-Za-z0-9]{10,}",           # Tavily search API key
    r"exa_[A-Za-z0-9]{10,}",            # Exa search API key
    r"gsk_[A-Za-z0-9]{10,}",            # Groq Cloud API key
    r"syt_[A-Za-z0-9]{10,}",            # Matrix access token
    r"retaindb_[A-Za-z0-9]{10,}",       # RetainDB API key
    r"hsk-[A-Za-z0-9]{10,}",            # Hindsight API key
    r"mem0_[A-Za-z0-9]{10,}",           # Mem0 Platform API key
    r"brv_[A-Za-z0-9]{10,}",            # ByteRover API key
]

# ENV assignment patterns: KEY=value where KEY contains a secret-like name.
_SECRET_ENV_NAMES = r"(?:API_?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)"
_ENV_ASSIGN_RE = re.compile(
    rf"([A-Z0-9_]{{0,50}}{_SECRET_ENV_NAMES}[A-Z0-9_]{{0,50}})\s*=\s*(['\"]?)(\S+)\2",
)

# JSON field patterns: "apiKey": "value", "token": "value", etc.
_JSON_KEY_NAMES = (
    r"(?:api_?[Kk]ey|token|secret|password|access_token|refresh_token|"
    r"auth_token|bearer|secret_value|raw_secret|secret_input|key_material)"
)
_JSON_FIELD_RE = re.compile(
    rf'("{_JSON_KEY_NAMES}")\s*:\s*"([^"]+)"',
    re.IGNORECASE,
)

# Authorization headers.
_AUTH_HEADER_RE = re.compile(
    r"(Authorization:\s*Bearer\s+)(\S+)",
    re.IGNORECASE,
)

# Telegram bot tokens: bot<digits>:<token> or <digits>:<token>,
# where token part is restricted to [-A-Za-z0-9_] and length >= 30.
_TELEGRAM_RE = re.compile(
    r"(bot)?(\d{8,}):([-A-Za-z0-9_]{30,})",
)

# Private key blocks: -----BEGIN RSA PRIVATE KEY----- ... -----END RSA PRIVATE KEY-----.
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----"
)

# Database connection strings: protocol://user:PASSWORD@host.
_DB_CONNSTR_RE = re.compile(
    r"((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^:]+:)([^@]+)(@)",
    re.IGNORECASE,
)

# JWT tokens: header.payload[.signature] — always start with "eyJ" (base64 for "{").
_JWT_RE = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}"           # Header (always starts with eyJ)
    r"(?:\.[A-Za-z0-9_=-]{4,}){0,2}"   # Optional payload and/or signature
)

# Discord user/role mentions: <@123456789012345678> or <@!123456789012345678>.
_DISCORD_MENTION_RE = re.compile(r"<@!?(\d{17,20})>")

# E.164 phone numbers: +<country><number>, 7-15 digits.
# Negative lookahead prevents matching hex strings or identifiers.
_SIGNAL_PHONE_RE = re.compile(r"(\+[1-9]\d{6,14})(?![A-Za-z0-9])")

# Compile known prefix patterns into one alternation. Guards against
# false-positives in the middle of a longer identifier via look-around.
_PREFIX_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(" + "|".join(_PREFIX_PATTERNS) + r")(?![A-Za-z0-9_-])"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RedactionResult:
    """Return value for :func:`redact_span_event` + :func:`redact_dict`.

    ``count`` lets callers emit the ``audit.redaction_count`` span-attribute
    without re-scanning the returned payload.
    """

    value: Any
    count: int


def _mask_token(token: str) -> str:
    """Mask a token, preserving prefix for long tokens.

    Behaviour matches hermes 1:1 so operators reading both products see the
    same masking. Short tokens become ``***``; longer tokens preserve a
    6-char prefix + 4-char suffix with ``...`` between them.
    """
    if len(token) < 18:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def redact_sensitive_text(text: str | None) -> str | None:
    """Apply all redaction patterns to a single string.

    Safe to call on any string — non-matching text passes through unchanged.
    Returns ``None`` when input is ``None`` (convenience for optional
    content fields). Disabled entirely when ``MATRIX_REDACT_SECRETS`` is
    off (snapshot at import time).

    For dict-payload redaction use :func:`redact_dict` or
    :func:`redact_span_event`. For logging use :class:`RedactingFormatter`.
    """
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return text
    if not _REDACT_ENABLED:
        return text

    # Known prefixes (sk-, ghp_, etc.)
    text = _PREFIX_RE.sub(lambda m: _mask_token(m.group(1)), text)

    # ENV assignments: OPENAI_API_KEY=sk-abc...
    def _redact_env(m: re.Match[str]) -> str:
        name, quote, value = m.group(1), m.group(2), m.group(3)
        return f"{name}={quote}{_mask_token(value)}{quote}"

    text = _ENV_ASSIGN_RE.sub(_redact_env, text)

    # JSON fields: "apiKey": "value"
    def _redact_json(m: re.Match[str]) -> str:
        key, value = m.group(1), m.group(2)
        return f'{key}: "{_mask_token(value)}"'

    text = _JSON_FIELD_RE.sub(_redact_json, text)

    # Authorization headers
    text = _AUTH_HEADER_RE.sub(
        lambda m: m.group(1) + _mask_token(m.group(2)),
        text,
    )

    # Telegram bot tokens
    def _redact_telegram(m: re.Match[str]) -> str:
        prefix = m.group(1) or ""
        digits = m.group(2)
        return f"{prefix}{digits}:***"

    text = _TELEGRAM_RE.sub(_redact_telegram, text)

    # Private key blocks
    text = _PRIVATE_KEY_RE.sub("[REDACTED PRIVATE KEY]", text)

    # Database connection string passwords
    text = _DB_CONNSTR_RE.sub(lambda m: f"{m.group(1)}***{m.group(3)}", text)

    # JWT tokens (eyJ... — base64-encoded JSON headers)
    text = _JWT_RE.sub(lambda m: _mask_token(m.group(0)), text)

    # Discord user/role mentions (<@snowflake_id>)
    text = _DISCORD_MENTION_RE.sub(
        lambda m: f"<@{'!' if '!' in m.group(0) else ''}***>", text
    )

    # E.164 phone numbers (Signal, WhatsApp)
    def _redact_phone(m: re.Match[str]) -> str:
        phone = m.group(1)
        if len(phone) <= 8:
            return phone[:2] + "****" + phone[-2:]
        return phone[:4] + "****" + phone[-4:]

    text = _SIGNAL_PHONE_RE.sub(_redact_phone, text)

    return text


def _redact_value(value: Any, counter: list[int]) -> Any:
    """Recursively redact a JSON-serialisable value.

    ``counter`` is a 1-slot mutable list so the recursion can accumulate
    a substitution-count without returning a tuple per call. Caller reads
    ``counter[0]`` after the top-level call.

    Cycles: we don't guard against reference cycles because span-events
    come from OTel which materialises plain JSON trees (no cycles).
    """
    if isinstance(value, str):
        redacted = redact_sensitive_text(value)
        if redacted != value:
            counter[0] += 1
        return redacted
    if isinstance(value, dict):
        return {k: _redact_value(v, counter) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, counter) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item, counter) for item in value)
    # ints, floats, bools, None — pass through unchanged.
    return value


def redact_dict(payload: dict[str, Any]) -> RedactionResult:
    """Recursively redact a JSON-serialisable dict payload.

    Used by :func:`trajectory.exporter` (ShareGPT JSONL export), by REST
    serializers that return span-event content, and by anything that
    persists user-facing strings into Postgres JSONB columns.

    Returns a :class:`RedactionResult` carrying the redacted dict + a
    substitution count. Pass-through (no change) when redaction is
    disabled via env-var.
    """
    if not _REDACT_ENABLED or not payload:
        return RedactionResult(value=payload, count=0)
    counter = [0]
    redacted = _redact_value(payload, counter)
    return RedactionResult(value=redacted, count=counter[0])


def redact_span_event(event: dict[str, Any]) -> RedactionResult:
    """Redact a single OTel span-event dict (primary exec-17 §2.5 hook).

    Span-events have this shape::

        {
          "name": "llm_request",
          "timestamp": 1234567890,
          "attributes": {
            "prompt": "...",
            "response": "...",
            ...
          }
        }

    Only the ``attributes`` sub-tree carries user-facing content, so we
    redact that and pass through the envelope. If ``attributes`` is
    missing (malformed event) we redact the whole event defensively.
    """
    if not _REDACT_ENABLED or not event:
        return RedactionResult(value=event, count=0)

    attrs = event.get("attributes")
    if isinstance(attrs, dict):
        result = redact_dict(attrs)
        if result.count == 0:
            return RedactionResult(value=event, count=0)
        # Build a new dict to avoid mutating the caller's copy.
        return RedactionResult(
            value={**event, "attributes": result.value},
            count=result.count,
        )
    # Unusual shape — redact the whole tree.
    return redact_dict(event)


class RedactingFormatter(logging.Formatter):
    """Log formatter that redacts secrets from all log messages.

    Swap-in replacement for :class:`logging.Formatter`. Attach at the
    handler level to redact every log record passing through that handler.
    Cheap enough to use in the default root handler — per-message regex
    scan is dominated by the I/O cost of the log write itself.
    """

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = redact_sensitive_text(original)
        return redacted if redacted is not None else ""
