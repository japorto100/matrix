from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.security.agent_settings import (
    get_user_agent_settings,
    normalize_user_agent_settings,
)


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


def test_normalize_user_agent_settings_supports_prompt_memory_skills_tools():
    settings = normalize_user_agent_settings(
        {
            "prompt": "Use concise risk language.",
            "memoryScope": "personal_kb",
            "enabledSkills": ["market", "macro"],
            "disabledSkills": "social,unsafe",
            "toolAllowlist": ["get_quote", "memory_recall"],
        },
        user_id="@alice:matrix.local",
        agent_id="researcher",
    )

    assert settings.agent_id == "researcher"
    assert settings.prompt == "Use concise risk language."
    assert settings.memory_scope == "personal_kb"
    assert settings.enabled_skills == ("market", "macro")
    assert settings.disabled_skills == ("social", "unsafe")
    assert settings.tool_allowlist == ("get_quote", "memory_recall")
    assert "tool_allowlist: get_quote, memory_recall" in settings.prompt_block()


def test_normalize_user_agent_settings_falls_back_on_bad_memory_scope():
    settings = normalize_user_agent_settings(
        {"memory_scope": "root"},
        user_id="@alice:matrix.local",
    )

    assert settings.memory_scope == "all"


@pytest.mark.asyncio
async def test_get_user_agent_settings_reads_json_settings(monkeypatch):
    hits: list[int] = []
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://fake/test")
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(
            (
                {
                    "agent_id": "researcher",
                    "system_prompt": "prefer primary sources",
                    "memory_scope": "world",
                    "enabled_skills": ["research"],
                    "tool_allowlist": ["search_news"],
                },
            ),
            hits,
        ),
    )

    settings = await get_user_agent_settings(
        "@alice:matrix.local",
        agent_id="researcher",
    )

    assert settings is not None
    assert settings.prompt == "prefer primary sources"
    assert settings.memory_scope == "world"
    assert settings.enabled_skills == ("research",)
    assert settings.tool_allowlist == ("search_news",)
    assert len(hits) == 1
