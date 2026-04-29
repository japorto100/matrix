from __future__ import annotations

import json

import pytest

from agent.consent.config import ConsentLevel, ConsentSeverity
from agent.consent.provider import ConsentDecision
from agent.graph.nodes.approval_node import approval_node


@pytest.mark.asyncio
async def test_approval_node_blocks_rate_limited_tool(monkeypatch):
    calls: list[str] = []

    async def _deny(*_args: object, **_kwargs: object) -> ConsentDecision:
        return ConsentDecision(
            needs_consent=True,
            level=ConsentLevel.DENY,
            severity=ConsentSeverity.HIGH,
            reason="Tool blocked",
            policy_id="rate_limit",
        )

    def _not_called(**kwargs) -> str:
        pytest.fail("interrupt must not be called for hard deny decisions")

    async def _audit_log(**kwargs) -> None:
        calls.append(str(kwargs["metadata"]["decision"]))

    async def _record_consent(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr("agent.consent.check_consent", _deny)
    monkeypatch.setattr("agent.graph.nodes.approval_node.interrupt", _not_called)
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr(
        "agent.consent.record_consent_decision",
        _record_consent,
    )

    result = await approval_node(
        {
            "thread_id": "t1",
            "agent_class": "advisory",
            "user_role": "analyst",
            "tool_calls": [
                {
                    "tool_call_id": "sandbox-1",
                    "tool_name": "sandbox_execute",
                    "tool_input": {"code": "print('x')"},
                }
            ],
        }
    )

    assert result["tool_calls"] == []
    assert "hard_deny" in calls
    assert result["denied_tool_calls"][0]["tool_call_id"] == "sandbox-1"
    denial_message = result["messages"][0]
    assert denial_message["role"] == "tool"
    assert denial_message["tool_call_id"] == "sandbox-1"
    denial = json.loads(denial_message["content"])
    assert denial["error"] == "tool_denied"
    assert denial["policy_id"] == "rate_limit"


@pytest.mark.asyncio
async def test_approval_node_confirm_requires_interrupt_and_caches_session_decision(monkeypatch):
    tool_calls = [
        {
            "tool_call_id": "sandbox-2",
            "tool_name": "sandbox_execute",
            "tool_input": {"code": "print('y')"},
        }
    ]
    captured: list[tuple[str, tuple[str, str]]] = []

    async def _confirm(*_args: object, **_kwargs: object) -> ConsentDecision:
        return ConsentDecision(
            needs_consent=True,
            level=ConsentLevel.CONFIRM,
            severity=ConsentSeverity.HIGH,
            reason="explicit consent required",
            allow_session_cache=True,
            policy_id="yaml:tool:sandbox_execute",
        )

    def _interrupt(payload: dict) -> str:
        captured.append(("interrupt", (payload["tool_name"], payload["tool_call_id"])))
        return "allow_session"

    async def _audit_log(**kwargs) -> None:
        captured.append(("audit", (kwargs["metadata"]["decision"], kwargs["success"])))

    async def _record_consent(
        thread_id: str, tool_name: str, user_decision: str, allow_session_cache: bool
    ) -> None:
        captured.append(
            (
                "record",
                (thread_id, tool_name, user_decision, str(allow_session_cache)),
            )
        )

    monkeypatch.setattr("agent.consent.check_consent", _confirm)
    monkeypatch.setattr("agent.graph.nodes.approval_node.interrupt", _interrupt)
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr(
        "agent.consent.record_consent_decision", _record_consent
    )

    result = await approval_node(
        {
            "thread_id": "t2",
            "agent_class": "advisory",
            "user_role": "analyst",
            "tool_calls": tool_calls,
        }
    )

    assert result["tool_calls"] == tool_calls
    assert ("interrupt", ("sandbox_execute", "sandbox-2")) in captured
    assert ("record", ("t2", "sandbox_execute", "allow_session", "True")) in captured


@pytest.mark.asyncio
async def test_approval_node_inform_level_is_auto_allowed_without_interrupt(monkeypatch):
    tool_calls = [
        {
            "tool_call_id": "inform-1",
            "tool_name": "set_chart_state",
            "tool_input": {},
        }
    ]
    captured: list[tuple[str, str]] = []

    async def _inform(*_args: object, **_kwargs: object) -> ConsentDecision:
        return ConsentDecision(
            needs_consent=True,
            level=ConsentLevel.INFORM,
            severity=ConsentSeverity.MEDIUM,
            reason="informational",
            policy_id="yaml:tool:set_chart_state",
        )

    def _interrupt(*_args: object, **_kwargs: object) -> str:
        pytest.fail("interrupt should not run for inform-level decisions")

    async def _audit_log(**kwargs) -> None:
        captured.append(("audit", kwargs["metadata"]["decision"]))

    async def _record_consent(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("record_consent should not run for inform-level decisions")

    monkeypatch.setattr("agent.consent.check_consent", _inform)
    monkeypatch.setattr("agent.graph.nodes.approval_node.interrupt", _interrupt)
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr(
        "agent.consent.record_consent_decision", _record_consent
    )

    result = await approval_node(
        {
            "thread_id": "t4",
            "agent_class": "advisory",
            "user_role": "analyst",
            "tool_calls": tool_calls,
        }
    )

    assert result["tool_calls"] == tool_calls
    assert ("audit", "inform_allow") in captured


@pytest.mark.asyncio
async def test_approval_node_confirm_without_interrupts_fails_closed(monkeypatch):
    tool_calls = [
        {
            "tool_call_id": "confirm-simple-1",
            "tool_name": "sandbox_execute",
            "tool_input": {"code": "print('simple')"},
        }
    ]
    captured: list[str] = []

    async def _confirm(*_args: object, **_kwargs: object) -> ConsentDecision:
        return ConsentDecision(
            needs_consent=True,
            level=ConsentLevel.CONFIRM,
            severity=ConsentSeverity.HIGH,
            reason="explicit consent required",
            allow_session_cache=True,
            policy_id="yaml:tool:sandbox_execute",
        )

    def _interrupt(*_args: object, **_kwargs: object) -> str:
        pytest.fail("interrupt should not run when approval_interrupts is false")

    async def _audit_log(**kwargs) -> None:
        captured.append(kwargs["metadata"]["decision"])

    async def _record_consent(*_args: object, **_kwargs: object) -> None:
        pytest.fail("record_consent should not run without a user decision")

    monkeypatch.setattr("agent.consent.check_consent", _confirm)
    monkeypatch.setattr("agent.graph.nodes.approval_node.interrupt", _interrupt)
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("agent.consent.record_consent_decision", _record_consent)

    result = await approval_node(
        {
            "thread_id": "t-simple",
            "agent_class": "advisory",
            "user_role": "analyst",
            "approval_interrupts": False,
            "tool_calls": tool_calls,
        }
    )

    assert result["tool_calls"] == []
    assert result["denied_tool_calls"][0]["tool_call_id"] == "confirm-simple-1"
    denial = json.loads(result["messages"][0]["content"])
    assert denial["error"] == "tool_denied"
    assert denial["policy_id"] == "yaml:tool:sandbox_execute"
    assert "pause and resume" in denial["reason"]
    assert captured == ["confirm_unavailable"]


@pytest.mark.asyncio
async def test_approval_node_injects_grace_warning_message(monkeypatch):
    async def _auto_allow(*_args: object, **_kwargs: object) -> ConsentDecision:
        return ConsentDecision(
            needs_consent=False,
            level=ConsentLevel.NONE,
            severity=ConsentSeverity.LOW,
            policy_id="yaml:default",
            metadata={
                "grace_warning": True,
                "grace_warning_reason": "Warning: 1 iteration remaining before hard stop",
            },
        )

    async def _audit_log(**kwargs) -> None:
        return None

    monkeypatch.setattr("agent.consent.check_consent", _auto_allow)
    def _interrupt(**_kwargs) -> str:
        pytest.fail("interrupt should not be called for auto-allow decisions")

    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("agent.graph.nodes.approval_node.interrupt", _interrupt)

    result = await approval_node(
        {
            "thread_id": "t3",
            "agent_class": "advisory",
            "user_role": "analyst",
            "tool_calls": [
                {
                    "tool_call_id": "summ-3",
                    "tool_name": "get_portfolio_summary",
                    "tool_input": {},
                }
            ],
        }
    )

    assert result["tool_calls"] == [
        {
            "tool_call_id": "summ-3",
            "tool_name": "get_portfolio_summary",
            "tool_input": {},
        }
    ]
    assert len(result["messages"]) == 1
    assert (
        "[SYSTEM WARNING] Warning: 1 iteration remaining before hard stop. "
        "Finish your current task and provide a final response."
    in result["messages"][0]["content"]
    )


@pytest.mark.asyncio
async def test_approval_node_session_deny_cache_auto_blocks_without_interrupt(monkeypatch):
    captured: list[str] = []

    async def _deny(*_args: object, **_kwargs: object) -> ConsentDecision:
        return ConsentDecision(
            needs_consent=True,
            level=ConsentLevel.DENY,
            severity=ConsentSeverity.HIGH,
            reason="Previously denied in this session",
            policy_id="cache:session_deny",
            metadata={"cached": True, "session_denied": True},
        )

    def _interrupt(*_args: object, **_kwargs: object) -> str:
        pytest.fail("interrupt should not be called for cached-deny decisions")

    async def _audit_log(**kwargs) -> None:
        captured.append(kwargs["metadata"]["decision"])

    async def _record_consent(*_args: object, **_kwargs: object) -> None:
        pytest.fail("record_consent should not run for cached-deny decisions")

    monkeypatch.setattr("agent.consent.check_consent", _deny)
    monkeypatch.setattr("agent.graph.nodes.approval_node.interrupt", _interrupt)
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr(
        "agent.consent.record_consent_decision",
        _record_consent,
    )

    result = await approval_node(
        {
            "thread_id": "t5",
            "agent_class": "advisory",
            "user_role": "analyst",
            "tool_calls": [
                {
                    "tool_call_id": "cache-deny-1",
                    "tool_name": "sandbox_execute",
                    "tool_input": {"code": "print('z')"},
                }
            ],
        }
    )

    assert result["tool_calls"] == []
    assert "hard_deny" in captured
