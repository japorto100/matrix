"""Tests for agent/llm/model_metadata.py."""
from __future__ import annotations

from agent.llm import model_metadata as mm


def test_normalize_empty():
    assert mm.normalize_model_id("") == ""
    assert mm.normalize_model_id(None) == ""


def test_normalize_colon_to_slash():
    assert mm.normalize_model_id("openai:gpt-4o") == "openai/gpt-4o"


def test_normalize_preserves_slash_form():
    assert mm.normalize_model_id("anthropic/claude-sonnet-4-6") == "anthropic/claude-sonnet-4-6"


def test_normalize_strips_whitespace():
    assert mm.normalize_model_id("  gpt-4o  ") == "gpt-4o"


def test_context_window_known_model():
    # gpt-4o has a stable 128000-token context in LiteLLM.
    mm.reset_cache()
    assert mm.get_model_context_window("gpt-4o") == 128_000


def test_context_window_fallback():
    mm.reset_cache()
    # Totally-made-up model name → LiteLLM returns nothing → fallback.
    assert mm.get_model_context_window("fake-model-xyzzy") == mm.DEFAULT_CONTEXT_WINDOW


def test_cache_hit_shortcircuits_lookup():
    mm.reset_cache()
    # First call populates; second should be cache-hit (cheap).
    first = mm.get_model_info("gpt-4o")
    assert first is not None
    second = mm.get_model_info("gpt-4o")
    assert second is first  # same object → cached


def test_get_model_info_unknown():
    mm.reset_cache()
    assert mm.get_model_info("nonexistent-model-123") is None
