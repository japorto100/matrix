"""Trajectory export (exec-hermes §3.6).

ShareGPT-format JSONL exporter over the exec-18 ``agent.sessions`` +
``agent.spans`` schema. Pure-logic builder (:func:`build_sharegpt_conversation`)
is trivially testable with in-memory fixtures; the DB adapter
(:func:`iter_sessions_with_spans`) is a thin psycopg reader.
"""
from agent.trajectory.exporter import (
    build_sharegpt_conversation,
    iter_sessions_with_spans,
    role_from_span_and_event,
    serialize_jsonl,
)

__all__ = [
    "build_sharegpt_conversation",
    "iter_sessions_with_spans",
    "role_from_span_and_event",
    "serialize_jsonl",
]
