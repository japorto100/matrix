from __future__ import annotations

import pytest

from agent.context import AgentExecutionContext
from agent.tools.registry import ToolRegistry
from agent.tools.semantic_lookup import SemanticLookupTool


def _ctx(*, tenant_id: str = "", role: str = "analyst") -> AgentExecutionContext:
    return AgentExecutionContext(
        user_id="alice",
        thread_id="thread-semantic",
        model="test-model",
        system_prompt="",
        tools=(),
        user_role=role,
        market_snapshot={"tenant_id": tenant_id} if tenant_id else None,
    )


def test_semantic_lookup_registered_for_agent_runners():
    registry = ToolRegistry.load()

    tool = registry.lookup("semantic_lookup")

    assert isinstance(tool, SemanticLookupTool)
    assert tool.definition()["input_schema"]["properties"]["phrase"]


@pytest.mark.asyncio
async def test_semantic_lookup_metric_returns_contract_with_tenant_scope():
    tool = SemanticLookupTool()

    result = await tool.execute(
        {"phrase": "tool success rate", "tenant_id": "tenant-a"},
        _ctx(),
    )

    assert result["status"] == "matched_metric"
    assert result["authoritative"] is True
    assert result["raw_sql_allowed"] is False
    assert result["metric_plan"]["allowed"] is True
    assert result["metric_plan"]["semantic_contract"]["source_table"] == "agent.audit_events"
    assert result["answer_template"]["freshness"] == "15m"


@pytest.mark.asyncio
async def test_semantic_lookup_metric_fails_closed_without_scope():
    tool = SemanticLookupTool()

    result = await tool.execute({"phrase": "tool success rate"}, _ctx())

    assert result["status"] == "metric_permission_denied"
    assert result["authoritative"] is False
    assert result["refusal_reason"] == "missing-tenant-context"
    assert result["metric_plan"]["raw_sql_allowed"] is False


@pytest.mark.asyncio
async def test_semantic_lookup_unknown_phrase_returns_refusal_guidance():
    tool = SemanticLookupTool()

    result = await tool.execute({"phrase": "made up pnl velocity"}, _ctx())

    assert result["status"] == "not_found"
    assert result["authoritative"] is False
    assert result["refusal_reason"] == "no-authoritative-definition"
    assert "should not invent" in result["answer_template"]


@pytest.mark.asyncio
async def test_semantic_lookup_unknown_phrase_returns_candidates_without_authority():
    tool = SemanticLookupTool()

    result = await tool.execute({"phrase": "tool success ratio"}, _ctx())
    model_output = tool.to_model_output(result)

    assert result["status"] == "not_found"
    assert result["authoritative"] is False
    assert result["suggested_phrases"][0]["id"] == "agent_tool_success_rate"
    assert model_output["candidate_matches"] == [
        {
            "type": "metric",
            "id": "agent_tool_success_rate",
            "name": "Agent tool success rate",
            "score": result["suggested_phrases"][0]["score"],
            "matched_terms": ["success", "tool"],
            "authoritative": False,
            "requires_confirmation": True,
        }
    ]


@pytest.mark.asyncio
async def test_semantic_lookup_model_output_is_compact():
    tool = SemanticLookupTool()
    result = await tool.execute(
        {"phrase": "tool success rate", "tenant_id": "tenant-a"},
        _ctx(),
    )

    model_output = tool.to_model_output(result)

    assert model_output["status"] == "matched_metric"
    assert model_output["metric_plan"]["semantic_contract"]["source_refs"] == [
        "feature-014",
        "feature-016",
    ]
    assert model_output["metric_plan"]["metric_id"] == "agent_tool_success_rate"
    assert model_output["metric_plan"]["semantic_catalog_version"] == "1.0.0"
    assert "matches" not in model_output


@pytest.mark.asyncio
async def test_semantic_lookup_term_output_carries_rag_kg_handoff_metadata():
    tool = SemanticLookupTool()
    result = await tool.execute({"phrase": "RAG citation"}, _ctx())

    model_output = tool.to_model_output(result)

    assert model_output["status"] == "matched_term"
    assert model_output["semantic_context"] == {
        "semantic_catalog_version": "1.0.0",
        "semantic_term_ids": ["rag_citation"],
        "kg_claim_types": [],
        "rag_source_classes": ["document_chunk", "kg_claim"],
        "source_refs": ["feature-019", "retrieval/verifiers/citation.py"],
    }
    assert "matches" not in model_output
