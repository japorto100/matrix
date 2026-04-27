from __future__ import annotations

import importlib
import os


def test_app_factory_preserves_process_env_over_env_specific(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AGENT_AUTO_MIGRATE", "false")

    import shared.app_factory as app_factory

    importlib.reload(app_factory)

    assert os.environ["AGENT_AUTO_MIGRATE"] == "false"


def test_bridge_config_preserves_process_env_over_env_specific(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PORT", "9999")

    import bridge.config as bridge_config

    importlib.reload(bridge_config)

    assert bridge_config.Config.from_env().port == 9999
