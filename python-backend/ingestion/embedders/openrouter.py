"""OpenRouter/OpenAI-compatible embedding provider."""

from __future__ import annotations

import os
from typing import Any

import httpx
from ingestion.core.exceptions import EmbeddingError
from ingestion.embedders.base import Embedder


class OpenRouterEmbedder(Embedder):
    """Remote embedding provider for weak local machines."""

    name = "openrouter"

    def __init__(
        self,
        model_name: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self.model_name = model_name
        self.base_url = (
            base_url
            or os.getenv("OPENROUTER_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.api_key = (
            api_key
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        self.timeout_s = float(timeout_s)
        self.dim = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise EmbeddingError(
                "OPENROUTER_API_KEY or OPENAI_API_KEY is required for "
                "EMBEDDER_PROVIDER=openrouter"
            )

        payload: dict[str, Any] = {"model": self.model_name, "input": texts}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Matrix Ingestion"),
        }
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.post(
                    f"{self.base_url}/embeddings",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:300] if e.response is not None else str(e)
            raise EmbeddingError(f"remote embedding failed: {detail}") from e
        except (httpx.HTTPError, ValueError) as e:
            raise EmbeddingError(f"remote embedding failed: {e}") from e

        data = body.get("data")
        if not isinstance(data, list):
            raise EmbeddingError("remote embedding response missing data list")

        vectors: list[list[float]] = []
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
                raise EmbeddingError("remote embedding response contains invalid item")
            vector = [float(x) for x in item["embedding"]]
            if not vector:
                raise EmbeddingError("remote embedding response contains empty vector")
            vectors.append(vector)

        if len(vectors) != len(texts):
            raise EmbeddingError(
                f"remote embedding returned {len(vectors)} vectors for {len(texts)} texts"
            )
        self.dim = len(vectors[0])
        return vectors
