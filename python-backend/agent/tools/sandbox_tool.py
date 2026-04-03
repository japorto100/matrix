# SandboxExecuteTool — exec-12 Phase 1.3
# LLM-generierter Code wird in isolierter OpenSandbox ausgefuehrt.
# Consent: level=confirm (consent_policy.yaml), Rate Limit: max 5 Calls/Session.

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agent.sandbox.config import BACKTEST_SANDBOX, CODE_SANDBOX
from agent.sandbox.manager import SandboxManager, SandboxResult
from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class CodeExecuteInput(BaseModel):
    """Input schema for sandbox code execution."""

    code: str = Field(
        min_length=1,
        max_length=50000,
        description="Code to execute in the sandbox.",
    )
    language: str = Field(
        default="python",
        pattern=r"^(python|javascript|js|typescript|ts|bash|shell|go|java)$",
        description="Programming language: python | javascript | typescript | bash | go | java",
    )
    timeout_minutes: int = Field(
        default=10,
        ge=1,
        le=30,
        description="Execution timeout in minutes (1-30). Use >10 for backtesting.",
    )
    files: list[dict[str, str]] | None = Field(
        default=None,
        description=(
            "Optional files to upload into the sandbox before execution. "
            'Format: [{"name": "data.csv", "content_b64": "base64-encoded-content"}]'
        ),
    )


class SandboxExecuteTool(TradingTool):
    """Execute code in an isolated sandbox environment.

    Supports Python (with pandas, numpy, matplotlib, pandas-ta),
    JavaScript, and Bash. Returns stdout, stderr, and any generated files
    (charts as base64 images).

    Use for: data analysis, backtesting, custom indicators, file processing.
    """

    input_model = CodeExecuteInput

    @property
    def name(self) -> str:
        return "sandbox_execute"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Execute code in an isolated sandbox environment. "
                "Supports Python (with pandas, numpy, matplotlib, pandas-ta), "
                "JavaScript, TypeScript, Bash, Go, and Java. Returns stdout, stderr, and any generated files "
                "(charts as base64 images). Use for data analysis, backtesting, "
                "custom indicators, and computation that requires code execution. "
                "Save charts/plots to /tmp/output/ for automatic collection."
            ),
            "input_schema": CodeExecuteInput.model_json_schema(),
        }

    def to_model_output(self, result: dict) -> dict | str:
        """Truncate large outputs to save LLM tokens.

        Full result (with base64 images) goes to UI via tool_results.
        LLM only sees truncated text summary.
        """
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        files = result.get("files", [])

        summary: dict = {
            "exit_code": result.get("exit_code", 0),
            "stdout": stdout[:2000] + ("..." if len(stdout) > 2000 else ""),
            "execution_time_ms": result.get("execution_time_ms", 0),
        }
        if stderr:
            summary["stderr"] = stderr[:500] + ("..." if len(stderr) > 500 else "")
        if files:
            summary["files"] = [{"name": f["name"], "mime": f.get("mime", "")} for f in files]
        if result.get("error"):
            summary["error"] = result["error"]
        return summary

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        params = CodeExecuteInput(**tool_input)

        # Select config: longer timeout for backtesting
        config = BACKTEST_SANDBOX if params.timeout_minutes > 10 else CODE_SANDBOX

        manager = SandboxManager()
        result = await manager.execute_code(
            code=params.code,
            language=params.language,
            config=config,
            thread_id=ctx.thread_id,
            upload_files=params.files,
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "files": result.files,
            "execution_time_ms": result.execution_time_ms,
            "error": result.error,
        }
