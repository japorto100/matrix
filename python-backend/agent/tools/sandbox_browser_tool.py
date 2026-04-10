# SandboxBrowserTool — exec-12 Phase 1.5 / exec-13 Phase 5
# Browser-Automation in isolierter Sandbox via Playwright.
# HIGH_RISK_TOOL: Output wird automatisch P0/P1/P2 sanitized (sanitizer.py).
# Consent: level=confirm (consent_policy.yaml), Rate Limit: max 3 Calls/Session.

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agent.sandbox.config import BROWSER_SANDBOX
from agent.sandbox.manager import SandboxManager
from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class BrowserInput(BaseModel):
    """Input schema for sandbox browser automation."""

    url: str = Field(
        min_length=1,
        description="URL to navigate to.",
    )
    script: str = Field(
        default="",
        max_length=10000,
        description=(
            "Optional Playwright script to run after page load. "
            "Has access to 'page' object. Example: await page.click('button#load-more')"
        ),
    )
    extract_text: bool = Field(
        default=True,
        description="Extract page text content (body inner text).",
    )
    screenshot: bool = Field(
        default=False,
        description="Take a full-page screenshot (returned as base64 PNG).",
    )


class SandboxBrowserTool(TradingTool):
    """Open a web page in an isolated browser sandbox.

    Uses Playwright inside an OpenSandbox container — isolated from host
    browser and host network. Only allowed domains are reachable.

    Use for: JS-heavy pages, research reports, news scraping.
    """

    input_model = BrowserInput

    @property
    def name(self) -> str:
        return "sandbox_browser"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Open a web page in an isolated browser sandbox with Playwright. "
                "Extracts page text and/or takes screenshots. "
                "Isolated from host browser — only allowed domains reachable. "
                "Use for JS-heavy financial news, research reports, market data pages."
            ),
            "input_schema": BrowserInput.model_json_schema(),
        }

    def to_model_output(self, result: dict) -> dict | str:
        """Truncate browser output — strip base64 screenshots for LLM."""
        stdout = result.get("stdout", "")
        files = result.get("files", [])

        summary: dict = {
            "exit_code": result.get("exit_code", 0),
            "text": stdout[:3000] + ("..." if len(stdout) > 3000 else ""),
            "execution_time_ms": result.get("execution_time_ms", 0),
        }
        if files:
            summary["screenshots"] = [f["name"] for f in files]
        if result.get("stderr"):
            summary["stderr"] = result["stderr"][:300]
        if result.get("error"):
            summary["error"] = result["error"]
        return summary

    async def execute(self, tool_input: dict, ctx: AgentExecutionContext) -> dict:
        params = BrowserInput(**tool_input)

        manager = SandboxManager()
        result = await manager.execute_browser(
            url=params.url,
            script=params.script,
            extract_text=params.extract_text,
            screenshot=params.screenshot,
            config=BROWSER_SANDBOX,
            thread_id=ctx.thread_id,
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "files": result.files,
            "execution_time_ms": result.execution_time_ms,
            "error": result.error,
        }
