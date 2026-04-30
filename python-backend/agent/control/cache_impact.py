"""Provider-agnostic cache-impact contract for control-plane reloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from agent.runtime_events import make_runtime_event

CACHE_IMPACT_CONTRACT = "agent-cache-impact/v1"


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def digest_records(records: list[dict[str, Any]]) -> str:
    return stable_digest(records)


def build_cache_impact(
    *,
    source: str,
    reason: str,
    next_digest: str,
    previous_digest: str | None = None,
    scope: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous = str(previous_digest or "")
    current = str(next_digest or "")
    previous_known = bool(previous)
    changed = bool(previous_known and previous != current)
    action = "rebind_required" if not previous_known or changed else "no_change"
    return {
        "contract": CACHE_IMPACT_CONTRACT,
        "source": source,
        "reason": reason,
        "previous_digest": previous,
        "next_digest": current,
        "previous_digest_known": previous_known,
        "changed": changed,
        "action": action,
        "affected_sessions": [],
        "scope": scope or {},
        "details": details or {},
    }


def cache_impact_runtime_event(
    impact: dict[str, Any],
    *,
    session_id: str = "",
    thread_id: str = "",
) -> dict[str, Any]:
    action = str(impact.get("action") or "")
    source = str(impact.get("source") or "cache")
    changed = action == "rebind_required"
    return make_runtime_event(
        kind="control",
        status="completed",
        name="cache.invalidated" if changed else "cache.unchanged",
        summary=(
            f"{source} requires cached sessions to rebind"
            if changed
            else f"{source} left cached sessions unchanged"
        ),
        session_id=session_id,
        thread_id=thread_id,
        metadata={
            "cache_impact": {
                "contract": impact.get("contract"),
                "source": impact.get("source"),
                "reason": impact.get("reason"),
                "previous_digest": impact.get("previous_digest"),
                "next_digest": impact.get("next_digest"),
                "previous_digest_known": impact.get("previous_digest_known"),
                "changed": impact.get("changed"),
                "action": impact.get("action"),
            }
        },
    )
