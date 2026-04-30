"""Remote-first embedding helpers for memory_fusion.

Matrix production memory should not cold-load local embedding models during
agent or Meta-Harness loops. OpenRouter is the default remote provider; tests
and explicit dev harness runs can select a deterministic embedder.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx


def _coerce_texts(texts: str | Sequence[str]) -> list[str]:
    if isinstance(texts, str):
        return [texts]
    return list(texts)


def _ordered_vectors(data: list[dict], expected_count: int) -> list[list[float]]:
    vectors_by_index: dict[int, list[float]] = {}
    for idx, item in enumerate(data):
        vector = item.get("embedding")
        if not isinstance(vector, list):
            continue
        vectors_by_index[int(item.get("index", idx))] = [float(v) for v in vector]
    try:
        return [vectors_by_index[i] for i in range(expected_count)]
    except KeyError as exc:
        raise RuntimeError(
            f"Embedding response returned {len(vectors_by_index)} vectors for {expected_count} inputs"
        ) from exc


class Embedder(Protocol):
    model: str

    async def embed(self, texts: str | Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


def _deterministic_vector(text: str, dim: int) -> list[float]:
    values: list[float] = []
    block = 0
    while len(values) < dim:
        digest = hashlib.sha256(f"{block}:{text}".encode()).digest()
        for byte in digest:
            raw = byte / 255.0
            values.append(round((raw * 2.0) - 1.0, 6))
            if len(values) == dim:
                break
        block += 1
    return values


@dataclass
class OpenRouterEmbedder:
    """OpenRouter embeddings client.

    Defaults to a 384-dimensional OpenRouter model so it can preserve existing
    Hindsight memory tables without destructive re-embedding.
    """

    api_key: str
    model: str = "sentence-transformers/all-minilm-l6-v2"
    base_url: str = "https://openrouter.ai/api/v1"
    timeout_s: float = 30.0

    async def embed(self, texts: str | Sequence[str]) -> list[list[float]]:
        texts = _coerce_texts(texts)
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                    "encoding_format": "float",
                },
            )
            response.raise_for_status()
            data = response.json().get("data") or []

        return _ordered_vectors(data, len(texts))


@dataclass
class HindsightOpenRouterEmbeddings:
    """Hindsight-compatible synchronous encode wrapper for OpenRouter.

    Hindsight's built-in OpenAI-compatible embedding class uses the OpenAI SDK.
    OpenRouter's embeddings endpoint works reliably through plain HTTP here, so
    this adapter implements Hindsight's `Embeddings` protocol directly.
    """

    api_key: str
    model: str = "sentence-transformers/all-minilm-l6-v2"
    base_url: str = "https://openrouter.ai/api/v1"
    batch_size: int = 100
    timeout_s: float = 60.0
    _dimension: int | None = None

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            raise RuntimeError("Embeddings not initialized. Call initialize() first.")
        return self._dimension

    async def initialize(self) -> None:
        if self._dimension is not None:
            return
        vectors = await OpenRouterEmbedder(
            api_key=self.api_key,
            model=self.model,
            base_url=self.base_url,
            timeout_s=self.timeout_s,
        ).embed(["test"])
        if not vectors or not vectors[0]:
            raise RuntimeError("OpenRouter embedding probe returned no vector")
        self._dimension = len(vectors[0])

    def encode(self, texts: str | Sequence[str]) -> list[list[float]]:
        if self._dimension is None:
            raise RuntimeError("Embeddings not initialized. Call initialize() first.")
        texts = _coerce_texts(texts)
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_s, headers=headers) as client:
            for idx in range(0, len(texts), self.batch_size):
                batch = texts[idx : idx + self.batch_size]
                response = client.post(
                    f"{self.base_url.rstrip('/')}/embeddings",
                    json={
                        "model": self.model,
                        "input": batch,
                        "encoding_format": "float",
                    },
                )
                response.raise_for_status()
                data = response.json().get("data") or []
                all_embeddings.extend(_ordered_vectors(data, len(batch)))
        return all_embeddings


@dataclass
class DeterministicEmbedder:
    """No-network embedder for tests and explicit dev harness runs."""

    model: str = "deterministic-test-8d"
    dim: int = 8

    async def embed(self, texts: str | Sequence[str]) -> list[list[float]]:
        texts = _coerce_texts(texts)
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        return _deterministic_vector(text, self.dim)


@dataclass
class HindsightDeterministicEmbeddings:
    """Hindsight-compatible deterministic embeddings for dev/Meta-Harness.

    This is intentionally opt-in. Production should keep using a real remote or
    local embedding provider so recall quality is measured on realistic vectors.
    """

    model: str = "deterministic-dev-384d"
    _dimension: int = 384

    @property
    def provider_name(self) -> str:
        return "deterministic"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def initialize(self) -> None:
        return None

    def encode(self, texts: str | Sequence[str]) -> list[list[float]]:
        texts = _coerce_texts(texts)
        return [_deterministic_vector(text, self._dimension) for text in texts]


def _deterministic_embedder_from_env(*, default_dim: int = 384) -> DeterministicEmbedder:
    dim = _env_int("MEMORY_EMBEDDING_DIMENSION", default_dim)
    model = (
        os.environ.get("MEMORY_EMBEDDING_MODEL")
        or os.environ.get("MEMPALACE_EMBEDDING_MODEL")
        or f"deterministic-dev-{dim}d"
    )
    return DeterministicEmbedder(model=model, dim=dim)


def create_mempalace_embedder() -> Embedder:
    provider = (
        os.environ.get("MEMPALACE_EMBEDDING_PROVIDER")
        or os.environ.get("MEMORY_EMBEDDING_PROVIDER")
        or "openrouter"
    ).strip().lower()
    if provider == "deterministic":
        return _deterministic_embedder_from_env()
    if provider != "openrouter":
        raise RuntimeError(f"Unsupported MEMPALACE_EMBEDDING_PROVIDER={provider!r}")

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set for MemPalace OpenRouter embeddings")
    model = (
        os.environ.get("MEMPALACE_EMBEDDING_MODEL")
        or os.environ.get("MEMORY_EMBEDDING_MODEL")
        or os.environ.get("OPENROUTER_EMBEDDING_MODEL")
        or OpenRouterEmbedder.model
    )
    base_url = os.environ.get(
        "MEMORY_EMBEDDING_BASE_URL",
        os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    return OpenRouterEmbedder(api_key=api_key, model=model, base_url=base_url)


def create_hindsight_embedder() -> HindsightOpenRouterEmbeddings | HindsightDeterministicEmbeddings:
    provider = os.environ.get("MEMORY_EMBEDDING_PROVIDER", "openrouter").strip().lower()
    if provider == "deterministic":
        embedder = _deterministic_embedder_from_env()
        return HindsightDeterministicEmbeddings(model=embedder.model, _dimension=embedder.dim)
    if provider not in {"openrouter", "openai-compatible"}:
        raise RuntimeError(f"Unsupported MEMORY_EMBEDDING_PROVIDER={provider!r} for Hindsight")
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set for Hindsight OpenRouter embeddings")
    model = (
        os.environ.get("MEMORY_EMBEDDING_MODEL")
        or os.environ.get("HINDSIGHT_EMBEDDING_MODEL")
        or os.environ.get("OPENROUTER_EMBEDDING_MODEL")
        or HindsightOpenRouterEmbeddings.model
    )
    base_url = os.environ.get(
        "MEMORY_EMBEDDING_BASE_URL",
        os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    return HindsightOpenRouterEmbeddings(api_key=api_key, model=model, base_url=base_url)
