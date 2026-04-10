"""Control Surface — Permission Matrix (Slice 5 backend).

Consent matrix = (role × tool_category × level) where:
  role = TradingRole (6 values from agent/roles.py)
  tool_category = group of tools ("market_data", "trading", "risk", ...)
  level = "auto" | "inform" | "confirm" | "deny"

Defaults come from agent/consent_policy.yaml. DB overrides from
`agent.consent_overrides` table (Migration 005). Pattern D2.

Hot-reload pattern: 5s TTL cache + explicit /reload endpoint.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import UTC, datetime
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.control.request_scope import RequestScope, resolve_scope
from agent.roles import TradingRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "permissions"])

VALID_LEVELS = frozenset({"auto", "inform", "confirm", "deny"})

# Tool categories — maps category_id to tool list (matches frontend mock)
TOOL_CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "market_data",
        "display_name": "Market Data",
        "tools": ["get_quote", "search_news", "yield_curves", "fred_data"],
    },
    {
        "id": "trading",
        "display_name": "Trading",
        "tools": ["place_order", "cancel_order", "get_order_status"],
    },
    {
        "id": "risk",
        "display_name": "Risk Management",
        "tools": ["calc_var", "stress_test", "halt_trading", "get_positions"],
    },
    {
        "id": "memory",
        "display_name": "Memory",
        "tools": ["memory_retain", "memory_recall", "memory_reflect"],
    },
    {
        "id": "sandbox",
        "display_name": "Sandbox Execution",
        "tools": ["sandbox_python", "sandbox_bash", "sandbox_browser"],
    },
    {
        "id": "system",
        "display_name": "System",
        "tools": ["read_audit_log", "flag_event", "list_files"],
    },
    {
        "id": "a2a",
        "display_name": "A2A Delegation",
        "tools": ["delegate_to_agent", "wait_for_agent"],
    },
]


# Default matrix — reasonable starting point. Real defaults come from yaml later.
DEFAULT_MATRIX: dict[tuple[str, str], str] = {
    # (role_id, category_id) → level
    ("fundamentals_analyst", "market_data"): "auto",
    ("fundamentals_analyst", "memory"): "auto",
    ("fundamentals_analyst", "sandbox"): "confirm",
    ("fundamentals_analyst", "trading"): "deny",
    ("fundamentals_analyst", "risk"): "inform",
    ("fundamentals_analyst", "system"): "deny",
    ("fundamentals_analyst", "a2a"): "inform",
    ("sentiment_analyst", "market_data"): "auto",
    ("sentiment_analyst", "memory"): "auto",
    ("sentiment_analyst", "sandbox"): "deny",
    ("sentiment_analyst", "trading"): "deny",
    ("sentiment_analyst", "risk"): "inform",
    ("sentiment_analyst", "system"): "deny",
    ("sentiment_analyst", "a2a"): "inform",
    ("technical_analyst", "market_data"): "auto",
    ("technical_analyst", "memory"): "auto",
    ("technical_analyst", "sandbox"): "confirm",
    ("technical_analyst", "trading"): "deny",
    ("technical_analyst", "risk"): "inform",
    ("technical_analyst", "system"): "deny",
    ("technical_analyst", "a2a"): "inform",
    ("researcher", "market_data"): "auto",
    ("researcher", "memory"): "auto",
    ("researcher", "sandbox"): "confirm",
    ("researcher", "trading"): "deny",
    ("researcher", "risk"): "inform",
    ("researcher", "system"): "deny",
    ("researcher", "a2a"): "auto",
    ("trader", "market_data"): "auto",
    ("trader", "memory"): "auto",
    ("trader", "sandbox"): "deny",
    ("trader", "trading"): "confirm",
    ("trader", "risk"): "inform",
    ("trader", "system"): "deny",
    ("trader", "a2a"): "inform",
    ("risk_manager", "market_data"): "auto",
    ("risk_manager", "memory"): "auto",
    ("risk_manager", "sandbox"): "deny",
    ("risk_manager", "trading"): "deny",
    ("risk_manager", "risk"): "auto",
    ("risk_manager", "system"): "auto",
    ("risk_manager", "a2a"): "inform",
}


# ─── Cache (5s TTL, D2 pattern) ────────────────────────────────────────────


class _OverlayCache:
    def __init__(self, ttl_s: float = 5.0) -> None:
        self.ttl_s = ttl_s
        self._data: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._ts: float = 0.0
        self._lock = threading.Lock()

    def get(self, user_id: str) -> dict[tuple[str, str], dict[str, Any]]:
        """Return {(role_id, category_id): overlay} for this user.

        Holds the lock across the entire read + optional refresh path to avoid
        races where a concurrent invalidate() clears _data between _refresh()
        and the projection.
        """
        now = time.time()
        with self._lock:
            if now - self._ts >= self.ttl_s or not self._data:
                self._refresh()
            return {
                (k[0], k[1]): v
                for k, v in self._data.items()
                if k[2] == user_id
            }

    def _refresh(self) -> None:
        try:
            db_url = os.environ.get(
                "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
            )
            with psycopg.connect(db_url, autocommit=True) as conn:
                rows = conn.execute(
                    "SELECT role_id, category_id, user_id, level, updated_by, updated_at "
                    "FROM agent.consent_overrides"
                ).fetchall()
        except Exception as e:  # noqa: BLE001
            logger.warning("consent overlay refresh failed: %s", e)
            self._ts = time.time()
            return
        new_data: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in rows:
            role_id, category_id, user_id, level, updated_by, updated_at = row
            new_data[(role_id, category_id, user_id)] = {
                "level": level,
                "updated_by": updated_by,
                "updated_at": updated_at.isoformat() if updated_at else None,
            }
        self._data = new_data
        self._ts = time.time()

    def invalidate(self) -> None:
        with self._lock:
            self._data = {}
            self._ts = 0.0


_cache = _OverlayCache()


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


# ─── Request models ────────────────────────────────────────────────────────


class PatchCellRequest(BaseModel):
    role_id: str
    category_id: str
    level: str
    updated_by: str = "local"


# ─── Routes ────────────────────────────────────────────────────────────────


@router.get("/permissions/categories")
async def list_categories() -> dict[str, Any]:
    """List tool categories (for PermissionMatrix columns)."""
    return {"items": TOOL_CATEGORIES, "total": len(TOOL_CATEGORIES)}


@router.get("/permissions/matrix")
async def get_permission_matrix(request: Request, user_id: str | None = None) -> dict[str, Any]:
    """Full permission matrix (roles × categories → level), with DB overrides."""
    scope: RequestScope = resolve_scope(request, user_id=user_id)
    overlays = _cache.get(scope.user_id)
    cells: list[dict[str, Any]] = []
    for role in TradingRole:
        for cat in TOOL_CATEGORIES:
            default_level = DEFAULT_MATRIX.get((role.value, cat["id"]), "inform")
            overlay = overlays.get((role.value, cat["id"]))
            level = overlay["level"] if overlay else default_level
            cells.append(
                {
                    "role_id": role.value,
                    "category_id": cat["id"],
                    "level": level,
                    "is_overridden": overlay is not None,
                    "default_level": default_level,
                    "updated_by": overlay["updated_by"] if overlay else None,
                    "updated_at": overlay["updated_at"] if overlay else None,
                }
            )
    return {
        "items": cells,
        "total": len(cells),
        "roles": [r.value for r in TradingRole],
        "categories": [c["id"] for c in TOOL_CATEGORIES],
    }


@router.patch("/permissions/cell")
async def patch_permission_cell(
    req: PatchCellRequest, request: Request, user_id: str | None = None
) -> dict[str, Any]:
    """UPSERT consent overlay cell (bounded-write)."""
    scope: RequestScope = resolve_scope(request, user_id=user_id)
    if req.level not in VALID_LEVELS:
        raise HTTPException(
            status_code=400, detail=f"level must be one of {sorted(VALID_LEVELS)}"
        )
    try:
        TradingRole(req.role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Unknown role") from None
    if not any(c["id"] == req.category_id for c in TOOL_CATEGORIES):
        raise HTTPException(status_code=400, detail="Unknown category")

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                """
                INSERT INTO agent.consent_overrides
                    (role_id, category_id, user_id, level, updated_by, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (role_id, category_id, user_id)
                DO UPDATE SET
                    level = EXCLUDED.level,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    req.role_id,
                    req.category_id,
                    scope.user_id,
                    req.level,
                    req.updated_by,
                    datetime.now(UTC),
                ),
            )
    except Exception as e:  # noqa: BLE001
        logger.exception("patch cell failed")
        raise HTTPException(status_code=500, detail=f"patch: {e}") from e

    _cache.invalidate()
    return {
        "status": "updated",
        "role_id": req.role_id,
        "category_id": req.category_id,
        "level": req.level,
    }


@router.delete("/permissions/cell/{role_id}/{category_id}")
async def reset_permission_cell(
    role_id: str, category_id: str, request: Request, user_id: str | None = None
) -> dict[str, Any]:
    scope: RequestScope = resolve_scope(request, user_id=user_id)
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            cur = conn.execute(
                "DELETE FROM agent.consent_overrides "
                "WHERE role_id = %s AND category_id = %s AND user_id = %s",
                (role_id, category_id, scope.user_id),
            )
            deleted = cur.rowcount or 0
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"reset: {e}") from e
    _cache.invalidate()
    return {"status": "reset", "deleted": deleted > 0}


@router.post("/permissions/reload")
async def reload_permissions() -> dict[str, Any]:
    """Force-reload consent overlay cache (D2 hot-reload pattern)."""
    _cache.invalidate()
    return {"status": "cache_invalidated"}
