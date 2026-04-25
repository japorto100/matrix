---
title: Multi-Agent A2A Orchestration Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 009
---

# Sources

## Normative Local Sources

| Source | Role in SDD |
|---|---|
| `specs/execution/exec-10-multi-agent.md` | Primary implementation history, paper insights and verify gates. |
| `specs/execution/exec2-04-verify-gates.md` | Later manual/live gate context for Matrix and routing integration. |
| `docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md` | Control UI / A2A / Agents surface context. |
| `specs/execution/exec-hermes.md` | Hermes stance on A2A/ACP, NATS-native delegation and multi-agent production patterns. |
| `specs/execution/exec-05c-agent-isolation.md` | `target_agent`, dynamic reply routing and isolation dependency. |

## Papers / Reference Repos

| Source | Use |
|---|---|
| `_ref/TradingAgents` | Trading-role orchestration inspiration. |
| `_ref/deer-flow` | Middleware/guardrail/skills patterns. |
| `_ref/MetaClaw` and MetaClaw arXiv 2603.17187 | SkillEvolver, 3-tier skills, per-user skill learning, PRM/LoRA/OMLS infrastructure. |
| `_ref/A2A` / Google A2A | AgentCard and message-passing baseline; used pragmatically, not as memory sharing. |
| Trace2Skill arXiv 2603.25158v2 | Batch skill consolidation research and consolidation graph inspiration. |
| Natural-Language Agent Harnesses arXiv 2603.25723v1 | Completion gates and file-backed state; broader NL-harness idea remains research. |
| Hermes-Agent / Hermes-4 | NATS-native A2A preference, enterprise translation of CLI-agent patterns. |

## Adopted Into Matrix

- LangGraph is the base stateful graph runtime.
- Trading roles are explicit nodes/contracts, not ad-hoc prompts.
- Skills are three-tier: global, team and personal.
- A2A is message passing and delegation, not memory sharing.
- Working memory/supermemory handle shared context; A2A does not need a separate
  memory protocol.
- PRM/RL exists as disabled infrastructure until eval/harness gates justify it.
