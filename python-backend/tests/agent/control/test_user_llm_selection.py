from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.control import user_llm


class _Request:
    def __init__(self, body=None, user_id: str = "@alice:matrix.local") -> None:
        self.headers = {"x-auth-user": user_id}
        self._body = body or {}

    async def json(self):
        return self._body


def _make_fake_conn(row=None):
    cursor = MagicMock()
    cursor.fetchone = AsyncMock(return_value=row)
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=cursor)
    conn.commit = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn


async def _fake_connect_factory(conn, hits):
    async def _connect(_url):
        hits.append(1)
        return conn

    return _connect


@pytest.fixture(autouse=True)
def _db_url(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://fake/test")


@pytest.mark.asyncio
async def test_set_default_model_persists_user_choice(monkeypatch):
    hits: list[int] = []
    conn = _make_fake_conn()
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(conn, hits),
    )

    result = await user_llm.set_default_model(
        _Request({"model": "openrouter/anthropic/claude-sonnet-4-6"})
    )

    assert result == {
        "status": "ok",
        "user_id": "@alice:matrix.local",
        "default_model": "openrouter/anthropic/claude-sonnet-4-6",
    }
    assert len(hits) == 1
    conn.commit.assert_awaited_once()
    sql, params = conn.execute.await_args.args
    assert "default_model" in sql
    assert params == (
        "@alice:matrix.local",
        "openrouter/anthropic/claude-sonnet-4-6",
        "openrouter/anthropic/claude-sonnet-4-6",
    )


@pytest.mark.asyncio
async def test_set_selected_models_persists_model_picker_scope(monkeypatch):
    hits: list[int] = []
    conn = _make_fake_conn()
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(conn, hits),
    )

    models = ["openai/gpt-5-mini", "anthropic/claude-sonnet-4.5"]
    result = await user_llm.set_selected_models(_Request({"models": models}))

    assert result == {
        "status": "ok",
        "user_id": "@alice:matrix.local",
        "selected_models": models,
        "count": 2,
    }
    assert len(hits) == 1
    conn.commit.assert_awaited_once()
    sql, params = conn.execute.await_args.args
    assert "selected_models" in sql
    assert params == ("@alice:matrix.local", json.dumps(models), json.dumps(models))


@pytest.mark.asyncio
async def test_get_selected_models_reads_persisted_scope(monkeypatch):
    hits: list[int] = []
    models = ["openai/gpt-5-mini"]
    conn = _make_fake_conn((models,))
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(conn, hits),
    )

    assert await user_llm.get_selected_models(_Request()) == {
        "user_id": "@alice:matrix.local",
        "selected_models": models,
    }
    assert len(hits) == 1


@pytest.mark.asyncio
async def test_set_selected_models_rejects_non_list():
    result = await user_llm.set_selected_models(_Request({"models": "openai/gpt"}))

    assert result == {"status": "error", "message": "models must be a list of strings"}
