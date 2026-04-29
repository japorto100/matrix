from __future__ import annotations

from memory_engine.vector_store import VectorStore


def test_vector_store_mock_roundtrip() -> None:
    store = VectorStore(mock=True, provider="chroma")
    store.add("doc-1", "macro regime change", {"type": "note"})

    results = store.search("macro regime", n_results=3)

    assert store.count() == 1
    assert len(results) == 1
    assert results[0]["id"] == "doc-1"
    assert results[0]["metadata"]["type"] == "note"
    assert results[0]["metadata"]["embedding_model"] == "all-MiniLM-L6-v2"
    assert results[0]["metadata"]["embedding_version"] == (
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    assert results[0]["metadata"]["embedding_dimension"] == 384


def test_vector_store_preserves_explicit_embedding_metadata() -> None:
    store = VectorStore(mock=True, provider="chroma")
    store.add(
        "doc-1",
        "macro regime change",
        {
            "embedding_model": "custom-model",
            "embedding_version": "custom-model@2026-04",
            "embedding_dimension": 768,
        },
    )

    results = store.search("macro regime", n_results=3)

    assert results[0]["metadata"]["embedding_model"] == "custom-model"
    assert results[0]["metadata"]["embedding_version"] == "custom-model@2026-04"
    assert results[0]["metadata"]["embedding_dimension"] == 768


def test_vector_store_mock_delete() -> None:
    store = VectorStore(mock=True, provider="chroma")
    store.add("doc-del", "to be deleted", {})
    assert store.count() == 1

    store.delete("doc-del")

    assert store.count() == 0
    assert store.search("deleted", n_results=3) == []


def test_vector_store_mock_multiple_docs() -> None:
    store = VectorStore(mock=True, provider="chroma")
    store.add("a", "first document", {"tag": "a"})
    store.add("b", "second document", {"tag": "b"})
    store.add("c", "third document", {"tag": "c"})

    assert store.count() == 3
    results = store.search("document", n_results=2)
    assert len(results) == 2


def test_vector_store_mock_status() -> None:
    store = VectorStore(mock=True, provider="chroma")
    status = store.status()

    assert status["provider"] == "chroma"
    assert status["status"] in {"ready", "mock"}


def test_pgvector_status_is_unavailable_without_dsn(monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_PROVIDER", "pgvector")
    monkeypatch.delenv("VECTOR_STORE_PGVECTOR_DSN", raising=False)

    store = VectorStore(provider="pgvector", mock=True)
    status = store.status()

    assert status["provider"] == "pgvector"
    assert status["status"] == "unavailable"
