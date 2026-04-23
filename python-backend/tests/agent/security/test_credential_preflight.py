"""ADR-001 G2 — user_has_provider_credential pre-flight.

Non-mutating check used by smart-routing before silently switching the
model to a provider the user can't authenticate for.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent.security import credentials


@pytest.mark.asyncio
async def test_returns_true_when_key_exists():
    with patch.object(
        credentials, "get_user_api_key", AsyncMock(return_value="sk-abc")
    ):
        assert await credentials.user_has_provider_credential("alice", "openai")


@pytest.mark.asyncio
async def test_returns_false_when_key_missing():
    with patch.object(
        credentials, "get_user_api_key", AsyncMock(return_value=None)
    ):
        assert not await credentials.user_has_provider_credential("alice", "openai")


@pytest.mark.asyncio
async def test_returns_false_for_empty_user_id():
    """Safety: empty user_id is a no-credential case, not an error."""
    with patch.object(credentials, "get_user_api_key", AsyncMock()) as mock:
        assert not await credentials.user_has_provider_credential("", "openai")
        mock.assert_not_called()


@pytest.mark.asyncio
async def test_returns_false_for_empty_provider():
    with patch.object(credentials, "get_user_api_key", AsyncMock()) as mock:
        assert not await credentials.user_has_provider_credential("alice", "")
        mock.assert_not_called()


@pytest.mark.asyncio
async def test_returns_false_for_empty_key_string():
    """An empty string key is not a usable credential."""
    with patch.object(
        credentials, "get_user_api_key", AsyncMock(return_value="")
    ):
        assert not await credentials.user_has_provider_credential("alice", "openai")
