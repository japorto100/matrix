from __future__ import annotations

import os

import pytest

from memory_fusion.embeddings import (
    HindsightDeterministicEmbeddings,
    OpenRouterEmbedder,
    create_hindsight_embedder,
    create_mempalace_embedder,
    embedding_audit_snapshot,
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


def test_embedding_audit_snapshot_redacts_remote_credentials(monkeypatch) -> None:
    monkeypatch.setenv("MEMORY_EMBEDDING_QUOTA_POLICY", "dev-smoke-only")
    monkeypatch.setenv("MEMORY_EMBEDDING_LIVE_CALL_BUDGET", "3")

    snapshot = embedding_audit_snapshot(
        provider="openrouter",
        model="sentence-transformers/all-minilm-l6-v2",
        base_url="https://openrouter.ai/api/v1",
        api_key="sk-test-secret-123",
    )

    assert snapshot["provider"] == "openrouter"
    assert snapshot["base_url_host"] == "openrouter.ai"
    assert snapshot["api_key_present"] is True
    assert snapshot["api_key_redacted"] == "[redacted]"
    assert snapshot["api_key_fingerprint"]
    assert "sk-test-secret-123" not in str(snapshot)
    assert snapshot["quota_policy"] == "dev-smoke-only"
    assert snapshot["live_call_budget"] == 3


def test_openrouter_embedder_exposes_redacted_audit_metadata(monkeypatch) -> None:
    monkeypatch.delenv("MEMORY_EMBEDDING_QUOTA_POLICY", raising=False)
    monkeypatch.delenv("MEMORY_EMBEDDING_LIVE_CALL_BUDGET", raising=False)

    embedder = OpenRouterEmbedder(
        api_key="sk-test-secret-456",
        model="embedding-model",
        base_url="https://openrouter.ai/api/v1",
    )

    metadata = embedder.audit_metadata()

    assert metadata["model"] == "embedding-model"
    assert metadata["api_key_present"] is True
    assert metadata["quota_policy"] == "unset"
    assert metadata["live_call_budget"] == 1
    assert "sk-test-secret-456" not in str(metadata)
