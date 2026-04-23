"""Tests for agent/llm/smart_routing.py."""
from __future__ import annotations

from agent.llm.smart_routing import (
    RouteDecision,
    choose_cheap_model_route,
    resolve_model_for_turn,
)

# Minimal enabled config used by most tests.
_CFG = {"enabled": True, "cheap_model": "gpt-4o-mini"}


def test_disabled_config_returns_none():
    assert choose_cheap_model_route("hi", {"enabled": False, "cheap_model": "x"}) is None


def test_missing_cheap_model_returns_none():
    assert choose_cheap_model_route("hi", {"enabled": True}) is None


def test_empty_message_returns_none():
    assert choose_cheap_model_route("", _CFG) is None
    assert choose_cheap_model_route("   ", _CFG) is None


def test_simple_short_message_routes():
    assert choose_cheap_model_route("wie geht es dir?", _CFG) == "gpt-4o-mini"


def test_over_char_limit_rejected():
    long_msg = "x" * 200
    assert choose_cheap_model_route(long_msg, _CFG) is None


def test_over_word_limit_rejected():
    long_msg = " ".join(["word"] * 40)
    assert choose_cheap_model_route(long_msg, _CFG) is None


def test_multiline_rejected():
    msg = "line 1\nline 2\nline 3"
    assert choose_cheap_model_route(msg, _CFG) is None


def test_code_fence_rejected():
    assert choose_cheap_model_route("run ```this code```", _CFG) is None
    assert choose_cheap_model_route("try `foo()`", _CFG) is None


def test_url_rejected():
    assert choose_cheap_model_route("check https://example.com", _CFG) is None
    assert choose_cheap_model_route("visit www.foo.org", _CFG) is None


def test_complex_keyword_coding_rejected():
    assert choose_cheap_model_route("debug this", _CFG) is None
    assert choose_cheap_model_route("refactor the function", _CFG) is None


def test_complex_keyword_trading_rejected():
    """matrix-specific: trading terms should stay on primary model."""
    assert choose_cheap_model_route("rebalance my portfolio", _CFG) is None
    assert choose_cheap_model_route("backtest this strategy", _CFG) is None
    assert choose_cheap_model_route("compute sharpe ratio", _CFG) is None


def test_complex_keyword_research_rejected():
    assert choose_cheap_model_route("synthesize the literature", _CFG) is None
    assert choose_cheap_model_route("evaluate this hypothesis", _CFG) is None


def test_resolve_defaults():
    """Empty config → always primary."""
    decision = resolve_model_for_turn(
        user_message="hi", primary_model="gpt-4o", routing_config=None,
    )
    assert decision == RouteDecision(
        model="gpt-4o", used_cheap=False, reason="config_absent",
    )


def test_resolve_disabled():
    decision = resolve_model_for_turn(
        user_message="hi",
        primary_model="gpt-4o",
        routing_config={"enabled": False, "cheap_model": "gpt-4o-mini"},
    )
    assert decision.used_cheap is False
    assert decision.model == "gpt-4o"
    assert decision.reason == "config_disabled"


def test_resolve_simple_routes_to_cheap():
    decision = resolve_model_for_turn(
        user_message="hallo wie geht's",
        primary_model="claude-opus-4-7",
        routing_config=_CFG,
    )
    assert decision.used_cheap is True
    assert decision.model == "gpt-4o-mini"
    assert decision.reason == "simple_turn"


def test_resolve_complex_stays_primary():
    decision = resolve_model_for_turn(
        user_message="please debug this stacktrace",
        primary_model="claude-opus-4-7",
        routing_config=_CFG,
    )
    assert decision.used_cheap is False
    assert decision.model == "claude-opus-4-7"
    assert decision.reason == "complex_heuristic"


def test_resolve_no_cheap_configured_falls_through():
    decision = resolve_model_for_turn(
        user_message="hi",
        primary_model="gpt-4o",
        routing_config={"enabled": True},  # no cheap_model
    )
    assert decision.used_cheap is False
    assert decision.reason == "no_cheap_configured"


def test_resolve_custom_thresholds():
    """User can tighten thresholds via config."""
    tight_cfg = {
        "enabled": True,
        "cheap_model": "gpt-4o-mini",
        "max_simple_chars": 10,
        "max_simple_words": 3,
    }
    # "hallo wie geht's" = 16 chars > 10 → rejected
    decision = resolve_model_for_turn(
        user_message="hallo wie geht's",
        primary_model="gpt-4o",
        routing_config=tight_cfg,
    )
    assert decision.used_cheap is False


def test_resolve_truthy_coercion():
    """Config values often arrive as strings from JSONB/env — accept 'true'."""
    decision = resolve_model_for_turn(
        user_message="hi",
        primary_model="gpt-4o",
        routing_config={"enabled": "true", "cheap_model": "gpt-4o-mini"},
    )
    assert decision.used_cheap is True


# ---------------------------------------------------------------------------
# ADR-001 G1 — bilingual keyword set + hyphen-tokenizer
# ---------------------------------------------------------------------------

def test_de_reasoning_keyword_rejected():
    """DE reasoning verbs must route to primary, not cheap."""
    assert choose_cheap_model_route("analysiere das kurz", _CFG) is None
    assert choose_cheap_model_route("bewerte den text", _CFG) is None
    assert choose_cheap_model_route("vergleiche a und b", _CFG) is None
    assert choose_cheap_model_route("prüfe das bitte", _CFG) is None


def test_de_trading_keyword_rejected():
    """DE trading/finance terms must route to primary."""
    assert choose_cheap_model_route("mein portfolio", _CFG) is None
    assert choose_cheap_model_route("berechne das risiko", _CFG) is None
    assert choose_cheap_model_route("optimiere die strategie", _CFG) is None
    assert choose_cheap_model_route("welche positionen?", _CFG) is None


def test_de_research_keyword_rejected():
    """DE research terms must route to primary."""
    assert choose_cheap_model_route("recherche zum thema", _CFG) is None
    assert choose_cheap_model_route("deine hypothese?", _CFG) is None


def test_de_coding_keyword_rejected():
    """DE coding verbs must route to primary."""
    assert choose_cheap_model_route("implementiere das", _CFG) is None
    assert choose_cheap_model_route("refaktoriere bitte", _CFG) is None


def test_de_simple_greeting_routes():
    """DE trivial small-talk should still route to cheap."""
    assert choose_cheap_model_route("hallo wie geht es dir", _CFG) == "gpt-4o-mini"
    assert choose_cheap_model_route("was gibt es neues", _CFG) == "gpt-4o-mini"


def test_hyphen_compound_matches_keyword():
    """Hyphenated compounds must be split so 'Sharpe-Ratio' hits sharpe."""
    assert choose_cheap_model_route("Sharpe-Ratio", _CFG) is None
    assert choose_cheap_model_route("risk-adjusted return", _CFG) is None
    assert choose_cheap_model_route("fine-tune the model", _CFG) is None


def test_hyphen_non_keyword_still_routes():
    """Hyphenated text without complex keywords should still route."""
    assert choose_cheap_model_route("one-off question", _CFG) == "gpt-4o-mini"


def test_de_analyse_all_flections():
    """All common flection forms of 'analysieren' block cheap route."""
    for msg in (
        "analysiere das",
        "analysieren bitte",
        "analysiert hier",
        "deine analyse?",
    ):
        assert choose_cheap_model_route(msg, _CFG) is None, f"should reject: {msg}"


def test_resolve_de_complex_stays_primary():
    """End-to-end: DE complex question resolves to primary with reason."""
    decision = resolve_model_for_turn(
        user_message="analysiere meine positionen",
        primary_model="claude-opus-4-7",
        routing_config=_CFG,
    )
    assert decision.used_cheap is False
    assert decision.model == "claude-opus-4-7"
    assert decision.reason == "complex_heuristic"
