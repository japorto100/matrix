"""Basis-Tests für Config-Parsing."""

from __future__ import annotations

import pytest

from agent_bridge.config import Config


def test_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config-Defaults werden korrekt gesetzt."""
    monkeypatch.setenv("MATRIX_BOT_PASSWORD", "test123")
    monkeypatch.delenv("MATRIX_BOT_ACCESS_TOKEN", raising=False)

    cfg = Config.from_env()

    assert cfg.homeserver_url == "http://localhost:8448"
    assert cfg.bot_user_id == "@trading-agent:matrix.local"
    assert cfg.bot_password == "test123"
    assert cfg.bot_access_token is None
    assert cfg.agent_service_url == "http://localhost:8094"
    assert cfg.port == 8097
    assert cfg.mention_only_in_groups is True


def test_config_bot_localpart() -> None:
    """bot_localpart extrahiert den Localpart korrekt."""
    cfg = Config(
        homeserver_url="http://localhost:8448",
        bot_user_id="@trading-agent:matrix.local",
        bot_password="pw",
        bot_access_token=None,
        device_name="test",
        store_path="./data",
        agent_service_url="http://localhost:8094",
        agent_timeout_sec=120.0,
        nats_url=None,
        host="127.0.0.1",
        port=8097,
    )
    assert cfg.bot_localpart == "trading-agent"


def test_config_missing_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fehlende MATRIX_BOT_PASSWORD wirft RuntimeError."""
    monkeypatch.delenv("MATRIX_BOT_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="MATRIX_BOT_PASSWORD"):
        Config.from_env()
