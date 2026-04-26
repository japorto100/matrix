---
title: Open Work Triage
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-26
---

# Open Work Triage

This file is the working queue after the static SDD pass. It does not replace
feature `tasks.md`; it classifies the remaining unchecked work so the next
implementation sessions do not confuse live verification, product decisions,
external blockers and local implementation.

## Snapshot

Unchecked SDD items after task implementation pass: 145.

Counting rule: only active implementation tasks in `tasks.md` and true
acceptance gates in `gates.md` use unchecked boxes. `spec.md`,
`live-verify.md`, templates and procedure details use plain bullets so they do
not inflate the work queue.
Decision/defer questions live in `DECISION_BACKLOG.md`.

| Feature | Open Items | Dominant Open Work | Triage |
|---|---:|---|---|
| 001 Platform Baseline | 0 | none | closed_static |
| 002 Devstack Bootstrap/Ops | 1 | Alembic/Postgres/operator bootstrap | live_verify |
| 003 Frontend Shell | 3 | browser/full-stack route smoke | live_verify |
| 004 Homeserver/Connectivity | 7 | Tuwunel startup, appservice registration, mobile/tunnel, URL-preview config | live_verify + config_decision |
| 005 Matrix Chat Core | 0 | procedure details only; feature-level live gate lives in Feature 005 docs | live_verify |
| 006 Appservice/NATS/E2EE/Bridges | 18 | A4 E2E, E2EE, subject-routing live verify; Python routed-subject and NATS scoped-subscription static path done | live_verify |
| 007 Agent Chat/Voice | 22 | BFF/Gateway/Python roundtrip, live approvals/context/title, voice; static approval/context/sanitizer coverage done | live_verify |
| 008 A2UI/MCP | 9 | visible A2UI roundtrip, surface persistence, MCP/WebMCP; #93/#94/#95 decisions done | live_verify |
| 009 Multi-Agent/A2A | 25 | A2A live, skills/research live/deferred splits; graph/role/username/model/settings static cleanup done | live_verify |
| 010 Control UI | 10 | tab-by-tab live/mock inventory, files/storage, memory/KG, system/audit/MCP/A2A | live_verify + owner_routing |
| 011 LLM Gateway/Billing | 18 | LiteLLM/provider live, model picker propagation, billing spans; routing/model-persistence follow-ups closed static | provider_live |
| 012 Memory/Context/World/KB | 10 | Postgres memory live and context/compaction live gates; eval/world/KB active tasks closed static | live_verify |
| 013 Sandbox/Security/HITL | 22 | OpenSandbox live, Skills-Guard live decision/audit, prod URL-preview config, audit integrity | live_verify |
| 014 Observability/Harness/Evals | 0 | active implementation tasks closed; live trace/audit/eval gates remain in feature gates/live verify | live_verify |
| 015 Scheduler/Skills/Planning | 0 | active design task closed; phase decisions moved to backlog | live_verify |
| 016 Meta-Harness Agent Optimization | 0 | active T-tasks are tracked in Feature 016; runner/CLI/MCP first slices implemented | planned_implementation |

## Triage Buckets

### A. Implement Now, No Full Live Stack Required

These can be worked in the current branch with local tests and GitNexus impact
checks before code edits.

1. Done static: Feature 006 Python subscribes to global/routed subjects in
   default mode and only allowed agent subjects in scoped mode; live enabled
   routing remains.
2. Done docs: Feature 006 `native` E2EE capability remains interface-only until
   real ciphertext forwarding exists.
3. Done static: Feature 007 approval controls, context/degradation rail and
   markdown sanitizer have component tests; full approve/reject stack remains live.
4. Done static/docs: Feature 007 compression/context status is explicit at UI
   level; title display/dispatch remains live/open.
5. Done decision: Feature 008 keeps local widgets plus fallback; native custom
   catalog extension is deferred until cross-runtime reuse needs it.
6. Done decision: Feature 008 MCP external enablement requires auth/tool
   filtering first.
7. Done static: Feature 009 graph compile, orchestrator compile, six roles,
   role contracts and runtime tool allowlists are tested.
8. Done static: Feature 009 Matrix agent-name sanitization exists in Go
   `AgentSender`/mention parsing and Python bridge reply identity construction.
9. Done decision: Feature 009 default Matrix DM agent is the Python bridge
   `AGENT_USER_ID` fallback.
10. Done static: Feature 009 per-user default model lookup is DB-mocked and
    empty-user guarded.
11. Done static: Feature 009 per-user agent settings resolver covers prompt,
    memory scope, enabled/disabled skills and tool allowlist.
12. Done static: Feature 011 F-G4 race fixed by upsert semantics, F-G1 keyword
   quality narrowed, F-4g4 eval-id first-write-wins documented.
13. Done static: Feature 011 persisted default-model and selected-model
    endpoints are covered by DB-mocked tests.
14. Moved decision: Feature 011 multi-key CredentialPool scope is tracked as
    D011-002 in `DECISION_BACKLOG.md`.
15. Done decision: Feature 012 first World Model slice and Personal KB
    namespace/store are selected.
16. Done static: Feature 012 memory eval classes/metrics, world contracts and
    Personal KB capture/import/annotation contracts are defined.
17. Done config/static: Feature 013 active Tuwunel dev config explicitly
    disables URL-preview allowlists.
18. Done static: Feature 013 Skills-Guard BFF/FastAPI verdict shape is parsed
    by frontend tests.
19. Done static/evidence: Feature 014 harness CSV/report are linked with checksum and
    eval-id semantics synchronized with Feature 011.
20. Done static: Feature 014 async evaluator, cache, scorer interface,
    proposer/evaluator loop and exec-eval workpack migration are covered.
21. Done static: Feature 015 skill loader source modes and disabled-skill
    filtering are tested.
22. Done design: Feature 015 PDDL refusal/repair loop is defined before any
    execution integration.

### B. Local Full-Stack Live Verify

These require starting local services. They should be run as a batch once the
branch has no obvious `implement_now` gaps left.

1. Feature 002: Alembic against local Postgres and bootstrap smoke.
2. Feature 003: Playwright route smoke for `/matrix`, `/control`, `/files`,
   `/memory`.
3. Feature 004: Tuwunel startup, appservice registration and `.well-known`.
4. Feature 005: Matrix login, room list, timeline, send/edit/react/redact,
   uploads and E2EE state.
5. Feature 006: A4 Matrix -> Go -> NATS -> Python -> NATS -> Go -> Matrix.
6. Feature 010: Control UI tab-by-tab live/mock/broken inventory.
7. Feature 012: memory/context live endpoints and Postgres retain/recall.
8. Feature 014: one OpenObserve trace, one audit row and one persisted eval
   score.
9. Feature 015: scheduler cron tick, Python subscriber, Matrix delivery and
   `task_executions` completion row.
10. Feature 016: Python-only Meta-Harness stack smoke after PostgreSQL,
    LiteLLM and Python Agent are available.

### C. Agent Runtime Live Verify

These need the Agent Chat stack and usually a configured model provider.

1. Feature 007: BFF -> Go Gateway -> Python Agent text roundtrip.
2. Feature 007: tool rendering and approve/reject roundtrip.
3. Feature 007: title/compression/context provenance visible behavior.
4. Feature 008: live LLM emits visible `data-a2ui-*` surface.
5. Feature 009: live A2A delegation from Agent A to Agent B.
6. Feature 011: selected model reaches backend/provider and routing metadata is
   visible to the user.
7. Feature 015: skill retrieval/refinement is visible in a real agent turn.
8. Feature 016: proposer iteration consumes artifact history from real
   simulated-user runs.

### D. External/Provider-Gated Live Verify

These should not block local implementation unless the dependency is available.

1. Feature 004/005/006: mobile Element X, tunnel, E2EE cross-signing/key backup
   and federation-related checks.
2. Feature 007: LiveKit/STT/TTS voice.
3. Feature 008: Browser WebMCP `navigator.modelContext` roundtrip where the
   browser/runtime supports it.
4. Feature 011: Anthropic/OpenRouter/OpenAI reasoning-token live checks and
   LiteLLM provider spend logs.
5. Feature 013: OpenSandbox browser artifacts if the profile is not installed.

### E. Product/Architecture Decisions

Open decision/defer questions now live in `DECISION_BACKLOG.md`. This triage
file only keeps execution order and live-verify grouping, so product questions
do not inflate the implementation queue.

## Execution Order

### Wave 1: Local Implementation Cleanup

Order:

1. Feature 006 subject-routing/native-E2EE cleanup. Done static.
2. Feature 007 approval/context/sanitizer static cleanup. Done static.
3. Feature 009 static graph/role/routing/research-status cleanup. Done static.
4. Feature 011 routing follow-up decisions and tests. Done static.
5. Feature 013 active URL-preview config and Skills-Guard BFF static coverage.
   Done static.
6. Feature 015 skill loader/source-mode static coverage. Done static.
7. Feature 008 A2UI catalog/MCP auth decision docs. Done.
8. Feature 012 World/KB first-slice decision docs. Done.
9. Feature 014 evidence linkage and eval-id closeout. Done.

### Wave 2: Local Full-Stack Verify Batch

Start services once, then run Features 002-006, 010, 012, 014 and 015 live
checks in one session. Record evidence into each feature's `live-verify.md` and
`closeout.md`.

### Wave 3: Agent Runtime Verify Batch

Run Agent Chat with a configured provider. Verify Features 007, 008, 009, 011
and skill usage from 015.

### Wave 4: External Capability Verify

Run mobile/tunnel/E2EE/voice/WebMCP/provider-specific checks only when the
external dependency is intentionally available.

## Closure Discipline

- Do not mark a feature closed from static tests alone unless live verify is
  explicitly not applicable.
- Do not convert product decisions into implementation by accident.
- Do not let optional research tracks block local runtime closure.
- Every reopened or deferred item must have an owning feature and a next gate.
