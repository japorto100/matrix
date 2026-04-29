"""Control Surface - read-only semantic catalog."""

from __future__ import annotations

from fastapi import APIRouter, Query

from semantic_layer.catalog import (
    DEFAULT_SEMANTIC_CATALOG,
    PermissionContext,
    lookup_phrase,
    plan_metric_query,
    validate_catalog,
)

router = APIRouter(tags=["control", "semantic"])


@router.get("/semantic/catalog")
async def semantic_catalog() -> dict:
    catalog = DEFAULT_SEMANTIC_CATALOG
    return {
        "catalog": catalog.as_dict(),
        "validation": validate_catalog(catalog),
    }


@router.get("/semantic/lookup")
async def semantic_lookup(phrase: str = Query(..., min_length=1)) -> dict:
    return lookup_phrase(DEFAULT_SEMANTIC_CATALOG, phrase)


@router.get("/semantic/metrics/{metric_id}/plan")
async def semantic_metric_plan(
    metric_id: str,
    user_id: str = "",
    tenant_id: str = "",
    role: list[str] | None = None,
) -> dict:
    return plan_metric_query(
        DEFAULT_SEMANTIC_CATALOG,
        metric_id,
        PermissionContext(
            user_id=user_id, tenant_id=tenant_id, roles=tuple(role or ())
        ),
    )
