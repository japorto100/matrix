"""Remote-LLM session-title generator — **OFFLINE-FALLBACK ONLY**.

**Primary title-gen path is transformers.js** in the browser — see
``exec-transformersjs.md §3.5`` (owner re-scoped 2026-04-20). This module
exists as the server-side degradation path for environments where WebGPU
and WASM are both unavailable or disabled. When the frontend can run the
local model, it SHOULD NOT call this module at all.

Port of ``_ref/hermes-agent/agent/title_generator.py`` adapted for matrix
enterprise guarantees:

* **Credential-isolation (Contrarian-2 MAJOR-5):** title-gen uses a
  DEDICATED service credential via env ``MATRIX_TITLE_GEN_KEY`` /
  ``MATRIX_TITLE_GEN_MODEL``. It never touches the user's CredentialPool,
  never consumes user-quota, never shows up in the user's InsightsEngine
  report.
* If the env-vars are missing or the call fails, we **skip** gracefully.
  The UI falls back to a truncated-first-message label. Failing title-gen
  must never block the user's chat turn.
* Non-blocking dispatch: runner should invoke via ``asyncio.create_task``
  after the first assistant turn is streamed back to the user.

Why remote is the fallback (not primary): a remote LLM call per session
is a cost-and-latency tax that makes no sense when a 0.5–1B parameter
model runs locally in the browser in <200ms. See exec-transformersjs.md
§3.5 for the primary path + the degradation chain (WebGPU → WASM →
this module).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

__all__ = [
    "generate_title",
    "persist_session_title",
    "generate_and_persist_title",
]


_TITLE_PROMPT = """You are naming a chat session based on its first exchange.

Rules:
- 3-7 words
- No quotes, no punctuation at the end
- Use the user's language if obvious, otherwise English
- Focus on the topic, not the greeting

Exchange:
User: {user_message}
Assistant: {assistant_reply}

Title:"""


def _service_credential() -> tuple[str | None, str]:
    """Return (api_key, model) for the dedicated title-gen service credential."""
    key = os.environ.get("MATRIX_TITLE_GEN_KEY") or None
    model = os.environ.get("MATRIX_TITLE_GEN_MODEL", "claude-haiku-4-5-20251001")
    return key, model


async def generate_title(
    *,
    user_message: str,
    assistant_reply: str,
    max_words: int = 7,
) -> str | None:
    """Return a 3–7 word session title, or ``None`` if the service-credential
    is missing or the LLM call fails.

    Fails closed — the UI falls back to a truncated-first-message label.
    Never raises.
    """
    if not user_message or not assistant_reply:
        return None

    api_key, model = _service_credential()
    if not api_key:
        logger.debug("title-gen skipped: MATRIX_TITLE_GEN_KEY not set")
        return None

    prompt = _TITLE_PROMPT.format(
        user_message=user_message[:500],
        assistant_reply=assistant_reply[:500],
    )

    try:
        import litellm

        resp = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key,
            max_tokens=32,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.debug("title-gen LLM call failed: %s", exc)
        return None

    title = _sanitize(raw, max_words=max_words)
    return title or None


def _sanitize(raw: str, *, max_words: int) -> str:
    """Trim surrounding whitespace/quotes, collapse to first line, cap words."""
    text = (raw or "").strip()
    if not text:
        return ""
    # Take only the first line in case the model added explanations.
    text = text.splitlines()[0].strip()
    # Iteratively strip wrapping quotes + trailing punctuation the prompt
    # already bans (defence-in-depth). Loop because "…!" → …! → … → OK.
    _trim_chars = "\"' \t.!?:;,"
    while text and text[0] in _trim_chars:
        text = text[1:]
    while text and text[-1] in _trim_chars:
        text = text[:-1]
    # Hard length cap so a runaway model output doesn't bloat the DB row.
    words = text.split()
    if len(words) > max_words:
        words = words[:max_words]
    return " ".join(words)


async def persist_session_title(
    session_id: str,
    title: str,
    *,
    db_url: str | None = None,
) -> bool:
    """UPDATE agent.sessions.title. Returns True on success, False otherwise.

    Uses the same psycopg async-pool pattern as other agent persistence.
    Fail-soft — DB outage must not break the chat turn.
    """
    if not session_id or not title:
        return False
    try:
        import psycopg
    except ImportError:
        return False

    dsn = db_url or os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )
    try:
        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            # Idempotent: only set title the first time. If the row already
            # has a non-null/non-empty title (from a prior turn or an ops
            # backfill), keep it. Callers can invoke this on every turn
            # without worrying about clobbering an existing title.
            await conn.execute(
                """
                UPDATE agent.sessions
                SET title = %s
                WHERE session_id = %s
                  AND (title IS NULL OR title = '')
                """,
                (title, session_id),
            )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("persist_session_title failed: %s", exc)
        return False


async def generate_and_persist_title(
    *,
    session_id: str,
    user_message: str,
    assistant_reply: str,
    max_words: int = 7,
) -> str | None:
    """Convenience wrapper: generate a title and persist it idempotently.

    Designed for ``asyncio.create_task(...)`` dispatch from the runner
    right after the first assistant reply completes. Returns the title
    (for callers that want to emit it via SSE) or ``None`` when the
    service-credential is missing or the LLM call failed — the caller
    should not distinguish, either way the session just stays
    title-less until a later turn succeeds.
    """
    title = await generate_title(
        user_message=user_message,
        assistant_reply=assistant_reply,
        max_words=max_words,
    )
    if not title:
        return None
    ok = await persist_session_title(session_id, title)
    return title if ok else None
