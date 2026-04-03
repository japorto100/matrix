# File Analyze Tool — exec-12 Phase 1.4
# Uploads a user-provided file into a sandbox, runs analysis code, returns result.
# The file is stored temporarily in working memory (base64) by app.py attachment routing.
# Agent decides what analysis code to generate based on the user's prompt.

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, override

from pydantic import BaseModel, Field

from agent.audit.logger import AuditAction, audit_duration, audit_log, audit_timer
from agent.sandbox.manager import SandboxManager
from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class FileAnalyzeInput(BaseModel):
    file_ref: str = Field(
        ...,
        description=(
            "Reference key for the uploaded file in working memory "
            "(provided in the system message when user uploads a file)."
        ),
    )
    analysis_code: str = Field(
        ...,
        description=(
            "Python code to analyze the file. The file is available at "
            "/tmp/uploads/<filename> inside the sandbox. "
            "Use pandas, numpy, matplotlib as needed. "
            "Print results to stdout or save charts to /tmp/output/."
        ),
    )


class FileAnalyzeTool(TradingTool):
    """Analyze a user-uploaded file (CSV, Excel, JSON, code) in an isolated sandbox.

    The file is copied into the sandbox, analysis code runs, sandbox is destroyed.
    The original file never touches the agent process directly.

    Consent level: confirm — user must approve each analysis.
    Audit: SANDBOX_EXEC events logged with file_ref, code preview, result.
    """

    input_model: type[BaseModel] | None = FileAnalyzeInput

    def __init__(self) -> None:
        self._manager: SandboxManager | None = None

    @property
    @override
    def name(self) -> str:
        return "file_analyze"

    @override
    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Analyze a user-uploaded file in an isolated sandbox. "
                "Use this when the user uploads a CSV, Excel, JSON, or code file "
                "and wants analysis, statistics, charts, or data processing. "
                "The file is available at /tmp/uploads/<filename> in the sandbox. "
                "Write Python code using pandas, numpy, matplotlib to analyze it. "
                "Print results to stdout. The sandbox is destroyed after execution."
            ),
            "input_schema": FileAnalyzeInput.model_json_schema(),
        }

    def _get_manager(self) -> SandboxManager:
        if self._manager is None:
            self._manager = SandboxManager()
        return self._manager

    @override
    async def execute(self, tool_input: dict[str, Any], ctx: AgentExecutionContext) -> dict[str, Any]:
        from agent.working_memory import working_memory_get_entry

        params = FileAnalyzeInput(**tool_input)
        manager = self._get_manager()

        # Retrieve file from working memory
        file_entry = await working_memory_get_entry(ctx.thread_id, params.file_ref)
        if file_entry is None:
            return {"error": f"File reference '{params.file_ref}' not found in working memory."}

        if not isinstance(file_entry, dict):
            return {"error": f"Invalid file entry format for '{params.file_ref}'."}

        file_b64: str = file_entry.get("base64", "")
        file_name: str = file_entry.get("name", "uploaded_file")
        if not file_b64:
            return {"error": f"No file data in '{params.file_ref}'."}

        file_bytes = base64.b64decode(file_b64)

        start = audit_timer()

        result = await manager.execute_file(
            file_content=file_bytes,
            file_name=file_name,
            analysis_code=params.analysis_code,
        )

        duration = audit_duration(start)

        await audit_log(
            action=AuditAction.SANDBOX_EXEC,
            agent_id=ctx.agent_class,
            thread_id=ctx.thread_id,
            tool_name=self.name,
            input_data={
                "file_ref": params.file_ref,
                "file_name": file_name,
                "code_preview": params.analysis_code[:500],
            },
            output_data=result.to_dict(),
            duration_ms=duration,
            success=result.success,
        )

        return result.to_dict()

    @override
    def to_model_output(self, result: dict[str, Any]) -> dict[str, Any] | str:
        """Trim large output for the LLM context window."""
        output = dict(result)
        for key in ("stdout", "stderr", "result"):
            val = output.get(key, "")
            if isinstance(val, str) and len(val) > 2000:
                output[key] = val[:2000] + f"\n... [truncated, {len(val)} chars total]"
        return output
