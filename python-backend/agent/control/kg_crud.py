"""Control Surface — Trading KG CRUD (Slice 4 backend).

Uses memory_engine/kg_store.py (Kuzu-backed Trading domain KG).
NOT legacy — Hindsight has no domain-specific KG, this is our Trading KG.

Node types: Stratagem, Regime, BTEMarker, TransmissionChannel, Asset, Institution
Edge types: causes, inhibits, activates, precedes, transmits, signals
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from memory_engine.kg_store import (
    ALLOWED_EDGE_TYPES,
    ALLOWED_NODE_TYPES,
    create_kg_store,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "kg"])


def _get_store():  # type: ignore[return-type]  # KG store has dynamic methods
    try:
        return create_kg_store()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"KG store unavailable: {e}") from e


# ─── Request Models ────────────────────────────────────────────────────────


class CreateNodeRequest(BaseModel):
    type: str
    label: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class UpdateNodeRequest(BaseModel):
    properties: dict[str, Any]


class CreateEdgeRequest(BaseModel):
    from_id: str
    to_id: str
    type: str
    properties: dict[str, Any] | None = None


# ─── Nodes ─────────────────────────────────────────────────────────────────


@router.get("/kg/nodes")
async def list_kg_nodes(
    type: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """List KG nodes, optionally filtered by type."""
    store = _get_store()
    if type:
        if type not in ALLOWED_NODE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown node type. Allowed: {sorted(ALLOWED_NODE_TYPES)}",
            )
        items = store.get_nodes(type, limit)
        return {"items": items, "total": len(items), "type": type}

    # List all types
    all_items: list[dict[str, Any]] = []
    for node_type in ALLOWED_NODE_TYPES:
        try:
            nodes = store.get_nodes(node_type, limit)
            for n in nodes:
                n["_type"] = node_type
            all_items.extend(nodes)
        except Exception:  # noqa: BLE001
            continue
    return {"items": all_items[:limit], "total": len(all_items)}


@router.get("/kg/nodes/{node_id}")
async def get_kg_node(node_id: str) -> dict[str, Any]:
    store = _get_store()
    if not hasattr(store, "get_node"):
        raise HTTPException(status_code=501, detail="KG store backend has no get_node (SQLite fallback?)")
    node = store.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.post("/kg/nodes")
async def create_kg_node(req: CreateNodeRequest) -> dict[str, Any]:
    store = _get_store()
    if not hasattr(store, "create_node"):
        raise HTTPException(status_code=501, detail="KG store backend has no create_node")
    try:
        props = dict(req.properties)
        if req.label:
            props.setdefault("name", req.label)
        node_id = store.create_node(req.type, props)
        return {"status": "created", "id": node_id, "type": req.type}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("create_kg_node failed")
        raise HTTPException(status_code=500, detail=f"create_node: {e}") from e


@router.patch("/kg/nodes/{node_id}")
async def update_kg_node(node_id: str, req: UpdateNodeRequest) -> dict[str, Any]:
    store = _get_store()
    if not hasattr(store, "update_node"):
        raise HTTPException(status_code=501, detail="KG store backend has no update_node")
    updated = store.update_node(node_id, req.properties)
    if updated is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return updated


@router.delete("/kg/nodes/{node_id}")
async def delete_kg_node(node_id: str) -> dict[str, Any]:
    store = _get_store()
    if not hasattr(store, "delete_node"):
        raise HTTPException(status_code=501, detail="KG store backend has no delete_node")
    deleted = store.delete_node(node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"status": "deleted", "id": node_id}


# ─── Edges ─────────────────────────────────────────────────────────────────


@router.get("/kg/edges")
async def list_kg_edges(
    from_id: str | None = None,
    to_id: str | None = None,
    type: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    store = _get_store()
    if not hasattr(store, "list_edges"):
        return {"items": [], "total": 0}
    if type and type not in ALLOWED_EDGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown edge type. Allowed: {sorted(ALLOWED_EDGE_TYPES)}",
        )
    edges = store.list_edges(from_id=from_id, to_id=to_id, edge_type=type, limit=limit)
    return {"items": edges, "total": len(edges)}


@router.post("/kg/edges")
async def create_kg_edge(req: CreateEdgeRequest) -> dict[str, Any]:
    store = _get_store()
    if not hasattr(store, "create_edge"):
        raise HTTPException(status_code=501, detail="KG store backend has no create_edge")
    try:
        edge = store.create_edge(req.from_id, req.to_id, req.type, req.properties)
        return {"status": "created", **edge}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("create_kg_edge failed")
        raise HTTPException(status_code=500, detail=f"create_edge: {e}") from e


@router.delete("/kg/edges/{from_id}/{to_id}/{type}")
async def delete_kg_edge(from_id: str, to_id: str, type: str) -> dict[str, Any]:
    store = _get_store()
    if not hasattr(store, "delete_edge"):
        raise HTTPException(status_code=501, detail="KG store backend has no delete_edge")
    try:
        deleted = store.delete_edge(from_id, to_id, type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Edge not found")
    return {"status": "deleted", "from": from_id, "to": to_id, "type": type}


# ─── Combined Graph (for visualization) ────────────────────────────────────


@router.get("/kg/graph")
async def get_kg_graph(
    type: str | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """Combined {nodes, edges} for visualization — efficient single call.

    K4 (exec-15 Slice 4): replaces separate /kg/nodes + /kg/edges fetches.
    If ``type`` is provided, only nodes of that type are returned.
    Otherwise nodes across all ALLOWED_NODE_TYPES are sampled evenly.
    """
    store = _get_store()

    # ── Nodes ──────────────────────────────────────────────────────────────
    nodes: list[dict[str, Any]] = []
    if type:
        if type not in ALLOWED_NODE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown node type. Allowed: {sorted(ALLOWED_NODE_TYPES)}",
            )
        nodes = store.get_nodes(type, limit)
        for n in nodes:
            n.setdefault("_type", type)
    else:
        per_type = max(1, limit // max(1, len(ALLOWED_NODE_TYPES)) + 1)
        for t in ALLOWED_NODE_TYPES:
            try:
                typed_nodes = store.get_nodes(t, per_type)
            except Exception:  # noqa: BLE001
                continue
            for n in typed_nodes:
                n.setdefault("_type", t)
            nodes.extend(typed_nodes)

    nodes = nodes[:limit]

    # ── Edges ──────────────────────────────────────────────────────────────
    edges: list[dict[str, Any]] = []
    if hasattr(store, "list_edges"):
        try:
            edges = store.list_edges(limit=limit)
        except Exception as e:  # noqa: BLE001
            logger.warning("list_edges failed: %s", e)
            edges = []

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


# ─── Seed ──────────────────────────────────────────────────────────────────


@router.post("/kg/seed")
async def seed_kg(force: bool = False) -> dict[str, Any]:
    """Seed the Trading KG with default Stratagems/Regimes/Assets/Institutions."""
    store = _get_store()
    try:
        result = store.seed(force=force)
        return {"status": "ok", **result}
    except Exception as e:  # noqa: BLE001
        logger.exception("seed_kg failed")
        raise HTTPException(status_code=500, detail=f"seed: {e}") from e
