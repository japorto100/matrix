"""Agent tools for provider-agnostic report validation and artifact builds."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from agent.tools.base import TradingTool
from reports.contract import (
    Citation,
    ReportManifest,
    build_report_artifacts,
    compute_checksum,
    validate_report_manifest,
)

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext

_REPORT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


class ReportCitationInput(BaseModel):
    citation_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    uri: str = ""
    excerpt: str = ""
    source_type: str = "document"


class ReportArtifactInput(BaseModel):
    report_id: str = Field(
        min_length=1,
        description="Stable report id. Path separators are rejected.",
    )
    title: str = Field(min_length=1)
    owner: str = Field(default="matrix")
    source_markdown: str = Field(
        min_length=1,
        description="Markdown report source with citation markers like [S1].",
    )
    input_sources: list[str] = Field(default_factory=list)
    citations: list[ReportCitationInput] = Field(default_factory=list)
    renderer: Literal["markdown-fallback", "quarkdown"] = "markdown-fallback"
    renderer_version: str = "builtin"


class ReportValidateTool(TradingTool):
    input_model = ReportArtifactInput

    @property
    def name(self) -> str:
        return "report_validate"

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Validate a provider-agnostic report manifest/source pair before publication. "
                "Checks required metadata, citation usage and checksum rules without writing files."
            ),
            "input_schema": ReportArtifactInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict[str, Any], ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = _validated_input(tool_input)
        manifest = _manifest(params, checksum=compute_checksum(params.source_markdown))
        validation = validate_report_manifest(
            manifest,
            source_markdown=params.source_markdown,
        )
        return {
            "ok": validation["passed"],
            "report_id": manifest.report_id,
            "title": manifest.title,
            "renderer": manifest.renderer,
            "checksum": manifest.checksum,
            "validation": validation,
            "raw_execution_allowed": False,
        }

    def to_model_output(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": result.get("ok"),
            "report_id": result.get("report_id"),
            "validation": result.get("validation"),
            "checksum": result.get("checksum"),
            "raw_execution_allowed": False,
        }


class ReportBuildTool(TradingTool):
    input_model = ReportArtifactInput

    @property
    def name(self) -> str:
        return "report_build"

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Build deterministic report artifacts from Markdown source and citations. "
                "Writes only under MATRIX_REPORT_ARTIFACT_DIR/data/reports using the safe "
                "markdown-fallback renderer until Quarkdown is explicitly promoted."
            ),
            "input_schema": ReportArtifactInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict[str, Any], ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = _validated_input(tool_input)
        renderer = "markdown-fallback" if params.renderer == "quarkdown" else params.renderer
        manifest = _manifest(
            params,
            checksum=compute_checksum(params.source_markdown),
            renderer=renderer,
        )
        result = build_report_artifacts(
            source_markdown=params.source_markdown,
            manifest=manifest,
            output_dir=_report_root(),
        )
        return {
            "ok": bool(result.get("passed")),
            "report_id": manifest.report_id,
            "title": manifest.title,
            "renderer": manifest.renderer,
            "validation": result.get("validation"),
            "artifacts": result.get("artifacts", {}),
            "quarkdown_promoted": False,
        }

    def to_model_output(self, result: dict[str, Any]) -> dict[str, Any]:
        artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), dict) else {}
        return {
            "ok": result.get("ok"),
            "report_id": result.get("report_id"),
            "renderer": result.get("renderer"),
            "validation": result.get("validation"),
            "manifest": artifacts.get("manifest"),
            "html": artifacts.get("html"),
            "quarkdown_promoted": False,
        }


def _validated_input(tool_input: dict[str, Any]) -> ReportArtifactInput:
    params = ReportArtifactInput(**tool_input)
    if not _REPORT_ID_RE.fullmatch(params.report_id):
        raise ValueError("report_id must be a simple path-safe id")
    if not params.input_sources:
        raise ValueError("input_sources must include at least one source artifact")
    if not params.citations:
        raise ValueError("citations must include at least one citation")
    return params


def _manifest(
    params: ReportArtifactInput,
    *,
    checksum: str,
    renderer: Literal["markdown-fallback", "quarkdown"] | None = None,
) -> ReportManifest:
    return ReportManifest(
        report_id=params.report_id,
        title=params.title,
        owner=params.owner,
        input_sources=tuple(params.input_sources),
        citations=tuple(
            Citation(
                citation_id=item.citation_id,
                source_id=item.source_id,
                title=item.title,
                uri=item.uri,
                excerpt=item.excerpt,
                source_type=item.source_type,
            )
            for item in params.citations
        ),
        renderer=renderer or params.renderer,
        renderer_version=params.renderer_version,
        checksum=checksum,
    )


def _report_root() -> Path:
    return Path(os.environ.get("MATRIX_REPORT_ARTIFACT_DIR", "data/reports"))
