from __future__ import annotations


def test_memory_semantic_feedback_creates_review_only_proposal():
    from memory_fusion.semantic_feedback import (
        proposal_payload,
        propose_semantic_correction_from_memory,
    )

    result = propose_semantic_correction_from_memory(
        target_type="metric",
        target_id="retrieval_pass_rate",
        proposed_by="memory_fusion",
        rationale="A retained benchmark note says split semantics are unclear.",
        patch={"description": "Clarify that holdout and search splits differ."},
        memory_unit_id="mem-123",
        evidence_ref="audit:event-9",
    )

    payload = proposal_payload(result)

    assert payload["accepted"] is True
    assert payload["catalog_mutated"] is False
    assert payload["review_required"] is True
    assert payload["proposal"]["status"] == "proposed"
    assert payload["proposal"]["patch"]["_feedback_source"] == "memory_fusion"
    evidence = payload["feedback_evidence"]
    assert evidence["memory_unit_id"] == "mem-123"
    assert evidence["source_status"] == "durable"
    assert evidence["raw_evidence_ref"] == "audit:event-9"
    assert evidence["operation_log_id"].startswith("memory-op:semantic_correction")


def test_memory_semantic_feedback_requires_evidence():
    from memory_fusion.semantic_feedback import propose_semantic_correction_from_memory

    result = propose_semantic_correction_from_memory(
        target_type="metric",
        target_id="retrieval_pass_rate",
        proposed_by="memory_fusion",
        rationale="No evidence.",
    )

    assert result["accepted"] is False
    assert result["reason"] == "memory-feedback-evidence-required"
    assert result["catalog_mutated"] is False
