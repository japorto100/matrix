"""Agent Card — A2A Protocol Agent Manifest (exec-10 Phase 4).

Definiert Capabilities, Skills, und Endpoints eines Agents.
Basiert auf Google A2A Protocol (a2aproject/A2A).
Vereinfacht: HTTP+JSON statt gRPC/Proto3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentSkill:
    """Eine Faehigkeit des Agents."""

    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


@dataclass
class AgentCard:
    """A2A Agent Card — beschreibt einen Agent fuer andere Agents."""

    name: str
    description: str
    version: str = "1.0.0"
    url: str = ""
    skills: list[AgentSkill] = field(default_factory=list)
    input_modes: list[str] = field(default_factory=lambda: ["text/plain"])
    output_modes: list[str] = field(default_factory=lambda: ["text/plain"])
    supports_streaming: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "url": self.url,
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "tags": s.tags,
                    "examples": s.examples,
                }
                for s in self.skills
            ],
            "default_input_modes": self.input_modes,
            "default_output_modes": self.output_modes,
            "capabilities": {"streaming": self.supports_streaming},
        }


# Vordefinierte Agent Cards fuer unsere Trading-Rollen
TRADING_AGENT_CARDS: dict[str, AgentCard] = {
    "fundamentals": AgentCard(
        name="Fundamentals Analyst",
        description="Analyzes company financials, valuations, and earnings.",
        skills=[
            AgentSkill(
                id="fundamentals-analysis",
                name="Financial Analysis",
                description="Balance sheet, income, cash flow analysis",
                tags=["finance", "valuation"],
            ),
        ],
    ),
    "sentiment": AgentCard(
        name="Sentiment Analyst",
        description="Analyzes market sentiment from news, social media, and indicators.",
        skills=[
            AgentSkill(
                id="sentiment-scan",
                name="Sentiment Scan",
                description="News and social media sentiment analysis",
                tags=["sentiment", "news"],
            ),
        ],
    ),
    "technical": AgentCard(
        name="Technical Analyst",
        description="Analyzes price charts, patterns, and technical indicators.",
        skills=[
            AgentSkill(
                id="chart-analysis",
                name="Chart Analysis",
                description="Multi-timeframe technical analysis",
                tags=["technical", "charts"],
            ),
        ],
    ),
    "researcher": AgentCard(
        name="Research Analyst",
        description="Synthesizes findings from all analysts into balanced research summary.",
        skills=[
            AgentSkill(
                id="research-synthesis",
                name="Research Synthesis",
                description="Bull/bear framework synthesis",
                tags=["research"],
            ),
        ],
    ),
    "trader": AgentCard(
        name="Trader",
        description="Makes actionable trading decisions based on research.",
        skills=[
            AgentSkill(
                id="trade-decision",
                name="Trade Decision",
                description="Entry/exit, position sizing",
                tags=["trading"],
            ),
        ],
    ),
    "risk_manager": AgentCard(
        name="Risk Manager",
        description="Evaluates trade proposals for risk exposure and portfolio impact.",
        skills=[
            AgentSkill(
                id="risk-eval",
                name="Risk Evaluation",
                description="Position sizing, drawdown, correlation risk",
                tags=["risk"],
            ),
        ],
    ),
}
