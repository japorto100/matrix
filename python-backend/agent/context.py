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
    # exec-16: user-specific API key (decrypted, aus DB)
    api_key: str | None = None
    # Optional live snapshots — populated from Go Gateway before loop starts
    market_snapshot: dict | None = None
    portfolio_state: dict | None = None
    # AC108: reasoning effort level
    reasoning_effort: str | None = None
    # Agent capability class — used by CapabilityEnvelope checks (ASR2)
    agent_class: str = "advisory"
    # User role forwarded from Go Gateway (X-User-Role header)
    # Values: viewer, analyst, trader, admin (matches tradeview-fusion RBAC)
    user_role: str = "viewer"
    # Request-level metadata (forwarded from Go)
    request_id: str | None = None
    # ADR-001 G4: A/B experiment row id (UUID). Set by the dispatcher
    # when a turn is run under an active experiment so downstream nodes
    # (notably llm_node's smart-routing block) can mark their dimension
    # of the turn on the same row via fire-and-forget UPDATE. None when
    # the turn runs outside the experiment ledger (tests, ad-hoc calls).
    ab_row_id: str | None = None
    # A2A/subagent execution policy. Defaults keep normal agent turns unchanged.
    delegation_role: str = ""
    parent_thread_id: str = ""
    spawn_depth: int = 0
    max_spawn_depth: int = 0
    context_mode: str = ""
    memory_scope: str = "current_user"
    memory_write_policy: str = "default"
    allowed_tool_names: tuple[str, ...] = ()
    child_memory_write_allowed: bool = True

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
        """Raise CapabilityViolationError if tool_name is not in allowed_tools."""
        from agent.errors import CapabilityViolationError

        if self.allowed_tools and tool_name not in self.allowed_tools:
            raise CapabilityViolationError(tool_name, self.agent_class)


# Default envelope for the advisory agent class (no mutations, no order placement)
ADVISORY_ENVELOPE = CapabilityEnvelope(
    agent_class="advisory",
    allowed_tools=frozenset(
        {
            "get_chart_state",
            "tool_search",
            "get_portfolio_summary",
            "get_geomap_focus",
            "save_memory",
            "load_memory",
            "memory_search",
            "memory_add",
            "semantic_lookup",
            "retrieve_context",
            "report_validate",
            "report_build",
            "sandbox_execute",
            "sandbox_browser",
        }
    ),
    risk_level="read-only",
    needs_human_approval=False,
)

ENVELOPES: dict[str, CapabilityEnvelope] = {
    "advisory": ADVISORY_ENVELOPE,
}
