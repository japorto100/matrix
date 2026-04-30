from __future__ import annotations

import os
import sys
import types

import pytest


@pytest.mark.asyncio
async def test_create_hindsight_engine_restores_runtime_db_env(monkeypatch):
    from memory_fusion.providers import create_hindsight_engine

    requested_db_url = "postgresql://postgres:postgres@localhost:55433/hindsight_dev"
    dotenv_db_url = "postgresql://postgres:wrong@localhost:5433/hindsight_dev"
    requested_litellm_url = "http://127.0.0.1:8081/v1"
    dotenv_litellm_url = "http://localhost:4000"
    created: dict[str, object] = {}

    class FakeMemoryEngine:
        def __init__(self, *, db_url, embeddings, task_backend):
            created["db_url"] = db_url
            created["embeddings"] = embeddings
            created["task_backend"] = task_backend

        async def initialize(self):
            created["initialize_called"] = True

    fake_memory_engine_mod = types.ModuleType("hindsight_api.engine.memory_engine")
    fake_memory_engine_mod.MemoryEngine = FakeMemoryEngine

    original_import = __import__

    def mutate_env_on_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "hindsight_api.engine.memory_engine":
            monkeypatch.setenv("HINDSIGHT_DB_URL", dotenv_db_url)
            monkeypatch.setenv("LITELLM_BASE_URL", dotenv_litellm_url)
            monkeypatch.delenv("HINDSIGHT_API_DATABASE_URL", raising=False)
            return fake_memory_engine_mod
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setenv("HINDSIGHT_DB_URL", requested_db_url)
    monkeypatch.setenv("LITELLM_BASE_URL", requested_litellm_url)
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "bonsai-8b")
    monkeypatch.setenv("MEMORY_EMBEDDING_PROVIDER", "deterministic")
    monkeypatch.setenv("MEMORY_EMBEDDING_MODEL", "deterministic-dev-384d")
    monkeypatch.setenv("MEMORY_EMBEDDING_DIMENSION", "384")
    monkeypatch.delitem(sys.modules, "hindsight_api.engine.memory_engine", raising=False)
    monkeypatch.setattr("builtins.__import__", mutate_env_on_import)

    engine = await create_hindsight_engine(db_url=requested_db_url, use_sync_tasks=False)

    assert isinstance(engine, FakeMemoryEngine)
    assert created["db_url"] == requested_db_url
    assert created["initialize_called"] is True
    assert created["task_backend"] is None
    assert created["embeddings"] is not None
    assert os.environ["HINDSIGHT_DB_URL"] == requested_db_url
    assert os.environ["HINDSIGHT_API_DATABASE_URL"] == requested_db_url
    assert os.environ["LITELLM_BASE_URL"] == requested_litellm_url
    assert os.environ["AGENT_DEFAULT_MODEL"] == "bonsai-8b"
