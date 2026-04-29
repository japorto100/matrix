---
title: Multi-Agent and A2A Orchestration Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 009
---

# Closeout

## Built

- LangGraph/orchestrator code for trading roles exists.
- Base LangGraph and orchestrator graphs compile under the current LangGraph
  dependency.
- `tool_node` enforces `TRADING_ROLE_TOOLS` for known trading roles.
- A2A AgentCards exist for the six trading cards and serialize to JSON.
- A2A HTTP client exists and now parses AI-SDK `text-delta.delta` packets.
- Dispatcher/router tests cover current routing and smart-routing behavior.
- Dynamic reply identity is covered through the Feature 006 NATS bridge test.
- Agent-name sanitization exists in Go and Python before Matrix user IDs or
  routed NATS subjects are constructed.
- Default Matrix DM agent convention is recorded in `decisions.md`.
- Per-user default model lookup is static-tested.

## Not Built

- Proven live A2A delegation from one running agent to another.
- Per-user agent settings for prompt, memory scope, skills and tool allowlist.
- Strong agent isolation without Feature 006 NATS authorization.
- Persistent PostgreSQL LangGraph checkpointing in the async runner lifecycle.

## Deviations From Plan

- A2A remains HTTP+JSON/SSE, not a full gRPC/proto implementation.
- The sync graph factory no longer instantiates `AsyncPostgresSaver` from
  `HINDSIGHT_DB_URL`; current LangGraph exposes it as an async context manager,
  so production persistence needs a runner-owned lifecycle.
- Paper-derived learning features are mixed: SkillEvolver exists, while
  PRM/LoRA/OMLS and Trace2Skill/NLAH stay disabled/research unless promoted.

## Verify Result

- PASS static: `uv run pytest tests/agent/test_roles.py tests/agent/graph/test_agent_graph.py tests/agent/graph/test_orchestrator.py tests/agent/graph/nodes/test_tool_node.py -q`.
- PASS static: `uv run ruff check agent/graph/agent_graph.py agent/graph/nodes/tool_node.py tests/agent/test_roles.py tests/agent/graph/test_agent_graph.py tests/agent/graph/test_orchestrator.py tests/agent/graph/nodes/test_tool_node.py`.
- PASS static: `go test -tags goolm ./internal/intent ./internal/handler ./internal/natsbridge`.
- PASS static: `uv run pytest tests/bridge/test_nats_handler.py -q`.
- PASS static: `uv run pytest tests/agent/security/test_user_model_lookup.py tests/agent/security/test_smart_routing_cache.py tests/agent/security/test_credential_preflight.py -q`.

## Live Verify Result

Pending A2A live smoke.

## Follow-Ups

- Run live local A2A smoke through `a2a_node` with a real target agent.
- Wire Control Agents/A2A tabs to backend state or an actionable empty state.
