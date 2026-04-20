"""LiteLLM-backed model-metadata wrapper with in-memory TTL cache.

Hermes `_ref/hermes-agent/agent/model_metadata.py` is 1116 LOC because it
caches sync `requests.get()` fetches against OpenRouter + Anthropic
provider-APIs at import-time. Matrix doesn't need that: LiteLLM
(``litellm.get_model_info``) already normalises model metadata across
providers, ships with pricing + context-window data, and caches internally.
This module is the **thin wrapper** — ~80 LOC — that replaces the 3
hardcoded ``MODEL_MAX_TOKENS`` / ``MODEL_COST_PER_MTOK`` dicts scattered
across the codebase.

Public API:

* :func:`get_model_info(model)` — full ``ModelInfo`` dict from LiteLLM, or
  ``None`` if the model is unknown.
* :func:`get_model_context_window(model)` — ``max_input_tokens`` (or
  ``max_tokens`` fallback). Replaces hardcoded dicts.
* :func:`normalize_model_id(raw)` — canonicalises ``claude-sonnet-4-6`` ↔
  ``anthropic/claude-sonnet-4-6``, etc.
* :data:`DEFAULT_CONTEXT_WINDOW` — absolute fallback when LiteLLM has no
  data. 200_000 is a safe 2026 modern-model default.

TTL: 1 hour. LiteLLM already caches internally but its cache is process-
local and lossy across imports. Our cache layers on top so the same model
ID resolved twice in one minute doesn't re-run LiteLLM's dispatch.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


DEFAULT_CONTEXT_WINDOW: int = 200_000
_TTL_SECONDS: float = 3600.0

# (value, expires_at_monotonic) keyed by normalised model id.
_cache: dict[str, tuple[dict[str, Any] | None, float]] = {}


def normalize_model_id(raw: str | None) -> str:
    """Return a canonical model id for LiteLLM lookup.

    Callers pass IDs in many shapes: ``claude-sonnet-4-6``,
    ``anthropic/claude-sonnet-4-6``, ``openai:gpt-4o-mini``,
    ``openrouter/meta-llama/llama-3-70b-instruct``. LiteLLM accepts most of
    these but a leading whitespace or accidental uppercase can miss. Normalise
    here so the cache key is stable.
    """
    if not raw:
        return ""
    text = raw.strip()
    # ``openai:foo`` → ``openai/foo`` for LiteLLM compatibility
    if ":" in text and "/" not in text and "://" not in text:
        text = text.replace(":", "/", 1)
    return text


def _fetch_model_info(model: str) -> dict[str, Any] | None:
    try:
        import litellm  # local import — optional dependency in tests
    except ImportError:
        return None

    try:
        return litellm.get_model_info(model)
    except Exception as exc:  # noqa: BLE001
        logger.debug("litellm.get_model_info(%s) failed: %s", model, exc)
        return None


def get_model_info(model: str) -> dict[str, Any] | None:
    """Return LiteLLM's ModelInfo dict (cached ~1h). ``None`` if unknown.

    Keys include: ``max_tokens``, ``max_input_tokens``,
    ``max_output_tokens``, ``input_cost_per_token``,
    ``output_cost_per_token``, ``cache_read_input_token_cost``, etc.
    """
    key = normalize_model_id(model)
    if not key:
        return None
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and hit[1] > now:
        return hit[0]
    info = _fetch_model_info(key)
    _cache[key] = (info, now + _TTL_SECONDS)
    return info


def get_model_context_window(model: str) -> int:
    """Return the model's context window. Falls back to ``DEFAULT_CONTEXT_WINDOW``.

    LiteLLM exposes ``max_input_tokens`` (preferred — only the prompt budget)
    and ``max_tokens`` (historic — often equal to ``max_input_tokens``
    minus completion tokens). We prefer the former for context-engine
    sizing but accept either.
    """
    info = get_model_info(model)
    if info is None:
        return DEFAULT_CONTEXT_WINDOW
    for key in ("max_input_tokens", "max_tokens"):
        value = info.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return DEFAULT_CONTEXT_WINDOW


def reset_cache() -> None:
    """Test-hook: clear the TTL cache."""
    _cache.clear()
