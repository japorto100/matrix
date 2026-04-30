"""Paper-aligned Meta-Harness outer-loop artifacts.

Meta-Harness works when a proposer can inspect executable candidate history:
source references, scores, raw execution traces and decisions. This module keeps
that experience navigable without letting the proposer self-certify promotion.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from meta_harness.pareto import compute_pareto_frontier
from meta_harness.proposer import META_HARNESS_DATA_DIR

PAPER_REF = "docs/Meta-Harness-2603.28052v1.md"
PAPER_ARXIV_ID = "2603.28052v1"
ALLOWED_CANDIDATE_TYPES = frozenset(
    {
        "benchmark_candidate",
        "bounded_code_patch",
        "code_patch",
        "config_overlay",
        "docs_only",
        "inner_loop_candidate",
        "policy_overlay",
        "prompt_policy_change",
    }
)


@dataclass(frozen=True)
class CandidateInventory:
    """Filesystem inventory for one evaluated candidate."""

    run_id: str
    candidate_id: str
    candidate_path: str
    has_run_manifest: bool
    has_config: bool
    has_source_snapshot: bool
    has_scores: bool
    has_verdicts: bool
    has_raw_traces: bool
    has_sse: bool
    has_results: bool
    has_proposal: bool
    has_pending_eval: bool
    has_decision: bool
    benchmark_artifacts: tuple[str, ...] = ()
    trace_files: tuple[str, ...] = ()
    trace_event_count: int = 0
    trace_quality_failures: tuple[str, ...] = ()
    result_files: tuple[str, ...] = ()
    source_files: tuple[dict[str, Any], ...] = ()
    candidate_type: str = "benchmark_candidate"
    paper_failures: tuple[str, ...] = field(default_factory=tuple)

    @property
    def paper_ready(self) -> bool:
        return not self.paper_failures

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "candidate_path": self.candidate_path,
            "candidate_type": self.candidate_type,
            "paper_ready": self.paper_ready,
            "paper_failures": list(self.paper_failures),
            "artifact_inventory": {
                "run_manifest": self.has_run_manifest,
                "config": self.has_config,
                "source_snapshot": self.has_source_snapshot,
                "scores": self.has_scores,
                "verdicts": self.has_verdicts,
                "raw_traces": self.has_raw_traces,
                "sse": self.has_sse,
                "results": self.has_results,
                "proposal": self.has_proposal,
                "pending_eval": self.has_pending_eval,
                "decision": self.has_decision,
                "benchmark_artifacts": list(self.benchmark_artifacts),
            },
            "trace_files": list(self.trace_files),
            "trace_event_count": self.trace_event_count,
            "trace_quality_failures": list(self.trace_quality_failures),
            "result_files": list(self.result_files),
            "source_files": list(self.source_files),
            "roles": {
                "proposer": "Codex or explicitly enabled external proposer",
                "simulated_user": "scenario fixtures/search-set driver",
                "evaluator": "frozen Meta-Harness runner and trace gates",
                "promotion_authority": "Pareto frontier plus explicit decision/holdout gates",
            },
            "paper_mapping": {
                "paper_ref": PAPER_REF,
                "arxiv_id": PAPER_ARXIV_ID,
                "source_code": "source_snapshot.source_files or repository paths",
                "scores": "scores.json or aggregate.json",
                "execution_traces": "traces/**/*.json plus sse/*.jsonl when available",
                "test_leakage_policy": "holdout paths and scores are excluded from proposer packets",
            },
        }


def build_candidate_inventory(candidate_dir: Path) -> CandidateInventory:
    """Inspect one candidate directory and return paper-readiness metadata."""

    run_dir = candidate_dir.parents[1]
    run_id = run_dir.name
    candidate_id = candidate_dir.name
    trace_files = tuple(
        str(path.relative_to(candidate_dir))
        for path in sorted((candidate_dir / "traces").glob("**/*.json"))
        if path.is_file()
    )
    result_files = tuple(
        str(path.relative_to(candidate_dir))
        for path in sorted((candidate_dir / "results").glob("*.json"))
        if path.is_file()
    )
    benchmark_artifacts = tuple(
        name
        for name in (
            "retrieval_benchmark.json",
            "extraction_benchmark.json",
            "inner_loop_candidate.json",
            "knowledge_contract.json",
            "domain_contract.json",
        )
        if (candidate_dir / name).exists()
    )
    source_snapshot = _load_json(candidate_dir / "source_snapshot.json")
    source_files = _source_files_from_snapshot(source_snapshot)
    candidate_type = _infer_candidate_type(candidate_dir, benchmark_artifacts)
    trace_event_count, trace_quality_failures = _trace_quality(candidate_dir, trace_files)
    failures = _paper_failures(
        candidate_dir,
        has_run_manifest=(run_dir / "run.json").exists(),
        has_source_snapshot=(candidate_dir / "source_snapshot.json").exists(),
        has_scores=(candidate_dir / "scores.json").exists()
        or (candidate_dir / "aggregate.json").exists(),
        has_trace_or_benchmark=bool(trace_files or benchmark_artifacts),
        trace_quality_failures=trace_quality_failures,
        candidate_type=candidate_type,
    )
    return CandidateInventory(
        run_id=run_id,
        candidate_id=candidate_id,
        candidate_path=str(candidate_dir),
        has_run_manifest=(run_dir / "run.json").exists(),
        has_config=(candidate_dir / "config.json").exists(),
        has_source_snapshot=(candidate_dir / "source_snapshot.json").exists(),
        has_scores=(candidate_dir / "scores.json").exists()
        or (candidate_dir / "aggregate.json").exists(),
        has_verdicts=(candidate_dir / "verdicts.json").exists(),
        has_raw_traces=bool(trace_files),
        has_sse=any((candidate_dir / "sse").glob("*.jsonl")),
        has_results=bool(result_files) or (candidate_dir / "result.json").exists(),
        has_proposal=(candidate_dir / "proposal.json").exists(),
        has_pending_eval=(candidate_dir / "pending_eval.json").exists(),
        has_decision=(candidate_dir / "decision.json").exists(),
        benchmark_artifacts=benchmark_artifacts,
        trace_files=trace_files,
        trace_event_count=trace_event_count,
        trace_quality_failures=tuple(trace_quality_failures),
        result_files=result_files,
        source_files=source_files,
        candidate_type=candidate_type,
        paper_failures=tuple(failures),
    )


def write_candidate_manifest(candidate_dir: Path) -> dict[str, Any]:
    """Write `candidate_manifest.json` for one candidate directory."""

    manifest = build_candidate_inventory(candidate_dir).as_dict()
    (candidate_dir / "candidate_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return manifest


def build_experience_packet(
    *,
    data_dir: Path = META_HARNESS_DATA_DIR,
    limit: int = 40,
    write_manifests: bool = False,
) -> dict[str, Any]:
    """Build a proposer-facing packet from prior candidates.

    The packet intentionally contains search-set and candidate-history artifacts,
    not holdout results. It points to raw files instead of summarizing away the
    trace evidence the proposer should inspect.
    """

    candidates = _load_candidate_metrics(data_dir)
    frontier = compute_pareto_frontier(candidates)
    frontier_versions = {str(candidate.get("version") or "") for candidate in frontier}
    candidate_dirs = _recent_candidate_dirs(data_dir, limit=limit)
    manifests = [
        write_candidate_manifest(path) if write_manifests else build_candidate_inventory(path).as_dict()
        for path in candidate_dirs
    ]
    failure_clusters = _failure_clusters(candidate_dirs)
    decisions = _load_decisions(data_dir, limit=limit)
    inner_loop = _inner_loop_bridge(candidate_dirs)
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "paper_ref": PAPER_REF,
        "arxiv_id": PAPER_ARXIV_ID,
        "data_dir": str(data_dir),
        "roles": {
            "proposer": "Codex in this session unless external LLM is explicitly enabled",
            "simulated_user": "search-set scenario runner generating user turns and traces",
            "evaluator": "frozen CLI lanes, trace gates and Pareto calculation",
        },
        "holdout_policy": {
            "visible_to_proposer": False,
            "allowed_in_packet": False,
            "promotion_requires_explicit_holdout_gate": True,
        },
        "candidate_count": len(candidates),
        "frontier_size": len(frontier),
        "frontier": [_frontier_entry(candidate) for candidate in frontier],
        "dominated_versions": [
            str(candidate.get("version") or "")
            for candidate in candidates
            if str(candidate.get("version") or "") not in frontier_versions
        ],
        "candidate_manifests": manifests,
        "paper_readiness": _paper_readiness(manifests),
        "failure_clusters": failure_clusters,
        "decisions": decisions,
        "inner_loop_bridge": inner_loop,
        "autoresearch_bridge": {
            "fixed_evaluator_required": True,
            "one_run_log_required": True,
            "keep_discard_defer_required": True,
            "evaluator_mutation_during_run_forbidden": True,
            "rollback_on_regression_required": True,
        },
        "next_proposer_actions": _next_proposer_actions(failure_clusters, inner_loop),
    }


def write_experience_packet(
    *,
    run_id: str,
    data_dir: Path = META_HARNESS_DATA_DIR,
    limit: int = 40,
    write_manifests: bool = True,
) -> dict[str, Any]:
    """Write a paper-style outer-loop experience packet under `runs/<run_id>`."""

    packet = build_experience_packet(
        data_dir=data_dir,
        limit=limit,
        write_manifests=write_manifests,
    )
    run_dir = data_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = {
        "run_id": run_id,
        "kind": "outer_loop_experience_packet",
        "created_at": packet["created_at"],
        "paper_ref": PAPER_REF,
        "candidate_count": packet["candidate_count"],
        "frontier_size": packet["frontier_size"],
        "holdout_visible_to_proposer": False,
    }
    (run_dir / "run.json").write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    (run_dir / "experience_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return {"run_id": run_id, "run_path": str(run_dir), **packet}


def write_pending_eval(
    *,
    run_id: str,
    candidate_id: str,
    candidate_type: str,
    domain_id: str,
    write_scope: list[str],
    evaluation: str,
    rollback_ref: str = "",
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> dict[str, Any]:
    """Write a frozen pending-evaluation envelope for a candidate."""

    candidate_dir = data_dir / "runs" / run_id / "candidates" / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "domain_id": domain_id,
        "write_scope": write_scope,
        "evaluation": evaluation,
        "rollback_ref": rollback_ref,
        "created_at": datetime.now(UTC).isoformat(),
        "frozen_evaluator_required": True,
        "holdout_visible_to_proposer": False,
        "proposer_self_certification_allowed": False,
    }
    (candidate_dir / "pending_eval.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    write_candidate_manifest(candidate_dir)
    return payload


def promotion_gate(
    *,
    run_id: str,
    candidate_id: str,
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> dict[str, Any]:
    """Fail-closed promotion preflight for a candidate.

    This does not promote by itself. It verifies that the candidate has the
    paper-required artifacts plus search, holdout and safety evidence.
    """

    candidate_dir = data_dir / "runs" / run_id / "candidates" / candidate_id
    manifest = write_candidate_manifest(candidate_dir)
    aggregate = _load_json(candidate_dir / "aggregate.json")
    if not isinstance(aggregate, dict):
        aggregate = _load_json(candidate_dir / "scores.json")
    if not isinstance(aggregate, dict):
        aggregate = {}
    pending_eval = _load_json(candidate_dir / "pending_eval.json")
    holdout = _load_json(candidate_dir / "holdout.json") or _load_json(
        candidate_dir / "holdout_verdict.json"
    )
    safety = _load_json(candidate_dir / "safety.json") or _load_json(
        candidate_dir / "safety_verdict.json"
    )
    failures = []
    if not manifest.get("paper_ready"):
        failures.extend(str(item) for item in manifest.get("paper_failures") or [])
    if not isinstance(pending_eval, dict):
        failures.append("missing-pending-eval")
    if _as_float(aggregate.get("completion_rate")) < 1.0:
        failures.append("search-completion-rate-below-1.0")
    if _as_float(aggregate.get("trace_gate_pass_rate")) < 1.0:
        failures.append("search-trace-gate-pass-rate-below-1.0")
    if _as_float(aggregate.get("stream_gate_pass_rate"), default=1.0) < 1.0:
        failures.append("search-stream-gate-pass-rate-below-1.0")
    if not isinstance(holdout, dict):
        failures.append("missing-holdout-verdict")
    elif _as_float(holdout.get("trace_gate_pass_rate")) < 1.0 or _as_float(
        holdout.get("completion_rate")
    ) < 1.0:
        failures.append("holdout-gates-not-passing")
    elif _as_float(holdout.get("stream_gate_pass_rate"), default=1.0) < 1.0:
        failures.append("holdout-stream-gates-not-passing")
    if not isinstance(safety, dict):
        failures.append("missing-safety-verdict")
    elif safety.get("passed") is not True:
        failures.append("safety-verdict-not-passing")
    return {
        "run_id": run_id,
        "candidate_id": candidate_id,
        "passed": not failures,
        "failures": failures,
        "candidate_path": str(candidate_dir),
        "paper_ready": bool(manifest.get("paper_ready")),
        "search_metrics": {
            "completion_rate": aggregate.get("completion_rate"),
            "trace_gate_pass_rate": aggregate.get("trace_gate_pass_rate"),
            "stream_gate_pass_rate": aggregate.get("stream_gate_pass_rate"),
            "fitness_score": aggregate.get("fitness_score"),
        },
    }


def _load_candidate_metrics(data_dir: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for candidate_dir in sorted((data_dir / "runs").glob("*/candidates/*")):
        if not candidate_dir.is_dir():
            continue
        payload = _load_json(candidate_dir / "aggregate.json")
        if not isinstance(payload, dict):
            payload = _load_json(candidate_dir / "scores.json")
        if not isinstance(payload, dict):
            continue
        entry = dict(payload)
        entry.setdefault("run_id", candidate_dir.parents[1].name)
        entry.setdefault("candidate_id", candidate_dir.name)
        entry["version"] = f"{candidate_dir.parents[1].name}:{candidate_dir.name}"
        entry["candidate_path"] = str(candidate_dir)
        entry.setdefault("source", "meta_harness")
        candidates.append(_normalize_for_pareto(entry))
    return candidates


def _normalize_for_pareto(entry: dict[str, Any]) -> dict[str, Any]:
    turns = _as_float(entry.get("avg_turns") or entry.get("turns"), 10.0)
    tokens = _as_float(entry.get("avg_tokens") or entry.get("total_tokens"), 100000.0)
    cost = _as_float(entry.get("total_cost_usd") or entry.get("cost_usd"), 0.0)
    duration_ms = _as_float(
        entry.get("avg_duration_ms") or entry.get("total_duration_ms"),
        0.0,
    )
    entry.setdefault("turn_efficiency", round(1.0 / max(turns, 1.0), 4))
    entry.setdefault("token_efficiency", round(1000.0 / max(tokens, 1.0), 6))
    entry.setdefault("cost_efficiency", round(1.0 / (1.0 + max(cost, 0.0)), 6))
    entry.setdefault(
        "latency_efficiency",
        round(1000.0 / max(duration_ms, 1.0), 6) if duration_ms > 0 else 1.0,
    )
    entry.setdefault("trace_gate_pass_rate", 0.0)
    entry.setdefault("stream_gate_pass_rate", 1.0)
    entry.setdefault("completion_rate", 0.0)
    entry.setdefault("fitness_score", entry.get("avg_fitness_score", 0.0))
    entry.setdefault("tool_success_rate", 0.0)
    return entry


def _recent_candidate_dirs(data_dir: Path, *, limit: int) -> list[Path]:
    runs_dir = data_dir / "runs"
    if not runs_dir.exists():
        return []
    return sorted(
        (path for path in runs_dir.glob("*/candidates/*") if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:limit]


def _source_files_from_snapshot(snapshot: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(snapshot, dict):
        return ()
    raw_files = snapshot.get("source_files") or snapshot.get("files") or []
    if not isinstance(raw_files, list):
        return ()
    files = []
    for item in raw_files:
        if isinstance(item, dict):
            files.append(dict(item))
        elif item:
            files.append({"path": str(item)})
    return tuple(files)


def _infer_candidate_type(candidate_dir: Path, benchmark_artifacts: tuple[str, ...]) -> str:
    manifest = _load_json(candidate_dir / "candidate_manifest.json")
    if isinstance(manifest, dict) and manifest.get("candidate_type"):
        return str(manifest["candidate_type"])
    if "inner_loop_candidate.json" in benchmark_artifacts:
        return "inner_loop_candidate"
    if benchmark_artifacts:
        return "benchmark_candidate"
    if (candidate_dir / "proposal.json").exists():
        return "config_overlay"
    if (candidate_dir / "patch.diff").exists() or (candidate_dir / "diff.patch").exists():
        return "code_patch"
    return "benchmark_candidate"


def _paper_failures(
    candidate_dir: Path,
    *,
    has_run_manifest: bool,
    has_source_snapshot: bool,
    has_scores: bool,
    has_trace_or_benchmark: bool,
    trace_quality_failures: list[str],
    candidate_type: str,
) -> list[str]:
    failures: list[str] = []
    if candidate_type not in ALLOWED_CANDIDATE_TYPES:
        failures.append(f"invalid-candidate-type:{candidate_type}")
    if not has_run_manifest:
        failures.append("missing-run-manifest")
    if not has_source_snapshot:
        failures.append("missing-source-snapshot")
    if not has_scores:
        failures.append("missing-scores")
    if not has_trace_or_benchmark:
        failures.append("missing-raw-traces-or-benchmark-artifact")
    failures.extend(trace_quality_failures)
    if _contains_holdout_result(candidate_dir):
        failures.append("holdout-result-visible-to-proposer")
    return failures


def _contains_holdout_result(candidate_dir: Path) -> bool:
    for path in candidate_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(candidate_dir)).casefold()
        if "holdout" in rel and path.suffix in {".json", ".jsonl", ".md"}:
            return True
        if path.suffix in {".json", ".jsonl"} and _json_payload_has_holdout_key(path):
            return True
    return False


def _trace_quality(candidate_dir: Path, trace_files: tuple[str, ...]) -> tuple[int, list[str]]:
    if not trace_files:
        return 0, []
    event_count = 0
    failures: list[str] = []
    for rel in trace_files:
        data = _load_json(candidate_dir / rel)
        if not isinstance(data, list):
            failures.append(f"trace-invalid-json-list:{rel}")
            continue
        events = [event for event in data if isinstance(event, dict)]
        event_count += len(events)
    if event_count <= 0:
        failures.append("trace-empty")
    return event_count, failures


def _json_payload_has_holdout_key(path: Path) -> bool:
    payload = _load_json(path)
    return _contains_key_fragment(payload, "holdout")


def _contains_key_fragment(value: Any, fragment: str) -> bool:
    safe_policy_keys = {
        "holdout_visible_to_proposer",
        "holdout_policy",
        "promotion_requires_explicit_holdout_gate",
        "allow_holdout",
    }
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = str(key).casefold()
            if normalized_key in safe_policy_keys:
                continue
            if fragment in normalized_key:
                return True
            if _contains_key_fragment(nested, fragment):
                return True
    elif isinstance(value, list):
        return any(_contains_key_fragment(item, fragment) for item in value)
    return False


def _failure_clusters(candidate_dirs: list[Path]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for candidate_dir in candidate_dirs:
        for failure in _candidate_failures(candidate_dir):
            counts[failure] += 1
            examples.setdefault(failure, []).append(str(candidate_dir))
    return [
        {
            "failure": failure,
            "count": count,
            "example_candidate_paths": examples.get(failure, [])[:5],
        }
        for failure, count in counts.most_common()
    ]


def _candidate_failures(candidate_dir: Path) -> list[str]:
    failures: list[str] = []
    for name in ("aggregate.json", "verdicts.json"):
        payload = _load_json(candidate_dir / name)
        if not isinstance(payload, dict):
            continue
        for failure in payload.get("failures") or []:
            failures.append(str(failure))
        for section in ("trace", "stream"):
            section_payload = payload.get(section)
            if isinstance(section_payload, dict):
                for failure in section_payload.get("failures") or []:
                    failures.append(str(failure))
        for failed in payload.get("failed_scenarios") or []:
            if not isinstance(failed, dict):
                continue
            for failure in failed.get("failures") or []:
                failures.append(str(failure))
            for failure in failed.get("stream_failures") or []:
                failures.append(str(failure))
    return failures


def _paper_readiness(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(manifests)
    ready = sum(1 for manifest in manifests if manifest.get("paper_ready"))
    failures: Counter[str] = Counter()
    for manifest in manifests:
        failures.update(str(item) for item in manifest.get("paper_failures") or [])
    return {
        "checked_candidates": total,
        "paper_ready_candidates": ready,
        "paper_ready_rate": round(ready / max(total, 1), 4),
        "top_failures": [
            {"failure": failure, "count": count}
            for failure, count in failures.most_common()
        ],
    }


def _load_decisions(data_dir: Path, *, limit: int) -> list[dict[str, Any]]:
    from meta_harness.decisions import sanitize_decision_for_proposer

    decisions: list[dict[str, Any]] = []
    for path in [data_dir / "candidate_decisions.jsonl", *sorted((data_dir / "runs").glob("*/candidate_decisions.jsonl"))]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                decisions.append(sanitize_decision_for_proposer(payload))
    return decisions[-limit:]


def _inner_loop_bridge(candidate_dirs: list[Path]) -> dict[str, Any]:
    inner_candidates = []
    for candidate_dir in candidate_dirs:
        payload = _load_json(candidate_dir / "inner_loop_candidate.json")
        if not isinstance(payload, dict):
            continue
        inner_candidates.append(
            {
                "candidate_id": payload.get("candidate_id"),
                "feature_owner": payload.get("feature_owner"),
                "decision": payload.get("decision"),
                "metrics": payload.get("metrics") or {},
                "outer_loop_eligible": payload.get("decision") == "promote_outer_loop",
                "candidate_path": str(candidate_dir),
            }
        )
    return {
        "inner_loop_is_candidate_generator_only": True,
        "outer_loop_must_promote": True,
        "candidate_count": len(inner_candidates),
        "candidates": inner_candidates,
    }


def _next_proposer_actions(
    failure_clusters: list[dict[str, Any]],
    inner_loop: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for cluster in failure_clusters[:5]:
        failure = str(cluster.get("failure") or "")
        actions.append(
            {
                "hypothesis": _hypothesis_for_failure(failure),
                "evidence": failure,
                "candidate_quality_bar": "one mechanism, bounded write scope, search-set only",
            }
        )
    if inner_loop.get("candidate_count"):
        actions.append(
            {
                "hypothesis": "Promote only inner-loop candidates that survive outer-loop trace gates.",
                "evidence": "inner_loop_candidate.json artifacts are present",
                "candidate_quality_bar": "inner-loop metrics are advisory, not promotion authority",
            }
        )
    return actions


def _hypothesis_for_failure(failure: str) -> str:
    text = failure.casefold()
    if "memory" in text:
        return "Memory/context candidate should improve evidence routing without increasing unrelated writes."
    if "tool" in text:
        return "Tool-policy candidate should tighten selection/recovery while preserving allowed tool groups."
    if "route" in text or "runner" in text:
        return "Runner-routing candidate should expose route decisions and prevent loop/regression paths."
    if "citation" in text or "source" in text:
        return "Source-grounding candidate should preserve artifact/chunk/citation metadata through context assembly."
    return "Inspect raw traces for this repeated failure before proposing a bounded mechanism change."


def _frontier_entry(candidate: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "version",
        "candidate_path",
        "trace_gate_pass_rate",
        "stream_gate_pass_rate",
        "completion_rate",
        "fitness_score",
        "tool_success_rate",
        "avg_turns",
        "total_tokens",
        "token_efficiency",
        "total_cost_usd",
        "cost_efficiency",
        "avg_duration_ms",
        "latency_efficiency",
    )
    return {key: candidate.get(key) for key in keys if key in candidate}


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
