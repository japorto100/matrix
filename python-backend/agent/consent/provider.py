# Consent Provider — exec-12 Phase 2.2
# Protocol-based plugin system (deer-flow GuardrailProvider pattern).
# Providers decide whether a tool call needs user consent.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from agent.consent.config import (
    ConsentLevel,
    ConsentSeverity,
    ToolConsentConfig,
    get_consent_config,
)

# Sentinel for hard-blocked decisions (deny level — no interrupt, just block)
HARD_DENIED = "hard_denied"

logger = logging.getLogger(__name__)


# ── Request / Decision dataclasses ─────────────────────────────────────────

@dataclass
class ConsentRequest:
    tool_name: str
    tool_input: dict[str, Any]
    thread_id: str = ""
    agent_id: str = "default"
    agent_class: str = "advisory"


@dataclass
class ConsentDecision:
    needs_consent: bool
    level: ConsentLevel = ConsentLevel.NONE
    severity: ConsentSeverity = ConsentSeverity.MEDIUM
    reason: str = ""
    allow_session_cache: bool = True
    policy_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Protocol ───────────────────────────────────────────────────────────────

@runtime_checkable
class ConsentProvider(Protocol):
    """Plugin protocol for consent evaluation. Any class with evaluate() satisfies it."""
    name: str

    def evaluate(self, request: ConsentRequest) -> ConsentDecision: ...

    async def aevaluate(self, request: ConsentRequest) -> ConsentDecision: ...


# ── Built-in: AllowlistProvider ────────────────────────────────────────────

class AllowlistProvider:
    """Simple allowlist/denylist provider. Tools on denylist always need consent."""

    name = "allowlist"

    def __init__(
        self,
        *,
        consent_required: list[str] | None = None,
        auto_allow: list[str] | None = None,
        **_kwargs: Any,
    ) -> None:
        self._consent_required = set(consent_required) if consent_required else set()
        self._auto_allow = set(auto_allow) if auto_allow else None

    def evaluate(self, request: ConsentRequest) -> ConsentDecision:
        # Auto-allow takes precedence
        if self._auto_allow is not None and request.tool_name in self._auto_allow:
            return ConsentDecision(needs_consent=False, policy_id="allowlist:auto_allow")

        if request.tool_name in self._consent_required:
            return ConsentDecision(
                needs_consent=True,
                level=ConsentLevel.CONFIRM,
                severity=ConsentSeverity.MEDIUM,
                reason=f"Tool '{request.tool_name}' requires consent",
                policy_id="allowlist:consent_required",
            )

        return ConsentDecision(needs_consent=False, policy_id="allowlist:default")

    async def aevaluate(self, request: ConsentRequest) -> ConsentDecision:
        return self.evaluate(request)


# ── Built-in: YamlPolicyProvider ───────────────────────────────────────────

class YamlPolicyProvider:
    """Evaluates consent based on consent_policy.yaml config.
    This is the default provider — reads tool configs from YAML."""

    name = "yaml_policy"

    def __init__(self, **_kwargs: Any) -> None:
        pass

    def evaluate(self, request: ConsentRequest) -> ConsentDecision:
        config = get_consent_config()

        # 1. Check explicit tool config
        tool_cfg = config.tools.get(request.tool_name)
        if tool_cfg:
            return self._from_tool_config(request, tool_cfg)

        # 2. Check category (tool can declare a category via metadata)
        # For now: fall through to defaults
        # Future: tool registry could expose categories

        # 3. Use defaults
        if config.defaults.level == ConsentLevel.NONE:
            return ConsentDecision(needs_consent=False, policy_id="yaml:default")

        return ConsentDecision(
            needs_consent=True,
            level=config.defaults.level,
            severity=config.defaults.severity,
            reason="Default consent policy",
            policy_id="yaml:default",
        )

    async def aevaluate(self, request: ConsentRequest) -> ConsentDecision:
        return self.evaluate(request)

    def _from_tool_config(self, request: ConsentRequest, cfg: ToolConsentConfig) -> ConsentDecision:
        tool_name = request.tool_name

        # Role filter: if roles are specified, only apply to those roles
        if cfg.roles and request.agent_class not in cfg.roles:
            return ConsentDecision(needs_consent=False, policy_id=f"yaml:tool:{tool_name}:role_skip")

        if cfg.level == ConsentLevel.NONE:
            return ConsentDecision(needs_consent=False, policy_id=f"yaml:tool:{tool_name}")

        if cfg.level == ConsentLevel.DENY:
            return ConsentDecision(
                needs_consent=True,
                level=ConsentLevel.DENY,
                severity=cfg.severity,
                reason=cfg.reason or f"Tool '{tool_name}' is blocked by policy",
                allow_session_cache=False,
                policy_id=f"yaml:tool:{tool_name}:deny",
                metadata={HARD_DENIED: True},
            )

        return ConsentDecision(
            needs_consent=True,
            level=cfg.level,
            severity=cfg.severity,
            reason=cfg.reason or f"Tool '{tool_name}' requires consent",
            allow_session_cache=cfg.allow_session_cache,
            policy_id=f"yaml:tool:{tool_name}",
        )
