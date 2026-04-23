"""ADR-001 G3 — in-process TTL cache for get_user_smart_routing_config.

Verifies the cache avoids N DB hits for the same user within the TTL
window, caches negative (``None``) results, and serves stale-on-error.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.security import credentials


@pytest.fixture(autouse=True)
def _clear_cache_and_db_url(monkeypatch):
    credentials._smart_routing_cache_clear()
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://fake/test")
    yield
    credentials._smart_routing_cache_clear()


def _make_fake_conn(row_value):
    """Build an async-context-manager that mimics psycopg.AsyncConnection.

    `row_value` is what ``row[0]`` returns (dict or None), or the string
    ``"raise"`` to make `.connect(...)` raise.
    """
    row = [row_value] if row_value is not None else None
    cursor = MagicMock()
    cursor.fetchone = AsyncMock(return_value=row)
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=cursor)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    return conn


async def _fake_connect_factory(row_value, hits):
    async def _connect(_url):
        hits.append(1)
        if row_value == "raise":
            raise RuntimeError("db down")
        return _make_fake_conn(row_value)
    return _connect


@pytest.mark.asyncio
async def test_cache_hit_skips_db_within_ttl(monkeypatch):
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory({"enabled": True, "cheap_model": "m"}, hits),
    )

    a = await credentials.get_user_smart_routing_config("user-1")
    b = await credentials.get_user_smart_routing_config("user-1")
    c = await credentials.get_user_smart_routing_config("user-1")

    assert a == {"enabled": True, "cheap_model": "m"}
    assert b == a
    assert c == a
    assert len(hits) == 1, "expected one DB fetch + two cache hits"


@pytest.mark.asyncio
async def test_negative_result_is_cached(monkeypatch):
    """User with empty/missing smart_routing config → None must still cache."""
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory(None, hits),
    )

    a = await credentials.get_user_smart_routing_config("user-2")
    b = await credentials.get_user_smart_routing_config("user-2")
    c = await credentials.get_user_smart_routing_config("user-2")

    assert a is None
    assert b is None
    assert c is None
    assert len(hits) == 1, "negative result must be cached too"


@pytest.mark.asyncio
async def test_cache_expires_after_ttl(monkeypatch):
    """After TTL the cache re-fetches from DB."""
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory({"enabled": True, "cheap_model": "m"}, hits),
    )

    # First call — populates cache.
    await credentials.get_user_smart_routing_config("user-3")
    assert len(hits) == 1

    # Fast-forward monotonic clock past TTL.
    real_monotonic = credentials.time.monotonic
    offset = credentials._SMART_ROUTING_TTL_SECONDS + 1.0
    monkeypatch.setattr(
        credentials.time, "monotonic", lambda: real_monotonic() + offset
    )

    # Second call — cache expired, must re-fetch.
    await credentials.get_user_smart_routing_config("user-3")
    assert len(hits) == 2


@pytest.mark.asyncio
async def test_different_users_cached_independently(monkeypatch):
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory({"enabled": True, "cheap_model": "m"}, hits),
    )

    await credentials.get_user_smart_routing_config("alice")
    await credentials.get_user_smart_routing_config("bob")
    await credentials.get_user_smart_routing_config("alice")
    await credentials.get_user_smart_routing_config("bob")

    assert len(hits) == 2, "one fetch per distinct user, then cached"


@pytest.mark.asyncio
async def test_empty_user_id_skips_cache(monkeypatch):
    """Safety: empty user_id returns None without touching DB or cache."""
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory({"enabled": True, "cheap_model": "m"}, hits),
    )

    assert await credentials.get_user_smart_routing_config("") is None
    assert len(hits) == 0


@pytest.mark.asyncio
async def test_missing_db_url_returns_none(monkeypatch):
    monkeypatch.delenv("HINDSIGHT_DB_URL", raising=False)
    hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory({"enabled": True, "cheap_model": "m"}, hits),
    )

    assert await credentials.get_user_smart_routing_config("user-x") is None
    assert len(hits) == 0


@pytest.mark.asyncio
async def test_db_error_serves_stale_cache(monkeypatch):
    """If the cache has a prior value and DB fails on refresh, keep the prior value."""
    good_hits: list[int] = []
    monkeypatch.setattr(
        "psycopg.AsyncConnection.connect",
        await _fake_connect_factory({"enabled": True, "cheap_model": "m"}, good_hits),
    )
    first = await credentials.get_user_smart_routing_config("user-4")
    assert first == {"enabled": True, "cheap_model": "m"}

    # Expire cache.
    real_monotonic = credentials.time.monotonic
    offset = credentials._SMART_ROUTING_TTL_SECONDS + 1.0
    monkeypatch.setattr(
        credentials.time, "monotonic", lambda: real_monotonic() + offset
    )

    # Swap connect to raising variant.
    bad_hits: list[int] = []
    async def bad_connect(_url):
        bad_hits.append(1)
        raise RuntimeError("db down")
    monkeypatch.setattr("psycopg.AsyncConnection.connect", bad_connect)

    second = await credentials.get_user_smart_routing_config("user-4")
    assert second == {"enabled": True, "cheap_model": "m"}, (
        "must serve stale cache when DB refresh errors"
    )
    assert len(bad_hits) == 1
