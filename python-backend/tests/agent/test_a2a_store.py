from __future__ import annotations

import pytest

from agent.a2a import store


@pytest.mark.asyncio
async def test_a2a_store_skips_without_db_url(monkeypatch) -> None:
    monkeypatch.delenv("AUDIT_DB_URL", raising=False)
    monkeypatch.delenv("HINDSIGHT_DB_URL", raising=False)

    started = await store.record_delegation_started(
        delegation_id="11111111-1111-1111-1111-111111111111",
        from_role="orchestrator",
        to_role="researcher",
        task="analyze AAPL",
        thread_id="thread-1",
        user_id="u1",
    )
    finished = await store.record_delegation_finished(
        delegation_id="11111111-1111-1111-1111-111111111111",
        status="completed",
        result={"text": "done"},
    )

    assert started is False
    assert finished is False


@pytest.mark.asyncio
async def test_a2a_store_writes_started_and_finished(monkeypatch) -> None:
    calls: list[tuple[str, tuple]] = []

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, sql: str, params: tuple) -> None:
            calls.append((" ".join(sql.split()), params))

    def _connect(db_url: str, *, autocommit: bool):
        assert db_url == "postgresql://example/test"
        assert autocommit is True
        return _Conn()

    monkeypatch.setenv("AUDIT_DB_URL", "postgresql://example/test")
    monkeypatch.setattr(store.psycopg, "connect", _connect)

    delegation_id = "11111111-1111-1111-1111-111111111111"
    started = await store.record_delegation_started(
        delegation_id=delegation_id,
        from_role="orchestrator",
        to_role="researcher",
        task="analyze AAPL",
        thread_id="thread-1",
        user_id="u1",
    )
    finished = await store.record_delegation_finished(
        delegation_id=delegation_id,
        status="completed",
        result={"text": "done"},
    )

    assert started is True
    assert finished is True
    assert "INSERT INTO agent.a2a_delegations" in calls[0][0]
    assert calls[0][1][0] == delegation_id
    assert calls[0][1][1:4] == ("orchestrator", "researcher", "analyze AAPL")
    assert "UPDATE agent.a2a_delegations" in calls[1][0]
    assert calls[1][1][0] == "completed"
    assert calls[1][1][2] == delegation_id
