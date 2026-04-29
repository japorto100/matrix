# Sandbox Manager — exec-12 Phase 1.2
# Lifecycle: Create → Execute → Collect Result → Destroy
# Reusable by sandbox_execute and sandbox_browser tools.

from __future__ import annotations

import base64
import hashlib
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import trace

from agent.audit.logger import AuditAction, audit_duration, audit_log, audit_timer
from agent.errors import CriticalError, RepairableError
from agent.sandbox.config import (
    CODE_SANDBOX,
    SandboxConfig,
    get_sandbox_connection_config,
    get_sandbox_ready_timeout,
    get_sandbox_server_url,
)

logger = logging.getLogger(__name__)

# Language mapping for OpenSandbox CodeInterpreter
_LANGUAGE_MAP: dict[str, str] = {
    "python": "PYTHON",
    "javascript": "TYPESCRIPT",  # OpenSandbox uses TS runtime for JS
    "js": "TYPESCRIPT",
    "typescript": "TYPESCRIPT",
    "ts": "TYPESCRIPT",
    "bash": "PYTHON",  # Bash executed via Python subprocess wrapper
    "shell": "PYTHON",
    "go": "GO",
    "java": "JAVA",
}

# Maximum output sizes (bytes) to prevent memory issues
_MAX_STDOUT = 50_000
_MAX_STDERR = 10_000
_MAX_FILE_SIZE = 5_000_000  # 5 MB per file
_MAX_DIAGNOSTIC = 8_000


@dataclass
class SandboxResult:
    """Result from sandbox execution."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    files: list[dict[str, str]] = field(
        default_factory=list
    )  # [{name, data_b64, mime}]
    sandbox_id: str = ""
    diagnostics: dict[str, str] = field(default_factory=dict)
    execution_time_ms: float = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.error

    def to_dict(self) -> dict[str, Any]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "files": self.files,
            "sandbox_id": self.sandbox_id,
            "diagnostics": self.diagnostics,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "success": self.success,
        }


class SandboxManager:
    """Manages OpenSandbox lifecycle. Stateless — create one per tool call.

    Usage:
        manager = SandboxManager()
        result = await manager.execute_code(code="print('hello')", language="python", config=CODE_SANDBOX)
    """

    async def execute_code(
        self,
        *,
        code: str,
        language: str = "python",
        config: SandboxConfig,
        thread_id: str = "",
        upload_files: list[dict[str, str]] | None = None,
    ) -> SandboxResult:
        """Execute code in an isolated sandbox.

        Args:
            code: Source code to execute.
            language: python | javascript | bash
            config: Sandbox configuration (image, timeout, resources).
            thread_id: For audit logging.
            upload_files: Optional files to upload: [{"name": "data.csv", "content_b64": "..."}]

        Returns:
            SandboxResult with stdout, stderr, files, execution_time_ms.

        Raises:
            RepairableError: Timeout, code error, server temporarily unavailable.
            CriticalError: Server unreachable, image not found.
        """
        start = audit_timer()
        sandbox = None
        sandbox_id = ""
        diagnostics: dict[str, str] = {}
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
        trace_id = _current_trace_id()

        try:
            from opensandbox import Sandbox

            try:
                from opensandbox_code_interpreter import (
                    CodeInterpreter,
                    SupportedLanguage,
                )
            except ImportError:
                from code_interpreter import CodeInterpreter, SupportedLanguage

            # 1. Create sandbox
            sandbox = await Sandbox.create(
                config.image or "opensandbox/code-interpreter:v1.0.2",
                entrypoint=list(config.entrypoint),
                timeout=config.timeout,
                ready_timeout=get_sandbox_ready_timeout(),
                connection_config=get_sandbox_connection_config(),
            )
            sandbox_id = getattr(sandbox, "id", "")
            logger.info(
                "Sandbox created: %s (image=%s, timeout=%s)",
                sandbox.id,
                config.image,
                config.timeout,
            )

            # 2. Upload files if provided (exec-12 Phase 1.4)
            if upload_files:
                await self._upload_files(sandbox, upload_files)

            # 3. Execute code
            if language == "bash":
                result = await self._execute_bash(sandbox, code, config)
            else:
                lang_enum = getattr(
                    SupportedLanguage, _LANGUAGE_MAP.get(language, "PYTHON")
                )
                interpreter = await CodeInterpreter.create(sandbox=sandbox)
                ctx = await interpreter.codes.create_context(lang_enum)
                exec_result = await interpreter.codes.run(code, context=ctx)

                stdout_parts = []
                if exec_result.logs and exec_result.logs.stdout:
                    for msg in exec_result.logs.stdout:
                        stdout_parts.append(
                            msg.text if hasattr(msg, "text") else str(msg)
                        )
                stderr_parts = []
                if exec_result.logs and exec_result.logs.stderr:
                    for msg in exec_result.logs.stderr:
                        stderr_parts.append(
                            msg.text if hasattr(msg, "text") else str(msg)
                        )

                # Expression result (last expression value)
                if exec_result.result:
                    for r in exec_result.result:
                        if hasattr(r, "text") and r.text:
                            stdout_parts.append(r.text)

                result = SandboxResult(
                    stdout="\n".join(stdout_parts)[:_MAX_STDOUT],
                    stderr="\n".join(stderr_parts)[:_MAX_STDERR],
                    exit_code=0 if not stderr_parts else 1,
                )

            result.sandbox_id = sandbox_id
            result.diagnostics = await self._collect_diagnostics(
                sandbox_id=sandbox_id,
                scope=trace_id,
            )

            # 4. Collect generated files (charts, images)
            result.files = await self._collect_output_files(sandbox)
            result.execution_time_ms = audit_duration(start)

            # 5. Audit
            await audit_log(
                action=AuditAction.SANDBOX_EXEC,
                thread_id=thread_id,
                tool_name="sandbox_execute",
                input_data={
                    "language": language,
                    "code_hash": code_hash,
                    "code_len": len(code),
                },
                output_data={
                    "exit_code": result.exit_code,
                    "stdout_len": len(result.stdout),
                    "sandbox_id": result.sandbox_id,
                    "trace_id": trace_id,
                    "file_count": len(result.files),
                    "diagnostic_sizes": _diagnostic_sizes(result.diagnostics),
                },
                duration_ms=result.execution_time_ms,
                success=result.exit_code == 0,
            )

            return result

        except ImportError as e:
            raise CriticalError(
                f"OpenSandbox SDK not installed: {e}. "
                "Install with: uv pip install opensandbox opensandbox-code-interpreter"
            ) from e
        except ConnectionError as e:
            raise CriticalError(
                f"OpenSandbox server unreachable at {get_sandbox_server_url()}: {e}. "
                "Start with: docker-compose --profile sandbox up opensandbox-server"
            ) from e
        except TimeoutError as e:
            elapsed = audit_duration(start)
            diagnostics = await self._safe_collect_diagnostics(sandbox_id=sandbox_id, scope=trace_id)
            await audit_log(
                action=AuditAction.SANDBOX_EXEC,
                thread_id=thread_id,
                tool_name="sandbox_execute",
                input_data={"language": language, "code_hash": code_hash},
                duration_ms=elapsed,
                success=False,
                output_data={
                    "error": "timeout",
                    "sandbox_id": sandbox_id,
                    "trace_id": trace_id,
                    "diagnostic_sizes": _diagnostic_sizes(diagnostics),
                },
            )
            raise RepairableError(
                f"Sandbox execution timed out after {config.timeout.total_seconds():.0f}s. "
                "Try simpler code or increase timeout."
            ) from e
        except Exception as e:
            # Catch-all for SDK errors (image not found, resource limits, etc.)
            error_msg = str(e)
            logger.warning("Sandbox execution failed: %s", error_msg)
            elapsed = audit_duration(start)
            diagnostics = await self._safe_collect_diagnostics(
                sandbox_id=sandbox_id,
                scope=trace_id,
            )
            await audit_log(
                action=AuditAction.SANDBOX_EXEC,
                thread_id=thread_id,
                tool_name="sandbox_execute",
                input_data={"language": language, "code_hash": code_hash},
                duration_ms=elapsed,
                success=False,
                output_data={
                    "error": error_msg,
                    "sandbox_id": sandbox_id,
                    "trace_id": trace_id,
                    "diagnostic_sizes": _diagnostic_sizes(diagnostics),
                },
            )
            if "not found" in error_msg.lower() or "image" in error_msg.lower():
                raise CriticalError(f"Sandbox image not found: {error_msg}") from e
            raise RepairableError(f"Sandbox execution failed: {error_msg}") from e
        finally:
            if sandbox is not None:
                try:
                    await sandbox.kill()
                    logger.info("Sandbox destroyed: %s", sandbox.id)
                except Exception as kill_err:
                    logger.warning("Failed to destroy sandbox: %s", kill_err)

    async def execute_file(
        self,
        *,
        file_content: bytes,
        file_name: str,
        analysis_code: str,
        thread_id: str = "",
    ) -> SandboxResult:
        """Analyze an uploaded file by staging it under `/tmp/uploads/`.

        `FileAnalyzeTool` historically called this method, while the manager
        only exposed `execute_code(upload_files=...)`. Keep the public helper so
        file-analysis uses the same sandbox lifecycle and output collection as
        `sandbox_execute`.
        """
        encoded = base64.b64encode(file_content).decode()
        return await self.execute_code(
            code=analysis_code,
            language="python",
            config=CODE_SANDBOX,
            thread_id=thread_id,
            upload_files=[{"name": file_name, "content_b64": encoded}],
        )

    async def execute_browser(
        self,
        *,
        url: str,
        script: str = "",
        extract_text: bool = True,
        screenshot: bool = False,
        config: SandboxConfig,
        thread_id: str = "",
    ) -> SandboxResult:
        """Execute browser automation in an isolated sandbox.

        Creates a Playwright script, runs it in the browser sandbox,
        and collects extracted text and/or screenshots.

        Args:
            url: URL to navigate to.
            script: Optional additional Playwright script.
            extract_text: Whether to extract page text content.
            screenshot: Whether to take a screenshot.
            config: Browser sandbox config.
            thread_id: For audit logging.
        """
        # Build Playwright wrapper script
        playwright_code = _build_playwright_script(
            url=url,
            user_script=script,
            extract_text=extract_text,
            screenshot=screenshot,
        )

        start = audit_timer()
        sandbox = None
        sandbox_id = ""
        diagnostics: dict[str, str] = {}
        trace_id = _current_trace_id()

        try:
            from opensandbox import Sandbox

            try:
                from opensandbox_code_interpreter import (
                    CodeInterpreter,
                    SupportedLanguage,
                )
            except ImportError:
                from code_interpreter import CodeInterpreter, SupportedLanguage

            sandbox = await Sandbox.create(
                config.image or "opensandbox/code-interpreter:v1.0.2",
                entrypoint=list(config.entrypoint),
                timeout=config.timeout,
                ready_timeout=get_sandbox_ready_timeout(),
                connection_config=get_sandbox_connection_config(),
            )
            logger.info("Browser sandbox created: %s", sandbox.id)
            sandbox_id = getattr(sandbox, "id", "")

            interpreter = await CodeInterpreter.create(sandbox=sandbox)
            ctx = await interpreter.codes.create_context(SupportedLanguage.PYTHON)
            exec_result = await interpreter.codes.run(playwright_code, context=ctx)

            stdout_parts = []
            if exec_result.logs and exec_result.logs.stdout:
                for msg in exec_result.logs.stdout:
                    stdout_parts.append(msg.text if hasattr(msg, "text") else str(msg))
            stderr_parts = []
            if exec_result.logs and exec_result.logs.stderr:
                for msg in exec_result.logs.stderr:
                    stderr_parts.append(msg.text if hasattr(msg, "text") else str(msg))

            result = SandboxResult(
                stdout="\n".join(stdout_parts)[:_MAX_STDOUT],
                stderr="\n".join(stderr_parts)[:_MAX_STDERR],
                exit_code=0 if not stderr_parts else 1,
            )
            result.sandbox_id = sandbox_id
            result.diagnostics = await self._collect_diagnostics(
                sandbox_id=sandbox_id,
                scope=trace_id,
            )

            # Collect screenshots
            result.files = await self._collect_output_files(
                sandbox, directory="/tmp/screenshots"
            )
            result.execution_time_ms = audit_duration(start)

            await audit_log(
                action=AuditAction.SANDBOX_EXEC,
                thread_id=thread_id,
                tool_name="sandbox_browser",
                input_data={
                    "url": url,
                    "extract_text": extract_text,
                    "screenshot": screenshot,
                },
                output_data={
                    "exit_code": result.exit_code,
                    "stdout_len": len(result.stdout),
                    "sandbox_id": result.sandbox_id,
                    "trace_id": trace_id,
                    "file_count": len(result.files),
                    "diagnostic_sizes": _diagnostic_sizes(result.diagnostics),
                },
                duration_ms=result.execution_time_ms,
                success=result.exit_code == 0,
            )

            return result

        except ImportError as e:
            raise CriticalError(f"OpenSandbox SDK not installed: {e}") from e
        except ConnectionError as e:
            raise CriticalError(
                f"OpenSandbox server unreachable at {get_sandbox_server_url()}: {e}"
            ) from e
        except TimeoutError as e:
            diagnostics = await self._safe_collect_diagnostics(
                sandbox_id=sandbox_id,
                scope=trace_id,
            )
            await audit_log(
                action=AuditAction.SANDBOX_EXEC,
                thread_id=thread_id,
                tool_name="sandbox_browser",
                input_data={
                    "url": url,
                    "extract_text": extract_text,
                    "screenshot": screenshot,
                    "trace_id": trace_id,
                },
                duration_ms=audit_duration(start),
                success=False,
                output_data={
                    "error": "timeout",
                    "sandbox_id": sandbox_id,
                    "trace_id": trace_id,
                    "diagnostic_sizes": _diagnostic_sizes(diagnostics),
                },
            )
            raise RepairableError(
                f"Browser sandbox timed out after {config.timeout.total_seconds():.0f}s"
            ) from e
        except Exception as e:
            error_msg = str(e)
            logger.warning("Browser sandbox failed: %s", error_msg)
            diagnostics = await self._safe_collect_diagnostics(
                sandbox_id=sandbox_id,
                scope=trace_id,
            )
            await audit_log(
                action=AuditAction.SANDBOX_EXEC,
                thread_id=thread_id,
                tool_name="sandbox_browser",
                input_data={
                    "url": url,
                    "extract_text": extract_text,
                    "screenshot": screenshot,
                    "trace_id": trace_id,
                },
                duration_ms=audit_duration(start),
                success=False,
                output_data={
                    "error": error_msg,
                    "sandbox_id": sandbox_id,
                    "trace_id": trace_id,
                    "diagnostic_sizes": _diagnostic_sizes(diagnostics),
                },
            )
            if "not found" in error_msg.lower() or "image" in error_msg.lower():
                raise CriticalError(f"Browser image not found: {error_msg}") from e
            raise RepairableError(f"Browser sandbox failed: {error_msg}") from e
        finally:
            if sandbox is not None:
                try:
                    await sandbox.kill()
                except Exception as kill_err:
                    logger.warning("Failed to destroy browser sandbox: %s", kill_err)

    # ── Private helpers ────────────────────────────────────────────────────

    async def _upload_files(self, sandbox: Any, files: list[dict[str, str]]) -> None:
        """Upload files into the sandbox filesystem."""
        from opensandbox.models import WriteEntry

        entries = []
        for f in files:
            name = f.get("name", "upload.dat")
            content_b64 = f.get("content_b64", "")
            try:
                data = base64.b64decode(content_b64)
            except Exception:
                data = content_b64.encode()
            entries.append(WriteEntry(path=f"/tmp/uploads/{name}", data=data, mode=644))

        if entries:
            await sandbox.files.write_files(entries)
            logger.info("Uploaded %d files to sandbox", len(entries))

    async def _execute_bash(
        self, sandbox: Any, code: str, config: SandboxConfig
    ) -> SandboxResult:
        """Execute bash code via sandbox.commands.run()."""
        execution = await sandbox.commands.run(code)
        stdout = ""
        stderr = ""
        if execution.logs:
            if execution.logs.stdout:
                stdout = "\n".join(
                    msg.text if hasattr(msg, "text") else str(msg)
                    for msg in execution.logs.stdout
                )[:_MAX_STDOUT]
            if execution.logs.stderr:
                stderr = "\n".join(
                    msg.text if hasattr(msg, "text") else str(msg)
                    for msg in execution.logs.stderr
                )[:_MAX_STDERR]
        return SandboxResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=execution.exit_code if hasattr(execution, "exit_code") else 0,
        )

    async def _collect_output_files(
        self, sandbox: Any, directory: str = "/tmp/output"
    ) -> list[dict[str, str]]:
        """Collect generated files (charts, screenshots) as base64."""
        files: list[dict[str, str]] = []
        try:
            # List files in the output directory
            listing = await sandbox.commands.run(
                f"ls -1 {directory} 2>/dev/null || true"
            )
            if not listing.logs or not listing.logs.stdout:
                return files

            for msg in listing.logs.stdout:
                filename = (msg.text if hasattr(msg, "text") else str(msg)).strip()
                if not filename:
                    continue
                filepath = f"{directory}/{filename}"
                try:
                    content = await sandbox.files.read_file(filepath)
                    if isinstance(content, bytes):
                        if len(content) > _MAX_FILE_SIZE:
                            logger.warning(
                                "File %s too large (%d bytes), skipping",
                                filename,
                                len(content),
                            )
                            continue
                        data_b64 = base64.b64encode(content).decode()
                    else:
                        data_b64 = base64.b64encode(content.encode()).decode()

                    # Infer MIME type from extension
                    mime = _infer_mime(filename)
                    files.append({"name": filename, "data_b64": data_b64, "mime": mime})
                except Exception as e:
                    logger.warning("Failed to read file %s: %s", filepath, e)
        except Exception as e:
            logger.debug("No output files collected: %s", e)

        return files

    async def _collect_diagnostics(
        self, sandbox_id: str, trace_id: str
    ) -> dict[str, str]:
        """Collect lightweight diagnostics from OpenSandbox lifecycle APIs."""
        if not sandbox_id:
            return {}

        base_url = get_sandbox_server_url().rstrip("/")
        scopes = ("logs", "events")
        diagnostic_scope = "all"

        try:
            import httpx

            headers: dict[str, str] = {"X-Request-ID": trace_id}
            api_key = os.environ.get("OPEN_SANDBOX_API_KEY") or os.environ.get(
                "OPENSANDBOX_API_KEY"
            )
            if api_key:
                headers["OPEN-SANDBOX-API-KEY"] = api_key

            diagnostics: dict[str, str] = {}
            async with httpx.AsyncClient() as client:
                for scope in scopes:
                    response = await client.get(
                        f"{base_url}/v1/sandboxes/{sandbox_id}/diagnostics/{scope}",
                        headers=headers,
                        params={"scope": diagnostic_scope},
                        timeout=5.0,
                    )
                    if response.status_code == 200:
                        value = response.text
                        try:
                            payload = response.json()
                            if isinstance(payload, dict):
                                content = payload.get("content")
                                if isinstance(content, str):
                                    value = content
                                elif isinstance(payload.get("contentUrl"), str):
                                    content_url = payload["contentUrl"]
                                    if content_url:
                                        try:
                                            content_response = await client.get(
                                                content_url, headers=headers, timeout=5.0
                                            )
                                            if content_response.status_code == 200:
                                                value = content_response.text
                                            else:
                                                value = (
                                                    f"contentUrl={content_url} -> "
                                                    f"HTTP {content_response.status_code}"
                                                )
                                        except Exception as error:
                                            value = (
                                                f"contentUrl fetch failed for {scope}: "
                                                f"{error}"
                                            )
                        except ValueError:
                            # Keep raw response body when JSON parse fails.
                            pass
                    else:
                        value = (
                            f"HTTP {response.status_code}: "
                            f"{response.text[:320]}"
                        )
                    diagnostics[scope] = _truncate_diagnostic_text(value)
                    diagnostics[f"{scope}_request_id"] = response.headers.get(
                        "x-request-id", ""
                    )
            return diagnostics
        except Exception as error:
            return {"collect_error": str(error)}

    async def _safe_collect_diagnostics(
        self, sandbox_id: str, scope: str
    ) -> dict[str, str]:
        try:
            return await self._collect_diagnostics(sandbox_id, scope)
        except Exception as e:
            logger.warning("Failed to collect sandbox diagnostics: %s", e)
            return {}

    async def health_check(self) -> bool:
        """Check if OpenSandbox server is reachable."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                r = await client.get(f"{get_sandbox_server_url()}/health", timeout=5.0)
                return r.status_code == 200
        except Exception:
            return False


def _build_playwright_script(
    *,
    url: str,
    user_script: str = "",
    extract_text: bool = True,
    screenshot: bool = False,
) -> str:
    """Generate a Playwright Python script for browser automation."""
    parts = [
        "import asyncio",
        "from playwright.async_api import async_playwright",
        "",
        "async def run():",
        "    async with async_playwright() as p:",
        "        browser = await p.chromium.launch(headless=True)",
        "        page = await browser.new_page()",
        f"        await page.goto({url!r}, wait_until='networkidle', timeout=30000)",
    ]

    if user_script:
        # Indent user script inside the async function
        for line in user_script.strip().splitlines():
            parts.append(f"        {line}")

    if extract_text:
        parts.append("        text = await page.inner_text('body')")
        parts.append("        print(text[:10000])")

    if screenshot:
        parts.append("        import os")
        parts.append("        os.makedirs('/tmp/screenshots', exist_ok=True)")
        parts.append(
            "        await page.screenshot(path='/tmp/screenshots/page.png', full_page=True)"
        )
        parts.append("        print('[screenshot saved to /tmp/screenshots/page.png]')")

    parts.append("        await browser.close()")
    parts.append("")
    parts.append("asyncio.run(run())")

    return "\n".join(parts)


def _current_trace_id() -> str:
    """Return active OTel trace ID when available, else fallback to a UUID."""
    try:
        span_context = trace.get_current_span().get_span_context()
        if getattr(span_context, "trace_id", 0):
            return f"{span_context.trace_id:032x}"
    except Exception:
        pass
    return str(uuid.uuid4())


def _truncate_diagnostic_text(content: str) -> str:
    """Keep diagnostics small and JSON-friendly for audit/result payloads."""
    if len(content) <= _MAX_DIAGNOSTIC:
        return content
    return f"{content[:_MAX_DIAGNOSTIC]}\n[truncated]"


def _diagnostic_sizes(diagnostics: dict[str, str]) -> dict[str, int]:
    """Return short diagnostic size map for audit."""
    return {key: len(value) for key, value in diagnostics.items()}


def _infer_mime(filename: str) -> str:
    """Infer MIME type from file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
        "csv": "text/csv",
        "json": "application/json",
        "html": "text/html",
        "txt": "text/plain",
    }.get(ext, "application/octet-stream")
