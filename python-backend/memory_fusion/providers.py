"""Shared provider helpers for memory_fusion."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from memory_fusion.runtime_env import bridge_hindsight_env


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_ref(meta: dict[str, Any]) -> str:
    source_ref = str(meta.get("source_ref") or "").strip()
    if source_ref:
        return source_ref
    source_file = str(meta.get("source_file") or meta.get("source_path") or "?")
    chunk_id = str(meta.get("chunk_id") or meta.get("chunk_index") or meta.get("document_id") or "?")
    return f"{Path(source_file).name}#{chunk_id}"


@contextmanager
def _temporary_env(overrides: dict[str, str | None]):
    old_values = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def create_hindsight_engine(
    db_url: str | None = None,
    *,
    llm_provider: str | None = None,
    use_sync_tasks: bool = True,
    retain_extraction_mode: str | None = None,
    enable_observations: bool | None = None,
    retain_default_strategy: str | None = None,
) -> Any:
    db_url = db_url or os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        raise RuntimeError("HINDSIGHT_DB_URL not set")

    bridge_hindsight_env()

    runtime_env = {
        "HINDSIGHT_DB_URL": db_url,
        "MEMPALACE_DB_URL": os.environ.get("MEMPALACE_DB_URL"),
    }
    overrides = {
        "HINDSIGHT_API_DATABASE_URL": db_url,
        "HINDSIGHT_API_LLM_PROVIDER": llm_provider,
        "HINDSIGHT_API_RETAIN_EXTRACTION_MODE": retain_extraction_mode,
        "HINDSIGHT_API_ENABLE_OBSERVATIONS": (
            None if enable_observations is None else str(enable_observations).lower()
        ),
        "HINDSIGHT_API_RETAIN_DEFAULT_STRATEGY": retain_default_strategy,
    }
    memory_env = {
        key: os.environ.get(key)
        for key in (
            "MEMORY_EMBEDDING_PROVIDER",
            "MEMORY_EMBEDDING_MODEL",
            "MEMORY_EMBEDDING_DIMENSION",
            "MEMORY_EMBEDDING_BASE_URL",
            "HINDSIGHT_EMBEDDING_MODEL",
            "MEMPALACE_EMBEDDING_MODEL",
            "OPENROUTER_EMBEDDING_MODEL",
        )
        if os.environ.get(key) is not None
    }
    with _temporary_env(overrides):
        from hindsight_api.engine.memory_engine import MemoryEngine

        from memory_fusion.embeddings import create_hindsight_embedder

        # Hindsight's package import loads .env with override=True. Re-apply the
        # explicit runtime bridge so harness/dev-stack DB URLs keep winning.
        for key, value in runtime_env.items():
            if value is not None:
                os.environ[key] = value
        for key, value in overrides.items():
            if value is not None:
                os.environ[key] = value
        os.environ.update(memory_env)

        embeddings = create_hindsight_embedder()

        task_backend = None
        if use_sync_tasks:
            from hindsight_api.engine.task_backend import SyncTaskBackend

            task_backend = SyncTaskBackend()

        engine = MemoryEngine(db_url=db_url, embeddings=embeddings, task_backend=task_backend)
        await engine.initialize()
        return engine


async def create_mempalace_engine(
    palace_path: str | None = None,
    *,
    db_url: str | None = None,
):
    palace_path = palace_path or os.environ.get("MEMPALACE_PALACE_PATH", "postgres")
    db_url = db_url or os.environ.get("MEMPALACE_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
    from memory_fusion.mempalace_engine import MempalaceMemoryEngine

    engine = MempalaceMemoryEngine(palace_path=palace_path, db_url=db_url)
    await engine.initialize()
    return engine
