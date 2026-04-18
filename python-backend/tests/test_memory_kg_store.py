from __future__ import annotations

import pathlib

from memory_engine.kg_store import create_kg_store


def test_create_kg_store_forced_sqlite(monkeypatch, tmp_path: pathlib.Path) -> None:
    monkeypatch.setenv("KG_FORCE_SQLITE", "true")
    store = create_kg_store(str(tmp_path / "kg.db"))

    assert store.status() in {"ready", "degraded"}


def test_falkor_status_is_unavailable_without_server(monkeypatch) -> None:
    monkeypatch.setenv("KG_FORCE_SQLITE", "false")
    monkeypatch.setenv("KG_PROVIDER", "falkor")
    monkeypatch.setenv("KG_FALKORDB_URL", "redis://127.0.0.1:6381/0")

    store = create_kg_store()

    assert store.status() == "unavailable"


def test_sqlite_query_returns_list(monkeypatch, tmp_path: pathlib.Path) -> None:
    monkeypatch.setenv("KG_FORCE_SQLITE", "true")
    store = create_kg_store(str(tmp_path / "kg.db"))

    results = store.query("SELECT 1 AS val")

    assert isinstance(results, list)
    assert results[0]["val"] == 1


def test_sqlite_query_named_params(monkeypatch, tmp_path: pathlib.Path) -> None:
    """query() must support named parameters for SELECTs.

    Writes go through typed APIs (seed / update_node / delete_node), so we
    seed the store first and then read back with named params.
    """
    import pytest

    monkeypatch.setenv("KG_FORCE_SQLITE", "true")
    store = create_kg_store(str(tmp_path / "kg.db"))

    # Seed populates known Stratagem/Regime/Institution nodes.
    seed_result = store.seed(force=True)
    assert seed_result["seeded"] is True
    assert seed_result["node_count"] > 0

    # Named-param SELECT reads a seeded node type.
    results = store.query(
        "SELECT id, node_type FROM kg_nodes WHERE node_type = :nt LIMIT 1",
        {"nt": "Stratagem"},
    )
    assert len(results) == 1
    assert results[0]["node_type"] == "Stratagem"

    # Guard invariant: raw INSERT via query() is rejected even with named
    # params — writes MUST go through typed APIs. This protects against SQL-
    # injection style escapes via the query() read-only surface.
    with pytest.raises(ValueError, match="Query not allowed"):
        store.query(
            "INSERT INTO kg_nodes (id, node_type, name, properties) "
            "VALUES (:id, :node_type, :name, :properties)",
            {
                "id": "evil",
                "node_type": "Test",
                "name": "Rejected",
                "properties": "{}",
            },
        )


def test_sqlite_seed_populates_nodes(monkeypatch, tmp_path: pathlib.Path) -> None:
    monkeypatch.setenv("KG_FORCE_SQLITE", "true")
    store = create_kg_store(str(tmp_path / "kg.db"))
    result = store.seed(force=True)

    assert result["seeded"] is True
    assert result["node_count"] > 0

    nodes = store.query("SELECT COUNT(*) AS cnt FROM kg_nodes")
    assert nodes[0]["cnt"] == result["node_count"]


def test_sqlite_seed_idempotent(monkeypatch, tmp_path: pathlib.Path) -> None:
    monkeypatch.setenv("KG_FORCE_SQLITE", "true")
    store = create_kg_store(str(tmp_path / "kg.db"))
    store.seed(force=True)
    first_count = store.query("SELECT COUNT(*) AS cnt FROM kg_nodes")[0]["cnt"]

    store.seed()  # no-op: existing > 0 and force=False
    second_count = store.query("SELECT COUNT(*) AS cnt FROM kg_nodes")[0]["cnt"]

    assert first_count == second_count
