from __future__ import annotations

from typing import Any

import pytest

from agent.context import AgentExecutionContext
from agent.tools.registry import ToolRegistry
from agent.tools.retrieve_context import RetrieveContextTool
from retrieval.api import RetrievalResult


def _ctx() -> AgentExecutionContext:
    return AgentExecutionContext(
        user_id="alice",
        thread_id="thread-rag",
        model="test-model",
        system_prompt="",
        tools=(),
        user_role="analyst",
    )


def test_retrieve_context_registered_for_agent_runners() -> None:
    registry = ToolRegistry.load()

    tool = registry.lookup("retrieve_context")

    assert isinstance(tool, RetrieveContextTool)
    assert tool.definition()["input_schema"]["properties"]["query"]


@pytest.mark.asyncio
async def test_retrieve_context_returns_artifacts_and_compact_model_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_retrieve(query: str, **kwargs: Any) -> RetrievalResult:
        assert query == "ground tool success"
        assert kwargs["semantic_filter"]["semantic_term_ids"] == ["rag_citation"]
        assert kwargs["require_context_provenance"] is True
        return RetrievalResult(
            context="Agent tool success rate is grounded in S1.",
            hits=[
                {
                    "id": "kg-claim-tool-success-rate",
                    "content": "full KG content",
                    "source": "kg",
                    "score": 0.9,
                    "source_uri": "kg://claim/tool-success",
                    "metadata": {
                        "claim_id": "kg-claim-tool-success-rate",
                        "claim_type": "entity_attribute",
                        "kg_path": ["Agent", "MEASURES", "tool_success_rate"],
                        "source_artifact_id": "artifact-agent-audit",
                        "chunk_id": "chunk-tool-success",
                        "chunk_hash": "sha256:tool-success",
                        "citation_ref": "S1",
                        "semantic_catalog_version": "1.0.0",
                        "semantic_term_ids": ["rag_citation"],
                        "provenance_status": "complete",
                    },
                }
            ],
            intent="hybrid",
            references=[
                {
                    "id": "kg-claim-tool-success-rate",
                    "source": "kg",
                    "metadata": {
                        "citation_ref": "S1",
                        "provenance_status": "complete",
                    },
                }
            ],
            source_candidates=[
                {
                    "id": "candidate-1",
                    "source": "kg",
                    "source_uri": "kg://claim/tool-success",
                    "retrieval_lane": "kg",
                    "provenance_status": "complete",
                    "metadata": {"source_artifact_id": "artifact-agent-audit"},
                }
            ],
            degraded=False,
            degraded_reasons=[],
            runtime_events=[
                {
                    "kind": "rag",
                    "status": "completed",
                    "name": "rag.retrieve.completed",
                    "metadata": {"selected_context_ids": ["kg-claim-tool-success-rate"]},
                }
            ],
        )

    monkeypatch.setattr("agent.tools.retrieve_context.retrieve", fake_retrieve)
    tool = RetrieveContextTool()

    result = await tool.execute(
        {
            "query": "ground tool success",
            "mode": "hybrid",
            "semantic_context": {"semantic_term_ids": ["rag_citation"]},
        },
        _ctx(),
    )
    model_output = tool.to_model_output(result)

    assert result["ok"] is True
    assert {item["name"] for item in result["files"]} == {
        "rag-kg-sources.json",
        "kg-paths.json",
    }
    assert result["runtime_events"][-1]["name"] == "artifact.rag_kg_sources.ready"
    assert model_output["artifact_files"] == [
        {"name": "rag-kg-sources.json", "mime": "application/json"},
        {"name": "kg-paths.json", "mime": "application/json"},
    ]
    assert "hits" not in model_output
    assert model_output["references"][0]["citation_ref"] == "S1"
