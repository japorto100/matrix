"""Provider-backed Meta-Harness smoke gate.

The command is metadata-only by default. A real chat call is opt-in via the CLI
so static verification can run without spending provider quota.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent.llm.provider_capabilities import (
    configured_provider_snapshot,
    provider_live_gate,
)
from agent.llm_client import get_litellm_client
from meta_harness.proposer import META_HARNESS_DATA_DIR


async def run_provider_smoke(
    *,
    run_id: str | None = None,
    data_dir: Path = META_HARNESS_DATA_DIR,
    model: str | None = None,
    chat_call: bool = False,
    allow_deterministic_fake: bool = False,
) -> dict[str, Any]:
    """Run provider config gating and optionally one minimal chat completion."""

    run_id = run_id or f"run-provider-smoke-{uuid.uuid4().hex[:12]}"
    snapshot = configured_provider_snapshot(model)
    gate = provider_live_gate(
        snapshot,
        allow_deterministic_fake=allow_deterministic_fake,
    )
    result: dict[str, Any] = {
        "run_id": run_id,
        "feature_ids": ["011", "016", "020"],
        "provider_snapshot": snapshot,
        "provider_gate": gate,
        "blocked": not gate["passed"],
        "chat_requested": chat_call,
        "chat_checked": False,
        "passed": gate["passed"],
    }
    if gate["passed"] and chat_call:
        result["chat"] = await _chat_smoke(snapshot["agent_model"])
        result["chat_checked"] = True
        result["passed"] = bool(result["chat"].get("passed"))

    artifacts = _write_provider_smoke_artifacts(
        result,
        run_id=run_id,
        data_dir=data_dir,
    )
    result["artifacts"] = artifacts
    return result


async def _chat_smoke(model: str) -> dict[str, Any]:
    client = get_litellm_client()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Reply with a short health token."},
                {"role": "user", "content": "provider smoke"},
            ],
            max_tokens=16,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "error": _sanitize_error(exc),
        }
    choice = response.choices[0] if response.choices else None
    content = ""
    if choice is not None:
        message = getattr(choice, "message", None)
        content = str(getattr(message, "content", "") or "")
    return {
        "passed": bool(content.strip()),
        "model": str(getattr(response, "model", "") or model),
        "response_chars": len(content),
    }


def _write_provider_smoke_artifacts(
    result: dict[str, Any],
    *,
    run_id: str,
    data_dir: Path,
) -> dict[str, Any]:
    run_dir = data_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "kind": "provider_smoke",
        "feature_ids": result["feature_ids"],
        "provider_snapshot": result["provider_snapshot"],
        "provider_gate": result["provider_gate"],
        "chat_requested": result["chat_requested"],
        "chat_checked": result["chat_checked"],
        "passed": result["passed"],
        "blocked": result["blocked"],
    }
    _write_json(run_dir / "run.json", run_manifest)
    _write_json(run_dir / "provider_smoke.json", result)
    return {
        "run_path": str(run_dir),
        "run_manifest": str(run_dir / "run.json"),
        "provider_smoke": str(run_dir / "provider_smoke.json"),
    }


def _sanitize_error(exc: Exception) -> str:
    text = str(exc)
    replacements = ("sk-", "Bearer ")
    for marker in replacements:
        if marker in text:
            text = text.split(marker, 1)[0] + marker + "<redacted>"
    return text[:500]


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
