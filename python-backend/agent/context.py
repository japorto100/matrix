# AgentExecutionContext — Phase 22g / ABP.1
# Immutable execution context (Onyx-pattern: frozen dataclass).
# Created once per request; passed read-only through loop + tools.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class AgentExecutionContext:
    """Immutable per-request context passed to loop, tools, and validators."""

    user_id: str
    thread_id: str
    model: str
    system_prompt: str
    # Tool instances for this session
    tools: tuple  # tuple[TradingTool, ...] — tuple for hashability
    # Optional live snapshots — populated from Go Gateway before loop starts
    market_snapshot: dict | None = None
    portfolio_state: dict | None = None
    # AC108: reasoning effort level
    reasoning_effort: str | None = None
    # Agent capability class — used by CapabilityEnvelope checks (ASR2)
    agent_class: str = "advisory"
    # Request-level metadata (forwarded from Go)
    request_id: str | None = None

    def tool_definitions(self) -> list[dict]:
        """Return Anthropic tool_definition dicts for all registered tools."""
        return [t.definition() for t in self.tools]

    def find_tool(self, name: str):
        """Lookup a TradingTool by name. Returns None if not found."""
        for t in self.tools:
            if t.name == name:
                return t
        return None


@dataclass(frozen=True)
class CapabilityEnvelope:
    """ASR2: capability envelope — defines what an agent class is allowed to do."""

    agent_class: str
    allowed_tools: frozenset[str] = field(default_factory=frozenset)
    # read-only = no mutations; advisory = analysis only; executor = can queue orders
    risk_level: str = "read-only"
    needs_human_approval: bool = False

    def check(self, tool_name: str) -> None:
        """Raise CapabilityViolation if tool_name is not in allowed_tools."""
        from agent.errors import CapabilityViolation
        if self.allowed_tools and tool_name not in self.allowed_tools:
            raise CapabilityViolation(tool_name, self.agent_class)


# Default envelope for the advisory agent class (no mutations, no order placement)
ADVISORY_ENVELOPE = CapabilityEnvelope(
    agent_class="advisory",
    allowed_tools=frozenset({
        "get_chart_state",
        "get_portfolio_summary",
        "get_geomap_focus",
        "save_memory",
        "load_memory",
    }),
    risk_level="read-only",
    needs_human_approval=False,
)

ENVELOPES: dict[str, CapabilityEnvelope] = {
    "advisory": ADVISORY_ENVELOPE,
}
