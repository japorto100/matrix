"""ShareGPT-format trajectory exporter over exec-18 ``agent.sessions`` + ``agent.spans``.

Reads the exec-18 schema (Migration 017) — ``agent.traces`` (root per session)
and ``agent.spans`` (per turn, per tool-call) — and emits one ShareGPT
conversation per session as a JSONL line.

Pure-logic layer (:func:`build_sharegpt_conversation`) takes dicts mirroring
the DB schema, so unit tests don't need a live Postgres. The thin DB adapter
(:func:`iter_sessions_with_spans`) uses the same ``psycopg`` connection as
``agent/sessions.py`` and streams rows so export-all does not load the whole
DB into memory.

ShareGPT format::

    {"id": "...", "user_id": "...", "conversations":
      [{"from": "system"|"human"|"gpt"|"tool", "value": "..."}, ...]}

Span-event → role mapping is intentionally conservative: events we cannot
classify are dropped (a log line with ``unknown`` role leaks into the training
set otherwise).
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Iterator
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "build_sharegpt_conversation",
    "iter_sessions_with_spans",
    "role_from_span_and_event",
    "serialize_jsonl",
]


# ---------------------------------------------------------------------------
# Role mapping
# ---------------------------------------------------------------------------

_SYSTEM_EVENTS = frozenset({"system", "system_prompt"})
_HUMAN_EVENTS = frozenset({"prompt", "user_message", "user", "input"})
_GPT_EVENTS = frozenset({"completion", "assistant_message", "assistant", "output"})
_TOOL_EVENTS = frozenset({"tool_call", "tool_result", "tool_response"})


def role_from_span_and_event(span_kind: str, event_name: str) -> str | None:
    """Map ``(span_kind, event.name)`` → ShareGPT role, or None if unclassified.

    ShareGPT roles:
      - ``system`` — system prompt content
      - ``human`` — user input
      - ``gpt`` — assistant output
      - ``tool`` — tool call / tool result (on ``agent.tool_call`` spans)

    Unknown event names fall through to None — silently dropping them keeps the
    exported dataset consistent. Add new event taxonomy here as the harness
    emits more structured events.
    """
    lname = (event_name or "").lower()
    if lname in _SYSTEM_EVENTS:
        return "system"
    if lname in _HUMAN_EVENTS:
        return "human"
    if lname in _GPT_EVENTS:
        return "gpt"
    if span_kind == "agent.tool_call" and lname in _TOOL_EVENTS:
        return "tool"
    # Also accept tool events on agent.turn spans (some harness code attaches
    # tool calls to the parent turn span rather than a dedicated tool_call span).
    if lname in _TOOL_EVENTS:
        return "tool"
    return None


# ---------------------------------------------------------------------------
# Pure conversation builder
# ---------------------------------------------------------------------------

def build_sharegpt_conversation(
    session: dict[str, Any],
    spans: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    """Build one ShareGPT conversation from session+spans dicts.

    Returns ``None`` if the session has no usable turns — callers should skip
    rather than emit empty lines. Spans are sorted by ``start_time`` so the
    emitted conversation preserves the real sequence even if the caller
    shuffles the iterable (e.g. lazy DB cursor iteration with secondary indexes).
    """
    sorted_spans = sorted(
        (s for s in spans if isinstance(s, dict)),
        key=lambda s: str(s.get("start_time") or ""),
    )

    turns: list[dict[str, str]] = []
    for span in sorted_spans:
        span_kind = str(span.get("span_kind") or "")
        events = span.get("events")
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            name = str(event.get("name") or "")
            body = event.get("body")
            if not isinstance(body, str) or not body:
                continue
            role = role_from_span_and_event(span_kind, name)
            if role is None:
                continue
            turns.append({"from": role, "value": body})

    if not turns:
        return None

    return {
        "id": str(session.get("session_id") or ""),
        "user_id": str(session.get("user_id") or ""),
        "session_type": str(session.get("session_type") or ""),
        "agent_id": str(session.get("agent_id") or ""),
        "conversations": turns,
    }


def serialize_jsonl(items: Iterable[dict[str, Any]]) -> str:
    """Serialize an iterable of dicts to newline-terminated JSONL."""
    buf: list[str] = []
    for item in items:
        buf.append(json.dumps(item, ensure_ascii=False))
    if not buf:
        return ""
    return "\n".join(buf) + "\n"


# ---------------------------------------------------------------------------
# DB adapter (thin, streaming)
# ---------------------------------------------------------------------------

_SPANS_SQL = """
SELECT s.span_id, s.trace_id, s.parent_span_id, s.name, s.span_kind,
       s.attributes, s.events, s.start_time, s.end_time, s.duration_ms
FROM agent.spans s
JOIN agent.traces t ON t.trace_id = s.trace_id
WHERE t.session_id = %s
ORDER BY s.start_time ASC
"""


_SESSIONS_SQL = """
SELECT session_id, session_type, agent_id, user_id, thread_id, status,
       started_at, completed_at
FROM agent.sessions
WHERE (%(since_ms)s IS NULL OR started_at >= %(since_ms)s)
  AND (%(user_id)s IS NULL OR user_id = %(user_id)s)
ORDER BY started_at ASC
"""


def _default_db_url() -> str:
    """Mirror agent/sessions.py for consistent connection defaults."""
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def iter_sessions_with_spans(
    *,
    since_ms: int | None = None,
    user_id: str | None = None,
    db_url: str | None = None,
    conn=None,
) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    """Yield ``(session_dict, spans_list)`` for export, streaming from DB.

    Implementation is deliberately lightweight: we pull sessions matching
    the filter, then for each session issue a second query for its spans.
    Export is not latency-critical — simplicity beats join-based streaming
    complexity for now.

    Args:
        since_ms: Only sessions with ``started_at >= since_ms`` (epoch ms).
        user_id: Filter to a single user.
        db_url: Override DB URL (defaults to HINDSIGHT_DB_URL env).
        conn: Pre-opened psycopg connection (for tests). If None a new
            connection is opened and closed.
    """
    import psycopg  # local import so module import doesn't require psycopg

    close_after = False
    if conn is None:
        conn = psycopg.connect(db_url or _default_db_url())
        close_after = True
    try:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as sessions_cur:
            sessions_cur.execute(
                _SESSIONS_SQL, {"since_ms": since_ms, "user_id": user_id}
            )
            for session_row in sessions_cur:
                session = dict(session_row)
                with conn.cursor(row_factory=psycopg.rows.dict_row) as spans_cur:
                    spans_cur.execute(_SPANS_SQL, (session["session_id"],))
                    spans = [dict(r) for r in spans_cur]
                yield session, spans
    finally:
        if close_after:
            conn.close()
