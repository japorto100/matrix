"""Keep/discard/defer decision log for Meta-Harness candidates."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

META_HARNESS_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "meta_harness"
DecisionKind = Literal["keep", "discard", "defer"]
PROPOSER_PROTECTED_KEY_FRAGMENTS = ("holdout",)


@dataclass(frozen=True)
class CandidateDecision:
    run_id: str
    candidate_id: str
    decision: DecisionKind
    rationale: str
    decided_at: str
    metrics: dict[str, Any]
    follow_up: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def record_candidate_decision(
    *,
    run_id: str,
    candidate_id: str,
    decision: DecisionKind,
    rationale: str,
    metrics: dict[str, Any] | None = None,
    follow_up: str = "",
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> CandidateDecision:
    """Append a candidate decision to the run-local and global JSONL logs."""
    if decision not in ("keep", "discard", "defer"):
        raise ValueError(f"unsupported candidate decision: {decision}")
    if not rationale.strip():
        raise ValueError("candidate decision rationale is required")

    entry = CandidateDecision(
        run_id=run_id,
        candidate_id=candidate_id,
        decision=decision,
        rationale=rationale.strip(),
        decided_at=datetime.now(UTC).isoformat(),
        metrics=dict(metrics or {}),
        follow_up=follow_up.strip(),
    )
    payload = json.dumps(entry.as_dict(), default=str, sort_keys=True)

    global_log = data_dir / "candidate_decisions.jsonl"
    run_log = data_dir / "runs" / run_id / "candidate_decisions.jsonl"
    global_log.parent.mkdir(parents=True, exist_ok=True)
    run_log.parent.mkdir(parents=True, exist_ok=True)
    with global_log.open("a", encoding="utf-8") as fh:
        fh.write(payload + "\n")
    with run_log.open("a", encoding="utf-8") as fh:
        fh.write(payload + "\n")

    candidate_dir = data_dir / "runs" / run_id / "candidates" / candidate_id
    if candidate_dir.exists():
        (candidate_dir / "decision.json").write_text(
            json.dumps(entry.as_dict(), indent=2, default=str),
            encoding="utf-8",
        )
    return entry


def load_candidate_decisions(
    *,
    data_dir: Path = META_HARNESS_DATA_DIR,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Read recent candidate decisions, newest first."""
    path = data_dir / "candidate_decisions.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    decisions: list[dict[str, Any]] = []
    for line in reversed(lines[-limit:]):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                decisions.append(item)
        except json.JSONDecodeError:
            continue
    return decisions


def sanitize_decision_for_proposer(decision: dict[str, Any]) -> dict[str, Any]:
    """Return a proposer-visible decision without protected holdout fields."""

    return _sanitize_value(decision)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested in value.items():
            if any(fragment in str(key).casefold() for fragment in PROPOSER_PROTECTED_KEY_FRAGMENTS):
                sanitized[str(key)] = "[protected]"
                continue
            sanitized[str(key)] = _sanitize_value(nested)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value
