from __future__ import annotations

import os

import pytest

from memory_fusion.embeddings import (
    HindsightDeterministicEmbeddings,
    create_hindsight_embedder,
    create_mempalace_embedder,
)
from memory_fusion.runtime_env import bridge_hindsight_env


@pytest.mark.asyncio
async def test_hindsight_deterministic_embedder_is_explicit_no_network(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_EMBEDDING_PROVIDER", "deterministic")
    monkeypatch.setenv("MEMORY_EMBEDDING_DIMENSION", "384")
    monkeypatch.setenv("MEMORY_EMBEDDING_MODEL", "deterministic-dev-384d")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    embedder = create_hindsight_embedder()

    assert isinstance(embedder, HindsightDeterministicEmbeddings)
    assert embedder.provider_name == "deterministic"
    await embedder.initialize()
    vectors = embedder.encode(["alpha", "alpha", "beta"])
    assert len(vectors) == 3
    assert len(vectors[0]) == 384
    assert vectors[0] == vectors[1]
    assert vectors[0] != vectors[2]


@pytest.mark.asyncio
async def test_mempalace_deterministic_provider_uses_shared_dimension(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_EMBEDDING_PROVIDER", "deterministic")
    monkeypatch.setenv("MEMORY_EMBEDDING_DIMENSION", "384")
    monkeypatch.setenv("MEMORY_EMBEDDING_MODEL", "deterministic-dev-384d")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    embedder = create_mempalace_embedder()
    vectors = await embedder.embed(["alpha"])

    assert embedder.model == "deterministic-dev-384d"
    assert len(vectors) == 1
    assert len(vectors[0]) == 384


def test_hindsight_runtime_bridge_accepts_explicit_deterministic_provider(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_EMBEDDING_PROVIDER", "deterministic")
    monkeypatch.setenv("MEMORY_EMBEDDING_DIMENSION", "384")
    monkeypatch.setenv("MEMORY_EMBEDDING_MODEL", "deterministic-dev-384d")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    bridge_hindsight_env()

    assert os.environ["HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL"] == "deterministic-dev-384d"
