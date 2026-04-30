"""Paper-style iterative Meta-Harness loop for Matrix.

This module deliberately separates a true outer-loop iteration from static
contract lanes. A completed iteration must produce baseline artifacts, inspect
raw prior artifacts, create a bounded candidate envelope, run the frozen search
evaluator, record a keep/discard/defer decision and update the experience
packet/frontier artifacts.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from meta_harness.decisions import record_candidate_decision
from meta_harness.outer_loop import (
    write_candidate_manifest,
    write_experience_packet,
    write_pending_eval,
)
from meta_harness.proposer import META_HARNESS_DATA_DIR
from meta_harness.runtime_preflight import (
    ensure_runtime_preflight,
    write_runtime_preflight_artifact,
)
from meta_harness.scenario_runner import run_scenario_file

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIO_PATH = REPO_ROOT / "data" / "harness" / "memory_lifecycle" / "scenarios.json"
DEFAULT_DOMAIN_ID = "agent-runtime-memory-rag-tool-routing"
DEFAULT_WRITE_SCOPE = (
    "python-backend/agent/",
    "python-backend/memory_fusion/",
    "python-backend/rag/",
    "python-backend/kg/",
)
FROZEN_EVALUATOR_PATHS = (
    "python-backend/meta_harness/real_outer_loop.py",
    "python-backend/meta_harness/scenario_runner.py",
    "python-backend/meta_harness/outer_loop.py",
    "python-backend/meta_harness/evaluator.py",
)


@dataclass(frozen=True)
class LoopBudget:
    iterations: int
    max_scenarios: int
    provider_calls_budget: int
    max_wall_clock_minutes: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "iterations": self.iterations,
            "max_scenarios": self.max_scenarios,
            "provider_calls_budget": self.provider_calls_budget,
            "max_wall_clock_minutes": self.max_wall_clock_minutes,
        }


async def run_real_outer_loop(
    *,
    run_id: str | None = None,
    data_dir: Path = META_HARNESS_DATA_DIR,
    scenario_path: Path = DEFAULT_SCENARIO_PATH,
    iterations: int = 1,
    max_scenarios: int = 1,
    runner_variant: str = "simple",
    user_id: str = "anonymous",
    model: str = "",
    domain_id: str = DEFAULT_DOMAIN_ID,
    candidate_system_prompt: str = "",
    dry_run: bool = False,
    provider_calls_budget: int = 0,
    max_wall_clock_minutes: int = 30,
) -> dict[str, Any]:
    """Run a no-browser Meta-Harness outer loop over Matrix agent scenarios."""

    run_id = run_id or f"run-real-meta-harness-{uuid.uuid4().hex[:12]}"
    scenario_path = scenario_path if scenario_path.is_absolute() else (Path.cwd() / scenario_path)
    run_dir = data_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    runtime_preflight = ensure_runtime_preflight(command="outer-loop")
    write_runtime_preflight_artifact(
        data_dir=data_dir,
        run_id=run_id,
        result=runtime_preflight,
    )
    budget = LoopBudget(
        iterations=max(int(iterations), 0),
        max_scenarios=max(int(max_scenarios), 0),
        provider_calls_budget=max(int(provider_calls_budget), 0),
        max_wall_clock_minutes=max(int(max_wall_clock_minutes), 0),
    )
    frozen_before = _snapshot_frozen_inputs(scenario_path)
    baseline_candidate_id = "baseline"

    _write_outer_run_manifest(
        run_dir,
        run_id=run_id,
        scenario_path=scenario_path,
        domain_id=domain_id,
        budget=budget,
        runner_variant=runner_variant,
        dry_run=dry_run,
    )

    baseline = await run_scenario_file(
        scenario_path,
        max_scenarios=max_scenarios,
        run_id=run_id,
        candidate_id=baseline_candidate_id,
        user_id=user_id,
        model=model,
        runner_variant=runner_variant,
        data_dir=data_dir,
    )
    baseline_dir = data_dir / "runs" / run_id / "candidates" / baseline_candidate_id
    write_candidate_manifest(baseline_dir)

    iteration_results: list[dict[str, Any]] = []
    true_iteration = False
    for iteration in range(1, budget.iterations + 1):
        packet = write_experience_packet(
            run_id=f"{run_id}-experience-{iteration:03d}",
            data_dir=data_dir,
            limit=80,
            write_manifests=True,
        )
        inspection = _inspect_prior_artifacts(packet, data_dir=data_dir, limit=24)
        candidate_id = f"iter-{iteration:03d}-config-overlay"
        proposal = _build_deterministic_proposal(
            iteration=iteration,
            run_id=run_id,
            candidate_id=candidate_id,
            packet=packet,
            inspection=inspection,
            candidate_system_prompt=candidate_system_prompt,
        )
        candidate_dir = data_dir / "runs" / run_id / "candidates" / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        _write_json(candidate_dir / "proposal.json", proposal)
        _write_json(candidate_dir / "config_overlay.json", proposal["config_overlay"])
        _write_json(candidate_dir / "proposer_interaction.json", inspection)
        _write_text(candidate_dir / "patch.diff", "")
        pending = write_pending_eval(
            run_id=run_id,
            candidate_id=candidate_id,
            candidate_type="config_overlay",
            domain_id=domain_id,
            write_scope=list(DEFAULT_WRITE_SCOPE),
            evaluation="frozen search scenarios; holdout remains protected",
            rollback_ref=_current_git_ref(),
            data_dir=data_dir,
        )
        if dry_run:
            iteration_results.append(
                {
                    "iteration": iteration,
                    "candidate_id": candidate_id,
                    "dry_run": True,
                    "proposal": proposal,
                    "pending_eval": pending,
                    "inspection": inspection,
                }
            )
            continue

        candidate = await run_scenario_file(
            scenario_path,
            max_scenarios=max_scenarios,
            run_id=run_id,
            candidate_id=candidate_id,
            user_id=user_id,
            model=model,
            system_prompt_override=proposal["config_overlay"]["system_prompt_override"],
            runner_variant=runner_variant,
            data_dir=data_dir,
        )
        _write_json(candidate_dir / "proposal.json", proposal)
        _write_json(candidate_dir / "config_overlay.json", proposal["config_overlay"])
        _write_json(candidate_dir / "proposer_interaction.json", inspection)
        _write_json(candidate_dir / "pending_eval.json", pending)
        _write_text(candidate_dir / "patch.diff", "")
        manifest = write_candidate_manifest(candidate_dir)
        decision_payload = _decide_against_baseline(
            baseline=baseline,
            candidate=candidate,
            candidate_id=candidate_id,
            inspected_files=inspection["files_read"],
        )
        decision = record_candidate_decision(
            run_id=run_id,
            candidate_id=candidate_id,
            decision=decision_payload["decision"],
            rationale=decision_payload["rationale"],
            metrics=decision_payload["metrics"],
            follow_up=decision_payload["follow_up"],
            data_dir=data_dir,
        )
        true_iteration = True
        iteration_results.append(
            {
                "iteration": iteration,
                "candidate_id": candidate_id,
                "dry_run": False,
                "proposal": proposal,
                "pending_eval": pending,
                "candidate": _compact_eval_result(candidate),
                "manifest": manifest,
                "decision": decision.as_dict(),
                "inspection": inspection,
            }
        )

    final_packet = write_experience_packet(
        run_id=f"{run_id}-final-experience",
        data_dir=data_dir,
        limit=80,
        write_manifests=True,
    )
    frozen_after = _snapshot_frozen_inputs(scenario_path)
    frozen_gate = _compare_frozen_inputs(frozen_before, frozen_after)
    summary = {
        "run_id": run_id,
        "contract": "real-meta-harness-outer-loop/v1",
        "true_meta_harness_iteration": bool(true_iteration and frozen_gate["passed"]),
        "dry_run": dry_run,
        "domain_id": domain_id,
        "scenario_path": str(scenario_path),
        "baseline": _compact_eval_result(baseline),
        "iterations_requested": budget.iterations,
        "iterations_completed": len(iteration_results),
        "budget": budget.as_dict(),
        "roles": {
            "proposer": "deterministic Matrix proposer; Codex may inspect same artifacts",
            "simulated_user": "scenario file",
            "evaluator": "frozen scenario runner and trace gates",
            "promotion_authority": "decision ledger plus protected holdout gate",
        },
        "support_lanes_are_not_full_meta_harness": True,
        "runtime_preflight": runtime_preflight,
        "frozen_evaluator_gate": frozen_gate,
        "holdout_visible_to_proposer": False,
        "final_frontier_size": final_packet.get("frontier_size", 0),
        "iteration_results": iteration_results,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _write_json(run_dir / "real_outer_loop_summary.json", summary)
    return summary


def _write_outer_run_manifest(
    run_dir: Path,
    *,
    run_id: str,
    scenario_path: Path,
    domain_id: str,
    budget: LoopBudget,
    runner_variant: str,
    dry_run: bool,
) -> None:
    _write_json(
        run_dir / "real_outer_loop_run.json",
        {
            "run_id": run_id,
            "kind": "real_meta_harness_outer_loop",
            "contract": "real-meta-harness-outer-loop/v1",
            "created_at": datetime.now(UTC).isoformat(),
            "scenario_path": str(scenario_path),
            "domain_id": domain_id,
            "budget": budget.as_dict(),
            "runner_variant": runner_variant,
            "dry_run": dry_run,
            "holdout_visible_to_proposer": False,
            "support_lanes_are_not_full_meta_harness": True,
            "frozen_evaluator_paths": list(FROZEN_EVALUATOR_PATHS),
        },
    )


def _build_deterministic_proposal(
    *,
    iteration: int,
    run_id: str,
    candidate_id: str,
    packet: dict[str, Any],
    inspection: dict[str, Any],
    candidate_system_prompt: str,
) -> dict[str, Any]:
    actions = packet.get("next_proposer_actions") or []
    hypothesis = "Inspect raw traces and apply a bounded config overlay."
    evidence = ""
    if actions and isinstance(actions[0], dict):
        hypothesis = str(actions[0].get("hypothesis") or hypothesis)
        evidence = str(actions[0].get("evidence") or "")
    prompt = candidate_system_prompt.strip() or _default_candidate_prompt(hypothesis)
    return {
        "run_id": run_id,
        "candidate_id": candidate_id,
        "iteration": iteration,
        "candidate_type": "config_overlay",
        "created_at": datetime.now(UTC).isoformat(),
        "hypothesis": hypothesis,
        "evidence": evidence,
        "raw_artifact_inspection": {
            "files_read_count": len(inspection.get("files_read") or []),
            "artifact_classes": inspection.get("artifact_classes", []),
            "candidate_paths": inspection.get("candidate_paths", []),
        },
        "config_overlay": {
            "overlay_type": "system_prompt_override",
            "system_prompt_override": prompt,
            "provider_agnostic": True,
            "write_scope": list(DEFAULT_WRITE_SCOPE),
        },
        "self_certifies_promotion": False,
        "holdout_visible_to_proposer": False,
    }


def _default_candidate_prompt(hypothesis: str) -> str:
    return (
        "Meta-Harness candidate overlay. Preserve exact user intent, use tools "
        "only when the scenario contract requires them, keep memory writes "
        "evidence-backed, and surface RAG/KG/tool provenance in traceable form. "
        f"Current search hypothesis: {hypothesis}"
    )


def _inspect_prior_artifacts(
    packet: dict[str, Any],
    *,
    data_dir: Path,
    limit: int,
) -> dict[str, Any]:
    files_read: list[dict[str, Any]] = []
    artifact_classes: set[str] = set()
    candidate_paths: list[str] = []
    for manifest in packet.get("candidate_manifests") or []:
        if not isinstance(manifest, dict):
            continue
        candidate_path = Path(str(manifest.get("candidate_path") or ""))
        if not candidate_path.exists():
            continue
        candidate_paths.append(str(candidate_path))
        for artifact_class, rel in _artifact_refs_for_manifest(manifest):
            if len(files_read) >= limit:
                break
            path = candidate_path / rel
            if not path.exists() or not path.is_file():
                continue
            files_read.append(_read_artifact_preview(path, artifact_class, data_dir=data_dir))
            artifact_classes.add(artifact_class)
        if len(files_read) >= limit:
            break
    return {
        "contract": "proposer-interaction-log/v1",
        "proposer": "deterministic-matrix-policy",
        "created_at": datetime.now(UTC).isoformat(),
        "files_read": files_read,
        "files_read_count": len(files_read),
        "artifact_classes": sorted(artifact_classes),
        "candidate_paths": candidate_paths[:limit],
        "candidate_count_seen": len(packet.get("candidate_manifests") or []),
        "frontier_size_seen": packet.get("frontier_size", 0),
        "failure_clusters_seen": packet.get("failure_clusters", [])[:8],
        "notes": (
            "This log records raw artifact reads by the deterministic proposer. "
            "It is not a summary-only substitute."
        ),
    }


def _artifact_refs_for_manifest(manifest: dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    inventory = manifest.get("artifact_inventory") or {}
    if inventory.get("source_snapshot"):
        refs.append(("source", "source_snapshot.json"))
    if inventory.get("scores"):
        refs.append(("scores", "aggregate.json"))
        refs.append(("scores", "scores.json"))
    if inventory.get("verdicts"):
        refs.append(("verdicts", "verdicts.json"))
    if inventory.get("proposal"):
        refs.append(("proposal", "proposal.json"))
    if inventory.get("pending_eval"):
        refs.append(("pending_eval", "pending_eval.json"))
    if inventory.get("decision"):
        refs.append(("decision", "decision.json"))
    for rel in manifest.get("trace_files") or []:
        refs.append(("trace", str(rel)))
    return refs


def _read_artifact_preview(path: Path, artifact_class: str, *, data_dir: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "artifact_class": artifact_class,
        "path": str(_safe_relative(path, data_dir)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "preview": raw[:500].decode("utf-8", errors="replace"),
    }


def _decide_against_baseline(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    candidate_id: str,
    inspected_files: list[dict[str, Any]],
) -> dict[str, Any]:
    base = _metrics_from_eval(baseline)
    cand = _metrics_from_eval(candidate)
    regressions = [
        key for key in ("completion_rate", "trace_gate_pass_rate", "fitness_score")
        if cand.get(key, 0.0) < base.get(key, 0.0)
    ]
    improvements = [
        key for key in ("completion_rate", "trace_gate_pass_rate", "fitness_score")
        if cand.get(key, 0.0) > base.get(key, 0.0)
    ]
    if regressions:
        decision = "discard"
        rationale = (
            f"{candidate_id} regressed versus baseline on {', '.join(regressions)} "
            "under the frozen search evaluator."
        )
    elif improvements:
        decision = "keep"
        rationale = (
            f"{candidate_id} improved versus baseline on {', '.join(improvements)} "
            "without measured regressions under the frozen search evaluator."
        )
    else:
        decision = "defer"
        rationale = (
            f"{candidate_id} matched baseline under the frozen search evaluator; "
            "needs a stronger causal candidate before holdout."
        )
    return {
        "decision": decision,
        "rationale": rationale,
        "metrics": {
            "baseline": base,
            "candidate": cand,
            "inspected_files_count": len(inspected_files),
            "true_meta_harness_iteration": True,
        },
        "follow_up": "Inspect raw traces for next bounded candidate before holdout.",
    }


def _metrics_from_eval(result: dict[str, Any]) -> dict[str, float]:
    return {
        "completion_rate": _as_float(result.get("completion_rate")),
        "trace_gate_pass_rate": _as_float(result.get("trace_gate_pass_rate")),
        "stream_gate_pass_rate": _as_float(result.get("stream_gate_pass_rate"), 1.0),
        "fitness_score": _as_float(result.get("fitness_score")),
    }


def _compact_eval_result(result: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "candidate_id",
        "scenarios_evaluated",
        "completion_rate",
        "trace_gate_pass_rate",
        "stream_gate_pass_rate",
        "fitness_score",
        "artifact_dir",
    )
    return {key: result.get(key) for key in keys if key in result}


def _snapshot_frozen_inputs(scenario_path: Path) -> dict[str, Any]:
    paths = [scenario_path]
    paths.extend(REPO_ROOT / rel for rel in FROZEN_EVALUATOR_PATHS)
    snapshots = {}
    for path in paths:
        if not path.exists() or not path.is_file():
            snapshots[str(path)] = {"exists": False}
            continue
        raw = path.read_bytes()
        snapshots[str(path)] = {
            "exists": True,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    return snapshots


def _compare_frozen_inputs(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for path, snapshot in before.items():
        if after.get(path) != snapshot:
            changed.append(path)
    return {
        "passed": not changed,
        "changed_paths": changed,
        "checked_paths": sorted(before),
    }


def _current_git_ref() -> str:
    head = REPO_ROOT / ".git" / "HEAD"
    if not head.exists():
        return ""
    return head.read_text(encoding="utf-8").strip()


def _safe_relative(path: Path, base: Path) -> Path:
    try:
        return path.relative_to(base)
    except ValueError:
        return path


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
