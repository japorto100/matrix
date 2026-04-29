from __future__ import annotations

import pytest

from agent.context import AgentExecutionContext
from agent.roles import TRADING_ROLE_TOOLS, TradingRole
from agent.tools.registry import ToolRegistry
from agent.tools.report_artifacts import ReportBuildTool, ReportValidateTool


def _ctx() -> AgentExecutionContext:
    return AgentExecutionContext(
        user_id="u1",
        thread_id="t1",
        model="test",
        system_prompt="",
        tools=(),
        user_role="analyst",
    )


def _input() -> dict:
    return {
        "report_id": "report-1",
        "title": "RAG Summary",
        "owner": "matrix",
        "source_markdown": "# RAG Summary\nEvidence [S1]",
        "input_sources": ["artifact-a"],
        "citations": [
            {
                "citation_id": "S1",
                "source_id": "artifact-a",
                "title": "Artifact A",
                "uri": "doc://artifact-a",
            }
        ],
    }


def test_report_tools_registered_for_agent_runners():
    registry = ToolRegistry.load()

    assert registry.lookup("report_validate") is not None
    assert registry.lookup("report_build") is not None
    assert "report_validate" in TRADING_ROLE_TOOLS[TradingRole.RESEARCHER]
    assert "report_build" in TRADING_ROLE_TOOLS[TradingRole.RESEARCHER]


@pytest.mark.asyncio
async def test_report_validate_checks_source_and_citations():
    result = await ReportValidateTool().execute(_input(), _ctx())

    assert result["ok"] is True
    assert result["validation"]["passed"] is True
    assert result["raw_execution_allowed"] is False


@pytest.mark.asyncio
async def test_report_build_writes_only_configured_artifact_root(tmp_path, monkeypatch):
    monkeypatch.setenv("MATRIX_REPORT_ARTIFACT_DIR", str(tmp_path))

    result = await ReportBuildTool().execute(_input(), _ctx())

    assert result["ok"] is True
    assert result["renderer"] == "markdown-fallback"
    assert result["quarkdown_promoted"] is False
    assert result["artifacts"]["manifest"].startswith(str(tmp_path))
    assert (tmp_path / "report-1" / "manifest.json").exists()


@pytest.mark.asyncio
async def test_report_build_surfaces_validation_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("MATRIX_REPORT_ARTIFACT_DIR", str(tmp_path))
    payload = {**_input(), "source_markdown": "# RAG Summary\nNo citation"}

    result = await ReportBuildTool().execute(payload, _ctx())

    assert result["ok"] is False
    assert "citation-not-used:S1" in result["validation"]["failures"]
    assert not (tmp_path / "report-1" / "manifest.json").exists()


@pytest.mark.asyncio
async def test_report_build_rejects_path_traversal_id(tmp_path, monkeypatch):
    monkeypatch.setenv("MATRIX_REPORT_ARTIFACT_DIR", str(tmp_path))
    payload = {**_input(), "report_id": "../escape"}

    with pytest.raises(ValueError):
        await ReportBuildTool().execute(payload, _ctx())
