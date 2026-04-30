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
        _compaction_tool_output_provenance_contract(),
        _memory_to_kg_promotion_blocked_without_evidence(),
        _rag_kg_semantic_context_grounded(),
        _lexical_candidate_without_provenance_blocked(),
        _semantic_lookup_required_before_metric_answer(),
        _semantic_lexical_candidate_requires_confirmation(),
        _semantic_ambiguity_and_permission_fail_closed(),
        _semantic_correction_stays_review_proposal(),
        _memory_semantic_feedback_requires_review(),
        _delegation_parent_memory_handoff_contract(),
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
    visible_session_text = (
        "visible session says preserve tool evidence before summary retain"
    )
    tool_input_evidence = "memory_search query=verbatim_evidence_before_compaction"
    tool_output_evidence = (
        "memory_search output=verbatim evidence before compaction"
    )
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
                "source_timestamp": now,
                "captured_at": now,
                "room_id": "!room:matrix.local",
                "thread_id": "thread-42",
                "session_id": "session-42",
                "tool_call_id": "tool-call-memory-search-42",
                "tool_input_ref": "audit:tool-input-memory-search-42",
                "tool_output_ref": "audit:tool-output-memory-search-42",
                "visible_session_text": visible_session_text,
                "tool_input_evidence": tool_input_evidence,
                "tool_output_evidence": tool_output_evidence,
                "evidence": "verbatim evidence before compaction",
                "runtime_events": [
                    {
                        "name": "memory.recall.completed",
                        "metadata": {
                            "context_refs": [
                                {
                                    "source_refs": ["mempalace:drawer:turn-42"],
                                    "raw_evidence_ref": "mempalace:drawer:turn-42",
                                    "operation_log_id": "memop-001",
                                    "diff_ref": "memory-diff-001",
                                    "thread_id": "thread-42",
                                    "session_id": "session-42",
                                    "room_id": "!room:matrix.local",
                                    "source_timestamp": now,
                                    "captured_at": now,
                                    "tool_call_id": "tool-call-memory-search-42",
                                    "tool_input_ref": "audit:tool-input-memory-search-42",
                                    "tool_output_ref": "audit:tool-output-memory-search-42",
                                    "source_layer": "personal_raw",
                                    "context_tier": "L0",
                                }
                            ]
                        },
                    }
                ],
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
                "source_timestamp": now,
            },
            "createdAt": now,
        },
        {
            "action": "memory_retain",
            "success": True,
            "metadata": {
                "route": "summary",
                "provider": "hindsight",
                "bank_id": "project",
                "source": "automatic_summary_retain",
                "source_status": "derived_from_durable_raw",
                "raw_evidence_ref": "mempalace:drawer:turn-42",
                "operation_log_id": "memop-003",
                "diff_ref": "memory-diff-003",
                "source_timestamp": now,
                "captured_at": now,
                "room_id": "!room:matrix.local",
                "thread_id": "thread-42",
                "session_id": "session-42",
                "tool_call_id": "tool-call-memory-search-42",
                "tool_input_ref": "audit:tool-input-memory-search-42",
                "tool_output_ref": "audit:tool-output-memory-search-42",
                "visible_session_text": visible_session_text,
                "tool_input_evidence": tool_input_evidence,
                "tool_output_evidence": tool_output_evidence,
            },
            "createdAt": now,
        },
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_actions=("memory_recall", "memory_retain"),
            required_memory_routes=("fusion", "summary"),
            required_memory_providers=("hindsight", "mempalace"),
            required_memory_evidence_terms=(
                visible_session_text,
                tool_input_evidence,
                tool_output_evidence,
            ),
            required_memory_metadata_keys=(
                "bank_id",
                "source_status",
                "raw_evidence_ref",
                "operation_log_id",
                "diff_ref",
                "source_timestamp",
                "tool_call_id",
                "tool_input_ref",
                "tool_output_ref",
                "room_id",
                "thread_id",
                "session_id",
            ),
            required_event_metadata_values={
                "memory_retain": {"source": "automatic_summary_retain"}
            },
            required_runtime_event_names=("memory.recall.completed",),
            required_runtime_event_metadata_keys={
                "memory.recall.completed": (
                    "context_refs",
                )
            },
            expected_memory=True,
        ),
        response_text="Use verbatim evidence before compaction.",
    )
    context_refs = (
        events[0]["metadata"]["runtime_events"][0]["metadata"].get("context_refs") or []
    )
    failures = list(verdict.failures)
    if not context_refs:
        failures.append("missing-memory-recall-context-refs")
    else:
        first_ref = context_refs[0]
        for key in (
            "source_refs",
            "raw_evidence_ref",
            "operation_log_id",
            "diff_ref",
            "thread_id",
            "session_id",
            "room_id",
            "source_timestamp",
            "tool_call_id",
            "tool_input_ref",
            "tool_output_ref",
        ):
            if first_ref.get(key) in (None, "", [], ()):
                failures.append(f"missing-memory-context-ref:{key}")
    return _scenario_result(
        scenario_id="knowledge-memory-ground-truth-preserved",
        passed=verdict.passed and not failures,
        failures=failures,
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


def _compaction_tool_output_provenance_contract() -> dict[str, Any]:
    from agent.middleware import compaction

    content = "tool-output-evidence " * 400
    compacted = compaction.compact(
        [
            {
                "role": "tool",
                "tool_call_id": "call-kg-rag-1",
                "content": content,
                "metadata": {"source_ref": "audit:tool-output-1"},
            }
        ]
    )[0]
    metadata = (compacted.get("metadata") or {}).get("compaction") or {}
    failures: list[str] = []
    if len(str(compacted.get("content") or "")) >= len(content):
        failures.append("tool-output-not-compacted")
    for key in (
        "truncated",
        "offload_ref",
        "full_content_chars",
        "content_sha256",
        "preview_chars",
    ):
        if metadata.get(key) in (None, "", [], ()):
            failures.append(f"missing-compaction-metadata:{key}")
    if metadata.get("truncated") is not True:
        failures.append("compaction-metadata-not-truncated")
    if metadata.get("offload_ref") != "tool:call-kg-rag-1":
        failures.append("compaction-offload-ref-not-tool-call")
    if metadata.get("full_content_chars") != len(content):
        failures.append("compaction-full-size-not-preserved")
    return _scenario_result(
        scenario_id="knowledge-compaction-tool-output-provenance",
        passed=not failures,
        failures=failures,
        details={"compaction_metadata": metadata},
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


def _semantic_lookup_required_before_metric_answer() -> dict[str, Any]:
    lookup = lookup_phrase(DEFAULT_SEMANTIC_CATALOG, "tool success rate")
    failures: list[str] = []
    if lookup.get("matched") is not True or lookup.get("ambiguous") is not False:
        failures.append("semantic-metric-lookup-not-authoritative")
    match = (lookup.get("matches") or [{}])[0]
    metric = match.get("item") or {}
    metric_plan = plan_metric_query(
        DEFAULT_SEMANTIC_CATALOG,
        str(metric.get("metric_id") or ""),
        PermissionContext(user_id="alice", tenant_id="tenant-a", roles=("analyst",)),
    )
    model_output = {
        "status": "matched_metric",
        "phrase": "tool success rate",
        "authoritative": bool(metric_plan.get("allowed")),
        "ambiguous": False,
        "refusal_reason": None,
        "answer_template": {
            "definition": metric.get("measure", ""),
            "value": "Only answer with a computed value supplied by an approved data path.",
            "provenance": list(metric.get("source_refs") or ()),
            "freshness": metric.get("freshness_sla", ""),
        },
        "raw_sql_allowed": False,
        "metric_plan": {
            "allowed": metric_plan.get("allowed"),
            "reason": metric_plan.get("reason"),
            "metric_id": metric.get("metric_id"),
            "semantic_catalog_version": DEFAULT_SEMANTIC_CATALOG.version,
            "semantic_contract": metric_plan.get("semantic_contract"),
            "freshness_sla": metric_plan.get("freshness_sla"),
            "raw_sql_allowed": metric_plan.get("raw_sql_allowed", False),
        },
    }
    trace_events = [
        {
            "action": "tool_result",
            "toolName": "semantic_lookup",
            "success": True,
            "metadata": {
                "tool_output": model_output,
                "runtime_events": [
                    {
                        "name": "semantic.lookup.completed",
                        "metadata": {
                            "metric_id": "agent_tool_success_rate",
                            "semantic_catalog_version": (
                                DEFAULT_SEMANTIC_CATALOG.version
                            ),
                            "authoritative": True,
                            "raw_sql_allowed": False,
                        },
                    }
                ],
            },
        },
        {
            "action": "llm_response",
            "success": True,
            "metadata": {
                "answer": (
                    "Agent tool success rate uses the reviewed semantic metric "
                    "agent_tool_success_rate, freshness 15m, and must be computed "
                    "through an approved data path."
                )
            },
        },
    ]
    expectations = TraceExpectations(
        required_actions=("llm_response",),
        required_tools=("semantic_lookup",),
        required_runtime_event_names=("semantic.lookup.completed",),
        required_runtime_event_metadata_keys={
            "semantic.lookup.completed": (
                "metric_id",
                "semantic_catalog_version",
                "authoritative",
                "raw_sql_allowed",
            )
        },
        required_runtime_event_metadata_values={
            "semantic.lookup.completed": {
                "metric_id": "agent_tool_success_rate",
                "semantic_catalog_version": DEFAULT_SEMANTIC_CATALOG.version,
                "authoritative": "true",
                "raw_sql_allowed": "false",
            }
        },
        required_response_terms=(
            "agent_tool_success_rate",
            "approved data path",
            "freshness 15m",
        ),
    )
    trace_verdict = evaluate_trace_gates(
        trace_events,
        expectations,
        response_text=str(trace_events[1]["metadata"]["answer"]),
    )
    failures.extend(trace_verdict.failures)
    metric_output = model_output.get("metric_plan") or {}
    semantic_contract = metric_output.get("semantic_contract") or {}
    for key in (
        "metric_id",
        "semantic_catalog_version",
        "semantic_contract",
        "freshness_sla",
    ):
        if metric_output.get(key) in (None, "", [], ()):
            failures.append(f"missing-semantic-metric-output:{key}")
    for key in ("measure", "source_table", "source_refs"):
        if semantic_contract.get(key) in (None, "", [], ()):
            failures.append(f"missing-semantic-contract:{key}")
    if metric_output.get("raw_sql_allowed") is not False:
        failures.append("semantic-metric-raw-sql-not-blocked")
    if model_output.get("authoritative") is not True:
        failures.append("semantic-metric-not-authoritative")
    return _scenario_result(
        scenario_id="knowledge-semantic-lookup-before-metric-answer",
        passed=trace_verdict.passed and not failures,
        failures=failures,
        details={
            "trace_verdict": trace_verdict.as_dict(),
            "model_output": model_output,
        },
    )


def _semantic_lexical_candidate_requires_confirmation() -> dict[str, Any]:
    lookup = lookup_phrase(DEFAULT_SEMANTIC_CATALOG, "tool success ratio")
    candidates = lookup.get("candidate_matches") or []
    top_candidate = candidates[0] if candidates else {}
    item = top_candidate.get("item") if isinstance(top_candidate, dict) else {}
    model_output = {
        "status": "not_found",
        "phrase": lookup.get("phrase"),
        "authoritative": False,
        "ambiguous": False,
        "refusal_reason": "no-authoritative-definition",
        "candidate_matches": [
            {
                "type": top_candidate.get("type"),
                "id": item.get("metric_id") if isinstance(item, dict) else "",
                "name": item.get("name") if isinstance(item, dict) else "",
                "score": top_candidate.get("score"),
                "matched_terms": top_candidate.get("matched_terms") or [],
                "authoritative": False,
                "requires_confirmation": True,
            }
        ]
        if top_candidate
        else [],
        "raw_sql_allowed": False,
    }
    trace_events = [
        {
            "action": "tool_result",
            "toolName": "semantic_lookup",
            "success": True,
            "metadata": {
                "tool_output": model_output,
                "runtime_events": [
                    {
                        "name": "semantic.lookup.candidates",
                        "metadata": {
                            "phrase": "tool success ratio",
                            "lookup_status": "not_found",
                            "candidate_count": len(candidates),
                            "top_candidate_id": model_output["candidate_matches"][0][
                                "id"
                            ]
                            if model_output["candidate_matches"]
                            else "",
                            "authoritative": False,
                            "requires_confirmation": True,
                        },
                    }
                ],
            },
        }
    ]
    expectations = TraceExpectations(
        required_tools=("semantic_lookup",),
        required_runtime_event_names=("semantic.lookup.candidates",),
        required_runtime_event_metadata_keys={
            "semantic.lookup.candidates": (
                "phrase",
                "lookup_status",
                "candidate_count",
                "top_candidate_id",
                "authoritative",
                "requires_confirmation",
            )
        },
        required_runtime_event_metadata_values={
            "semantic.lookup.candidates": {
                "lookup_status": "not_found",
                "top_candidate_id": "agent_tool_success_rate",
                "authoritative": "false",
                "requires_confirmation": "true",
            }
        },
    )
    trace_verdict = evaluate_trace_gates(trace_events, expectations)
    failures = list(trace_verdict.failures)
    if lookup.get("matched") is not False:
        failures.append("near-miss-semantic-lookup-became-authoritative")
    if not candidates:
        failures.append("near-miss-semantic-candidate-missing")
    if model_output.get("authoritative") is not False:
        failures.append("near-miss-semantic-output-authoritative")
    if model_output.get("raw_sql_allowed") is not False:
        failures.append("near-miss-semantic-raw-sql-allowed")
    candidate_output = (model_output.get("candidate_matches") or [{}])[0]
    if candidate_output.get("requires_confirmation") is not True:
        failures.append("near-miss-semantic-confirmation-not-required")
    return _scenario_result(
        scenario_id="knowledge-semantic-lexical-candidate-requires-confirmation",
        passed=trace_verdict.passed and not failures,
        failures=failures,
        details={
            "trace_verdict": trace_verdict.as_dict(),
            "lookup": lookup,
            "model_output": model_output,
        },
    )


def _lexical_candidate_without_provenance_blocked() -> dict[str, Any]:
    trace_events = [
        {
            "action": "rag_retrieval",
            "success": False,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "rag.retrieve.completed",
                        "metadata": {
                            "lexical_hit_count": 1,
                            "lane_counts": {"bm25": 1},
                            "selected_lanes": ["bm25"],
                            "selected_context_ids": ["bm25-unattributed"],
                            "missing_provenance_ids": ["bm25-unattributed"],
                            "degraded": True,
                            "degraded_reasons": ["CONTEXT_PROVENANCE_MISSING"],
                        },
                    }
                ]
            },
        }
    ]
    expectations = TraceExpectations(
        required_actions=("rag_retrieval",),
        required_runtime_event_names=("rag.retrieve.completed",),
        required_runtime_event_metadata_keys={
            "rag.retrieve.completed": (
                "lexical_hit_count",
                "lane_counts",
                "selected_lanes",
                "missing_provenance_ids",
                "degraded_reasons",
            )
        },
    )
    verdict = evaluate_trace_gates(trace_events, expectations)
    metadata = trace_events[0]["metadata"]["runtime_events"][0]["metadata"]
    failures = list(verdict.failures)
    if metadata.get("lexical_hit_count") != 1:
        failures.append("missing-lexical-hit-count")
    if "bm25" not in set(metadata.get("selected_lanes") or []):
        failures.append("lexical-lane-not-selected")
    if not metadata.get("missing_provenance_ids"):
        failures.append("lexical-missing-provenance-not-surfaced")
    if "CONTEXT_PROVENANCE_MISSING" not in set(metadata.get("degraded_reasons") or []):
        failures.append("lexical-provenance-gate-not-fail-closed")
    return _scenario_result(
        scenario_id="knowledge-lexical-candidate-without-provenance-blocked",
        passed=verdict.passed and not failures,
        failures=failures,
        details={"trace_verdict": verdict.as_dict()},
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


def _delegation_parent_memory_handoff_contract() -> dict[str, Any]:
    trace_events = [
        {
            "action": "memory_retain",
            "success": True,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "subagent.parent_memory_handoff",
                        "metadata": {
                            "child_session_id": "a2a-task-1",
                            "child_task_id": "task-1",
                            "child_memory_write_allowed": False,
                            "parent_curated_memory_handoff": True,
                            "retain_decision": "parent_review_required",
                            "source_refs": ("a2a:task-1", "a2a-task-1"),
                            "confidence": "unverified_child_summary",
                            "degradation_flags": (),
                            "result_digest": "sha256:delegation-result",
                        },
                    }
                ]
            },
        }
    ]
    expectations = TraceExpectations(
        required_runtime_event_names=("subagent.parent_memory_handoff",),
        required_runtime_event_metadata_keys={
            "subagent.parent_memory_handoff": (
                "child_session_id",
                "child_task_id",
                "source_refs",
                "confidence",
                "degradation_flags",
                "retain_decision",
                "result_digest",
            )
        },
    )
    trace_verdict = evaluate_trace_gates(trace_events, expectations)
    metadata = trace_events[0]["metadata"]["runtime_events"][0]["metadata"]
    failures = list(trace_verdict.failures)
    if metadata.get("child_memory_write_allowed") is not False:
        failures.append("child-memory-write-not-blocked")
    if metadata.get("parent_curated_memory_handoff") is not True:
        failures.append("parent-curated-handoff-missing")
    if metadata.get("retain_decision") != "parent_review_required":
        failures.append("delegation-retain-decision-not-parent-review")
    return _scenario_result(
        scenario_id="knowledge-delegation-parent-memory-handoff",
        passed=trace_verdict.passed and not failures,
        failures=failures,
        details={"trace_verdict": trace_verdict.as_dict()},
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
