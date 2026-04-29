"""Vector chunk metadata contract for Feature 017/019 retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChunkMetadata:
    """Normalized metadata carried with vector chunks into fused retrieval."""

    chunk_id: str
    source_uri: str | None = None
    embedding_version: str | None = None
    embedding_model: str | None = None
    embedding_dimension: int | None = None
    ingested_at: str | None = None
    ttl_seconds: int | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    entity_signatures: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: dict[str, Any], metadata: dict[str, Any]) -> ChunkMetadata:
        chunk_id = str(row.get("id") or row.get("chunk_id") or metadata.get("chunk_id") or "")
        source_uri = metadata.get("source_uri") or metadata.get("uri") or row.get("source_uri")
        entity_signatures = metadata.get("entity_signatures") or []
        if isinstance(entity_signatures, str):
            entity_signatures = [entity_signatures]
        return cls(
            chunk_id=chunk_id,
            source_uri=str(source_uri) if source_uri else None,
            embedding_version=_optional_str(metadata.get("embedding_version")),
            embedding_model=_optional_str(metadata.get("embedding_model")),
            embedding_dimension=_optional_int(metadata.get("embedding_dimension")),
            ingested_at=_optional_str(
                metadata.get("ingested_at") or metadata.get("timestamp_ingested")
            ),
            ttl_seconds=_optional_int(metadata.get("ttl_seconds")),
            valid_from=_optional_str(metadata.get("valid_from")),
            valid_to=_optional_str(metadata.get("valid_to")),
            entity_signatures=tuple(str(value) for value in entity_signatures if value),
            raw=dict(metadata),
        )

    def as_metadata(self) -> dict[str, Any]:
        data = dict(self.raw)
        data["chunk_id"] = self.chunk_id
        if self.source_uri:
            data["source_uri"] = self.source_uri
        if self.embedding_version:
            data["embedding_version"] = self.embedding_version
        if self.embedding_model:
            data["embedding_model"] = self.embedding_model
        if self.embedding_dimension is not None:
            data["embedding_dimension"] = self.embedding_dimension
        if self.ingested_at:
            data["ingested_at"] = self.ingested_at
        if self.ttl_seconds is not None:
            data["ttl_seconds"] = self.ttl_seconds
        if self.valid_from:
            data["valid_from"] = self.valid_from
        if self.valid_to:
            data["valid_to"] = self.valid_to
        if self.entity_signatures:
            data["entity_signatures"] = list(self.entity_signatures)
        return data


def _optional_str(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
