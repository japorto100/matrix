"""Provider-free contracts for Matrix memory, KG, RAG and semantic boundaries."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from memory_fusion.semantic_feedback import (
    proposal_payload,
    propose_semantic_correction_from_memory,
)
from meta_harness.scenario_runner import (
    TraceExpectations,
    evaluate_stream_gates,
    evaluate_trace_gates,
)
from semantic_layer.catalog import (
    DEFAULT_SEMANTIC_CATALOG,
    PermissionContext,
    SemanticCatalog,
    SemanticTerm,
    lookup_phrase,
    plan_metric_query,
    propose_correction,
    validate_catalog,
)

DEFAULT_RUN_ID = "run-knowledge-contract"

REQUIRED_KG_PROPOSAL_METADATA = (
    "claim_id",
    "claim_type",
    "claim_status",
    "evidence_refs",
    "source_artifact_id",
    "chunk_id",
    "chunk_hash",
    "citation_ref",
    "semantic_term_ids",
    "valid_time_range",
    "transaction_time_range",
)

REQUIRED_CONTEXT_METADATA = (
    "source_artifact_id",
    "chunk_id",
    "chunk_hash",
    "citation_ref",
    "semantic_catalog_version",
    "semantic_term_ids",
)


def run_knowledge_contract_scenarios(
    *,
    run_id: str = DEFAULT_RUN_ID,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run deterministic knowledge-layer scenarios without provider calls."""

    data_root = data_dir or Path(__file__).resolve().parents[2] / "data" / "meta_harness"
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        _memory_ground_truth_preserved(),
        _memory_to_kg_promotion_blocked_without_evidence(),
        _rag_kg_semantic_context_grounded(),
        _semantic_ambiguity_and_permission_fail_closed(),
        _semantic_correction_stays_review_proposal(),
        _memory_semantic_feedback_requires_review(),
        _rag_kg_downstream_artifact_visible(),
    ]
    passed = all(scenario["passed"] for scenario in scenarios)
    summary = {
        "run_id": run_id,
        "kind": "knowledge_contract",
        "feature_id": "012/017/019/022/025",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "scenario_count": len(scenarios),
        "passed_count": sum(1 for scenario in scenarios if scenario["passed"]),
        "scenarios": scenarios,
    }
    _write_json(run_dir / "knowledge_contract.json", summary)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "kind": "knowledge_contract",
            "feature_id": "012/017/019/022/025",
            "frontend_required": False,
            "provider_calls_required": False,
            "created_at": summary["created_at"],
        },
    )
    _write_candidate_artifacts(run_dir, summary)
    return {**summary, "artifact_path": str(run_dir / "knowledge_contract.json")}


def validate_kg_claim_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """Validate that a KG claim proposal keeps evidence and semantic links."""

    metadata = proposal.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    failures = [
        f"missing-kg-proposal-metadata:{key}"
        for key in REQUIRED_KG_PROPOSAL_METADATA
        if metadata.get(key) in (None, "", (), [])
    ]
    if metadata.get("claim_status") not in {"proposed", "review", "accepted", "rejected"}:
        failures.append("invalid-claim-status")
    if proposal.get("source_scope") == "personal_memory" and not metadata.get(
        "promotion_review_required"
    ):
        failures.append("personal-memory-promotion-requires-review")
    return {
        "passed": not failures,
        "failures": failures,
        "required_metadata": list(REQUIRED_KG_PROPOSAL_METADATA),
    }


def validate_knowledge_context_item(item: dict[str, Any]) -> dict[str, Any]:
    """Validate one selected context item before it can support an answer."""

    metadata = item.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    failures = [
        f"missing-context-metadata:{key}"
        for key in REQUIRED_CONTEXT_METADATA
        if metadata.get(key) in (None, "", (), [])
    ]
    if item.get("source") == "kg":
        for key in ("claim_id", "claim_type", "valid_time_range"):
            if metadata.get(key) in (None, "", (), []):
                failures.append(f"missing-context-metadata:{key}")
    if item.get("selected") is not True:
        failures.append("context-item-not-selected")
    return {
        "passed": not failures,
        "failures": failures,
        "required_metadata": list(REQUIRED_CONTEXT_METADATA),
    }


def _memory_ground_truth_preserved() -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    events = [
        {
            "action": "memory_recall",
            "toolName": "memory_search",
            "success": True,
            "metadata": {
                "route": "fusion",
                "providers": "hindsight,mempalace",
                "bank_id": "project",
                "source": "memory_fusion",
                "source_status": "durable",
                "raw_evidence_ref": "mempalace:drawer:turn-42",
                "operation_log_id": "memop-001",
                "diff_ref": "memory-diff-001",
                "evidence": "verbatim evidence before compaction",
            },
            "createdAt": now,
        },
        {
            "action": "memory_retain",
            "success": True,
            "metadata": {
                "route": "fusion",
                "providers": "hindsight,mempalace",
                "bank_id": "project",
                "source": "pre_compaction_presave",
                "source_status": "durable",
                "raw_evidence_ref": "mempalace:drawer:turn-42",
                "operation_log_id": "memop-002",
                "diff_ref": "memory-diff-002",
            },
            "createdAt": now,
        },
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_actions=("memory_recall", "memory_retain"),
            required_memory_routes=("fusion",),
            required_memory_providers=("hindsight", "mempalace"),
            required_memory_metadata_keys=(
                "bank_id",
                "source_status",
                "raw_evidence_ref",
                "operation_log_id",
                "diff_ref",
            ),
            expected_memory=True,
        ),
        response_text="Use verbatim evidence before compaction.",
    )
    return _scenario_result(
        scenario_id="knowledge-memory-ground-truth-preserved",
        passed=verdict.passed,
        failures=list(verdict.failures),
        details={"trace_verdict": verdict.as_dict()},
    )


def _memory_to_kg_promotion_blocked_without_evidence() -> dict[str, Any]:
    validation = validate_kg_claim_proposal(
        {
            "source_scope": "personal_memory",
            "metadata": {
                "claim_id": "claim-personal-001",
                "claim_type": "user_preference",
                "claim_status": "proposed",
            },
        }
    )
    expected_failures = {
        "missing-kg-proposal-metadata:evidence_refs",
        "missing-kg-proposal-metadata:citation_ref",
        "missing-kg-proposal-metadata:semantic_term_ids",
        "personal-memory-promotion-requires-review",
    }
    failures = [
        f"missing-expected-failure:{item}"
        for item in sorted(expected_failures)
        if item not in set(validation["failures"])
    ]
    return _scenario_result(
        scenario_id="knowledge-personal-memory-kg-promotion-blocked",
        passed=not failures and validation["passed"] is False,
        failures=failures,
        details={"validation": validation, "blocked": validation["passed"] is False},
    )


def _rag_kg_semantic_context_grounded() -> dict[str, Any]:
    context_items = [
        {
            "id": "chunk-semantic-tool-success-rate",
            "source": "vector",
            "selected": True,
            "metadata": {
                "source_artifact_id": "artifact-agent-audit",
                "chunk_id": "chunk-semantic-tool-success-rate",
                "chunk_hash": "sha256:semantic-tool-success",
                "citation_ref": "S1",
                "semantic_catalog_version": DEFAULT_SEMANTIC_CATALOG.version,
                "semantic_term_ids": ("rag_citation",),
            },
        },
        {
            "id": "kg-claim-tool-success-rate",
            "source": "kg",
            "selected": True,
            "metadata": {
                "source_artifact_id": "artifact-agent-audit",
                "chunk_id": "chunk-semantic-tool-success-rate",
                "chunk_hash": "sha256:semantic-tool-success",
                "citation_ref": "S1",
                "semantic_catalog_version": DEFAULT_SEMANTIC_CATALOG.version,
                "semantic_term_ids": ("kg_claim",),
                "claim_id": "kg-claim-tool-success-rate",
                "claim_type": "entity_attribute",
                "valid_time_range": "2026-04-01/..",
            },
        },
    ]
    validations = [validate_knowledge_context_item(item) for item in context_items]
    failures = [
        failure
        for validation in validations
        for failure in validation["failures"]
        if failure
    ]
    answer = (
        "Agent tool success rate is defined by the semantic metric and grounded "
        "in the selected audit chunk [S1]."
    )
    if "[S1]" not in answer:
        failures.append("missing-answer-citation:S1")
    return _scenario_result(
        scenario_id="knowledge-rag-kg-semantic-context-grounded",
        passed=not failures,
        failures=failures,
        details={"context_validations": validations, "answer": answer},
    )


def _semantic_ambiguity_and_permission_fail_closed() -> dict[str, Any]:
    ambiguous_catalog = SemanticCatalog(
        terms=(
            *DEFAULT_SEMANTIC_CATALOG.terms,
            SemanticTerm(
                term_id="ambiguous_tool_success",
                name="Ambiguous tool success",
                aliases=("tool success",),
                description="Fixture alias collision for fail-closed semantic lookup.",
                source_refs=("feature-025",),
            ),
        ),
        metrics=DEFAULT_SEMANTIC_CATALOG.metrics,
        version=DEFAULT_SEMANTIC_CATALOG.version,
    )
    catalog_validation = validate_catalog(ambiguous_catalog)
    lookup = lookup_phrase(ambiguous_catalog, "tool success")
    plan = plan_metric_query(
        DEFAULT_SEMANTIC_CATALOG,
        "agent_tool_success_rate",
        PermissionContext(),
    )
    failures: list[str] = []
    if catalog_validation["passed"] is True:
        failures.append("semantic-alias-collision-not-detected")
    if lookup["ambiguous"] is not True:
        failures.append("semantic-ambiguity-not-fail-closed")
    if plan.get("allowed") is not False:
        failures.append("tenant-metric-permission-not-denied")
    if plan.get("raw_sql_allowed") is not False:
        failures.append("raw-sql-not-blocked")
    return _scenario_result(
        scenario_id="knowledge-semantic-ambiguity-permission-fail-closed",
        passed=not failures,
        failures=failures,
        details={
            "catalog_validation": catalog_validation,
            "lookup": lookup,
            "metric_plan": plan,
        },
    )


def _semantic_correction_stays_review_proposal() -> dict[str, Any]:
    proposal = propose_correction(
        target_type="term",
        target_id="kg_claim",
        proposed_by="memory-feedback",
        rationale="User corrected the term wording in a session.",
        patch={"description": "Updated by user feedback, pending review."},
    )
    failures: list[str] = []
    if proposal.status != "proposed":
        failures.append("semantic-correction-auto-accepted")
    if proposal.target_id != "kg_claim":
        failures.append("semantic-correction-lost-target")
    if proposal.patch.get("description") in (None, ""):
        failures.append("semantic-correction-lost-patch")
    return _scenario_result(
        scenario_id="knowledge-semantic-correction-review-proposal",
        passed=not failures,
        failures=failures,
        details={
            "proposal": proposal.as_dict(),
            "promotion_target": "semantic_proposal",
            "silent_kg_promotion": False,
        },
    )


def _memory_semantic_feedback_requires_review() -> dict[str, Any]:
    feedback = proposal_payload(
        propose_semantic_correction_from_memory(
            target_type="metric",
            target_id="retrieval_pass_rate",
            proposed_by="memory-feedback",
            rationale="Retained memory says the split wording is unclear.",
            patch={"description": "Clarify search vs holdout split wording."},
            memory_unit_id="mem-semantic-001",
            evidence_ref="mempalace:drawer:turn-42",
        )
    )
    failures: list[str] = []
    proposal = feedback.get("proposal") or {}
    evidence = feedback.get("feedback_evidence") or {}
    if feedback.get("accepted") is not True:
        failures.append("memory-semantic-feedback-not-accepted")
    if feedback.get("catalog_mutated") is not False:
        failures.append("memory-semantic-feedback-mutated-catalog")
    if feedback.get("review_required") is not True:
        failures.append("memory-semantic-feedback-review-not-required")
    if proposal.get("status") != "proposed":
        failures.append("memory-semantic-feedback-auto-promoted")
    if proposal.get("patch", {}).get("_feedback_source") != "memory_fusion":
        failures.append("memory-semantic-feedback-source-missing")
    for key in ("raw_evidence_ref", "operation_log_id", "diff_ref"):
        if evidence.get(key) in (None, ""):
            failures.append(f"memory-semantic-feedback-missing-evidence:{key}")
    return _scenario_result(
        scenario_id="knowledge-memory-semantic-feedback-review-proposal",
        passed=not failures,
        failures=failures,
        details={
            "feedback": feedback,
            "promotion_target": "semantic_proposal",
            "silent_catalog_mutation": False,
        },
    )


def _rag_kg_downstream_artifact_visible() -> dict[str, Any]:
    trace_events = [
        {
            "action": "rag_retrieval",
            "success": True,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "rag.retrieval.completed",
                        "metadata": {
                            "source_artifact_id": "artifact-agent-audit",
                            "chunk_id": "chunk-semantic-tool-success-rate",
                            "chunk_hash": "sha256:semantic-tool-success",
                            "citation_ref": "S1",
                            "source_candidate_count": 2,
                        },
                    },
                    {
                        "name": "kg.context.selected",
                        "metadata": {
                            "claim_id": "kg-claim-tool-success-rate",
                            "source_artifact_id": "artifact-agent-audit",
                            "citation_ref": "S1",
                            "semantic_term_ids": ("kg_claim",),
                        },
                    },
                ]
            },
        }
    ]
    expectations = TraceExpectations(
        required_runtime_event_names=(
            "rag.retrieval.completed",
            "kg.context.selected",
        ),
        required_runtime_event_metadata_keys={
            "rag.retrieval.completed": (
                "source_artifact_id",
                "chunk_id",
                "chunk_hash",
                "citation_ref",
                "source_candidate_count",
            ),
            "kg.context.selected": (
                "claim_id",
                "source_artifact_id",
                "citation_ref",
                "semantic_term_ids",
            ),
        },
        required_stream_parts=("tool-output-available",),
        required_stream_rich_renderers=("file_analyze",),
        required_stream_artifact_files=("rag-kg-sources.json", "kg-paths.json"),
    )
    trace_verdict = evaluate_trace_gates(trace_events, expectations)
    stream_verdict = evaluate_stream_gates(
        [
            'data: {"type":"start"}\n\n',
            (
                'data: {"type":"tool-input-start","toolName":"file_analyze",'
                '"toolCallId":"rag-artifact"}\n\n'
            ),
            (
                'data: {"type":"tool-output-available","toolName":"file_analyze",'
                '"toolCallId":"rag-artifact","output":{"files":['
                '{"name":"rag-kg-sources.json"},{"name":"kg-paths.json"}]}}\n\n'
            ),
            'data: {"type":"text-delta","delta":"Grounded sources ready."}\n\n',
            'data: {"type":"finish"}\n\n',
        ],
        expectations,
    )
    failures = [*trace_verdict.failures, *stream_verdict.failures]
    return _scenario_result(
        scenario_id="knowledge-rag-kg-downstream-artifact-visible",
        passed=trace_verdict.passed and stream_verdict.passed,
        failures=list(failures),
        details={
            "trace_verdict": trace_verdict.as_dict(),
            "stream_verdict": stream_verdict.as_dict(),
        },
    )


def _scenario_result(
    *,
    scenario_id: str,
    passed: bool,
    failures: list[str],
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": scenario_id,
        "passed": passed,
        "failures": failures,
        **details,
    }


def _write_candidate_artifacts(run_dir: Path, summary: dict[str, Any]) -> None:
    candidate_dir = run_dir / "candidates" / "knowledge-contract-static"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    aggregate = {
        "candidate_id": "knowledge-contract-static",
        "feature_id": summary["feature_id"],
        "completion_rate": 1.0 if summary["passed"] else 0.0,
        "tool_success_rate": summary["passed_count"] / max(1, summary["scenario_count"]),
        "scenarios_evaluated": summary["scenario_count"],
        "trace_gate_pass_rate": 1.0 if summary["passed"] else 0.0,
        "failed_scenarios": [
            {"scenario_id": item["id"], "failures": item["failures"]}
            for item in summary["scenarios"]
            if not item["passed"]
        ],
    }
    _write_json(candidate_dir / "aggregate.json", aggregate)
    _write_json(candidate_dir / "scenario_set.json", {"scenarios": summary["scenarios"]})
    _write_json(candidate_dir / "knowledge_contract.json", summary)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
