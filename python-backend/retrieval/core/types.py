"""Shared retrieval contracts for Matrix Feature 019."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RetrievalMode(StrEnum):
    """Retrieval strategy selected by the intent router."""

    text = "text"
    graph = "graph"
    hybrid = "hybrid"
    temporal = "temporal"


@dataclass(frozen=True)
class RetrievalHit:
    """Normalized retrieval candidate from vector, KG or fused sources."""

    id: str
    content: str
    source: str
    score: float = 0.0
    source_uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any], *, default_source: str) -> RetrievalHit:
        content = str(data.get("content") or data.get("text") or data.get("snippet") or "")
        hit_id = str(
            data.get("id")
            or data.get("chunk_id")
            or data.get("claim_id")
            or f"{default_source}:{abs(hash(content))}"
        )
        score = data.get("score", data.get("relevance", data.get("similarity", 0.0)))
        source_uri = data.get("source_uri") or data.get("uri") or data.get("url")
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        return cls(
            id=hit_id,
            content=content,
            source=str(data.get("source") or default_source),
            score=float(score or 0.0),
            source_uri=str(source_uri) if source_uri else None,
            metadata=metadata,
        )


@dataclass(frozen=True)
class RetrievalPlan:
    """Router output for a user query."""

    query: str
    mode: RetrievalMode
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextBubble:
    """Prompt-ready retrieval context plus structured references."""

    text: str
    hits: tuple[RetrievalHit, ...]
    references: tuple[dict[str, Any], ...]
