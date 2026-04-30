"""A2A Delegation Node — delegiert Tasks an Remote-Agents (exec-10 Phase 4.3).

Wenn ein Agent lokal nicht verfuegbar ist oder explizit remote sein soll,
wird die Anfrage via A2A Protocol an einen externen Agent geschickt.

Lokal: Sub-Graph (schnell, kein Netzwerk)
Remote: A2A Client → HTTP → Remote Agent → Response
"""

from __future__ import annotations

import asyncio
import logging
import os
from hashlib import sha256
from typing import Any

from agent.a2a.client import A2AClient
from agent.graph.state import AgentGraphState
from agent.routing.delegation_policy import build_single_hop_delegation_policy
from agent.runtime_events import make_runtime_event

logger = logging.getLogger(__name__)

# Remote Agent URLs (konfigurierbar via ENV)
REMOTE_AGENTS: dict[str, str] = {}


def _max_spawn_depth() -> int:
    raw = os.environ.get("AGENT_A2A_MAX_SPAWN_DEPTH", "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _spawn_depth(state: AgentGraphState) -> int:
    try:
        return max(0, int(state.get("spawn_depth", 0)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _max_concurrent_children() -> int:
    raw = os.environ.get("AGENT_A2A_MAX_CONCURRENT_CHILDREN", "1").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def _delegation_timeout_seconds() -> float:
    raw = os.environ.get("AGENT_A2A_DELEGATION_TIMEOUT_SECONDS", "120").strip()
    try:
        return max(0.1, float(raw))
    except ValueError:
        return 120.0


def _requested_tools(state: AgentGraphState) -> list[str]:
    definitions = state.get("tool_definitions") or []
    tools: list[str] = []
    for item in definitions:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name and isinstance(item.get("function"), dict):
            name = item["function"].get("name")
        if name:
            tools.append(str(name))
    return tools


def _event(
    *,
    status: str,
    name: str,
    state: AgentGraphState,
    summary: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return make_runtime_event(
        kind="subagent",  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        name=name,
        summary=summary,
        thread_id=str(state.get("thread_id", "") or ""),
        turn=int(state.get("iteration", 0) or 0),
        metadata=metadata or {},
    )


def _result_digest(value: str | None) -> str:
    if not value:
        return ""
    return sha256(value.encode("utf-8")).hexdigest()


async def _audit_delegation_runtime_events(
    *,
    state: AgentGraphState,
    role: str,
    runtime_events: list[dict[str, Any]],
    policy: dict[str, Any],
    success: bool,
    child_task_id: str = "",
    error: str = "",
) -> None:
    try:
        from agent.audit.logger import AuditAction, audit_log

        await audit_log(
            action=AuditAction.ROUTE_DECISION,
            thread_id=str(state.get("thread_id", "") or ""),
            agent_id=str(state.get("agent_id", "default") or "default"),
            user_id=str(state.get("user_id", "local") or "local"),
            success=success,
            metadata={
                "contract": "subagent-delegation-runtime/v1",
                "role": role,
                "delegation_decision": policy.get("delegation_decision", ""),
                "delegate_kind": policy.get("delegate_kind", ""),
                "child_task_id": child_task_id,
                "spawn_depth": policy.get("spawn_depth", 0),
                "next_spawn_depth": policy.get("next_spawn_depth", 0),
                "max_spawn_depth": policy.get("max_spawn_depth", 0),
                "error": error,
                "runtime_events": runtime_events,
            },
        )
    except Exception:  # noqa: BLE001
        logger.debug("A2A delegation runtime audit failed", exc_info=True)


def _delegation_context(
    *,
    role: str,
    state: AgentGraphState,
    next_depth: int,
    max_depth: int,
    tool_policy: dict[str, Any],
) -> str:
    thread_id = str(state.get("thread_id", "") or "")
    allowed_tools = ",".join(tool_policy.get("allowed_tools") or [])
    return (
        "Delegated from Matrix orchestrator; "
        f"role:{role}; parent_thread_id:{thread_id}; "
        f"spawn_depth:{next_depth}; max_spawn_depth:{max_depth}; "
        "memory_scope:explicit_context_only; "
        "context_mode:isolated; "
        f"allowed_tools:{allowed_tools}; "
        "memory_write_policy:parent_only; "
        "approval_mode:non_interactive_auto_deny"
    )


def _load_remote_agents() -> dict[str, str]:
    """Laedt Remote-Agent URLs aus Environment."""
    global REMOTE_AGENTS
    if REMOTE_AGENTS:
        return REMOTE_AGENTS

    # Format: AGENT_REMOTE_{ROLE}=http://host:port
    for key, value in os.environ.items():
        if key.startswith("AGENT_REMOTE_"):
            role = key.removeprefix("AGENT_REMOTE_").lower()
            REMOTE_AGENTS[role] = value.strip()

    return REMOTE_AGENTS


async def a2a_delegate_node(state: AgentGraphState) -> dict[str, Any]:
    """Delegiert die aktuelle Anfrage an einen Remote-Agent via A2A.

    Wird nur aufgerufen wenn der Orchestrator einen Remote-Agent fuer
    die aktuelle Rolle konfiguriert hat.
    """
    role = state.get("current_role", "")
    remote_agents = _load_remote_agents()

    if role not in remote_agents:
        logger.debug("No remote agent for role '%s', skipping A2A delegation", role)
        return {}

    current_depth = _spawn_depth(state)
    max_depth = _max_spawn_depth()
    policy = build_single_hop_delegation_policy(
        runner=str(state.get("runner_variant", "langgraph") or "langgraph"),
        role=str(role),
        current_depth=current_depth,
        max_spawn_depth=max_depth,
        requested_tools=_requested_tools(state),
        max_concurrent_children=_max_concurrent_children(),
    )
    if current_depth >= max_depth:
        logger.info(
            "A2A delegation disabled by spawn depth: role=%s current=%d max=%d",
            role,
            current_depth,
            max_depth,
        )
        runtime_events = [
            _event(
                status="blocked",
                name="subagent.delegation.blocked",
                state=state,
                summary="A2A delegation blocked by spawn-depth policy",
                metadata=policy,
            )
        ]
        await _audit_delegation_runtime_events(
            state=state,
            role=str(role),
            runtime_events=runtime_events,
            policy=policy,
            success=False,
            error="spawn_depth_exceeded",
        )
        return {
            "runtime_events": runtime_events,
            "degradation_flags": ["a2a_delegation_spawn_depth_blocked"],
        }

    agent_url = remote_agents[role]
    messages = state.get("messages", [])

    # Letzte User-Message als Anfrage
    user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            user_msg = msg["content"]
            break

    if not user_msg:
        runtime_events = [
            _event(
                status="blocked",
                name="subagent.delegation.blocked",
                state=state,
                summary="A2A delegation blocked because no user message was available",
                metadata={**policy, "fallback_reason": "missing_user_message"},
            )
        ]
        await _audit_delegation_runtime_events(
            state=state,
            role=str(role),
            runtime_events=runtime_events,
            policy=policy,
            success=False,
            error="missing_user_message",
        )
        return {
            "runtime_events": runtime_events,
            "degradation_flags": ["a2a_delegation_missing_user_message"],
        }

    logger.info("A2A delegation: role=%s → %s", role, agent_url)

    client = A2AClient()
    runtime_events = [
        _event(
            status="accepted",
            name="subagent.delegation.accepted",
            state=state,
            summary="A2A child delegation accepted by policy",
            metadata=policy,
        ),
        _event(
            status="started",
            name="subagent.delegation.started",
            state=state,
            summary="A2A child request started",
            metadata={**policy, "agent_url": agent_url},
        ),
    ]
    try:
        next_depth = current_depth + 1
        task = await asyncio.wait_for(
            client.send_message(
                agent_url=agent_url,
                message=user_msg,
                context=_delegation_context(
                    role=role,
                    state=state,
                    next_depth=next_depth,
                    max_depth=max_depth,
                    tool_policy=policy["tool_policy"],
                ),
            ),
            timeout=_delegation_timeout_seconds(),
        )

        if task.state == "completed" and task.result:
            child_session_id = f"a2a-{task.task_id}"
            result_digest = _result_digest(task.result)
            handoff_metadata = {
                "child_session_id": child_session_id,
                "child_task_id": task.task_id,
                "child_memory_write_allowed": False,
                "parent_curated_memory_handoff": True,
                "retain_decision": "parent_review_required",
                "source_refs": [f"a2a:{task.task_id}", child_session_id],
                "confidence": "unverified_child_summary",
                "degradation_flags": [],
                "result_digest": result_digest,
            }
            runtime_events.extend(
                [
                    _event(
                        status="completed",
                        name="subagent.delegation.completed",
                        state=state,
                        summary="A2A child request completed",
                        metadata={
                            **policy,
                            "child_task_id": task.task_id,
                            "child_session_id": child_session_id,
                            "result_digest": result_digest,
                        },
                    ),
                    make_runtime_event(
                        kind="memory",
                        status="accepted",
                        name="subagent.parent_memory_handoff",
                        summary="Delegation outcome is available for parent-side memory curation",
                        thread_id=str(state.get("thread_id", "") or ""),
                        turn=int(state.get("iteration", 0) or 0),
                        metadata=handoff_metadata,
                    ),
                ]
            )
            await _audit_delegation_runtime_events(
                state=state,
                role=str(role),
                runtime_events=runtime_events,
                policy=policy,
                success=True,
                child_task_id=task.task_id,
            )
            return {
                "messages": [
                    {"role": "assistant", "content": f"[{role} via A2A]: {task.result}"}
                ],
                "final_response": task.result,
                "done": True,
                "runtime_events": runtime_events,
            }

        error = task.error or "Unknown A2A error"
        status = "stale" if task.state == "timeout" else "failed"
        logger.warning("A2A delegation failed: %s", error)
        runtime_events.append(
            _event(
                status=status,
                name=f"subagent.delegation.{task.state}",
                state=state,
                summary="A2A child request did not complete",
                metadata={**policy, "child_task_id": task.task_id, "error": error},
            )
        )
        await _audit_delegation_runtime_events(
            state=state,
            role=str(role),
            runtime_events=runtime_events,
            policy=policy,
            success=False,
            child_task_id=task.task_id,
            error=error,
        )
        return {
            "messages": [
                {"role": "assistant", "content": f"[{role} A2A error]: {error}"}
            ],
            "runtime_events": runtime_events,
            "degradation_flags": [f"a2a_delegation_{task.state}"],
        }
    except TimeoutError:
        error = "node_level_timeout"
        logger.warning("A2A delegation node timed out: role=%s", role)
        runtime_events.append(
            _event(
                status="stale",
                name="subagent.delegation.timeout",
                state=state,
                summary="A2A child request exceeded node-level timeout",
                metadata={**policy, "error": error},
            )
        )
        await _audit_delegation_runtime_events(
            state=state,
            role=str(role),
            runtime_events=runtime_events,
            policy=policy,
            success=False,
            error=error,
        )
        return {
            "messages": [
                {"role": "assistant", "content": f"[{role} A2A error]: timeout"}
            ],
            "runtime_events": runtime_events,
            "degradation_flags": ["a2a_delegation_timeout"],
        }
    finally:
        await client.close()
