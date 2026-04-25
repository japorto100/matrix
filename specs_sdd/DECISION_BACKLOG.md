---
title: SDD Decision Backlog
status: draft
owner: filip
created: 2026-04-26
updated: 2026-04-26
---

# SDD Decision Backlog

This file holds decision/defer items removed from active `tasks.md` checkboxes.
They are not forgotten; they are blocked by missing evidence, missing live
verification, dependency availability or product scope choice.

Rule: if a question here becomes accepted, update the owning feature's
`decisions.md`, `tasks.md`, `gates.md` and `closeout.md` in the same change.

## Feature 006 - Appservice, NATS, E2EE and Bridges

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D006-001 | Should NATS subject authorization be implemented before multi-agent rollout? | Default: defer broad rollout and keep subject routing non-security until A4 live path is verified. Why: auth policy without live Matrix -> Go -> NATS -> Python proof risks locking in the wrong subject model. | A4 unencrypted handoff passes and target-agent subject routing is live-observed. |
| D006-002 | Does `MATRIX_DELETE_KEYS_AFTER_HOURS` need implementation before production? | Default: defer. Current binary keep/delete behavior is simpler and testable. Why: timed deletion needs lifecycle storage, restart semantics and operator policy. | E2EE restart/key-backup live verify passes and production retention policy is chosen. |
| D006-003 | Should `native` agent E2EE move beyond interface-only status? | Default: defer and keep `gateway` mode. Why: native ciphertext forwarding requires vetted vodozemac-python or equivalent, per-agent key ownership and fresh crypto review. | vodozemac-python/Soatok notes are reviewed and a native-agent threat model is accepted. |

## Feature 007 - Agent Chat and Voice Runtime

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D007-001 | Is Agent Voice in current product scope or explicitly deferred? | Default: defer voice. Why: text/tool Agent Chat still needs live BFF -> Go -> Python proof; voice adds LiveKit, STT, TTS and latency gates. | Text/tool stack is live-verified and one LiveKit SFU path is confirmed for Matrix Calls or Agent Voice. |

## Feature 009 - Multi-Agent and A2A Orchestration

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D009-001 | Should LangGraph use async PostgreSQL checkpointing now? | Default: keep in-memory graph checkpointing for this branch. Why: `AsyncPostgresSaver.from_conn_string` needs runner-owned async lifecycle; forcing it into the sync graph factory was unsafe. | Runner lifecycle refactor is scoped and graph live smoke needs durable resume. |
| D009-002 | How should subagents be visible: invisible LangGraph nodes, Matrix identities or hybrid? | Default: invisible LangGraph nodes plus explicit Matrix identity only for user-facing agents. Why: every Matrix identity adds routing, auth, audit and UX overhead. | A2A live delegation and Matrix mention routing both pass. |

## Feature 010 - Control UI and Runtime Surfaces

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D010-001 | Is media ingestion owned by Files UI, Feature 012, or research backlog? | Default: Feature 012 owns semantic ingestion; Files UI owns upload/preview/reindex affordances. Why: UI-only routing would blur storage vs knowledge semantics. | File upload live verify identifies which media types need semantic ingestion. |
| D010-002 | Are Graphiti/Cognee backend integrations in Control UI scope? | Default: defer to Feature 012 unless UI-only visualization is needed. Why: graph backend choice affects memory/world architecture. | World/KG backend decision in Feature 012 is accepted. |
| D010-003 | Which feature owns skills semantics visible in Control UI? | Default: Feature 015 owns skills runtime; Control UI owns status/action surfaces. Why: toggles without runtime semantics create misleading state. | Skill DB/source-mode live verify passes. |
| D010-004 | Which feature owns sandbox semantics visible in Control UI? | Default: Feature 013 owns sandbox execution and consent policy; Control UI owns health/status affordances. Why: policy belongs at security boundary. | OpenSandbox and Skills-Guard HITL live verify passes. |
| D010-005 | Which feature owns observability backend gaps? | Default: Feature 014 owns traces/audit/evals; Control UI owns display and filtering. Why: data contracts should not be invented by tab implementation. | One trace, audit row and eval score are live-queryable. |
| D010-006 | Should Agent Chat be embedded as a Control UI sub-surface? | Default: no, keep Agent Chat as overlay/control surface plus `/api/agent/*`. Why: embedding creates navigation and ownership ambiguity. | User workflow requires side-by-side Control and Agent Chat. |
| D010-007 | Are Computer Use and Artifacts first-class Control UI scope? | Default: defer to Features 008 and 013. Why: this crosses generative UI, sandbox and artifact governance. | A2UI surface persistence and sandbox artifact path are live-verified. |
| D010-008 | Which surfaces own Personal KB and World Model editing? | Default: Feature 012 owns domain semantics; Control UI owns Inbox/Library/Document/Note surfaces. Why: schema and promotion gates are not UI-only. | Personal KB/world schemas are accepted. |
| D010-009 | What is the policy for mock fallbacks in Control UI? | Default: mocks may exist only with explicit owner-feature gap/empty state. Why: hidden mock data blocks reliable live verification. | Tab-by-tab live/mock inventory is completed. |

## Feature 011 - LLM Gateway, Models, Routing and Billing

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D011-001 | Does docker-compose LiteLLM remain the active local gateway path? | Default: keep it as optional local provider gateway, not mandatory for static tests. Why: provider keys and spend DB are operator/live concerns. | LiteLLM chat/tool/streaming smoke is run locally. |
| D011-002 | Is multi-key CredentialPool in scope now? | Default: defer. Why: single-user credential preflight already protects smart routing; pool semantics require rotation, budget and audit policy. | Provider failover or multi-account budget need is observed. |
| D011-003 | Should `preferred_runner`/dispatcher override be user-configurable? | Default: defer. Why: runner override touches scheduling, billing and observability semantics. | User-visible model/runner selection reaches backend/provider in live verify. |
| D011-004 | Should event-driven billing rollup be implemented? | Default: defer until real spans/usage rows exist. Why: rollup without live provider data is mostly speculative. | One real billable request writes span/usage/cost data. |
| D011-005 | Should smart-routing cost attribution be split per primary vs cheap model? | Default: defer. Why: routing first needs live disclosure and enough sample rows. | A/B routing rows exist for both cheap and strong paths. |
| D011-006 | Should `_compute_auto_effort` ship? | Default: defer. Why: effort auto-mode depends on provider-specific reasoning token behavior. | OpenAI/Anthropic/OpenRouter reasoning live checks pass. |
| D011-007 | Should Control UI expose an auto-mode capable filter? | Default: defer with `_compute_auto_effort`. Why: UI filter would imply behavior not yet live-proven. | Auto effort semantics are accepted. |
| D011-008 | When should L1 post-hoc mode labeling start? | Default: defer until enough audit events exist. Why: labels from tiny corpus are noise. | Minimum audit corpus threshold is defined and met. |
| D011-009 | When should L2 adaptive reward feedback start? | Default: defer until L1 proves useful. Why: feedback loop before reliable labels risks optimizing wrong behavior. | L1 report shows stable signal. |

## Feature 012 - Memory, Context, World Model and Personal KB

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D012-001 | Should a durable `verbatim_store` schema be added now? | Default: defer until retain/recall live path proves storage shape. Why: verbatim storage affects privacy and deletion semantics. | Postgres retain/recall live verify passes. |
| D012-002 | Should DB-level source/status fields be added to memory rows? | Default: design after first live corpus. Why: status taxonomy must match evidence and derived-memory behavior. | Shared corpus runner produces representative records. |
| D012-003 | Do we need Memory Operation Logging and diffs? | Default: defer until audit/query requirements are clear. Why: diff storage can become high-volume and privacy-sensitive. | A concrete debugging/audit workflow requires it. |
| D012-004 | Should MemoryAccessPolicy be per agent/consumer now? | Default: defer. Why: per-agent identity/routing is still open in Feature 009. | Per-user/per-agent settings are accepted. |
| D012-005 | What is the PII/deletion path across memory tiers? | Default: defer implementation, keep production hybrid fallback disabled. Why: deletion must cover verbatim, derived, world and KB tiers. | Storage schemas are accepted and PII policy is chosen. |
| D012-006 | Should public benchmark adapters be wired now? | Default: defer unless a benchmark is needed for a concrete gate. Why: adapters add maintenance without current model-selection decision. | Memory eval class taxonomy is implemented. |
| D012-007 | How should per-model context thresholds feed harness/meta-regression? | Default: defer to Feature 014 integration. Why: thresholds need live cost/cache measurements. | ContextTab and harness score rows are live. |

## Feature 013 - Sandbox, Security and HITL

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D013-001 | Is Tier-3 ML redaction research needed after regex benchmark? | Default: defer. Why: Tier-1/static redaction already exists; ML redaction adds model/runtime cost and false-positive risk. | Redaction benchmark shows regex baseline cannot meet target. |

## Feature 014 - Observability, Harness and Evals

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D014-001 | Should browser RUM be added? | Default: defer until BFF proxy/privacy design exists. Why: browser telemetry can leak user content and identifiers. | Privacy-preserving RUM contract is accepted. |
| D014-002 | Should per-tool `audit_required` be added? | Default: defer to Feature 013 policy. Why: audit policy belongs with HITL/security semantics. | Consent/audit gates for sandbox and skills are live. |
| D014-003 | Should Pareto dashboards ship in Control UI? | Default: defer. Why: dashboards need real eval/score rows and useful weights. | One live eval run fills persistent score data. |
| D014-004 | Should fitness weights be tunable now? | Default: defer. Why: weight tuning before evaluator validity is premature. | Scorer interfaces and real evaluator are implemented. |
| D014-005 | Should Feedback Descent pairwise mode be adopted? | Default: defer. Why: pairwise mode needs evaluator cache and real comparison corpus. | Async evaluator and cache exist with sample results. |

## Feature 015 - Scheduler, Skills, Formal Planning and Automation

| ID | Concrete Question | Default / Why Deferred | Resume When |
|---|---|---|---|
| D015-001 | What is the first Scheduler Phase-2a slice? | Default: pick exactly one slice, likely scheduler metrics or Control-UI inline edit. Why: running dep-update, email, Telegram, webhooks and condition tasks in parallel fragments scope. | Phase-1 live delivery passes. |
| D015-002 | Should Temporal be introduced? | Default: defer. Why: current scheduler does not yet require saga/replay/human-approval complexity. | A workflow requires durable long-running orchestration with replay semantics. |
| D015-003 | Should Hindsight outcome feedback be implemented? | Default: defer. Why: requires real skill-use outcomes and audit events. | Skill_found/refined/used audit path is live. |
| D015-004 | Should a skill compliance judge be implemented? | Default: defer. Why: judge quality requires a policy corpus and outcome feedback. | Skill promotion pipeline is designed. |
| D015-005 | Should skill promotion pipeline ship now? | Default: defer. Why: promotion without reliable usage/correctness signal can degrade skills. | Usage counters and trigger-quality CLI are run on production-like data. |
| D015-006 | Should `experiments/skill_eval` A/B variants be built? | Default: defer. Why: needs N-way bucketing and artifact hash semantics. | Harness/eval variant storage is accepted. |
| D015-007 | What is the first PDDL pilot workflow? | Default: defer; do not use PDDL for trivial CRUD or low-latency paths. Why: formal planning adds overhead and refusal/repair complexity. | A multi-step workflow with constraints and recoverable failures is selected. |
| D015-008 | Which PDDL solver stack should be used? | Default: defer with pilot. Why: solver choice depends on selected workflow and deployment constraints. | Pilot workflow is accepted. |
| D015-009 | When should DSPy D-2/D-3 schema/interface ship? | Default: defer until benchmark winner. Why: schema before benchmark risks locking into the wrong optimizer. | G(-1).1 and G(-1).2 results exist. |
| D015-010 | When should DSPy A/B variant ship? | Default: defer until N-way bucketing and artifact hash exist. Why: untracked prompt/program variants are not reproducible. | Variant artifact model is accepted. |
