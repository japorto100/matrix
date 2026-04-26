"""Usage + cost insights aggregated over ``agent.spans``.

Hermes' ``_ref/hermes-agent/agent/insights.py`` (768 LOC) reads from its own
SQLite store — not applicable to matrix. This port reads from **agent.spans
JSONB** (exec-18 Migration 017) which already carries per-turn token-usage
and model attributes emitted by :mod:`agent.tracing`. No parallel store,
no dual-write — spans are the source of truth.

Dual-path design (both consume the same aggregation):

* **exec-16 billing-REST** — :class:`InsightsEngine` exposed through
  ``GET /api/v1/billing/insights?user_id=X&days=7`` for Control-UI
* **exec-harness fitness** — :mod:`meta_harness.scorer` imports
  :meth:`InsightsEngine.cost_for_session` as the authoritative cost signal
  (replacing its own per-model cost dict)

Tier-1 redact applied per-span in :meth:`generate` so leaked secrets in
span-attributes can't escape through a billing API if the async Tier-2
consumer is lagging.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["InsightsEngine", "InsightsReport", "SessionInsights"]

_ZERO = Decimal("0")


@dataclass(frozen=True)
class SessionInsights:
    session_id: str
    total_turns: int
    total_input_tokens: int
    total_output_tokens: int
    total_cache_read_tokens: int
    total_cache_write_tokens: int
    cost_usd: Decimal
    cost_status: str  # "known" | "partial" | "unknown"
    models_used: tuple[str, ...]


@dataclass(frozen=True)
class InsightsReport:
    user_id: str
    since: datetime
    until: datetime
    total_sessions: int
    total_turns: int
    total_input_tokens: int
    total_output_tokens: int
    total_cache_read_tokens: int
    total_cache_write_tokens: int
    total_cost_usd: Decimal
    cost_status: str  # aggregated: "known" if ALL sessions known
    per_model_cost: dict[str, Decimal] = field(default_factory=dict)
    per_model_tokens: dict[str, int] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """JSON-serialisable dict for REST response."""
        return {
            "user_id": self.user_id,
            "since": self.since.isoformat(),
            "until": self.until.isoformat(),
            "total_sessions": self.total_sessions,
            "total_turns": self.total_turns,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "total_cache_write_tokens": self.total_cache_write_tokens,
            "total_cost_usd": str(self.total_cost_usd),
            "cost_status": self.cost_status,
            "per_model_cost": {k: str(v) for k, v in self.per_model_cost.items()},
            "per_model_tokens": dict(self.per_model_tokens),
        }


class InsightsEngine:
    """Aggregate usage + cost from ``agent.spans`` per user over a time window.

    The engine is stateless — the DB connection is the only collaborator.
    Inject a test double via ``conn`` for unit tests (accepts any object
    exposing a psycopg-style ``cursor()``).
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def generate(
        self,
        user_id: str,
        *,
        days: int = 7,
        now: datetime | None = None,
    ) -> InsightsReport:
        """Return a :class:`InsightsReport` for the last ``days`` days."""
        until = now or datetime.now(UTC)
        since = until - timedelta(days=days)
        sessions = await self._iter_user_sessions(user_id, since, until)
        return self._aggregate(user_id, since, until, sessions)

    async def cost_for_session(self, session_id: str) -> Decimal:
        """Harness-path: total cost for a single session. Returns Decimal('0') on unknown."""
        rows = await self._iter_session_spans(session_id)
        total = _ZERO
        for span in rows:
            total += self._span_cost(span)
        return total

    # ------------------------------------------------------------------
    # SQL access
    # ------------------------------------------------------------------

    async def _iter_user_sessions(
        self,
        user_id: str,
        since: datetime,
        until: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch spans for a user within the window via async psycopg cursor."""
        sql = """
            SELECT s.span_id, s.trace_id, s.name, s.attributes, s.events,
                   s.start_time, t.session_id
            FROM agent.spans s
            JOIN agent.traces t ON t.trace_id = s.trace_id
            WHERE t.user_id = %s
              AND s.start_time >= %s
              AND s.start_time <= %s
        """
        return await self._fetch(sql, (user_id, since.isoformat(), until.isoformat()))

    async def _iter_session_spans(self, session_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT s.span_id, s.name, s.attributes, s.events
            FROM agent.spans s
            JOIN agent.traces t ON t.trace_id = s.trace_id
            WHERE t.session_id = %s
        """
        return await self._fetch(sql, (session_id,))

    async def _fetch(self, sql: str, params: tuple) -> list[dict[str, Any]]:
        """Tiny abstraction over sync/async psycopg cursor shapes."""
        cur = self._conn.cursor()
        if hasattr(cur, "__aenter__"):
            async with cur as c:
                await c.execute(sql, params)
                cols = [d[0] for d in c.description]
                rows = await c.fetchall()
                return [dict(zip(cols, r, strict=False)) for r in rows]
        with cur as c:
            c.execute(sql, params)
            cols = [d[0] for d in c.description]
            return [dict(zip(cols, r, strict=False)) for r in c.fetchall()]

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate(
        self,
        user_id: str,
        since: datetime,
        until: datetime,
        spans: list[dict[str, Any]],
    ) -> InsightsReport:
        session_ids: set[str] = set()
        total_in = total_out = total_cr = total_cw = total_turns = 0
        total_cost = _ZERO
        per_model_cost: dict[str, Decimal] = {}
        per_model_tokens: dict[str, int] = {}
        any_unknown = False

        for span in spans:
            attrs = _ensure_dict(span.get("attributes"))

            # Tier-1 redact on every span BEFORE pulling billing fields.
            # Custom-pattern content may be in attrs; don't leak through
            # billing API if Tier-2 consumer is behind.
            try:
                from agent.security.redact import redact_dict

                attrs = redact_dict(attrs).value
            except Exception:  # noqa: BLE001
                pass

            sid = span.get("session_id") or attrs.get("session.id")
            if sid:
                session_ids.add(str(sid))

            if span.get("name") == "agent.turn":
                total_turns += 1

            in_toks = int(attrs.get("llm.input_tokens") or 0)
            out_toks = int(attrs.get("llm.completion_tokens") or 0)
            cr_toks = int(attrs.get("llm.cache_read_tokens") or 0)
            cw_toks = int(attrs.get("llm.cache_write_tokens") or 0)
            total_in += in_toks
            total_out += out_toks
            total_cr += cr_toks
            total_cw += cw_toks

            model = str(attrs.get("llm.model") or "")
            if model and (in_toks or out_toks):
                per_model_tokens[model] = per_model_tokens.get(model, 0) + in_toks + out_toks

            cost = self._span_cost_from_attrs(attrs)
            if cost is None:
                any_unknown = True
            else:
                total_cost += cost
                if model:
                    per_model_cost[model] = per_model_cost.get(model, _ZERO) + cost

        status = "known"
        if any_unknown and total_cost == _ZERO:
            status = "unknown"
        elif any_unknown:
            status = "partial"

        return InsightsReport(
            user_id=user_id,
            since=since,
            until=until,
            total_sessions=len(session_ids),
            total_turns=total_turns,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_cache_read_tokens=total_cr,
            total_cache_write_tokens=total_cw,
            total_cost_usd=total_cost,
            cost_status=status,
            per_model_cost=per_model_cost,
            per_model_tokens=per_model_tokens,
        )

    def _span_cost(self, span: dict[str, Any]) -> Decimal:
        attrs = _ensure_dict(span.get("attributes"))
        cost = self._span_cost_from_attrs(attrs)
        return cost if cost is not None else _ZERO

    @staticmethod
    def _span_cost_from_attrs(attrs: dict[str, Any]) -> Decimal | None:
        """Prefer the pre-computed ``llm.cost_usd`` attribute.

        llm_node.py (Phase-B P4) writes the estimate into the span on every
        turn so aggregation is O(span-count) instead of O(span-count ×
        LiteLLM-lookup). Spans without the attribute (pre-P4 history) are
        reported as unknown — we refuse to retro-estimate to keep billing
        reports reproducible.
        """
        value = attrs.get("llm.cost_usd")
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (TypeError, ValueError):
            return None


def _ensure_dict(value: Any) -> dict[str, Any]:
    """Span.attributes may arrive as dict (asyncpg row_factory) or JSON string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    return {}
