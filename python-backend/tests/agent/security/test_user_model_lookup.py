from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.security import credentials


def _make_fake_conn(row):
    cursor = MagicMock()
    cursor.fetchone = AsyncMock(return_value=row)
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=cursor)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn


async def _fake_connect_factory(row, hits):
    async def _connect(_url):
        hits.append(1)
        return _make_fake_conn(row)

    return _connect


@pytest.fixture(autouse=True)
def _db_url(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://fake/test")
    monkeypatch.setenv("AGENT_ALLOW_ENV_CREDENTIAL_FALLBACK", "false")


@pytest.mark.asyncio
async def test_get_user_default_model_reads_user_llm_settings(monkeypatch):
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(("openai/gpt-5-mini",), hits),
    )

    assert await credentials.get_user_default_model("@alice:matrix.local") == (
        "openai/gpt-5-mini"
    )
    assert len(hits) == 1


@pytest.mark.asyncio
async def test_get_user_default_model_skips_empty_user(monkeypatch):
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(("openai/gpt-5-mini",), hits),
    )

    assert await credentials.get_user_default_model("") is None
    assert hits == []


@pytest.mark.asyncio
async def test_get_user_role_model_reads_role_override(monkeypatch):
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(({"default": "anthropic/claude-sonnet-4.5"},), hits),
    )

    assert await credentials.get_user_role_model("@alice:matrix.local", "default") == (
        "anthropic/claude-sonnet-4.5"
    )
    assert len(hits) == 1


@pytest.mark.asyncio
async def test_get_user_role_model_skips_empty_role(monkeypatch):
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(({"default": "anthropic/claude-sonnet-4.5"},), hits),
    )

    assert await credentials.get_user_role_model("@alice:matrix.local", "") is None
    assert hits == []


@pytest.mark.asyncio
async def test_get_user_api_key_can_use_dev_env_fallback(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AGENT_ALLOW_ENV_CREDENTIAL_FALLBACK", "true")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-dev")
    monkeypatch.delenv("HINDSIGHT_DB_URL", raising=False)

    assert await credentials.get_user_api_key("@alice:matrix.local", "openrouter") == (
        "sk-openrouter-dev"
    )


@pytest.mark.asyncio
async def test_get_user_api_key_env_fallback_disabled_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AGENT_ALLOW_ENV_CREDENTIAL_FALLBACK", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-dev")
    monkeypatch.delenv("HINDSIGHT_DB_URL", raising=False)

    assert await credentials.get_user_api_key("@alice:matrix.local", "openrouter") is None
