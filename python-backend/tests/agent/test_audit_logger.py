from __future__ import annotations

import pytest

from agent.audit import logger
from agent.audit.logger import AuditAction, audit_log


class _CaptureStore:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    async def append(self, entry: dict) -> None:
        self.entries.append(entry)


@pytest.mark.asyncio
async def test_audit_log_sets_local_user_scope_by_default(monkeypatch) -> None:
    store = _CaptureStore()
    monkeypatch.setattr(logger, "get_audit_store", lambda: store)

    await audit_log(action=AuditAction.TOOL_CALL, tool_name="smoke")

    assert store.entries[0]["userId"] == "local"
    assert store.entries[0]["toolName"] == "smoke"


@pytest.mark.asyncio
async def test_audit_log_accepts_explicit_user_scope(monkeypatch) -> None:
    store = _CaptureStore()
    monkeypatch.setattr(logger, "get_audit_store", lambda: store)

    await audit_log(action=AuditAction.TOOL_CALL, user_id="alice")

    assert store.entries[0]["userId"] == "alice"
