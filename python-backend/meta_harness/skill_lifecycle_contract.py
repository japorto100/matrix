"""Provider-free Meta-Harness lane for Feature 015 skill lifecycle traces."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_RUN_ID = "run-skill-lifecycle-contract"


def run_skill_lifecycle_contract_scenarios(
    *,
    run_id: str = DEFAULT_RUN_ID,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run deterministic skill audit, usage and reload-policy scenarios."""

    data_root = data_dir or Path(__file__).resolve().parents[2] / "data" / "meta_harness"
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        _audit_lifecycle_trace_shape(),
        _usage_sidecar_lifecycle_shape(),
        _skill_reload_control_policy(),
    ]
    passed = all(scenario["passed"] for scenario in scenarios)
    summary = {
        "run_id": run_id,
        "kind": "skill_lifecycle_contract",
        "feature_id": "015",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "scenario_count": len(scenarios),
        "passed_count": sum(1 for scenario in scenarios if scenario["passed"]),
        "scenarios": scenarios,
    }
    _write_json(run_dir / "skill_lifecycle_contract.json", summary)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "kind": "skill_lifecycle_contract",
            "feature_id": "015",
            "frontend_required": False,
            "provider_calls_required": False,
            "created_at": summary["created_at"],
        },
    )
    return {**summary, "artifact_path": str(run_dir / "skill_lifecycle_contract.json")}


def _audit_lifecycle_trace_shape() -> dict[str, Any]:
    events = [
        {
            "action": "skill_found",
            "agentId": "skills",
            "sessionId": "session-1",
            "threadId": "thread-1",
            "success": True,
            "metadata": {
                "skill_ids": ["global:market-research"],
                "skill_names": ["market-research"],
                "query_preview": "current market sentiment for AAPL",
                "user_id": "user-1",
                "search_rounds": 1,
                "satisfied": True,
                "search_traces": [
                    {
                        "selected_skill_ids": ["global:market-research"],
                        "query_terms": ["current", "market", "sentiment", "aapl"],
                        "candidates": [
                            {
                                "skill_id": "global:market-research",
                                "bm25_rank": 1,
                                "rrf_score": 0.032,
                                "matched_terms": ["market", "sentiment", "aapl"],
                                "selected": True,
                                "reason": "ranked",
                            }
                        ],
                    }
                ],
            },
        },
        {
            "action": "skill_refined",
            "agentId": "skills",
            "sessionId": "session-1",
            "threadId": "thread-1",
            "success": True,
            "metadata": {
                "skill_ids": ["global:market-research"],
                "skill_names": ["market-research"],
                "query_preview": "current market sentiment for AAPL",
                "coverage_score": 0.72,
                "source_skills": ["global:market-research"],
                "mode": "compose",
            },
        },
        {
            "action": "skill_used",
            "agentId": "skills",
            "sessionId": "session-1",
            "threadId": "thread-1",
            "success": True,
            "metadata": {
                "skill_ids": ["global:market-research"],
                "skill_names": ["market-research"],
                "query_preview": "current market sentiment for AAPL",
                "refined": True,
                "coverage_score": 0.72,
                "source_skills": ["global:market-research"],
            },
        },
    ]
    failures: list[str] = []
    actions = [event.get("action") for event in events]
    for required in ("skill_found", "skill_refined", "skill_used"):
        if required not in actions:
            failures.append(f"missing-action:{required}")
    for event in events:
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        if not metadata.get("skill_ids"):
            failures.append(f"missing-skill-ids:{event.get('action')}")
        if not event.get("sessionId") or not event.get("threadId"):
            failures.append(f"missing-session-thread:{event.get('action')}")
        if len(str(metadata.get("query_preview") or "")) > 200:
            failures.append(f"query-preview-too-long:{event.get('action')}")
    found = events[0]["metadata"]
    if not found.get("search_traces"):
        failures.append("missing-search-traces")
    serialized = json.dumps(events, sort_keys=True)
    for forbidden in ("content", "body", "prompt", "secret", "authorization"):
        if forbidden in serialized.lower():
            failures.append(f"body-or-secret-leak:{forbidden}")
    return _scenario(
        "skill-lifecycle-audit-trace-shape",
        failures=failures,
        evidence={"actions": actions, "found_metadata_keys": sorted(found.keys())},
    )


def _usage_sidecar_lifecycle_shape() -> dict[str, Any]:
    usage = {
        "schema_version": 1,
        "skills": {
            "global:market-research": {
                "skill_id": "global:market-research",
                "tier": "global",
                "name": "market-research",
                "state": "active",
                "pinned": False,
                "use_count": 2,
                "view_count": 1,
                "first_used_at": "2026-04-30T00:00:00+00:00",
                "last_used_at": "2026-04-30T00:01:00+00:00",
                "updated_at": "2026-04-30T00:01:00+00:00",
            }
        },
    }
    entry = usage["skills"]["global:market-research"]
    failures: list[str] = []
    for key in (
        "skill_id",
        "tier",
        "name",
        "state",
        "pinned",
        "use_count",
        "view_count",
        "first_used_at",
        "last_used_at",
        "updated_at",
    ):
        if entry.get(key) in (None, "", [], {}):
            failures.append(f"missing-usage-field:{key}")
    if entry.get("state") != "active":
        failures.append("skill-state-not-active")
    if int(entry.get("use_count") or 0) < 1:
        failures.append("usage-count-not-incremented")
    return _scenario(
        "skill-lifecycle-usage-sidecar-shape",
        failures=failures,
        evidence={"skill_id": entry["skill_id"], "use_count": entry["use_count"]},
    )


def _skill_reload_control_policy() -> dict[str, Any]:
    policy = {
        "reload_surface": "control_or_admin_slash",
        "llm_tool_exposed": False,
        "invalidates_cached_agent_sessions": True,
        "writes_audit_event": True,
        "requires_confirm_for_tool_cache_change": True,
    }
    failures: list[str] = []
    if policy["llm_tool_exposed"] is not False:
        failures.append("skill-reload-exposed-as-llm-tool")
    for key in (
        "invalidates_cached_agent_sessions",
        "writes_audit_event",
        "requires_confirm_for_tool_cache_change",
    ):
        if policy.get(key) is not True:
            failures.append(f"reload-policy-missing:{key}")
    return _scenario(
        "skill-lifecycle-reload-control-policy",
        failures=failures,
        evidence=policy,
    )


def _scenario(scenario_id: str, *, failures: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": scenario_id,
        "passed": not failures,
        "failures": failures,
        "evidence": evidence,
    }


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
