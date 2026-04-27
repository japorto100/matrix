"""Store facade for Feature 017 global KG claims."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Protocol

from memory_engine.global_kg import ClaimProposal, decay_score


class GlobalKGStore(Protocol):
    def propose_claim(self, proposal: ClaimProposal) -> str: ...
    def search_claims(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...
    def status(self) -> dict[str, Any]: ...


class InMemoryGlobalKGStore:
    """Small deterministic store for tests and offline retrieval smoke runs."""

    def __init__(self) -> None:
        self._claims: dict[str, ClaimProposal] = {}

    def propose_claim(self, proposal: ClaimProposal) -> str:
        self._claims[proposal.claim_id] = proposal
        return proposal.claim_id

    def search_claims(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
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

                cur.execute(
                    """
                    INSERT INTO agent.kg_claims (
                        claim_id, conflict_key, subject_entity_id, predicate,
                        object_entity_id, object_value, claim_text, lane, status,
                        confidence, valid_period, provenance, metadata
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        tstzrange(%s, COALESCE(%s, 'infinity'::timestamptz), '[)'),
                        %s, %s
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

    def search_claims(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 20))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT claim_id, claim_text, predicate, lane, status, confidence,
                           valid_period::text, provenance, metadata
                    FROM agent.kg_claims
                    WHERE sys_to = 'infinity'::timestamptz
                      AND status IN ('proposed', 'promoted')
                      AND claim_text ILIKE %s
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT %s
                    """,
                    (f"%{query}%", safe_limit),
                )
                rows = cur.fetchall()
        return [
            {
                "claim_id": row[0],
                "claim_text": row[1],
                "predicate": row[2],
                "lane": row[3],
                "status": row[4],
                "confidence": float(row[5] or 0.0),
                "valid_period": row[6],
                "provenance": row[7] or [],
                "metadata": row[8] or {},
                "final_score": float(row[5] or 0.0),
            }
            for row in rows
        ]

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
        "final_score": final_score,
    }


def create_global_kg_store(*, mock: bool | None = None) -> GlobalKGStore:
    use_mock = mock if mock is not None else os.getenv("GLOBAL_KG_MOCK", "false") == "true"
    if use_mock:
        return InMemoryGlobalKGStore()
    return PostgresGlobalKGStore()
