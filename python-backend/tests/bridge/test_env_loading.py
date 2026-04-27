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


def test_ingestion_config_loads_env_specific_over_base(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("HINDSIGHT_DB_URL", raising=False)
    monkeypatch.delenv("INGESTION_DB_URL", raising=False)

    (tmp_path / ".env").write_text(
        "HINDSIGHT_DB_URL=postgresql://base\nEMBEDDER_PROVIDER=base\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.development").write_text(
        "HINDSIGHT_DB_URL=postgresql://dev\nEMBEDDER_PROVIDER=dev\n",
        encoding="utf-8",
    )

    import ingestion.core.config as ingestion_config

    monkeypatch.setattr(ingestion_config, "_ROOT", tmp_path)
    monkeypatch.setattr(ingestion_config, "_ORIGINAL_ENV_KEYS", {"APP_ENV"})
    ingestion_config.get_config.cache_clear()

    cfg = ingestion_config.get_config()

    assert cfg.db_url == "postgresql://dev"
    assert cfg.embedder_provider == "dev"


def test_ingestion_config_preserves_process_env_over_env_specific(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://shell")
    (tmp_path / ".env.development").write_text(
        "HINDSIGHT_DB_URL=postgresql://dev\n",
        encoding="utf-8",
    )

    import ingestion.core.config as ingestion_config

    monkeypatch.setattr(ingestion_config, "_ROOT", tmp_path)
    monkeypatch.setattr(ingestion_config, "_ORIGINAL_ENV_KEYS", set(os.environ))
    ingestion_config.get_config.cache_clear()

    assert ingestion_config.get_config().db_url == "postgresql://shell"
