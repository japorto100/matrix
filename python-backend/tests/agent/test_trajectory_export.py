"""Unit tests for agent.trajectory.exporter — pure logic only (no DB).

Covers exec-hermes §3.6 ShareGPT JSONL export.
"""
from __future__ import annotations

import json

from agent.trajectory.exporter import (
    build_sharegpt_conversation,
    role_from_span_and_event,
    serialize_jsonl,
)

# ---------------------------------------------------------------------------
# Role mapping
# ---------------------------------------------------------------------------

def test_role_mapping_prompt_to_human():
    assert role_from_span_and_event("agent.turn", "prompt") == "human"
    assert role_from_span_and_event("agent.turn", "user_message") == "human"


def test_role_mapping_completion_to_gpt():
    assert role_from_span_and_event("agent.turn", "completion") == "gpt"
    assert role_from_span_and_event("agent.turn", "assistant_message") == "gpt"


def test_role_mapping_system_prompt():
    assert role_from_span_and_event("agent.turn", "system") == "system"
    assert role_from_span_and_event("agent.turn", "system_prompt") == "system"


def test_role_mapping_tool_call():
    assert role_from_span_and_event("agent.tool_call", "tool_call") == "tool"
    assert role_from_span_and_event("agent.tool_call", "tool_result") == "tool"
    # Also accepted on turn-level spans (some harness emissions).
    assert role_from_span_and_event("agent.turn", "tool_result") == "tool"


def test_role_mapping_unknown_returns_none():
    assert role_from_span_and_event("agent.turn", "") is None
    assert role_from_span_and_event("agent.turn", "llm_error") is None
    assert role_from_span_and_event("agent.memory", "retrieve") is None


def test_role_mapping_case_insensitive():
    assert role_from_span_and_event("agent.turn", "PROMPT") == "human"
    assert role_from_span_and_event("agent.turn", "Completion") == "gpt"


# ---------------------------------------------------------------------------
# Conversation builder
# ---------------------------------------------------------------------------

def _session(**overrides) -> dict:
    base = {
        "session_id": "sess-1",
        "user_id": "alice",
        "session_type": "agent_chat",
        "agent_id": "default",
        "started_at": 1_700_000_000_000,
    }
    base.update(overrides)
    return base


def _span(start: str, kind: str, events: list[dict]) -> dict:
    return {
        "span_id": f"span-{start}",
        "span_kind": kind,
        "start_time": start,
        "events": events,
    }


def test_build_sharegpt_single_turn():
    session = _session()
    spans = [
        _span(
            "2026-04-18T10:00:00Z",
            "agent.turn",
            [
                {"name": "system", "body": "You are helpful."},
                {"name": "prompt", "body": "Hi"},
                {"name": "completion", "body": "Hello!"},
            ],
        )
    ]
    conv = build_sharegpt_conversation(session, spans)
    assert conv is not None
    assert conv["id"] == "sess-1"
    assert conv["user_id"] == "alice"
    assert [(t["from"], t["value"]) for t in conv["conversations"]] == [
        ("system", "You are helpful."),
        ("human", "Hi"),
        ("gpt", "Hello!"),
    ]


def test_build_sharegpt_orders_spans_by_start_time():
    session = _session()
    spans = [
        _span("2026-04-18T10:00:03Z", "agent.turn", [
            {"name": "prompt", "body": "second"},
        ]),
        _span("2026-04-18T10:00:01Z", "agent.turn", [
            {"name": "prompt", "body": "first"},
        ]),
    ]
    conv = build_sharegpt_conversation(session, spans)
    values = [t["value"] for t in conv["conversations"]]
    assert values == ["first", "second"]


def test_build_sharegpt_empty_session_returns_none():
    """No spans at all."""
    assert build_sharegpt_conversation(_session(), []) is None


def test_build_sharegpt_spans_without_events_skipped():
    """Spans present but no usable events → still None."""
    session = _session()
    spans = [
        _span("t", "agent.turn", []),
        _span("t2", "agent.memory", [{"name": "retrieve", "body": "…"}]),
    ]
    assert build_sharegpt_conversation(session, spans) is None


def test_build_sharegpt_skips_non_dict_events():
    session = _session()
    spans = [
        _span("t", "agent.turn", [
            "not-a-dict",
            {"name": "prompt", "body": "ok"},
            {"name": "completion"},  # missing body
            {"name": "completion", "body": ""},  # empty body
            {"name": "completion", "body": "answer"},
        ]),
    ]
    conv = build_sharegpt_conversation(session, spans)
    assert [t["value"] for t in conv["conversations"]] == ["ok", "answer"]


def test_build_sharegpt_tool_call_role():
    session = _session()
    spans = [
        _span("t1", "agent.turn", [{"name": "prompt", "body": "run"}]),
        _span("t2", "agent.tool_call", [
            {"name": "tool_call", "body": "search(q='x')"},
            {"name": "tool_result", "body": "result"},
        ]),
        _span("t3", "agent.turn", [{"name": "completion", "body": "done"}]),
    ]
    conv = build_sharegpt_conversation(session, spans)
    roles = [t["from"] for t in conv["conversations"]]
    assert roles == ["human", "tool", "tool", "gpt"]


def test_build_sharegpt_long_body_not_truncated():
    """Agent spans keep unbounded JSONB bodies — exporter must preserve
    them verbatim (audit_events truncation is what we're replacing)."""
    huge = "x" * 10_000
    session = _session()
    spans = [
        _span("t", "agent.turn", [{"name": "prompt", "body": huge}]),
    ]
    conv = build_sharegpt_conversation(session, spans)
    assert conv["conversations"][0]["value"] == huge


def test_build_sharegpt_handles_missing_start_time():
    session = _session()
    spans = [
        _span("", "agent.turn", [{"name": "prompt", "body": "one"}]),
        {
            "span_id": "s2",
            "span_kind": "agent.turn",
            # no start_time at all
            "events": [{"name": "completion", "body": "two"}],
        },
    ]
    conv = build_sharegpt_conversation(session, spans)
    assert [t["value"] for t in conv["conversations"]] == ["one", "two"]


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def test_serialize_jsonl_empty_returns_empty_string():
    assert serialize_jsonl([]) == ""


def test_serialize_jsonl_produces_valid_ndjson():
    items = [{"a": 1}, {"b": "zwei"}]
    out = serialize_jsonl(items)
    lines = out.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[1]) == {"b": "zwei"}


def test_serialize_jsonl_unicode_passthrough():
    """ensure_ascii=False so emojis / non-latin survive the JSONL round-trip."""
    out = serialize_jsonl([{"value": "über 💡 résumé"}])
    assert "über" in out
    assert "💡" in out


def test_end_to_end_session_to_jsonl():
    session = _session(session_id="sess-xyz")
    spans = [
        _span("2026-04-18T10:00:00Z", "agent.turn", [
            {"name": "system", "body": "sys"},
            {"name": "prompt", "body": "Q"},
            {"name": "completion", "body": "A"},
        ])
    ]
    conv = build_sharegpt_conversation(session, spans)
    line = serialize_jsonl([conv])
    parsed = json.loads(line.strip())
    assert parsed["id"] == "sess-xyz"
    assert parsed["conversations"][1] == {"from": "human", "value": "Q"}
