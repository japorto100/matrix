"""Router Node — ADR-001 P1 inversion target.

Phase-1 of exec-a2fm: the smart cheap-vs-strong routing decision is
produced HERE as its own first-class node, instead of as a side-effect
inside :func:`agent.graph.nodes.llm_node.llm_node` (Phase-0.5 wire-point).

Why a dedicated node?

* **A/B semantics.** The dispatcher can treat ``routing_used`` as a
  proper variant dimension in fitness-regression analysis (ADR-001 G4).
* **iteration-0 guarantee.** The graph flow is
  ``START → memory_recall → router → llm_call → (tools → increment → llm_call)*``.
  Tool-continuation turns loop ``increment → llm_call`` directly — they
  never re-enter this node. So "first turn of a chat" is enforced by
  graph construction, not by a ``state["iteration"] == 0`` check that
  had to be re-derived everywhere.
* **Clean separation.** Smart-routing no longer mutates ``state["model"]``
  from inside the LLM-call hot path; the decision is produced upstream
  and llm_node consumes it via state.

Decision-output contract (written to state):

* ``model`` — the model ``llm_node`` should call (primary, or cheap
  when the heuristic said routing was safe + credentials present)
* ``llm_model`` — mirror of ``model`` for downstream spans
* ``routing_reason`` — mirror of
  :attr:`agent.llm.smart_routing.RouteDecision.reason`
* ``routing_used`` — ``True`` iff we routed to the cheap model
* ``routing_picked_model`` — the actual model chosen (cheap when
  routed, primary otherwise); ``""`` when routing was not evaluated

Side-effects (both non-blocking):

* Fire-and-forget UPDATE of ``agent.ab_experiments.routing_*`` via
  :func:`agent.runners.dispatcher._mark_routing` when ``ab_row_id``
  is present (set by the dispatcher for A/B runs).
* ``logger.debug`` on failure — routing **must never** break the turn.

See:

* ADR-001 rollout gate: ``docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md``
* exec-a2fm Phase-1 spec
"""
from __future__ import annotations

import logging
from typing import Any

from agent.graph.state import AgentGraphState

logger = logging.getLogger(__name__)


async def router_node(state: AgentGraphState) -> dict[str, Any]:
    """Resolve the cheap-vs-primary routing decision for this turn.

    Returns a dict merged into the graph state. Always sets
    ``routing_reason`` (even when routing was not evaluated, so
    downstream span-attributes stay stable).
    """
    model = state["model"]
    messages = state["messages"]
    user_id = state.get("user_id") or "anonymous"
    ab_row_id = state.get("ab_row_id") or ""

    routing_reason = "not_evaluated"
    routing_used = False
    routing_picked_model: str = ""
    resolved_model = model

    # Anonymous traffic doesn't have user config; skip entirely.
    if user_id == "anonymous":
        return _result(
            resolved_model,
            routing_reason=routing_reason,
            routing_used=routing_used,
            routing_picked_model=routing_picked_model,
        )

    try:
        from agent.llm.smart_routing import resolve_model_for_turn
        from agent.security.credentials import (
            get_user_smart_routing_config,
            user_has_provider_credential,
        )

        routing_cfg = await get_user_smart_routing_config(user_id)
        user_msg_text = _last_user_text(messages)
        decision = resolve_model_for_turn(
            user_message=user_msg_text,
            primary_model=model,
            routing_config=routing_cfg,
        )
        routing_reason = decision.reason

        if decision.used_cheap:
            # ADR-001 G2: cross-provider credential pre-flight.
            cheap_provider = _provider_label(decision.model)
            primary_provider = _provider_label(model)
            cheap_ok = cheap_provider == primary_provider or (
                await user_has_provider_credential(user_id, cheap_provider)
            )
            if cheap_ok:
                resolved_model = decision.model
                routing_used = True
                routing_picked_model = decision.model
            else:
                routing_reason = "no_cheap_credentials"
                routing_picked_model = model
        else:
            routing_picked_model = model
    except Exception:  # noqa: BLE001 — routing must never break the call
        logger.debug("smart_routing skipped in router_node", exc_info=True)

    # ADR-001 G4: fire-and-forget UPDATE on ab_experiments so the
    # harness can separate routing effects from runner-variant effects.
    if ab_row_id and routing_reason != "not_evaluated":
        try:
            import asyncio

            from agent.runners.dispatcher import _mark_routing

            asyncio.create_task(
                _mark_routing(
                    ab_row_id,
                    routing_used=routing_used,
                    routing_reason=routing_reason,
                    routing_picked_model=routing_picked_model,
                )
            )
        except Exception:  # noqa: BLE001 — telemetry must never break the call
            logger.debug("ab_experiments routing mark skipped", exc_info=True)

    return _result(
        resolved_model,
        routing_reason=routing_reason,
        routing_used=routing_used,
        routing_picked_model=routing_picked_model,
    )


def _result(
    model: str,
    *,
    routing_reason: str,
    routing_used: bool,
    routing_picked_model: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "llm_model": model,
        "routing_reason": routing_reason,
        "routing_used": routing_used,
        "routing_picked_model": routing_picked_model,
    }


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                blk.get("text", "")
                for blk in content
                if isinstance(blk, dict) and blk.get("type") == "text"
            )
    return ""


def _provider_label(model: str) -> str:
    """Mirror of :func:`agent.graph.nodes.llm_node._provider_label`."""
    parts = [part for part in str(model or "").split("/") if part]
    if not parts:
        return "litellm"
    if parts[0] == "openrouter":
        return "openrouter"
    if parts[0] in {"anthropic", "openai", "google", "deepseek", "groq", "mistral"}:
        return parts[0]
    return "litellm"
