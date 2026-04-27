"""Store facade for Feature 017 global KG claims."""

from __future__ import annotations

import math
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from memory_engine.global_kg import ClaimProposal, decay_score


class GlobalKGStore(Protocol):
    def propose_claim(self, proposal: ClaimProposal) -> str: ...
    def search_claims(
        self,
        query: str,
        limit: int = 5,
        *,
        query_embedding: Sequence[float] | None = None,
        embedding_model: str | None = None,
    ) -> list[dict[str, Any]]: ...
    def expand_claim_context(self, claim_id: str, *, limit: int = 5) -> dict[str, Any] | None: ...
    def record_claim_access(self, claim_ids: Sequence[str]) -> int: ...
    def status(self) -> dict[str, Any]: ...


class InMemoryGlobalKGStore:
    """Small deterministic store for tests and offline retrieval smoke runs."""

    def __init__(self) -> None:
        self._claims: dict[str, ClaimProposal] = {}
        self._access_counts: dict[str, int] = {}

    def propose_claim(self, proposal: ClaimProposal) -> str:
        self._claims[proposal.claim_id] = proposal
        return proposal.claim_id

    def search_claims(
        self,
        query: str,
        limit: int = 5,
        *,
        query_embedding: Sequence[float] | None = None,
        embedding_model: str | None = None,
    ) -> list[dict[str, Any]]:
        del query_embedding, embedding_model
        q_tokens = {token for token in query.lower().split() if token}
        rows: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        for proposal in self._claims.values():
            text = proposal.claim_text
            text_tokens = set(text.lower().split())
            overlap = len(q_tokens & text_tokens) / max(len(q_tokens), 1)
            score = decay_score(
                max(proposal.confidence, overlap),
                now=now,
                valid_to=proposal.valid_to,
            )
            rows.append(_proposal_to_row(proposal, final_score=score))
        rows.sort(key=lambda row: row["final_score"], reverse=True)
        return rows[: max(1, min(limit, 20))]

    def expand_claim_context(self, claim_id: str, *, limit: int = 5) -> dict[str, Any] | None:
        del limit
        proposal = self._claims.get(claim_id)
        if proposal is None:
            return None
        return _proposal_context(proposal)

    def record_claim_access(self, claim_ids: Sequence[str]) -> int:
        touched = 0
        for claim_id in sorted({str(value) for value in claim_ids if str(value).strip()}):
            if claim_id not in self._claims:
                continue
            self._access_counts[claim_id] = self._access_counts.get(claim_id, 0) + 1
            touched += 1
        return touched

    def status(self) -> dict[str, Any]:
        return {"status": "ready", "provider": "memory", "count": len(self._claims)}


class PostgresGlobalKGStore:
    """Postgres-backed global KG store using `agent.kg_*` tables."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or os.getenv("GLOBAL_KG_DB_URL") or os.getenv("HINDSIGHT_DB_URL")

    def _connect(self):
        if not self._dsn:
            raise RuntimeError("GLOBAL_KG_DB_URL or HINDSIGHT_DB_URL is not configured")
        import psycopg

        return psycopg.connect(self._dsn, autocommit=True)

    def propose_claim(self, proposal: ClaimProposal) -> str:
        from psycopg.types.json import Json

        with self._connect() as conn:
            with conn.cursor() as cur:
                for entity in [proposal.subject, proposal.object_entity]:
                    if entity is None:
                        continue
                    cur.execute(
                        """
                        INSERT INTO agent.kg_entities (
                            entity_id, canonical_key, entity_type, names, aliases,
                            provenance, metadata, updated_at
                        )
                        VALUES (%s, %s, %s, %s, '[]'::jsonb, '[]'::jsonb, '{}'::jsonb, now())
                        ON CONFLICT (canonical_key) DO UPDATE SET
                            entity_type = EXCLUDED.entity_type,
                            names = EXCLUDED.names,
                            updated_at = now()
                        """,
                        (
                            entity.entity_id,
                            entity.key,
                            entity.entity_type,
                            Json([entity.name] if entity.name else []),
                        ),
                    )

                embedding_literal, embedding_dim, embedding_model = _claim_embedding(proposal.metadata)
                cur.execute(
                    """
                    INSERT INTO agent.kg_claims (
                        claim_id, conflict_key, subject_entity_id, predicate,
                        object_entity_id, object_value, claim_text, lane, status,
                        confidence, valid_period, embedding, embedding_model,
                        embedding_dim, provenance, metadata
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        tstzrange(%s, COALESCE(%s, 'infinity'::timestamptz), '[)'),
                        %s::vector, %s, %s, %s, %s
                    )
                    ON CONFLICT (claim_id) DO NOTHING
                    """,
                    (
                        proposal.claim_id,
                        proposal.conflict_key,
                        proposal.subject.entity_id,
                        proposal.predicate,
                        proposal.object_entity.entity_id if proposal.object_entity else None,
                        Json(proposal.object_value) if proposal.object_value is not None else None,
                        proposal.claim_text,
                        proposal.lane,
                        proposal.status,
                        proposal.confidence,
                        proposal.valid_from,
                        proposal.valid_to,
                        embedding_literal,
                        embedding_model,
                        embedding_dim,
                        Json([e.evidence_id for e in proposal.evidence]),
                        Json(proposal.metadata),
                    ),
                )

                for evidence in proposal.evidence:
                    cur.execute(
                        """
                        INSERT INTO agent.kg_claim_evidence (
                            evidence_id, claim_id, source_layer, source_ref,
                            source_uri, content_hash, quote, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (evidence_id) DO NOTHING
                        """,
                        (
                            evidence.evidence_id,
                            proposal.claim_id,
                            evidence.source_layer,
                            evidence.source_ref,
                            evidence.source_uri,
                            evidence.content_hash,
                            evidence.quote,
                            Json(evidence.metadata),
                        ),
                    )

                cur.execute(
                    """
                    INSERT INTO agent.kg_projection_outbox (
                        event_id, claim_id, projection_target, operation, payload
                    )
                    VALUES (%s, %s, 'nornicdb', 'upsert_claim', %s)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        f"out_{proposal.claim_id}",
                        proposal.claim_id,
                        Json(proposal.projection_payload()),
                    ),
                )
        return proposal.claim_id

    def search_claims(
        self,
        query: str,
        limit: int = 5,
        *,
        query_embedding: Sequence[float] | None = None,
        embedding_model: str | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 20))
        vector_literal = _vector_literal(query_embedding) if query_embedding is not None else None
        if vector_literal is not None:
            rows = self._search_claims_vector(
                vector_literal=vector_literal,
                embedding_model=embedding_model,
                limit=safe_limit,
            )
            if rows:
                return rows
        return self._search_claims_lexical(query, safe_limit)

    def _search_claims_vector(
        self,
        *,
        vector_literal: str,
        embedding_model: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        candidate_limit = max(limit, min(limit * 5, 100))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.claim_id, c.claim_text, c.predicate, c.lane, c.status,
                           c.confidence, c.valid_period::text, c.provenance,
                           c.metadata, lower(c.valid_period)::text,
                           CASE
                               WHEN upper(c.valid_period)::text = 'infinity' THEN NULL
                               ELSE upper(c.valid_period)::text
                           END,
                           s.last_accessed,
                           jsonb_build_object(
                               'subject', jsonb_build_object(
                                   'entity_id', sub.entity_id,
                                   'canonical_key', sub.canonical_key,
                                   'entity_type', sub.entity_type,
                                   'name', COALESCE(sub.names->>0, sub.canonical_key)
                               ),
                               'object', jsonb_build_object(
                                   'entity_id', obj.entity_id,
                                   'canonical_key', obj.canonical_key,
                                   'entity_type', obj.entity_type,
                                   'name', COALESCE(obj.names->>0, c.object_value::text),
                                   'value', c.object_value
                               ),
                               'path', jsonb_build_array(
                                   COALESCE(sub.names->>0, sub.canonical_key),
                                   c.predicate,
                                   COALESCE(obj.names->>0, c.object_value::text)
                               ),
                               'evidence', COALESCE((
                                   SELECT jsonb_agg(jsonb_build_object(
                                       'evidence_id', e.evidence_id,
                                       'source_layer', e.source_layer,
                                       'source_ref', e.source_ref,
                                       'source_uri', e.source_uri,
                                       'content_hash', e.content_hash,
                                       'quote', e.quote
                                   ) ORDER BY e.created_at)
                                   FROM agent.kg_claim_evidence e
                                   WHERE e.claim_id = c.claim_id
                               ), '[]'::jsonb)
                           ) AS context,
                           1 - (c.embedding <=> %s::vector) AS semantic_similarity
                    FROM agent.kg_claims c
                    JOIN agent.kg_entities sub ON sub.entity_id = c.subject_entity_id
                    LEFT JOIN agent.kg_entities obj ON obj.entity_id = c.object_entity_id
                    LEFT JOIN agent.kg_claim_access_stats s ON s.claim_id = c.claim_id
                    WHERE c.sys_to = 'infinity'::timestamptz
                      AND c.status IN ('proposed', 'promoted')
                      AND c.embedding IS NOT NULL
                      AND (%s::text IS NULL OR c.embedding_model = %s)
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (
                        vector_literal,
                        embedding_model,
                        embedding_model,
                        vector_literal,
                        candidate_limit,
                    ),
                )
                rows = cur.fetchall()
        now = datetime.now(UTC)
        scored = [_row_to_claim_hit(row, now=now, semantic_index=13) for row in rows]
        scored.sort(key=lambda row: row["final_score"], reverse=True)
        return scored[:limit]

    def _search_claims_lexical(self, query: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.claim_id, c.claim_text, c.predicate, c.lane, c.status,
                           c.confidence, c.valid_period::text, c.provenance,
                           c.metadata, lower(c.valid_period)::text,
                           CASE
                               WHEN upper(c.valid_period)::text = 'infinity' THEN NULL
                               ELSE upper(c.valid_period)::text
                           END,
                           s.last_accessed,
                           jsonb_build_object(
                               'subject', jsonb_build_object(
                                   'entity_id', sub.entity_id,
                                   'canonical_key', sub.canonical_key,
                                   'entity_type', sub.entity_type,
                                   'name', COALESCE(sub.names->>0, sub.canonical_key)
                               ),
                               'object', jsonb_build_object(
                                   'entity_id', obj.entity_id,
                                   'canonical_key', obj.canonical_key,
                                   'entity_type', obj.entity_type,
                                   'name', COALESCE(obj.names->>0, c.object_value::text),
                                   'value', c.object_value
                               ),
                               'path', jsonb_build_array(
                                   COALESCE(sub.names->>0, sub.canonical_key),
                                   c.predicate,
                                   COALESCE(obj.names->>0, c.object_value::text)
                               ),
                               'evidence', COALESCE((
                                   SELECT jsonb_agg(jsonb_build_object(
                                       'evidence_id', e.evidence_id,
                                       'source_layer', e.source_layer,
                                       'source_ref', e.source_ref,
                                       'source_uri', e.source_uri,
                                       'content_hash', e.content_hash,
                                       'quote', e.quote
                                   ) ORDER BY e.created_at)
                                   FROM agent.kg_claim_evidence e
                                   WHERE e.claim_id = c.claim_id
                               ), '[]'::jsonb)
                           ) AS context
                    FROM agent.kg_claims c
                    JOIN agent.kg_entities sub ON sub.entity_id = c.subject_entity_id
                    LEFT JOIN agent.kg_entities obj ON obj.entity_id = c.object_entity_id
                    LEFT JOIN agent.kg_claim_access_stats s ON s.claim_id = c.claim_id
                    WHERE c.sys_to = 'infinity'::timestamptz
                      AND c.status IN ('proposed', 'promoted')
                      AND c.claim_text ILIKE %s
                    ORDER BY c.confidence DESC, c.created_at DESC
                    LIMIT %s
                    """,
                    (f"%{query}%", limit),
                )
                rows = cur.fetchall()
        now = datetime.now(UTC)
        return [_row_to_claim_hit(row, now=now, semantic_index=None) for row in rows]

    def expand_claim_context(self, claim_id: str, *, limit: int = 5) -> dict[str, Any] | None:
        safe_limit = max(1, min(limit, 20))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.claim_id, c.claim_text, c.predicate, c.lane, c.status,
                           c.confidence, c.valid_period::text, c.provenance,
                           c.metadata, lower(c.valid_period)::text,
                           CASE
                               WHEN upper(c.valid_period)::text = 'infinity' THEN NULL
                               ELSE upper(c.valid_period)::text
                           END,
                           s.last_accessed,
                           jsonb_build_object(
                               'subject', jsonb_build_object(
                                   'entity_id', sub.entity_id,
                                   'canonical_key', sub.canonical_key,
                                   'entity_type', sub.entity_type,
                                   'name', COALESCE(sub.names->>0, sub.canonical_key)
                               ),
                               'object', jsonb_build_object(
                                   'entity_id', obj.entity_id,
                                   'canonical_key', obj.canonical_key,
                                   'entity_type', obj.entity_type,
                                   'name', COALESCE(obj.names->>0, c.object_value::text),
                                   'value', c.object_value
                               ),
                               'path', jsonb_build_array(
                                   COALESCE(sub.names->>0, sub.canonical_key),
                                   c.predicate,
                                   COALESCE(obj.names->>0, c.object_value::text)
                               ),
                               'evidence', COALESCE((
                                   SELECT jsonb_agg(jsonb_build_object(
                                       'evidence_id', e.evidence_id,
                                       'source_layer', e.source_layer,
                                       'source_ref', e.source_ref,
                                       'source_uri', e.source_uri,
                                       'content_hash', e.content_hash,
                                       'quote', e.quote
                                   ) ORDER BY e.created_at)
                                   FROM (
                                       SELECT *
                                       FROM agent.kg_claim_evidence
                                       WHERE claim_id = c.claim_id
                                       ORDER BY created_at
                                       LIMIT %s
                                   ) e
                               ), '[]'::jsonb)
                           ) AS context
                    FROM agent.kg_claims c
                    JOIN agent.kg_entities sub ON sub.entity_id = c.subject_entity_id
                    LEFT JOIN agent.kg_entities obj ON obj.entity_id = c.object_entity_id
                    LEFT JOIN agent.kg_claim_access_stats s ON s.claim_id = c.claim_id
                    WHERE c.claim_id = %s
                      AND c.sys_to = 'infinity'::timestamptz
                    """,
                    (safe_limit, claim_id),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return _row_to_claim_context(row)

    def record_claim_access(self, claim_ids: Sequence[str]) -> int:
        ids = sorted({str(value).strip() for value in claim_ids if str(value).strip()})
        if not ids:
            return 0
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH ids AS (
                        SELECT DISTINCT unnest(%s::text[]) AS claim_id
                    ),
                    upserted AS (
                        INSERT INTO agent.kg_claim_access_stats (
                            claim_id, access_count, last_accessed, updated_at
                        )
                        SELECT ids.claim_id, 1, now(), now()
                        FROM ids
                        JOIN agent.kg_claims c ON c.claim_id = ids.claim_id
                        ON CONFLICT (claim_id) DO UPDATE SET
                            access_count = agent.kg_claim_access_stats.access_count + 1,
                            last_accessed = now(),
                            updated_at = now()
                        RETURNING claim_id
                    )
                    SELECT COUNT(*) FROM upserted
                    """,
                    (ids,),
                )
                row = cur.fetchone()
        return int(row[0]) if row else 0

    def status(self) -> dict[str, Any]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM agent.kg_claims")
                    row = cur.fetchone()
            return {"status": "ready", "provider": "postgres", "count": int(row[0]) if row else 0}
        except Exception as exc:  # noqa: BLE001
            return {"status": "unavailable", "provider": "postgres", "error": str(exc)}


def _proposal_to_row(proposal: ClaimProposal, *, final_score: float) -> dict[str, Any]:
    context = _proposal_context(proposal)
    return {
        "claim_id": proposal.claim_id,
        "claim_text": proposal.claim_text,
        "predicate": proposal.predicate,
        "lane": proposal.lane,
        "status": proposal.status,
        "confidence": proposal.confidence,
        "valid_period": {
            "from": proposal.valid_from.isoformat(),
            "to": proposal.valid_to.isoformat() if proposal.valid_to else None,
        },
        "provenance": [e.evidence_id for e in proposal.evidence],
        "metadata": proposal.metadata,
        "path": context["path"],
        "source_refs": context["source_refs"],
        "context_metadata": context["context_metadata"],
        "final_score": final_score,
    }


def _proposal_context(proposal: ClaimProposal) -> dict[str, Any]:
    subject_name = proposal.subject.name or proposal.subject.key
    object_name = (
        proposal.object_entity.name
        if proposal.object_entity and proposal.object_entity.name
        else proposal.object_entity.key
        if proposal.object_entity
        else str(proposal.object_value)
    )
    evidence = [
        {
            "evidence_id": evidence.evidence_id,
            "source_layer": evidence.source_layer,
            "source_ref": evidence.source_ref,
            "source_uri": evidence.source_uri,
            "content_hash": evidence.content_hash,
            "quote": evidence.quote,
        }
        for evidence in proposal.evidence
    ]
    return {
        "claim_id": proposal.claim_id,
        "claim_text": proposal.claim_text,
        "path": [subject_name, proposal.predicate, object_name],
        "subject": {
            "entity_id": proposal.subject.entity_id,
            "canonical_key": proposal.subject.key,
            "entity_type": proposal.subject.entity_type,
            "name": proposal.subject.name,
        },
        "object": {
            "entity_id": proposal.object_entity.entity_id if proposal.object_entity else None,
            "canonical_key": proposal.object_entity.key if proposal.object_entity else None,
            "entity_type": proposal.object_entity.entity_type if proposal.object_entity else None,
            "name": proposal.object_entity.name if proposal.object_entity else None,
            "value": proposal.object_value,
        },
        "source_refs": evidence,
        "context_metadata": {
            "lane": proposal.lane,
            "status": proposal.status,
            "confidence": proposal.confidence,
            "valid_from": proposal.valid_from.isoformat(),
            "valid_to": proposal.valid_to.isoformat() if proposal.valid_to else None,
            "freshness_anchor": proposal.valid_from.isoformat(),
        },
    }


def _row_to_claim_hit(
    row: Sequence[Any],
    *,
    now: datetime,
    semantic_index: int | None,
) -> dict[str, Any]:
    semantic_similarity = (
        float(row[semantic_index] or 0.0)
        if semantic_index is not None
        else float(row[5] or 0.0)
    )
    final_score = decay_score(
        semantic_similarity,
        now=now,
        last_accessed=row[11],
        valid_to=_parse_timestamptz(row[10]),
    )
    context = row[12] if len(row) > 12 and isinstance(row[12], dict) else {}
    context_metadata = {
        "lane": row[3],
        "status": row[4],
        "confidence": float(row[5] or 0.0),
        "valid_period": row[6],
        "valid_from": row[9],
        "valid_to": row[10],
        "freshness_anchor": row[11] or row[9],
    }
    return {
        "claim_id": row[0],
        "claim_text": row[1],
        "predicate": row[2],
        "lane": row[3],
        "status": row[4],
        "confidence": float(row[5] or 0.0),
        "valid_period": row[6],
        "provenance": row[7] or [],
        "metadata": row[8] or {},
        "path": context.get("path"),
        "source_refs": context.get("evidence", []),
        "subject": context.get("subject"),
        "object": context.get("object"),
        "context_metadata": context_metadata,
        "semantic_similarity": semantic_similarity,
        "final_score": final_score,
    }


def _row_to_claim_context(row: Sequence[Any]) -> dict[str, Any]:
    hit = _row_to_claim_hit(row, now=datetime.now(UTC), semantic_index=None)
    return {
        "claim_id": hit["claim_id"],
        "claim_text": hit["claim_text"],
        "predicate": hit["predicate"],
        "path": hit.get("path"),
        "subject": hit.get("subject"),
        "object": hit.get("object"),
        "source_refs": hit.get("source_refs", []),
        "context_metadata": hit["context_metadata"],
        "provenance": hit["provenance"],
        "metadata": hit["metadata"],
    }


def _claim_embedding(metadata: dict[str, Any]) -> tuple[str | None, int | None, str | None]:
    embedding = metadata.get("embedding")
    literal = _vector_literal(embedding) if embedding is not None else None
    if literal is None:
        return None, None, None
    model = str(metadata.get("embedding_model") or metadata.get("embedding_version") or "").strip() or None
    return literal, len(embedding), model


def _parse_timestamptz(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text or text == "infinity":
        return None
    return datetime.fromisoformat(text)


def _vector_literal(values: Sequence[float] | None) -> str | None:
    if values is None:
        return None
    coerced: list[float] = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("vector embeddings must contain finite numbers")
        coerced.append(number)
    if not coerced:
        return None
    return "[" + ",".join(f"{value:.8g}" for value in coerced) + "]"


def create_global_kg_store(*, mock: bool | None = None) -> GlobalKGStore:
    use_mock = mock if mock is not None else os.getenv("GLOBAL_KG_MOCK", "false") == "true"
    if use_mock:
        return InMemoryGlobalKGStore()
    return PostgresGlobalKGStore()
