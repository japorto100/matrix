from __future__ import annotations

from agent.sandbox.manager import SandboxManager, SandboxResult


class _RecordingManager(SandboxManager):
    def __init__(self) -> None:
        self.call: dict | None = None

    async def execute_code(self, **kwargs):
        self.call = kwargs
        return SandboxResult(stdout="ok\n")


async def test_execute_file_stages_upload_and_uses_code_sandbox() -> None:
    manager = _RecordingManager()

    result = await manager.execute_file(
        file_content=b"symbol,price\nAAPL,123\n",
        file_name="prices.csv",
        analysis_code="print(open('/tmp/uploads/prices.csv').read())",
        thread_id="thread-1",
    )

    assert result.success is True
    assert manager.call is not None
    assert manager.call["language"] == "python"
    assert manager.call["thread_id"] == "thread-1"
    assert manager.call["upload_files"] == [
        {
            "name": "prices.csv",
            "content_b64": "c3ltYm9sLHByaWNlCkFBUEwsMTIzCg==",
        }
    ]
    assert manager.call["config"].timeout.total_seconds() == 600


def test_sandbox_result_to_dict_includes_success() -> None:
    result = SandboxResult(stdout="ok", exit_code=0, execution_time_ms=12.5)

    assert result.to_dict() == {
        "stdout": "ok",
        "stderr": "",
        "exit_code": 0,
        "files": [],
        "execution_time_ms": 12.5,
        "error": None,
        "success": True,
    }
