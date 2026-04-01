# Consent System — exec-12 Phase 2.2
# Orchestrates: YAML Policy Config → ConsentProvider → SessionCache → Decision.
#
# Usage:
#   from agent.consent import check_consent, record_consent_decision
#   decision = await check_consent(tool_name, tool_input, thread_id)
#   if decision.needs_consent:
#       # interrupt() and wait for user
#       record_consent_decision(thread_id, tool_name, user_decision)

from __future__ import annotations

import logging
from typing import Any

from agent.audit.logger import AuditAction, audit_log
from agent.consent.cache import get_consent_cache
from agent.consent.config import ConsentLevel, get_consent_config, resolve_provider_class
from agent.consent.provider import ConsentDecision, ConsentProvider, ConsentRequest
from agent.consent.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

__all__ = [
    "check_consent",
    "record_consent_decision",
    "ConsentDecision",
    "ConsentRequest",
    "ConsentLevel",
]

# ── Provider singleton ─────────────────────────────────────────────────────

_provider: ConsentProvider | None = None


def _get_provider() -> ConsentProvider:
    """Get or create the consent provider from config."""
    global _provider
    if _provider is None:
        config = get_consent_config()
        try:
            provider_cls = resolve_provider_class(config.provider.use)
            _provider = provider_cls(**config.provider.config)
            logger.info("Consent provider: %s (%s)", _provider.name, config.provider.use)
        except Exception as e:
            logger.warning("Failed to load consent provider '%s': %s — using YamlPolicyProvider", config.provider.use, e)
            from agent.consent.provider import YamlPolicyProvider
            _provider = YamlPolicyProvider()
    return _provider


# ── Main API ───────────────────────────────────────────────────────────────

async def check_consent(
    tool_name: str,
    tool_input: dict[str, Any],
    thread_id: str = "",
    agent_id: str = "default",
    agent_class: str = "advisory",
    user_role: str = "viewer",
) -> ConsentDecision:
    """Check if a tool call needs user consent.

    Flow:
    1. Check rate limits → if exceeded, deny immediately
    2. Check session cache → if cached allow/deny, return immediately
    3. Ask provider → evaluate policy
    4. Return decision (caller handles interrupt if needed)
    """
    cache = get_consent_cache()
    config = get_consent_config()
    limiter = get_rate_limiter()

    # 1. Check rate limits
    rate_result = limiter.check(thread_id, tool_name)
    if not rate_result.allowed:
        await audit_log(
            action=AuditAction.RATE_LIMIT_HIT,
            thread_id=thread_id,
            agent_id=agent_id,
            tool_name=tool_name,
            metadata={"reason": rate_result.reason},
        )
        return ConsentDecision(
            needs_consent=True,
            level=ConsentLevel.DENY,
            reason=rate_result.reason,
            policy_id="rate_limit",
            metadata={"rate_limited": True},
        )

    # RL-4: Propagate grace warning through metadata
    grace_warning_reason = ""
    if rate_result.is_grace_warning:
        grace_warning_reason = rate_result.reason

    # 2. Check session cache
    cached = cache.get(thread_id, tool_name)
    if cached == "allow":
        return ConsentDecision(
            needs_consent=False,
            policy_id="cache:session_allow",
            metadata={"cached": True},
        )
    if cached == "deny":
        return ConsentDecision(
            needs_consent=True,
            level=ConsentLevel.CONFIRM,
            reason="Previously denied in this session",
            policy_id="cache:session_deny",
            metadata={"cached": True, "session_denied": True},
        )

    # 2. Ask provider
    provider = _get_provider()
    request = ConsentRequest(
        tool_name=tool_name,
        tool_input=tool_input,
        thread_id=thread_id,
        agent_id=agent_id,
        agent_class=agent_class,
        user_role=user_role,
    )

    try:
        decision = await provider.aevaluate(request)
    except Exception as e:
        logger.warning("Consent provider error: %s", e)
        if config.fail_closed:
            decision = ConsentDecision(
                needs_consent=True,
                level=ConsentLevel.CONFIRM,
                severity=config.defaults.severity,
                reason=f"Consent provider error (fail-closed): {e}",
                policy_id="error:fail_closed",
            )
        else:
            decision = ConsentDecision(needs_consent=False, policy_id="error:fail_open")

    # RL-4/CS-5: Attach grace warning to decision metadata
    if grace_warning_reason:
        decision.metadata["grace_warning"] = True
        decision.metadata["grace_warning_reason"] = grace_warning_reason

    # Audit log the consent check
    if decision.needs_consent:
        await audit_log(
            action=AuditAction.CONSENT_REQUEST,
            thread_id=thread_id,
            agent_id=agent_id,
            tool_name=tool_name,
            input_data=tool_input,
            metadata={
                "level": decision.level.value,
                "severity": decision.severity.value,
                "reason": decision.reason,
                "policy_id": decision.policy_id,
            },
        )

    return decision


async def record_consent_decision(
    thread_id: str,
    tool_name: str,
    user_decision: str,
    allow_session_cache: bool = True,
) -> None:
    """Record user's consent decision. Called after interrupt() returns.

    user_decision: "allow_once" | "allow_session" | "deny" | "deny_session"
    """
    cache = get_consent_cache()

    if user_decision == "allow_session" and allow_session_cache:
        cache.grant(thread_id, tool_name)
    elif user_decision == "deny_session":
        cache.deny(thread_id, tool_name)
    # allow_once and deny: no caching

    await audit_log(
        action=AuditAction.CONSENT_DECISION,
        thread_id=thread_id,
        tool_name=tool_name,
        success=user_decision in ("allow_once", "allow_session"),
        metadata={"decision": user_decision, "cached": user_decision.endswith("_session")},
    )
