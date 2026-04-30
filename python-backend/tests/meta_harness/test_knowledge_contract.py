from __future__ import annotations

import json

from meta_harness.knowledge_contract import (
    run_knowledge_contract_scenarios,
    validate_kg_claim_proposal,
    validate_knowledge_context_item,
)


def test_knowledge_contract_runs_provider_free_scenarios(tmp_path):
    result = run_knowledge_contract_scenarios(
        run_id="run-knowledge",
        data_dir=tmp_path,
    )

    assert result["passed"] is True
    assert result["feature_id"] == "012/017/019/022/025"
    assert result["scenario_count"] == 9
    scenario_ids = {scenario["id"] for scenario in result["scenarios"]}
    assert "knowledge-memory-ground-truth-preserved" in scenario_ids
    assert "knowledge-personal-memory-kg-promotion-blocked" in scenario_ids
    assert "knowledge-rag-kg-semantic-context-grounded" in scenario_ids
    assert "knowledge-rag-kg-downstream-artifact-visible" in scenario_ids
    assert "knowledge-memory-semantic-feedback-review-proposal" in scenario_ids
    assert "knowledge-delegation-parent-memory-handoff" in scenario_ids
    assert "knowledge-compaction-tool-output-provenance" in scenario_ids
    artifact = tmp_path / "runs" / "run-knowledge" / "knowledge_contract.json"
    aggregate = (
        tmp_path
        / "runs"
        / "run-knowledge"
        / "candidates"
        / "knowledge-contract-static"
        / "aggregate.json"
    )
    assert artifact.exists()
    assert aggregate.exists()
    saved = json.loads(artifact.read_text(encoding="utf-8"))
    assert saved["passed_count"] == 9


def test_kg_claim_proposal_requires_evidence_and_semantic_links():
    validation = validate_kg_claim_proposal(
        {
            "source_scope": "personal_memory",
            "metadata": {
                "claim_id": "claim-1",
                "claim_type": "entity_attribute",
                "claim_status": "proposed",
            },
        }
    )

    assert validation["passed"] is False
    assert "missing-kg-proposal-metadata:evidence_refs" in validation["failures"]
    assert "missing-kg-proposal-metadata:semantic_term_ids" in validation["failures"]
    assert "personal-memory-promotion-requires-review" in validation["failures"]


def test_knowledge_context_item_requires_source_and_semantic_metadata():
    validation = validate_knowledge_context_item(
        {
            "id": "kg-claim-1",
            "source": "kg",
            "selected": True,
            "metadata": {
                "source_artifact_id": "artifact-1",
                "chunk_id": "chunk-1",
                "chunk_hash": "sha256:chunk",
                "citation_ref": "S1",
                "semantic_catalog_version": "1.0.0",
                "semantic_term_ids": ("kg_claim",),
            },
        }
    )

    assert validation["passed"] is False
    assert "missing-context-metadata:claim_id" in validation["failures"]
    assert "missing-context-metadata:valid_time_range" in validation["failures"]
