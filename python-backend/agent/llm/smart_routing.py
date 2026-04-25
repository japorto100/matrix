"""Smart cheap-vs-strong model routing per user-turn.

Port of ``_ref/hermes-agent/agent/smart_model_routing.py`` adapted for
matrix's enterprise + multi-domain context. The hermes heuristic is
tuned for CLI-coding (complex-keywords like ``pytest``, ``kubernetes``,
``terminal``); matrix runs across trading, research, data-ops, coding —
the keyword set therefore spans all those domains.

**Policy philosophy:** conservative by design — a message must look
clearly simple to route to the cheap model. Anything that smells like a
complex task (URLs, code-fences, multi-line, long, domain-specific
keywords) stays on the primary model. False-negatives are cheap (pay
for primary); false-positives degrade user experience (weaker reply).

**Bilingual keyword set (ADR-001 G1):** matrix serves a German-speaking
user-base; the keyword set therefore covers EN + DE forms of the same
concept in parallel (e.g. ``analyze / analysiere / analyse``) and
splits hyphenated compounds (``sharpe-ratio`` → ``{sharpe, ratio}``).
Without this the conservative bias inverts for DE queries — exactly
the case where users expect the primary (stronger) model.

**Config source:** per-user `agent.user_llm_settings` (migration 009+).
The existing JSONB columns (`selected_models`, `utility_models`,
`per_role_overrides`) can carry a new `smart_routing` sub-key without a
schema change — keeps the migration surface zero and lets the control-
ui surface it as a toggle.

Expected config shape::

    {
      "enabled": true,
      "cheap_model": "gpt-4o-mini" | "openai/gpt-4o-mini",
      "max_simple_chars": 160,      # optional, default below
      "max_simple_words": 28        # optional, default below
    }

**Phase-C integration:** when a turn is routed to the cheap model, the
span carries `llm.routing_reason="simple_turn"` + `llm.routing_picked`
so A/B analysis (exec-harness §4g) can isolate smart-routing impact on
fitness. Smart-routing is orthogonal to the hybrid-loop variant — both
LangGraph and SimpleLoop runners honour the decision.

exec-a2fm is the home-spec; see exec-hermes §0 gems matrix row.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "RouteDecision",
    "choose_cheap_model_route",
    "resolve_model_for_turn",
]


# Keywords that reliably correlate with "this is a complex task" across
# matrix's supported domains. Intentionally broader than hermes (which
# was CLI-coding-only, English-only). Keyword-matching is
# language-parallel: both EN and DE forms of the same concept are
# included so DE-speaking users' complex queries don't silently route to
# the cheap model (ADR-001 G1 — without this the conservative-bias
# claim in the module docstring is inverted for the target user base).
#
# Verb forms: we include the common flected forms a user would actually
# type (e.g. "analysiere", "analysiert", "analyse") because this module
# uses exact set-intersection on tokenized words, not stemming.
_COMPLEX_KEYWORDS = frozenset({
    # --- coding / CLI ---
    # EN
    "debug", "debugging", "implement", "implementation", "refactor",
    "patch", "traceback", "stacktrace", "exception", "pytest",
    "terminal", "shell", "cron", "docker",
    "kubernetes", "compile", "deploy", "migration", "rollback",
    # DE
    "debuggen", "implementiere", "implementieren", "implementierung",
    "refaktoriere", "refaktorieren", "refactoring", "teste", "testen",
    "fehler", "ausnahme", "stapel", "kompiliere", "kompilieren",
    "einsetzen", "werkzeug", "werkzeuge", "zurücksetzen",
    # --- reasoning ---
    # EN
    "analyze", "analysis", "investigate", "architecture", "design",
    "compare", "benchmark", "optimize", "optimise",
    "planning", "delegate", "subagent", "evaluate",
    # DE
    "analysiere", "analysieren", "analysiert", "analyse", "untersuche",
    "untersuchen", "untersuchung", "architektur", "entwurf",
    "entwerfe", "entwerfen", "gestalte", "gestalten", "vergleiche",
    "vergleichen", "vergleich", "optimiere", "optimieren",
    "optimierung", "überarbeite", "überarbeiten", "plane", "planen",
    "planung", "bewerte", "bewerten", "bewertung", "begründe",
    "begründen", "prüfe", "prüfen", "prüfung",
    # --- trading / finance (matrix-specific) ---
    # EN
    "portfolio", "rebalance", "backtest", "options", "derivative",
    "margin", "leverage", "liquidity", "arbitrage", "strategy",
    "risk", "var", "drawdown", "sharpe", "pnl", "volatility",
    # DE (portfolio/arbitrage/backtest same as EN)
    "rebalancieren", "rebalancing", "optionen", "derivat", "derivate",
    "marge", "hebel", "liquidität", "strategie", "risiko", "varianz",
    "volatilität", "rendite", "renditen", "positionen", "position",
    "auftrag", "aufträge",
    # --- research / kg ---
    # EN
    "research", "synthesize", "literature", "citation", "hypothesis",
    "claim", "evidence", "contradict", "corroborate",
    # DE
    "recherche", "recherchiere", "recherchieren", "synthetisiere",
    "synthetisieren", "literatur", "zitat", "zitate", "hypothese",
    "behauptung", "beleg", "beweis", "widersprechen", "bestätigen",
    "bestätige", "untermauern",
    # --- data / ML ---
    # EN
    "dataset", "embedding", "train", "fine-tune", "finetune",
    "evaluation", "inference", "prompt",
    # DE
    "datensatz", "datensätze", "training", "trainiere", "trainieren",
    "feinabstimmung", "auswertung", "auswerten", "schlussfolgerung",
    "modell", "modelle", "eingabeaufforderung",
})

_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"```|`[^`]+`")
_COMPLEX_PHRASES = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(unit|integration|e2e|regression)\s+tests?\b",
        r"\btest\s+(suite|coverage|failure|failures|runner|matrix)\b",
        r"\b(code|pull\s+request|pr|architecture|security)\s+review\b",
        r"\breview\s+(this|the)?\s*(code|diff|patch|pr|pull\s+request)\b",
        r"\bfine[-\s]?tune\b",
        r"\b(reason|reasoning)\s+(through|about|chain|trace)\b",
        r"\b(model|prompt)\s+(routing|selection|metadata|pricing|evaluation)\b",
        r"\b(plan|planning)\s+(architecture|migration|rollout|implementation)\b",
    )
)


@dataclass(frozen=True)
class RouteDecision:
    """Outcome of :func:`resolve_model_for_turn`.

    When ``used_cheap`` is ``True``, ``model`` is the cheap model from
    config; otherwise it's the primary model the caller passed in.
    ``reason`` is surfaced as a span-attribute for A/B analysis.
    """

    model: str
    used_cheap: bool
    reason: str  # "simple_turn" | "config_disabled" | "no_cheap_configured" | "complex_heuristic" | ...


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on", "enabled")
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def choose_cheap_model_route(
    user_message: str,
    routing_config: dict[str, Any] | None,
) -> str | None:
    """Return the cheap model id when the message looks simple, else None.

    ``routing_config`` is the ``smart_routing`` sub-dict from the user's
    ``agent.user_llm_settings`` row. Missing / disabled / malformed
    configs return ``None`` (fall through to primary).
    """
    if not routing_config or not _as_bool(routing_config.get("enabled"), False):
        return None

    cheap_model = str(routing_config.get("cheap_model") or "").strip()
    if not cheap_model:
        return None

    text = (user_message or "").strip()
    if not text:
        # Empty user-message — not a routable turn. Primary handles the
        # edge case (e.g. tool-only continuation).
        return None

    max_chars = _as_int(routing_config.get("max_simple_chars"), 160)
    max_words = _as_int(routing_config.get("max_simple_words"), 28)

    if len(text) > max_chars:
        return None
    if len(text.split()) > max_words:
        return None
    if text.count("\n") > 1:
        return None
    if _CODE_FENCE_RE.search(text):
        return None
    if _URL_RE.search(text):
        return None
    if any(pattern.search(text) for pattern in _COMPLEX_PHRASES):
        return None

    # Tokenize: lowercase → whitespace-split → strip punctuation →
    # also split hyphenated compounds so "Sharpe-Ratio" → {sharpe, ratio}
    # and "risk-adjusted" → {risk, adjusted}. Without this split,
    # hyphenated domain terms bypass the keyword gate (ADR-001 G1).
    lowered = text.lower()
    words: set[str] = set()
    for tok in lowered.split():
        stripped = tok.strip(".,:;!?()[]{}\"'`")
        if not stripped:
            continue
        # Hyphen-split — handles "sharpe-ratio", "risk-adjusted",
        # "back-test", "fine-tune". Also keeps single-word tokens
        # unchanged (no hyphen → single-element list).
        for piece in stripped.split("-"):
            if piece:
                words.add(piece)
    if words & _COMPLEX_KEYWORDS:
        return None

    return cheap_model


def resolve_model_for_turn(
    *,
    user_message: str,
    primary_model: str,
    routing_config: dict[str, Any] | None,
) -> RouteDecision:
    """Top-level entry point used by :mod:`agent.graph.nodes.llm_node`.

    Returns a :class:`RouteDecision` whose ``model`` is the one to call.
    Never raises — malformed configs fall through to the primary.
    """
    if not primary_model:
        return RouteDecision(
            model=primary_model, used_cheap=False, reason="no_primary",
        )
    if not routing_config:
        return RouteDecision(
            model=primary_model, used_cheap=False, reason="config_absent",
        )
    if not _as_bool(routing_config.get("enabled"), False):
        return RouteDecision(
            model=primary_model, used_cheap=False, reason="config_disabled",
        )

    cheap = choose_cheap_model_route(user_message, routing_config)
    if cheap is None:
        # Either no cheap-model configured, or heuristic said "complex".
        has_cheap = bool(str(routing_config.get("cheap_model") or "").strip())
        reason = "complex_heuristic" if has_cheap else "no_cheap_configured"
        return RouteDecision(
            model=primary_model, used_cheap=False, reason=reason,
        )
    return RouteDecision(
        model=cheap, used_cheap=True, reason="simple_turn",
    )
