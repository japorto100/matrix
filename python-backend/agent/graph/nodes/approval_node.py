"""Consent Gate Node — Human-in-the-Loop via LangGraph interrupt.

exec-12 Phase 2.2: Plugin-based consent system replaces hardcoded approval.
Flow: check_consent() → cache hit? → provider evaluate → interrupt() if needed.
Levels: none (auto-allow), inform (log), confirm (interrupt), deny (hard block).
Supports: allow_once, allow_session, deny, deny_session.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import interrupt

from agent.graph.state import AgentGraphState

logger = logging.getLogger(__name__)


async def approval_node(state: AgentGraphState) -> dict[str, Any]:
    """Prueft tool_calls auf Consent-Bedarf via pluggable ConsentProvider."""
    from agent.audit.logger import AuditAction, audit_log
    from agent.consent import check_consent, record_consent_decision
    from agent.consent.config import ConsentLevel
    from agent.consent.provider import HARD_DENIED
    from agent.tracing import turn_span

    tool_calls = state.get("tool_calls", [])
    thread_id = state.get("thread_id", "")
    agent_class = state.get("agent_class", "advisory")
    user_role = state.get("user_role", "viewer")
    allow_interrupts = bool(state.get("approval_interrupts", True))
    if not tool_calls:
        return {}

    with turn_span("approval_gate", "", 0) as span:
        approved_calls = []
        denied_calls: list[dict[str, Any]] = []
        denied_messages: list[dict[str, Any]] = []
        denied_count = 0
        grace_warning_msg = ""
        for tc in tool_calls:
            tool_name = tc["tool_name"]
            tool_input = tc["tool_input"]

            # Single consent check — covers all levels (none/inform/confirm/deny)
            decision = await check_consent(
                tool_name=tool_name,
                tool_input=tool_input,
                thread_id=thread_id,
                agent_class=agent_class,
                user_role=user_role,
            )

            # CS-5: Capture grace warning for LLM injection
            if decision.metadata.get("grace_warning") and not grace_warning_msg:
                grace_warning_msg = decision.metadata["grace_warning_reason"]

            if not decision.needs_consent:
                await audit_log(
                    action=AuditAction.CONSENT_DECISION,
                    thread_id=thread_id,
                    tool_name=tool_name,
                    success=True,
                    metadata={
                        "decision": "auto_allow",
                        "policy_id": decision.policy_id,
                    },
                )
                approved_calls.append(tc)
                continue

            # Hard deny — no interrupt, just block
            if decision.level == ConsentLevel.DENY or decision.metadata.get(
                HARD_DENIED
            ):
                denied_call = {
                    **dict(tc),
                    "denied_reason": decision.reason,
                    "denied_policy_id": decision.policy_id,
                }
                denied_calls.append(denied_call)
                denied_messages.append(_denied_tool_message(denied_call))
                await audit_log(
                    action=AuditAction.CONSENT_DECISION,
                    thread_id=thread_id,
                    tool_name=tool_name,
                    success=False,
                    metadata={
                        "decision": "hard_deny",
                        "reason": decision.reason,
                        "policy_id": decision.policy_id,
                    },
                )
                denied_count += 1
                logger.info("Policy deny: %s — %s", tool_name, decision.reason)
                continue

            if decision.level == ConsentLevel.INFORM:
                await audit_log(
                    action=AuditAction.CONSENT_DECISION,
                    thread_id=thread_id,
                    tool_name=tool_name,
                    success=True,
                    metadata={
                        "decision": "inform_allow",
                        "reason": decision.reason,
                        "policy_id": decision.policy_id,
                    },
                )
                logger.info("Consent inform: %s — %s", tool_name, decision.reason)
                approved_calls.append(tc)
                continue

            if not allow_interrupts:
                denied_call = {
                    **dict(tc),
                    "denied_reason": (
                        "Tool requires interactive consent, but this runner cannot "
                        "pause and resume approval."
                    ),
                    "denied_policy_id": decision.policy_id,
                }
                denied_calls.append(denied_call)
                denied_messages.append(_denied_tool_message(denied_call))
                await audit_log(
                    action=AuditAction.CONSENT_DECISION,
                    thread_id=thread_id,
                    tool_name=tool_name,
                    success=False,
                    metadata={
                        "decision": "confirm_unavailable",
                        "reason": decision.reason,
                        "policy_id": decision.policy_id,
                    },
                )
                denied_count += 1
                logger.info("Consent unavailable: %s — %s", tool_name, decision.reason)
                continue

            # Level = CONFIRM → interrupt and wait for user
            user_decision = interrupt(
                {
                    "type": "consent_request",
                    "tool_call_id": tc["tool_call_id"],
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "severity": decision.severity.value,
                    "reason": decision.reason,
                    "allow_session_cache": decision.allow_session_cache,
                    "policy_id": decision.policy_id,
                }
            )

            # Record decision (handles caching + audit)
            await record_consent_decision(
                thread_id=thread_id,
                tool_name=tool_name,
                user_decision=user_decision,
                allow_session_cache=decision.allow_session_cache,
            )

            if user_decision in ("allow_once", "allow_session"):
                approved_calls.append(tc)
                logger.info("Consent granted: %s (%s)", tool_name, user_decision)
            else:
                denied_call = {
                    **dict(tc),
                    "denied_reason": "User denied consent",
                    "denied_policy_id": decision.policy_id,
                }
                denied_calls.append(denied_call)
                denied_messages.append(_denied_tool_message(denied_call))
                denied_count += 1
                logger.info("Consent denied: %s (%s)", tool_name, user_decision)

        # CS-5: Inject grace warning as system message so LLM knows to wrap up
        span.set_attribute("approval.total", len(tool_calls))
        span.set_attribute("approval.approved", len(approved_calls))
        span.set_attribute("approval.denied", denied_count)

        result: dict[str, Any] = {"tool_calls": approved_calls}
        if denied_calls:
            result["denied_tool_calls"] = denied_calls
            result["messages"] = denied_messages
        if grace_warning_msg:
            messages = list(result.get("messages", []))
            messages.append(
                {
                    "role": "system",
                    "content": f"[SYSTEM WARNING] {grace_warning_msg}. Finish your current task and provide a final response.",
                }
            )
            result["messages"] = messages
            logger.warning("Grace warning injected: %s", grace_warning_msg)

        return result


def _denied_tool_message(tool_call: dict[str, Any]) -> dict[str, Any]:
    """Build an OpenAI-compatible tool response for a denied tool call."""
    import json

    tool_call_id = str(tool_call.get("tool_call_id") or tool_call.get("id") or "")
    reason = str(tool_call.get("denied_reason") or "Tool call denied")
    policy_id = str(tool_call.get("denied_policy_id") or "")
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "tool_use_id": tool_call_id,
        "content": json.dumps(
            {
                "error": "tool_denied",
                "reason": reason,
                "policy_id": policy_id,
            }
        ),
    }
