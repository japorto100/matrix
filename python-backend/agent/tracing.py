"""Agent Tracing — unified OTel + Langfuse observability (exec-17).

Single entry point for all agent observability. Nodes call tracing helpers,
tracing.py decides where data goes (OTel spans + Langfuse generations).

Provides context managers for agent-specific spans:
- session_span: Root span for an entire agent invocation
- turn_span: Child span per LangGraph node execution (returns AgentSpan)
- tool_span: Child span per individual tool call
- memory_span: Child span per memory recall/retain operation

AgentSpan wraps an OTel span and adds:
- track_generation(): sends LLM input/output/usage to Langfuse (if enabled)
- set_attribute(): delegates to OTel span (unchanged API)

When OTEL_ENABLED is not set, trace.get_tracer() returns a NoopTracer
from the OTel SDK — all spans are zero-cost. No conditional checks needed.

Meta-Harness (arxiv:2603.28052v1): 40% of proposer reads are execution traces.
These spans capture WHAT the agent does, not just HTTP latency.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

tracer = trace.get_tracer("matrix.agent", "0.1.0")


class AgentSpan:
    """Wraps an OTel span with Langfuse generation tracking.

    Nodes use this like a regular span (set_attribute, add_event) plus
    track_generation() for LLM-specific data that goes to Langfuse.
    """

    __slots__ = ("_span",)

    def __init__(self, span: trace.Span) -> None:
        self._span = span

    def set_attribute(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, value)

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self._span.add_event(name, attributes=attributes)

    def track_generation(
        self,
        *,
        name: str,
        model: str,
        input: str,
        output: str,
        usage: dict[str, int],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Track an LLM generation in both OTel (attributes) and Langfuse.

        Called from llm_node.py after each LLM response.
        Langfuse is no-op when LANGFUSE_ENABLED is not true.
        """
        # OTel attributes
        self._span.set_attribute("llm.prompt_tokens", usage.get("prompt_tokens", 0))
        self._span.set_attribute(
            "llm.completion_tokens", usage.get("completion_tokens", 0)
        )
        self._span.set_attribute("llm.token_usage", usage.get("total_tokens", 0))

        # Langfuse (lazy import, no-op when disabled)
        from agent.langfuse_tracker import track_generation

        track_generation(
            name=name,
            model=model,
            input=input,
            output=output,
            usage=usage,
            metadata=metadata,
        )


@contextmanager
def session_span(
    session_id: str,
    user_id: str,
    source: str,
    role: str,
):
    """Root span wrapping an entire agent session (graph execution)."""
    with tracer.start_as_current_span(
        "agent.session",
        attributes={
            "session.id": session_id,
            "session.user_id": user_id,
            "session.source": source,
            "session.role": role,
        },
    ) as span:
        yield AgentSpan(span)


@contextmanager
def turn_span(
    node_name: str,
    model: str = "",
    turn_number: int = 0,
):
    """Child span for a LangGraph node execution (llm_call, approval, etc.)."""
    with tracer.start_as_current_span(
        "agent.turn",
        attributes={
            "agent.node": node_name,
            "llm.model": model,
            "agent.turn_number": turn_number,
        },
    ) as span:
        yield AgentSpan(span)


@contextmanager
def tool_span(
    tool_name: str,
    tool_type: str = "builtin",
):
    """Child span for a single tool call execution."""
    with tracer.start_as_current_span(
        "agent.tool_call",
        attributes={
            "tool.name": tool_name,
            "tool.type": tool_type,
        },
    ) as span:
        yield AgentSpan(span)


@contextmanager
def memory_span(
    memory_type: str,
    query: str = "",
):
    """Child span for a memory recall or retain operation."""
    with tracer.start_as_current_span(
        "agent.memory",
        attributes={
            "memory.type": memory_type,
            "memory.query": query[:200],
        },
    ) as span:
        yield AgentSpan(span)


def set_session_summary(
    span: AgentSpan,
    *,
    total_turns: int = 0,
    total_tokens: int = 0,
    total_cost: float = 0.0,
    outcome: str = "completed",
) -> None:
    """Set summary attributes on a session span after execution completes."""
    span.set_attribute("session.total_turns", total_turns)
    span.set_attribute("session.total_tokens", total_tokens)
    span.set_attribute("session.total_cost", total_cost)
    span.set_attribute("session.outcome", outcome)


# ── PostgresSpanProcessor ──────────────────────────────────────────────
# Exports OTel spans to agent.traces + agent.spans (exec-18, Migration 017).
# Runs parallel to OpenObserve — both get every span. Async background
# writes so agent latency is unaffected (Agno pattern).


class PostgresSpanProcessor:
    """OTel SpanProcessor that persists finished spans to agent.traces + agent.spans.

    Register via: TracerProvider.add_span_processor(PostgresSpanProcessor())
    Only active when AGENT_PERSIST_TRACES=1 (default: off until exec-18 verified).
    """

    def __init__(self) -> None:
        import os

        self._enabled = os.environ.get(
            "AGENT_PERSIST_TRACES", ""
        ).strip().lower() in ("1", "true", "yes")

    def on_start(self, span: Any, parent_context: Any = None) -> None:  # noqa: ARG002
        pass

    def on_end(self, span: Any) -> None:
        if not self._enabled:
            return
        try:
            self._persist(span)
        except Exception:  # noqa: BLE001
            pass  # fire-and-forget

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 0) -> bool:  # noqa: ARG002
        return True

    def _persist(self, span: Any) -> None:
        import json as _json
        import os
        from datetime import UTC, datetime

        import psycopg

        ctx = span.get_span_context()
        if not ctx or not ctx.trace_id:
            return

        trace_id = format(ctx.trace_id, "032x")
        span_id = format(ctx.span_id, "016x")
        parent_id = (
            format(span.parent.span_id, "016x")
            if span.parent and span.parent.span_id
            else None
        )
        now_iso = datetime.now(UTC).isoformat()
        start_ns = span.start_time or 0
        end_ns = span.end_time or 0
        duration_ms = (end_ns - start_ns) // 1_000_000

        # Attributes → JSONB
        attrs = {}
        if hasattr(span, "attributes") and span.attributes:
            attrs = dict(span.attributes)

        # Events → JSONB
        events = []
        if hasattr(span, "events") and span.events:
            for ev in span.events:
                events.append({
                    "name": ev.name,
                    "timestamp": ev.timestamp,
                    "attributes": dict(ev.attributes) if ev.attributes else {},
                })

        status_code = "ok"
        if hasattr(span, "status") and span.status:
            status_code = str(span.status.status_code.name).lower()

        db_url = os.environ.get(
            "HINDSIGHT_DB_URL",
            "postgresql://postgres@localhost:5433/hindsight_dev",
        )

        with psycopg.connect(db_url, autocommit=True) as conn:
            # Upsert trace (root span creates, children update end_time)
            conn.execute(
                """
                INSERT INTO agent.traces
                    (trace_id, name, status, start_time, end_time, duration_ms,
                     session_id, user_id, agent_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trace_id) DO UPDATE SET
                    end_time = EXCLUDED.end_time,
                    duration_ms = GREATEST(agent.traces.duration_ms, EXCLUDED.duration_ms),
                    status = EXCLUDED.status
                """,
                (
                    trace_id,
                    span.name,
                    status_code,
                    now_iso,
                    now_iso,
                    duration_ms,
                    attrs.get("session.id"),
                    attrs.get("session.user_id"),
                    attrs.get("session.role"),
                    now_iso,
                ),
            )

            # Insert span
            conn.execute(
                """
                INSERT INTO agent.spans
                    (span_id, trace_id, parent_span_id, name, span_kind,
                     status_code, start_time, end_time, duration_ms,
                     attributes, events, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                ON CONFLICT (span_id) DO NOTHING
                """,
                (
                    span_id,
                    trace_id,
                    parent_id,
                    span.name,
                    span.kind.name if hasattr(span, "kind") and span.kind else "INTERNAL",
                    status_code,
                    now_iso,
                    now_iso,
                    duration_ms,
                    _json.dumps(attrs, default=str),
                    _json.dumps(events, default=str) if events else None,
                    now_iso,
                ),
            )
