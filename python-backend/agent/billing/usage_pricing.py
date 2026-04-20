"""Canonical usage + LiteLLM-backed cost estimation.

Slim port of ``_ref/hermes-agent/agent/usage_pricing.py`` (687 LOC → ~180
LOC). We keep hermes' excellent :class:`CanonicalUsage` dataclass verbatim
(battle-tested across 4 providers) but replace the 500+ LOC of
``_OFFICIAL_DOCS_PRICING`` + OAuth-refresh + per-key-billing-mode logic
with a thin LiteLLM-first / snapshot-fallback cost estimator.

Why LiteLLM-first:

* LiteLLM ships with ``model_cost`` dict covering 100+ models (updated in
  each release) — matrix doesn't have to curate its own table
* Cache-read / cache-write / reasoning-token pricing is surfaced in
  LiteLLM's ``get_model_info``
* One source of truth instead of two that drift

Snapshot fallback:
For models LiteLLM doesn't know (custom deployments, new releases before
LiteLLM update) we carry a **small** dict of current flagship models. Keep
it under 20 entries — the moment it grows past that it's a sign LiteLLM
should be the source and we should remove snapshot entries.

exec-16.md §2.10 — Billing Ledger (CanonicalUsage → span → insights aggregate).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

logger = logging.getLogger(__name__)

__all__ = [
    "CanonicalUsage",
    "CostResult",
    "CostStatus",
    "estimate_usage_cost",
    "usage_from_litellm",
]

CostStatus = Literal["actual", "estimated", "included", "unknown"]

_ZERO = Decimal("0")
_ONE_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class CanonicalUsage:
    """Unified token-usage across providers (OpenAI / Anthropic / Google / OpenRouter).

    Provider response shapes differ:

    * OpenAI: ``{prompt_tokens, completion_tokens, total_tokens, prompt_tokens_details.cached_tokens}``
    * Anthropic: ``{input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens}``
    * Google: ``{promptTokenCount, candidatesTokenCount, totalTokenCount}``

    :func:`usage_from_litellm` normalises them.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    request_count: int = 1
    raw_usage: dict[str, Any] | None = None

    @property
    def prompt_tokens(self) -> int:
        """Total prompt tokens including cache hits/writes (for legacy billing)."""
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens


@dataclass(frozen=True)
class CostResult:
    amount_usd: Decimal | None
    status: CostStatus
    source: str = ""
    notes: tuple[str, ...] = ()

    @property
    def is_known(self) -> bool:
        return self.amount_usd is not None


# ---------------------------------------------------------------------------
# LiteLLM-integration
# ---------------------------------------------------------------------------


def usage_from_litellm(response_usage: dict[str, Any] | None) -> CanonicalUsage:
    """Build a :class:`CanonicalUsage` from LiteLLM's normalised response usage.

    LiteLLM already harmonises provider-specific shapes into:
    ``{prompt_tokens, completion_tokens, total_tokens}`` with optional
    ``prompt_tokens_details.cached_tokens`` / ``cache_creation_input_tokens``
    / ``completion_tokens_details.reasoning_tokens`` for providers that
    expose them.
    """
    if not response_usage or not isinstance(response_usage, dict):
        return CanonicalUsage()

    input_tokens = int(response_usage.get("prompt_tokens") or 0)
    output_tokens = int(response_usage.get("completion_tokens") or 0)

    # Cache details — LiteLLM exposes under prompt_tokens_details on OpenAI
    # and directly on Anthropic responses.
    cache_read = 0
    cache_write = 0
    ptd = response_usage.get("prompt_tokens_details")
    if isinstance(ptd, dict):
        cache_read = int(ptd.get("cached_tokens") or 0)
    cache_read = cache_read or int(
        response_usage.get("cache_read_input_tokens") or 0
    )
    cache_write = int(response_usage.get("cache_creation_input_tokens") or 0)

    # Reasoning-tokens (OpenAI o-series, Anthropic extended-thinking).
    reasoning = 0
    ctd = response_usage.get("completion_tokens_details")
    if isinstance(ctd, dict):
        reasoning = int(ctd.get("reasoning_tokens") or 0)
    reasoning = reasoning or int(response_usage.get("reasoning_tokens") or 0)

    # input_tokens in CanonicalUsage is "fresh" input — subtract cached
    # reads so double-billing doesn't happen downstream.
    fresh_input = max(0, input_tokens - cache_read - cache_write)

    return CanonicalUsage(
        input_tokens=fresh_input,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        reasoning_tokens=reasoning,
        request_count=1,
        raw_usage=dict(response_usage),
    )


def _per_million(cost_per_token: Any) -> Decimal | None:
    """Convert LiteLLM's per-token cost (float) to per-million Decimal."""
    if cost_per_token is None:
        return None
    try:
        return Decimal(str(cost_per_token)) * _ONE_MILLION
    except (TypeError, ValueError):
        return None


def _cost_from_litellm(model: str, usage: CanonicalUsage) -> CostResult | None:
    """Try LiteLLM's ``get_model_info`` for pricing. Return None if unavailable."""
    try:
        from agent.llm.model_metadata import get_model_info
    except ImportError:
        return None

    info = get_model_info(model)
    if not info:
        return None

    in_cost = _per_million(info.get("input_cost_per_token"))
    out_cost = _per_million(info.get("output_cost_per_token"))
    cr_cost = _per_million(info.get("cache_read_input_token_cost"))
    cw_cost = _per_million(info.get("cache_creation_input_token_cost"))

    if in_cost is None and out_cost is None:
        return None

    amount = _ZERO
    if in_cost is not None:
        amount += Decimal(usage.input_tokens) * in_cost / _ONE_MILLION
    if out_cost is not None:
        amount += Decimal(usage.output_tokens) * out_cost / _ONE_MILLION
    # Cache tokens: if LiteLLM exposes their own rate use it, otherwise
    # fall back to input rate (best-effort, matches provider defaults).
    effective_cr = cr_cost if cr_cost is not None else in_cost
    if effective_cr is not None:
        amount += Decimal(usage.cache_read_tokens) * effective_cr / _ONE_MILLION
    effective_cw = cw_cost if cw_cost is not None else in_cost
    if effective_cw is not None:
        amount += Decimal(usage.cache_write_tokens) * effective_cw / _ONE_MILLION

    return CostResult(
        amount_usd=amount,
        status="estimated",
        source="litellm",
    )


# Minimal snapshot fallback for models LiteLLM doesn't yet know. Keep this
# list short — grow LiteLLM upstream instead. All costs per 1M tokens.
_SNAPSHOT_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "claude-opus-4-7": (Decimal("15.00"), Decimal("75.00")),
    "claude-sonnet-4-6": (Decimal("3.00"), Decimal("15.00")),
    "claude-haiku-4-5-20251001": (Decimal("0.80"), Decimal("4.00")),
}


def _cost_from_snapshot(model: str, usage: CanonicalUsage) -> CostResult | None:
    # Strip provider prefix (``anthropic/claude-…`` → ``claude-…``).
    bare = model.rsplit("/", 1)[-1]
    entry = _SNAPSHOT_PRICING.get(bare)
    if entry is None:
        return None
    in_cost, out_cost = entry
    amount = (
        Decimal(usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens)
        * in_cost
        / _ONE_MILLION
        + Decimal(usage.output_tokens) * out_cost / _ONE_MILLION
    )
    return CostResult(
        amount_usd=amount,
        status="estimated",
        source="snapshot",
        notes=("falling back to static snapshot; LiteLLM has no data for this model",),
    )


def estimate_usage_cost(
    model: str,
    usage: CanonicalUsage,
) -> CostResult:
    """Estimate USD cost for a (model, usage) pair.

    Tries LiteLLM first, then snapshot fallback, finally returns ``unknown``.
    Never raises — callers can always attach the result to a span.
    """
    result = _cost_from_litellm(model, usage)
    if result is not None:
        return result
    result = _cost_from_snapshot(model, usage)
    if result is not None:
        return result
    return CostResult(amount_usd=None, status="unknown", source="none")
