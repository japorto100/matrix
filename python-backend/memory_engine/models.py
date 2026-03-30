"""Pydantic request/response models for the memory service."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# KG models
# ---------------------------------------------------------------------------

class KGSeedRequest(BaseModel):
    force: bool = False  # if True, clear and re-seed even if nodes exist


class KGSeedResponse(BaseModel):
    ok: bool
    seeded: bool  # False if skipped (already seeded + force=False)
    node_count: int
    message: str = ""


class KGQueryRequest(BaseModel):
    query: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class KGQueryResponse(BaseModel):
    ok: bool
    rows: list[dict[str, Any]]
    row_count: int


class KGNodesResponse(BaseModel):
    ok: bool
    nodes: list[dict[str, Any]]
    total: int


class KGSyncResponse(BaseModel):
    ok: bool
    snapshot: dict[str, Any]
    checksum: str
    synced_at: str


# ---------------------------------------------------------------------------
# Episode models
# ---------------------------------------------------------------------------

class EpisodeCreateRequest(BaseModel):
    session_id: str
    agent_role: str
    input_json: str
    output_json: str
    tools_used: list[str] = Field(default_factory=list)
    duration_ms: int
    token_count: int = 0
    confidence: float = 0.0
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    retain_days: int = 90


class EpisodeResponse(BaseModel):
    ok: bool
    id: str
    created_at: str


class EpisodesListResponse(BaseModel):
    ok: bool
    episodes: list[dict[str, Any]]
    total: int


# ---------------------------------------------------------------------------
# Vector search models
# ---------------------------------------------------------------------------

class VectorSearchRequest(BaseModel):
    query: str
    n_results: int = 5
    collection: str = "memory"
    filter_metadata: Optional[dict[str, Any]] = None


class VectorSearchResult(BaseModel):
    id: str
    text: str
    distance: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorSearchResponse(BaseModel):
    ok: bool
    results: list[VectorSearchResult]
    total: int


class VectorAddRequest(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    collection: str = "memory"


class VectorAddResponse(BaseModel):
    ok: bool
    id: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class MemoryHealthResponse(BaseModel):
    ok: bool
    kg: str       # "ready" | "unavailable" | "degraded"
    vector: str   # "ready" | "unavailable"
    cache: str    # "lru" | "redis" | "unavailable"
    episodic: str # "ready" | "unavailable"
