from __future__ import annotations

import pytest
from ingestion.core.exceptions import EmbeddingError
from ingestion.embedders.openrouter import OpenRouterEmbedder
from ingestion.embedders.registry import EmbedderRegistry


def test_registry_exposes_openrouter_embedder() -> None:
    registry = EmbedderRegistry(
        default_model="test/embed",
        remote_base_url="https://example.test/v1",
        remote_api_key="test-key",
    )

    embedder = registry.get("openrouter")

    assert isinstance(embedder, OpenRouterEmbedder)
    assert embedder.model_name == "test/embed"
    assert embedder.base_url == "https://example.test/v1"


def test_openrouter_embedder_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    embedder = OpenRouterEmbedder(model_name="test/embed", api_key="")

    with pytest.raises(EmbeddingError, match="API_KEY"):
        embedder.embed(["hello"])


def test_openrouter_embedder_parses_embedding_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyResponse:
        text = "{}"

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {"embedding": [0.1, 0.2, 0.3]},
                    {"embedding": [0.4, 0.5, 0.6]},
                ]
            }

    class DummyClient:
        def __init__(self, **_: object) -> None:
            pass

        def __enter__(self) -> DummyClient:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def post(self, url: str, json: dict, headers: dict) -> DummyResponse:
            assert url == "https://example.test/v1/embeddings"
            assert json["model"] == "test/embed"
            assert json["input"] == ["a", "b"]
            assert headers["Authorization"] == "Bearer test-key"
            return DummyResponse()

    monkeypatch.setattr("ingestion.embedders.openrouter.httpx.Client", DummyClient)

    embedder = OpenRouterEmbedder(
        model_name="test/embed",
        base_url="https://example.test/v1",
        api_key="test-key",
    )

    assert embedder.embed(["a", "b"]) == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert embedder.dim == 3
