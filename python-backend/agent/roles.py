# Agent roles — exec-10: erweitert mit Trading-spezifischen Rollen
# Basis: 4-role pattern (Extractor, Verifier, Guard, Synthesizer)
# Neu: 6 Trading-Rollen (inspiriert von TauricResearch/TradingAgents)

from __future__ import annotations

from enum import StrEnum


class AgentRole(StrEnum):
    """Four-role pattern for all KI workflows."""

    EXTRACTOR = "extractor"  # LLM: "Was steht im Text?"
    VERIFIER = "verifier"  # LLM + rules: "Stimmt das wirklich?"
    GUARD = "guard"  # Code-only: "Was sagen die Regeln?"
    SYNTHESIZER = "synthesizer"  # LLM: "Was bedeutet das fuer den User?"


class TradingRole(StrEnum):
    """Trading-spezifische Rollen fuer Multi-Agent Orchestrierung (exec-10).

    Inspiriert von TauricResearch/TradingAgents.
    Jede Rolle hat eigenen System-Prompt, eigene Tools, scoped Context.
    """

    FUNDAMENTALS = "fundamentals_analyst"
    SENTIMENT = "sentiment_analyst"
    TECHNICAL = "technical_analyst"
    RESEARCHER = "researcher"
    TRADER = "trader"
    RISK_MANAGER = "risk_manager"


# System-Prompts pro Trading-Rolle
TRADING_ROLE_PROMPTS: dict[TradingRole, str] = {
    TradingRole.FUNDAMENTALS: (
        "You are a Fundamentals Analyst. Analyze company financials: "
        "balance sheets, income statements, cash flow, earnings reports, and valuation metrics. "
        "Provide data-driven assessments of intrinsic value and financial health. "
        "Focus on P/E, P/B, debt ratios, revenue growth, and margin trends."
    ),
    TradingRole.SENTIMENT: (
        "You are a Sentiment Analyst. Analyze market sentiment from news, social media, "
        "analyst ratings, and market indicators (VIX, put/call ratios, fund flows). "
        "Assess whether sentiment is bullish, bearish, or neutral. "
        "Identify sentiment shifts and contrarian signals."
    ),
    TradingRole.TECHNICAL: (
        "You are a Technical Analyst. Analyze price charts, patterns, and indicators. "
        "Use RSI, MACD, moving averages, Bollinger Bands, support/resistance levels, "
        "volume analysis, and candlestick patterns. "
        "Identify trend direction, momentum, and potential reversal points."
    ),
    TradingRole.RESEARCHER: (
        "You are a Research Analyst. Synthesize findings from fundamental, sentiment, "
        "and technical analysis. Present balanced bull and bear arguments. "
        "Weigh evidence objectively and highlight key uncertainties. "
        "Provide a research summary with confidence level. "
        "When producing report artifacts, every factual paragraph must cite source "
        "markers like [S1] or explicitly mark unsupported material as [UNSUPPORTED]; "
        "validate with report_validate before calling report_build."
    ),
    TradingRole.TRADER: (
        "You are a Trader. Based on the research summary, make actionable trading decisions. "
        "Define entry/exit points, position size, and timeframe. "
        "Consider risk/reward ratio, market conditions, and portfolio context. "
        "Always state your conviction level and reasoning."
    ),
    TradingRole.RISK_MANAGER: (
        "You are a Risk Manager. Evaluate proposed trades for risk exposure. "
        "Check position sizing, portfolio concentration, correlation risk, and drawdown limits. "
        "Approve, modify, or reject trade proposals based on risk parameters. "
        "Enforce maximum loss limits and diversification rules. "
        "For generated risk reports, require source citations, checksum validation, "
        "and report_validate evidence before publication or attachment handoff."
    ),
}

# Tools pro Rolle (Name → erlaubte Tool-Namen)
TRADING_ROLE_TOOLS: dict[TradingRole, set[str]] = {
    TradingRole.FUNDAMENTALS: {
        "get_portfolio_summary",
        "get_chart_state",
        "save_memory",
        "load_memory",
        "semantic_lookup",
        "retrieve_context",
        "report_validate",
        "sandbox_execute",
    },
    TradingRole.SENTIMENT: {
        "get_chart_state",
        "save_memory",
        "load_memory",
        "semantic_lookup",
        "retrieve_context",
        "report_validate",
    },
    TradingRole.TECHNICAL: {
        "get_chart_state",
        "save_memory",
        "load_memory",
        "semantic_lookup",
        "retrieve_context",
        "report_validate",
        "sandbox_execute",
    },
    TradingRole.RESEARCHER: {
        "get_chart_state",
        "get_portfolio_summary",
        "save_memory",
        "load_memory",
        "semantic_lookup",
        "retrieve_context",
        "report_validate",
        "report_build",
        "sandbox_execute",
        "sandbox_browser",
    },
    TradingRole.TRADER: {
        "get_chart_state",
        "set_chart_state",
        "get_portfolio_summary",
        "save_memory",
        "load_memory",
        "semantic_lookup",
        "retrieve_context",
        "report_validate",
    },
    TradingRole.RISK_MANAGER: {
        "get_portfolio_summary",
        "save_memory",
        "load_memory",
        "semantic_lookup",
        "retrieve_context",
        "report_validate",
        "report_build",
    },
}

# Memory Sharing Permissions pro Rolle (exec-11 Phase 3.3)
# memory_write: darf Memories retainen (False = read-only)
# memory_recall_tags: None = alle sehen, Liste = nur diese Tags
TRADING_ROLE_MEMORY: dict[TradingRole, dict] = {
    TradingRole.FUNDAMENTALS: {"memory_write": True, "memory_recall_tags": None},
    TradingRole.SENTIMENT: {"memory_write": True, "memory_recall_tags": None},
    TradingRole.TECHNICAL: {"memory_write": True, "memory_recall_tags": None},
    TradingRole.RESEARCHER: {"memory_write": True, "memory_recall_tags": None},
    TradingRole.TRADER: {"memory_write": True, "memory_recall_tags": None},
    TradingRole.RISK_MANAGER: {
        "memory_write": False,
        "memory_recall_tags": None,
    },  # read-only
}

# Completion Gate Contracts pro Rolle (NLAH Paper Pattern)
# Jeder Contract definiert was der Agent-Output ENTHALTEN MUSS.
TRADING_ROLE_CONTRACTS: dict[TradingRole, list[str]] = {
    TradingRole.RESEARCHER: [
        "Must include bull arguments",
        "Must include bear arguments",
        "Must state confidence level",
        "Report artifacts must cite every factual paragraph or mark it [UNSUPPORTED]",
        "Report artifacts must pass report_validate before report_build",
    ],
    TradingRole.TRADER: [
        "Must define entry point",
        "Must define exit/target",
        "Must define stop loss",
    ],
    TradingRole.RISK_MANAGER: [
        "Must state approval or rejection",
        "Must provide risk score",
        "Risk reports must include citation and checksum validation evidence",
    ],
}
