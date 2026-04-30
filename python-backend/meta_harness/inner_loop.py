"""Deterministic inner-loop candidate artifacts for Feature 023.

This module is intentionally small: inner loops can search many dimensions, but
Meta-Harness should only consume explicit, typed candidates with frozen inputs.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from meta_harness.config import capture_current_config
from meta_harness.proposer import META_HARNESS_DATA_DIR
from meta_harness.retrieval_benchmark import run_retrieval_benchmark

ALLOW_PROVIDER_CALLS_ENV = "META_HARNESS_ALLOW_PROVIDER_CALLS"
MAX_PROVIDER_CALLS_ENV = "META_HARNESS_MAX_PROVIDER_CALLS"

CandidateType = Literal["config_overlay", "benchmark_candidate", "code_patch", "docs_only"]
PromotionDecision = Literal["promote_outer_loop", "discard", "defer", "needs_human_review"]

REQUIRED_CANDIDATE_FIELDS = (
    "candidate_id",
    "feature_owner",
    "candidate_type",
    "search_space_version",
    "parameters",
    "frozen_inputs",
    "budget",
)
REQUIRED_RUN_FIELDS = (
    "run_id",
    "feature_owner",
    "scenario_set",
    "train_split",
    "holdout_split",
    "candidates",
    "frozen_evaluator",
)
PROTECTED_INPUT_KEYS = (
    "golden_overrides",
    "goldens_patch",
    "holdout_results",
    "holdout_score",
    "evaluator_patch",
    "canary_patch",
    "security_relaxations",
    "tool_policy_relaxations",
    "allow_unsafe_tools",
    "disable_tool_policy",
    "prompt_injection_allowlist_patch",
)


@dataclass(frozen=True)
class InnerLoopCandidate:
    """A bounded candidate produced by a local optimizer or hand-authored sweep."""

    candidate_id: str
    feature_owner: str
    candidate_type: CandidateType
    search_space_version: str
    parameters: dict[str, Any]
    frozen_inputs: dict[str, Any]
    budget: dict[str, Any]
    metrics: dict[str, float] = field(default_factory=dict)
    source_artifacts: list[str] = field(default_factory=list)
    decision: PromotionDecision = "defer"
    decision_reason: str = "Candidate has not been promoted by the outer loop."

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "feature_owner": self.feature_owner,
            "candidate_type": self.candidate_type,
            "search_space_version": self.search_space_version,
            "parameters": self.parameters,
            "frozen_inputs": self.frozen_inputs,
            "budget": self.budget,
            "metrics": self.metrics,
            "source_artifacts": self.source_artifacts,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
        }


@dataclass(frozen=True)
class InnerLoopRun:
    """A train/holdout-aware inner-loop run convertible to Meta-Harness artifacts."""

    run_id: str
    feature_owner: str
    scenario_set: str
    train_split: str
    holdout_split: str
    candidates: list[InnerLoopCandidate]
    frozen_evaluator: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "feature_owner": self.feature_owner,
            "scenario_set": self.scenario_set,
            "train_split": self.train_split,
            "holdout_split": self.holdout_split,
            "frozen_evaluator": self.frozen_evaluator,
            "created_at": self.created_at,
            "candidates": [candidate.as_dict() for candidate in self.candidates],
        }


def validate_inner_loop_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return validation details for one inner-loop candidate payload."""

    missing = [key for key in REQUIRED_CANDIDATE_FIELDS if candidate.get(key) in (None, "")]
    failures = [f"missing-candidate-field:{key}" for key in missing]
    candidate_type = candidate.get("candidate_type")
    if candidate_type not in CandidateType.__args__:
        failures.append(f"invalid-candidate-type:{candidate_type}")
    if not isinstance(candidate.get("parameters"), dict):
        failures.append("invalid-candidate-parameters")
    if not isinstance(candidate.get("frozen_inputs"), dict):
        failures.append("invalid-candidate-frozen-inputs")
    if not isinstance(candidate.get("budget"), dict):
        failures.append("invalid-candidate-budget")
    return {"passed": not failures, "failures": failures}


def validate_inner_loop_run(run: dict[str, Any]) -> dict[str, Any]:
    """Validate run envelope and all nested candidates."""

    missing = [key for key in REQUIRED_RUN_FIELDS if run.get(key) in (None, "")]
    failures = [f"missing-run-field:{key}" for key in missing]
    candidates = run.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        failures.append("invalid-run-candidates")
        candidates = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            failures.append("invalid-candidate-payload")
            continue
        failures.extend(validate_inner_loop_candidate(candidate)["failures"])
    protected_gate = protected_input_gate(run)
    failures.extend(protected_gate["failures"])
    return {"passed": not failures, "failures": failures}


def protected_input_gate(run: dict[str, Any]) -> dict[str, Any]:
    """Ensure inner-loop candidates cannot train on holdout or mutate goldens."""

    failures: list[str] = []
    frozen_evaluator = run.get("frozen_evaluator")
    if not isinstance(frozen_evaluator, dict):
        frozen_evaluator = {}
    if frozen_evaluator.get("goldens_mutable") is not False:
        failures.append("goldens-mutable-or-unspecified")

    candidates = run.get("candidates")
    if not isinstance(candidates, list):
        candidates = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(candidate.get("candidate_id") or "unknown")
        for section_name in ("parameters", "frozen_inputs", "metrics"):
            section = candidate.get(section_name)
            if not isinstance(section, dict):
                continue
            for key in PROTECTED_INPUT_KEYS:
                if key in section:
                    failures.append(
                        f"protected-input:{candidate_id}:{section_name}.{key}"
                    )
    return {
        "passed": not failures,
        "failures": failures,
        "protected_keys": list(PROTECTED_INPUT_KEYS),
    }


async def run_deterministic_rag_inner_loop(
    *,
    run_id: str | None = None,
    data_dir: Path = META_HARNESS_DATA_DIR,
    k: int = 5,
    token_budget: int = 1600,
    max_hits: int = 8,
    provider_calls_budget: int = 0,
) -> dict[str, Any]:
    """Run the current deterministic retrieval sweep and write Feature 023 artifacts."""

    provider_gate = provider_call_gate(provider_calls_budget)
    if not provider_gate["allowed"]:
        return {
            "run_id": run_id or "",
            "blocked": True,
            "provider_gate": provider_gate,
            "candidates": [],
        }
    run_id = run_id or f"run-inner-loop-rag-{uuid.uuid4().hex[:12]}"
    benchmark = await run_retrieval_benchmark(
        run_id=f"{run_id}-retrieval",
        data_dir=data_dir,
        k=k,
        token_budget=token_budget,
        max_hits=max_hits,
    )
    candidates = [
        _candidate_from_retrieval_result(
            result,
            benchmark["run_id"],
            k=k,
            token_budget=token_budget,
            max_hits=max_hits,
        )
        for result in benchmark["report"].get("candidates", [])
        if isinstance(result, dict)
    ]
    inner_run = InnerLoopRun(
        run_id=run_id,
        feature_owner="023-auto-optimization-inner-loops",
        scenario_set="matrix-retrieval-canaries@2026-04-27",
        train_split="search/deterministic-fixture",
        holdout_split="holdout/protected",
        candidates=candidates,
        frozen_evaluator={
            "type": "retrieval_benchmark",
            "source_run_id": benchmark["run_id"],
            "metrics": ["pass_rate", f"recall@{k}", f"ndcg@{k}", "latency_ms_avg"],
            "goldens_mutable": False,
        },
    )
    return write_inner_loop_artifacts(
        inner_run,
        data_dir=data_dir,
        linked_artifacts=benchmark["artifacts"],
        provider_gate=provider_gate,
    )


def provider_call_gate(requested_calls: int) -> dict[str, Any]:
    """Block live-provider loops unless quota settings explicitly allow them."""

    requested = max(int(requested_calls or 0), 0)
    allow = _truthy_env(ALLOW_PROVIDER_CALLS_ENV)
    max_calls = _int_env(MAX_PROVIDER_CALLS_ENV, 0)
    if requested <= 0:
        return {
            "allowed": True,
            "requested_calls": requested,
            "max_calls": max_calls,
            "mode": "deterministic",
        }
    if not allow:
        return {
            "allowed": False,
            "requested_calls": requested,
            "max_calls": max_calls,
            "reason": f"{ALLOW_PROVIDER_CALLS_ENV} is not enabled",
        }
    if requested > max_calls:
        return {
            "allowed": False,
            "requested_calls": requested,
            "max_calls": max_calls,
            "reason": f"requested provider calls exceed {MAX_PROVIDER_CALLS_ENV}",
        }
    return {
        "allowed": True,
        "requested_calls": requested,
        "max_calls": max_calls,
        "mode": "live-provider",
    }


def write_inner_loop_artifacts(
    inner_run: InnerLoopRun,
    *,
    data_dir: Path = META_HARNESS_DATA_DIR,
    linked_artifacts: dict[str, Any] | None = None,
    provider_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write an inner-loop run and one Meta-Harness-compatible candidate folder."""

    payload = inner_run.as_dict()
    validation = validate_inner_loop_run(payload)
    protected_gate = protected_input_gate(payload)
    run_dir = data_dir / "runs" / inner_run.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": inner_run.run_id,
            "created_at": inner_run.created_at,
            "kind": "inner_loop",
            "feature_id": "023",
            "feature_owner": inner_run.feature_owner,
            "validation": validation,
            "protected_inputs": protected_gate,
            "linked_artifacts": linked_artifacts or {},
            "provider_gate": provider_gate or provider_call_gate(0),
        },
    )
    _write_json(run_dir / "inner_loop.json", payload)

    written: list[dict[str, Any]] = []
    for candidate in inner_run.candidates:
        candidate_dir = run_dir / "candidates" / candidate.candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        aggregate = _candidate_aggregate(inner_run.run_id, candidate)
        verdicts = {
            "passed": validation["passed"] and candidate.decision != "discard",
            "validation": validate_inner_loop_candidate(candidate.as_dict()),
            "decision": candidate.decision,
            "decision_reason": candidate.decision_reason,
            "observed_actions": ["inner_loop_candidate"],
            "observed_tools": [],
        }
        _write_json(candidate_dir / "inner_loop_candidate.json", candidate.as_dict())
        _write_json(candidate_dir / "aggregate.json", aggregate)
        _write_json(candidate_dir / "scores.json", aggregate)
        _write_json(candidate_dir / "verdicts.json", verdicts)
        _write_json(candidate_dir / "config.json", _config_snapshot())
        _write_json(candidate_dir / "source_snapshot.json", _source_snapshot(candidate))
        try:
            from meta_harness.outer_loop import write_candidate_manifest

            write_candidate_manifest(candidate_dir)
        except Exception as exc:  # noqa: BLE001
            _write_json(candidate_dir / "candidate_manifest_error.json", {"error": str(exc)})
        written.append(
            {
                "candidate_id": candidate.candidate_id,
                "candidate_path": str(candidate_dir),
                "decision": candidate.decision,
                "fitness_score": aggregate["fitness_score"],
            }
        )

    return {
        "run_id": inner_run.run_id,
        "validation": validation,
        "run_path": str(run_dir),
        "candidates": written,
    }


def _candidate_from_retrieval_result(
    result: dict[str, Any],
    source_run_id: str,
    *,
    k: int = 5,
    token_budget: int = 1600,
    max_hits: int = 8,
) -> InnerLoopCandidate:
    candidate_id = str(result.get("candidate_id") or "unknown")
    pass_rate = _as_float(result.get("pass_rate"))
    recall = _as_float(result.get("recall@5"))
    ndcg = _as_float(result.get("ndcg@5"))
    latency = _as_float(result.get("latency_ms_avg"))
    score = round((pass_rate * 0.5) + (recall * 0.3) + (ndcg * 0.2), 4)
    decision: PromotionDecision = "promote_outer_loop" if pass_rate >= 1.0 else "defer"
    reason = (
        "Promote as deterministic retrieval baseline candidate."
        if decision == "promote_outer_loop"
        else "Needs more canary coverage before outer-loop promotion."
    )
    question_classes = _question_classes(result)
    canary_tags = _canary_tags(result)
    return InnerLoopCandidate(
        candidate_id=f"inner-{candidate_id}",
        feature_owner="019-hybrid-rag-retrieval",
        candidate_type="benchmark_candidate",
        search_space_version="rag-retrieval-modes/v1",
        parameters={
            "retrieval_candidate_id": candidate_id,
            "mode": result.get("mode"),
            "include_vector": bool(result.get("include_vector")),
            "include_kg": bool(result.get("include_kg")),
            "top_k": int(k),
            "token_budget": int(token_budget),
            "max_hits": int(max_hits),
            "fusion": "rrf" if bool(result.get("include_vector")) and bool(result.get("include_kg")) else "single",
            "context_bubble": {
                "max_hits": int(max_hits),
                "token_budget": int(token_budget),
                "diversity_gate": "enabled",
            },
            "candidate_search_spaces": _candidate_search_spaces(
                result,
                top_k=int(k),
                token_budget=int(token_budget),
                max_hits=int(max_hits),
            ),
            "security_invariants": {
                "protected_input_keys": list(PROTECTED_INPUT_KEYS),
                "tool_policy_can_only_tighten": True,
                "prompt_injection_scan_required": True,
                "human_confirm_policy_relaxation_required": True,
            },
        },
        frozen_inputs={
            "source_run_id": source_run_id,
            "canary_count": int(result.get("count") or 0),
            "split_summary": result.get("split_summary") or {},
            "holdout_pass_rate": result.get("holdout_pass_rate"),
            "metadata": result.get("metadata") or {},
            "question_classes": question_classes,
            "canary_tags": canary_tags,
        },
        budget={
            "provider_calls": 0,
            "top_k": int(k),
            "max_hits": int(max_hits),
            "token_budget": int(token_budget),
        },
        metrics={
            "pass_rate": pass_rate,
            "recall@5": recall,
            "ndcg@5": ndcg,
            "latency_ms_avg": latency,
            "fitness_score": score,
        },
        source_artifacts=[source_run_id],
        decision=decision,
        decision_reason=reason,
    )


def _question_classes(result: dict[str, Any]) -> list[str]:
    classes = {
        str(item.get("question_class"))
        for item in result.get("results", [])
        if isinstance(item, dict) and item.get("question_class")
    }
    return sorted(classes)


def _canary_tags(result: dict[str, Any]) -> list[str]:
    tags: set[str] = set()
    for item in result.get("results", []):
        if not isinstance(item, dict):
            continue
        raw_tags = item.get("tags")
        if isinstance(raw_tags, list | tuple):
            tags.update(str(tag) for tag in raw_tags if str(tag))
    return sorted(tags)


def _candidate_search_spaces(
    result: dict[str, Any],
    *,
    top_k: int,
    token_budget: int,
    max_hits: int,
) -> dict[str, Any]:
    """Return bounded cross-feature knobs represented by this candidate."""

    question_classes = set(_question_classes(result))
    tags = set(_canary_tags(result))
    spaces: dict[str, Any] = {
        "retrieval": {
            "modes": [str(result.get("mode") or "auto")],
            "top_k": [top_k],
            "token_budget": [token_budget],
            "max_hits": [max_hits],
            "fusion": (
                ["rrf"]
                if bool(result.get("include_vector")) and bool(result.get("include_kg"))
                else ["single"]
            ),
            "citation_verifier": ["required"],
        },
        "tool_policy": {
            "selection_policy": ["current_catalog_only"],
            "discovery_policy": ["regex_bm25_rrf_visible_descriptors"],
            "descriptor_risk_gate": ["same_or_stricter"],
            "token_passthrough": ["deny"],
            "prompt_injection_scan": ["required"],
            "confirm_unavailable": ["fail_closed"],
        },
        "memory_context": {
            "recall_provider_blend": ["hindsight+mempalace"],
            "query_gate": ["default_evidence_terms"],
            "pre_save_threshold": [0.8],
            "compaction_threshold": [0.85, 0.95],
            "injection_order": ["system_context_then_memory_then_rag"],
            "decay_policy": ["current_decay_metadata"],
            "evidence_trace_required": [
                "source_status",
                "raw_evidence_ref",
                "operation_log_id",
                "diff_ref",
            ],
        },
        "skills": {
            "trigger_threshold": ["current_bm25_dense_rrf"],
            "max_selected_skills": [3, 5],
            "usage_evidence": ["prompt_usage", "view_count"],
            "pinned_write_fence": ["preserve"],
            "archive_import_overwrite": ["refuse_when_pinned"],
            "mutation_policy": ["recommend_only"],
        },
        "runner": {
            "variants": ["dispatcher", "langgraph", "simple"],
            "timeout_seconds": [60, 120],
            "max_iterations": [4, 8],
            "max_output_tokens": [2048, 4096],
            "approval_interrupts": ["preserve"],
            "confirm_unavailable": ["fail_closed"],
            "duplicate_tool_messages": ["prevent"],
        },
        "kg": {
            "projection_backend": ["off", "postgres", "nornicdb"],
            "path_expansion_depth": [1, 2],
            "temporal_filter": ["valid_current", "valid_at_question_time"],
            "decay": ["access_recency_validity"],
            "fusion_weight": [0.25, 0.5, 0.75],
            "semantic_term_ids_required": True,
            "promoted_claim_evidence_required": [
                "source_ref",
                "citation_or_source_or_hash",
            ],
        },
    }
    if "semantic_term_grounded" in question_classes or "semantic-layer" in tags:
        spaces["semantic_layer"] = {
            "term_filter_modes": ["exact_term_id", "approved_alias_expansion"],
            "ambiguity_thresholds": [0.72, 0.82, 0.9],
            "correction_routing": ["review_required"],
            "gold_catalog_mutable": False,
        }
    if "visual_layout_grounded" in question_classes or "visual-layout" in tags:
        spaces["visual_memory"] = {
            "min_ocr_confidence": [0.75, 0.9],
            "coordinate_policy": ["require_page_bbox"],
            "injection_threshold": [0.6, 0.8],
            "stale_evidence_policy": ["age_and_source_required"],
        }
    if "report_grounding" in question_classes or "report-grounding" in tags:
        spaces["report_grounding"] = {
            "renderer_candidates": ["markdown-fallback", "quarkdown-experimental"],
            "citation_policy": ["manifest_required"],
            "artifact_handoff": ["link_or_attachment"],
            "inline_rendering": ["feature_030_only"],
        }
    if "source-grounding" in tags:
        spaces["source_grounding"] = {
            "required_reference_metadata": [
                "source_artifact_id",
                "chunk_id",
                "chunk_hash",
                "citation_ref",
            ],
            "metadata_enrichment": ["required"],
            "citation_markers": ["required_when_answer_generated"],
        }
    return spaces


def _candidate_aggregate(run_id: str, candidate: InnerLoopCandidate) -> dict[str, Any]:
    fitness = _as_float(candidate.metrics.get("fitness_score"))
    return {
        "run_id": run_id,
        "candidate_id": candidate.candidate_id,
        "benchmark_type": "inner_loop",
        "feature_owner": candidate.feature_owner,
        "candidate_type": candidate.candidate_type,
        "scenarios_evaluated": int(candidate.frozen_inputs.get("canary_count") or 0),
        "completion_rate": 1.0,
        "fitness_score": fitness,
        "trace_gate_pass_rate": _as_float(candidate.metrics.get("pass_rate"), 1.0),
        "tool_success_rate": 1.0,
        "retrieval_pass_rate": _as_float(candidate.metrics.get("pass_rate")),
        "recall@5": _as_float(candidate.metrics.get("recall@5")),
        "ndcg@5": _as_float(candidate.metrics.get("ndcg@5")),
        "avg_turns": 1.0,
        "avg_duration_ms": _as_float(candidate.metrics.get("latency_ms_avg")),
        "total_cost_usd": 0.0,
        "total_tokens": 0,
        "token_efficiency": 1000.0,
        "cost_efficiency": 1.0,
        "decision": candidate.decision,
    }


def _source_snapshot(candidate: InnerLoopCandidate) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    files = []
    for rel in (
        "python-backend/meta_harness/inner_loop.py",
        "python-backend/meta_harness/retrieval_benchmark.py",
        "python-backend/retrieval/evals/benchmark_lab.py",
    ):
        path = root / rel
        if path.exists():
            files.append({"path": rel, "bytes": path.stat().st_size})
    return {
        "feature_owner": candidate.feature_owner,
        "source_artifacts": candidate.source_artifacts,
        "files": files,
    }


def _config_snapshot() -> dict[str, Any]:
    try:
        return json.loads(capture_current_config().to_json())
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _int_env(name: str, default: int) -> int:
    try:
        return int(str(os.environ.get(name, "")).strip() or default)
    except ValueError:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
