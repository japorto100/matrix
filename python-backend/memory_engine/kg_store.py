"""Knowledge Graph store abstraction.

Node tables: Stratagem, Regime, BTEMarker, TransmissionChannel, Asset, Institution
Edge tables: causes, inhibits, activates, precedes, transmits, signals

Providers:
    - kuzu     (current local default when available)
    - sqlite   (fallback / forced local path)
    - falkor   (prepared path, opt-in via KG_PROVIDER=falkor)
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Protocol

from memory_engine.seed_data import (
    INSTITUTIONS,
    REGIMES,
    STRATAGEMS,
    TRANSMISSION_CHANNELS,
)

_KUZU_AVAILABLE = False
try:
    import kuzu as _kuzu_probe  # noqa: F401  — import-probe only; real import inside KuzuKGStore
    _KUZU_AVAILABLE = True
except ImportError:
    pass

_FORCE_SQLITE = os.getenv("KG_FORCE_SQLITE", "false").strip().lower() == "true"


class KGStore(Protocol):
    def node_count(self) -> int: ...
    def seed(self, force: bool = False) -> dict[str, Any]: ...
    def query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...
    def get_nodes(self, node_type: str, limit: int = 100) -> list[dict[str, Any]]: ...
    def sync_snapshot(self) -> dict[str, Any]: ...
    def status(self) -> str: ...


def _normalize_provider(value: str | None) -> str:
    provider = (value or "").strip().lower()
    if provider in {"graph", "falkordb"}:
        return "falkor"
    if provider in {"sqlite", "kuzu", "falkor"}:
        return provider
    return "kuzu"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _default_kuzu_path() -> str:
    base = Path(__file__).resolve().parents[2]  # python-backend/
    return str(base / "data" / "kuzu.db")

def _default_sqlite_path() -> str:
    base = Path(__file__).resolve().parents[2]
    return str(base / "data" / "kg_fallback.db")


# ---------------------------------------------------------------------------
# KuzuDB store
# ---------------------------------------------------------------------------

class KuzuKGStore:
    def __init__(self, db_path: str | None = None) -> None:
        import kuzu  # type: ignore[import-untyped]  — available: factory only creates this when _KUZU_AVAILABLE
        configured = db_path or os.getenv("KG_KUZU_PATH", _default_kuzu_path())
        path = Path(configured)
        # Kuzu Python binding expects a file path on this runtime.
        if path.suffix == "":
            path = path / "kuzu.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(path)
        self._db: Any = kuzu.Database(self._path)
        self._conn: Any = kuzu.Connection(self._db)
        self._init_schema()

    def _init_schema(self) -> None:
        stmts = [
            "CREATE NODE TABLE IF NOT EXISTS Stratagem(id STRING, name STRING, category STRING, market_bias STRING, confidence_base DOUBLE, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Regime(id STRING, name STRING, description STRING, typical_duration_days INT64, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS BTEMarker(id STRING, name STRING, region STRING, severity DOUBLE, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS TransmissionChannel(id STRING, name STRING, direction STRING, lag_days INT64, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Asset(id STRING, symbol STRING, asset_class STRING, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Institution(id STRING, name STRING, type STRING, currency STRING, influence_score DOUBLE, PRIMARY KEY(id))",
            "CREATE REL TABLE IF NOT EXISTS causes(FROM Stratagem TO Stratagem, weight DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS inhibits(FROM Stratagem TO Stratagem, weight DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS activates(FROM Regime TO Stratagem, weight DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS precedes(FROM BTEMarker TO Regime, confidence DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS transmits(FROM TransmissionChannel TO Asset, strength DOUBLE)",
            "CREATE REL TABLE IF NOT EXISTS signals(FROM BTEMarker TO Stratagem, confidence DOUBLE)",
        ]
        for stmt in stmts:
            try:
                self._conn.execute(stmt)
            except Exception:
                pass  # table already exists

    def node_count(self) -> int:
        total = 0
        for table in ("Stratagem", "Regime", "BTEMarker", "TransmissionChannel", "Asset", "Institution"):
            try:
                result: Any = self._conn.execute(f"MATCH (n:{table}) RETURN count(n)")
                row: Any = result.get_next()
                if row:
                    total += int(row[0])
            except Exception:
                pass
        return total

    def seed(self, force: bool = False) -> dict[str, Any]:
        existing = self.node_count()
        if existing > 0 and not force:
            return {"seeded": False, "node_count": existing}

        # Seed Stratagems
        for s in STRATAGEMS:
            try:
                self._conn.execute(
                    "MERGE (n:Stratagem {id: $id}) SET n.name=$name, n.category=$cat, n.market_bias=$mb, n.confidence_base=$cb",
                    {"id": s["id"], "name": s["name"], "cat": s["category"], "mb": s["market_bias"], "cb": s["confidence_base"]},
                )
            except Exception:
                pass

        # Seed Regimes
        for r in REGIMES:
            try:
                self._conn.execute(
                    "MERGE (n:Regime {id: $id}) SET n.name=$name, n.description=$desc, n.typical_duration_days=$dur",
                    {"id": r["id"], "name": r["name"], "desc": r["description"], "dur": r["typical_duration_days"]},
                )
            except Exception:
                pass

        # Seed TransmissionChannels
        for tc in TRANSMISSION_CHANNELS:
            try:
                self._conn.execute(
                    "MERGE (n:TransmissionChannel {id: $id}) SET n.name=$name, n.direction=$dir, n.lag_days=$lag",
                    {"id": tc["id"], "name": tc["id"], "dir": tc["direction"], "lag": tc["lag_days"]},
                )
            except Exception:
                pass

        # Seed Institutions
        for inst in INSTITUTIONS:
            try:
                self._conn.execute(
                    "MERGE (n:Institution {id: $id}) SET n.name=$name, n.type=$type, n.currency=$cur, n.influence_score=$inf",
                    {"id": inst["id"], "name": inst["name"], "type": inst["type"], "cur": inst["currency"], "inf": inst["influence_score"]},
                )
            except Exception:
                pass

        total = self.node_count()
        return {"seeded": True, "node_count": total}

    def query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result: Any = self._conn.execute(query, parameters or {})
        rows = []
        while result.has_next():
            row: Any = result.get_next()
            rows.append({"values": list(row)})
        return rows

    def get_nodes(self, node_type: str, limit: int = 100) -> list[dict[str, Any]]:
        allowed = {"Stratagem", "Regime", "BTEMarker", "TransmissionChannel", "Asset", "Institution"}
        if node_type not in allowed:
            return []
        result: Any = self._conn.execute(f"MATCH (n:{node_type}) RETURN n LIMIT {limit}")
        nodes = []
        while result.has_next():
            row: Any = result.get_next()
            nodes.append({"node": str(row[0])})
        return nodes

    def sync_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {"stratagems": [], "regimes": [], "institutions": []}
        try:
            r: Any = self._conn.execute("MATCH (n:Stratagem) RETURN n.id, n.name, n.category, n.market_bias, n.confidence_base")
            while r.has_next():
                row: Any = r.get_next()
                snapshot["stratagems"].append({"id": row[0], "name": row[1], "category": row[2], "market_bias": row[3], "confidence_base": row[4]})
        except Exception:
            pass
        raw = json.dumps(snapshot, sort_keys=True)
        checksum = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return {"snapshot": snapshot, "checksum": checksum}

    def status(self) -> str:
        try:
            self.node_count()
            return "ready"
        except Exception:
            return "degraded"


# ---------------------------------------------------------------------------
# SQLite fallback KG store
# ---------------------------------------------------------------------------

class SQLiteKGStore:
    """Fallback when KuzuDB is not available. Uses SQLite with 3 tables."""

    def __init__(self, db_path: str | None = None) -> None:
        self._path = db_path or os.getenv("KG_SQLITE_PATH", _default_sqlite_path())
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS kg_nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                name TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS kg_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edge_type TEXT NOT NULL,
                from_id TEXT NOT NULL,
                to_id TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(node_type);
            CREATE INDEX IF NOT EXISTS idx_kg_edges_type ON kg_edges(edge_type);
        """)
        self._conn.commit()

    def node_count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM kg_nodes")
        return int(cur.fetchone()[0])

    def seed(self, force: bool = False) -> dict[str, Any]:
        existing = self.node_count()
        if existing > 0 and not force:
            return {"seeded": False, "node_count": existing}

        for s in STRATAGEMS:
            props = {k: v for k, v in s.items() if k != "id" and k != "name"}
            self._conn.execute(
                "INSERT OR REPLACE INTO kg_nodes(id, node_type, name, properties) VALUES(?,?,?,?)",
                (s["id"], "Stratagem", s["name"], json.dumps(props)),
            )
        for r in REGIMES:
            props = {k: v for k, v in r.items() if k not in ("id", "name")}
            self._conn.execute(
                "INSERT OR REPLACE INTO kg_nodes(id, node_type, name, properties) VALUES(?,?,?,?)",
                (r["id"], "Regime", r["name"], json.dumps(props)),
            )
        for tc in TRANSMISSION_CHANNELS:
            props = {k: v for k, v in tc.items() if k not in ("id",)}
            self._conn.execute(
                "INSERT OR REPLACE INTO kg_nodes(id, node_type, name, properties) VALUES(?,?,?,?)",
                (tc["id"], "TransmissionChannel", tc["id"], json.dumps(props)),
            )
        for inst in INSTITUTIONS:
            props = {k: v for k, v in inst.items() if k not in ("id", "name")}
            self._conn.execute(
                "INSERT OR REPLACE INTO kg_nodes(id, node_type, name, properties) VALUES(?,?,?,?)",
                (inst["id"], "Institution", inst["name"], json.dumps(props)),
            )
        self._conn.commit()
        return {"seeded": True, "node_count": self.node_count()}

    def query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        cur = self._conn.execute(query, parameters or {})
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_nodes(self, node_type: str, limit: int = 100) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT id, node_type, name, properties FROM kg_nodes WHERE node_type=? LIMIT ?",
            (node_type, limit),
        )
        return [
            {"id": row[0], "node_type": row[1], "name": row[2], **json.loads(row[3])}
            for row in cur.fetchall()
        ]

    def sync_snapshot(self) -> dict[str, Any]:
        stratagems = self.get_nodes("Stratagem", limit=100)
        regimes = self.get_nodes("Regime", limit=20)
        snapshot = {"stratagems": stratagems, "regimes": regimes}
        raw = json.dumps(snapshot, sort_keys=True)
        checksum = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return {"snapshot": snapshot, "checksum": checksum}

    def status(self) -> str:
        try:
            self.node_count()
            return "ready"
        except Exception:
            return "degraded"


class FalkorKGStore:
    def __init__(self, url: str | None = None, graph_name: str | None = None) -> None:
        self._url = (url or os.getenv("KG_FALKORDB_URL", "")).strip()
        self._graph_name = (graph_name or os.getenv("KG_FALKORDB_GRAPH", "tradeviewfusion")).strip() or "tradeviewfusion"

    def _connect(self):
        if not self._url:
            raise RuntimeError("KG_FALKORDB_URL is not configured")
        import redis

        return redis.Redis.from_url(self._url, decode_responses=True)

    def _query_rows(self, cypher: str) -> list[list[Any]]:
        client = self._connect()
        response = client.execute_command("GRAPH.QUERY", self._graph_name, cypher, "--compact")
        if not isinstance(response, list) or len(response) < 2:
            return []
        rows = response[1]
        if not isinstance(rows, list):
            return []
        return rows

    def node_count(self) -> int:
        rows = self._query_rows("MATCH (n) RETURN count(n)")
        if not rows:
            return 0
        try:
            return int(rows[0][0])
        except Exception:
            return 0

    def seed(self, force: bool = False) -> dict[str, Any]:
        if force:
            try:
                self._query_rows("MATCH (n) DETACH DELETE n")
            except Exception:
                pass

        existing = self.node_count()
        if existing > 0 and not force:
            return {"seeded": False, "node_count": existing}

        client = self._connect()
        for s in STRATAGEMS:
            client.execute_command(
                "GRAPH.QUERY",
                self._graph_name,
                (
                    "MERGE (n:Stratagem {id: '%s'}) "
                    "SET n.name = '%s', n.category = '%s', n.market_bias = '%s', n.confidence_base = %s"
                )
                % (
                    str(s["id"]).replace("'", "\\'"),
                    str(s["name"]).replace("'", "\\'"),
                    str(s["category"]).replace("'", "\\'"),
                    str(s["market_bias"]).replace("'", "\\'"),
                    float(s["confidence_base"]),
                ),
                "--compact",
            )
        for r in REGIMES:
            client.execute_command(
                "GRAPH.QUERY",
                self._graph_name,
                (
                    "MERGE (n:Regime {id: '%s'}) "
                    "SET n.name = '%s', n.description = '%s', n.typical_duration_days = %s"
                )
                % (
                    str(r["id"]).replace("'", "\\'"),
                    str(r["name"]).replace("'", "\\'"),
                    str(r["description"]).replace("'", "\\'"),
                    int(r["typical_duration_days"]),
                ),
                "--compact",
            )
        for tc in TRANSMISSION_CHANNELS:
            client.execute_command(
                "GRAPH.QUERY",
                self._graph_name,
                (
                    "MERGE (n:TransmissionChannel {id: '%s'}) "
                    "SET n.name = '%s', n.direction = '%s', n.lag_days = %s"
                )
                % (
                    str(tc["id"]).replace("'", "\\'"),
                    str(tc["id"]).replace("'", "\\'"),
                    str(tc["direction"]).replace("'", "\\'"),
                    int(tc["lag_days"]),
                ),
                "--compact",
            )
        for inst in INSTITUTIONS:
            client.execute_command(
                "GRAPH.QUERY",
                self._graph_name,
                (
                    "MERGE (n:Institution {id: '%s'}) "
                    "SET n.name = '%s', n.type = '%s', n.currency = '%s', n.influence_score = %s"
                )
                % (
                    str(inst["id"]).replace("'", "\\'"),
                    str(inst["name"]).replace("'", "\\'"),
                    str(inst["type"]).replace("'", "\\'"),
                    str(inst["currency"]).replace("'", "\\'"),
                    float(inst["influence_score"]),
                ),
                "--compact",
            )
        total = self.node_count()
        return {"seeded": True, "node_count": total}

    def query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if parameters:
            raise ValueError("FalkorKGStore.query does not yet support parameter maps")
        rows = self._query_rows(query)
        return [{"values": list(row)} for row in rows]

    def get_nodes(self, node_type: str, limit: int = 100) -> list[dict[str, Any]]:
        allowed = {"Stratagem", "Regime", "BTEMarker", "TransmissionChannel", "Asset", "Institution"}
        if node_type not in allowed:
            return []
        rows = self._query_rows(
            f"MATCH (n:{node_type}) RETURN n.id, n.name LIMIT {max(1, min(limit, 500))}"
        )
        return [{"id": row[0], "name": row[1], "node_type": node_type} for row in rows if len(row) >= 2]

    def sync_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {"stratagems": [], "regimes": [], "institutions": []}
        for label, key in (("Stratagem", "stratagems"), ("Regime", "regimes"), ("Institution", "institutions")):
            rows = self._query_rows(f"MATCH (n:{label}) RETURN n.id, n.name LIMIT 200")
            snapshot[key] = [{"id": row[0], "name": row[1]} for row in rows if len(row) >= 2]
        raw = json.dumps(snapshot, sort_keys=True)
        checksum = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return {"snapshot": snapshot, "checksum": checksum}

    def status(self) -> str:
        try:
            client = self._connect()
            client.ping()
            self.node_count()
            return "ready"
        except Exception:
            return "unavailable"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_kg_store(db_path: str | None = None) -> KGStore:
    # Read at call-time so tests can override via monkeypatch.setenv.
    force_sqlite = os.getenv("KG_FORCE_SQLITE", "false").strip().lower() == "true"
    if force_sqlite or _FORCE_SQLITE:
        return SQLiteKGStore(db_path)
    provider = _normalize_provider(os.getenv("KG_PROVIDER"))
    if provider == "sqlite":
        return SQLiteKGStore(db_path)
    if provider == "falkor":
        return FalkorKGStore()
    if _KUZU_AVAILABLE:
        try:
            return KuzuKGStore(db_path)
        except Exception:
            # Graceful degradation when Kuzu is installed but runtime init fails.
            return SQLiteKGStore(db_path)
    return SQLiteKGStore(db_path)
