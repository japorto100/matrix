---
title: Legacy Coverage Audit
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
---

# Legacy Coverage Audit

This audit confirms that the old spec landscape is represented in
`specs_sdd/`. It is not a content migration checklist; it is the coverage map.

## Audit Result

Checked on 2026-04-25:

| Source Set | Count | Coverage Result |
|---|---:|---|
| `specs/` markdown/text/csv files up to depth 3 | 92 | 100% referenced in `specs_sdd` |
| `specs/execution/` markdown/text/csv files up to depth 3 | 65 | 100% referenced in `specs_sdd` |
| `docs/superpowers/` files up to depth 4 | 17 | 100% referenced in `specs_sdd` |

Verification command used:

```bash
(find specs -maxdepth 3 -type f \( -name '*.md' -o -name '*.txt' -o -name '*.csv' \) -print; find docs/superpowers -maxdepth 4 -type f -print) | sort | while IFS= read -r f; do if ! rg -F -q "$f" specs_sdd; then printf '%s\n' "$f"; fi; done
```

Result: no output, meaning every inventoried legacy path is referenced at least
once in `specs_sdd`.

Important distinction: this proves **file-level coverage**, not final feature
granularity. A referenced file can still be too large for one feature and may be
split into subfeatures during content migration.

## Top-Level `specs/*.md`

Classification was completed during Feature 001. "Current" means the file still
contains accepted operating guidance. "Split" means the file remains useful, but
its contents are owned by multiple SDD features/backlog entries. "Historical"
means the file is provenance only and should not drive new implementation
without re-triage.

| Source | Destination | Classification | Notes |
|---|---|---|---|
| `specs/00-overview.md` | Feature 001 | current | Baseline project purpose and architecture context. |
| `specs/01-homeserver.md` | Feature 004 | current | Homeserver setup owner. |
| `specs/02-go-appservice.md` | Feature 006 | current | Go Matrix gateway owner. |
| `specs/03-python-agent-bridge.md` | Feature 006 | current | Python NATS bridge owner. |
| `specs/04-nextjs-chat.md` | Feature 005 | split | Chat UI history now lives in `frontend_merger`; protocol details remain active. |
| `specs/05-devstack.md` | Feature 002 | current | Devstack/bootstrap source material. |
| `specs/06-e2ee.md` | Feature 006 | current | E2EE gateway and hardening source. |
| `specs/07-mobile.md` | Feature 004 | current | Mobile/connectivity source. |
| `specs/08-tooling.md` | Feature 001 | current | Tooling invariants promoted to `constitution.md`. |
| `specs/09-privacy.md` | Feature 001 / Feature 013 | current | Privacy invariants promoted to `constitution.md`; security follow-ups live in Feature 013. |
| `specs/10-portierung.md` | Feature 001 | current | Porting direction and tradeview-fusion boundary guidance. |
| `specs/11-bore-tunnel.md` | Feature 004 | current | Tunnel/mobile connectivity source. |
| `specs/12-connectivity.md` | Feature 004 | current | Connectivity troubleshooting source. |
| `specs/13-e2ee-agent-architecture.md` | Feature 006 | current | Agent/E2EE architecture source. |
| `specs/14-agent-chat-ui-enhancements.md` | Feature 007 / backlog | split | Implemented parts in Feature 007; nice-to-haves in backlog. |
| `specs/15-document-preview-evaluation.md` | `research/backlog/` / Feature 010 | split | Viewer decisions are UI backlog unless tied to Files surface. |
| `specs/16-security.md` | Feature 013 | current | Sandbox/security/HITL owner. |
| `specs/17-schema-ownership.md` | `archive/schema-history/` | historical | Superseded schema ownership history. |
| `specs/18-python-backend-workspace-refactor.md` | Feature 001 / Feature 002 | current | Python workspace/cache invariants promoted to baseline/devstack. |
| `specs/FUTURE_IDEAS.md` | `research/backlog/future-ideas.md` plus owning features | split | Converted into categorized backlog with feature owners. |
| `specs/agent-output-pattern.md` | Feature 001 / Feature 006 / Feature 007 | current | Matrix/mobile output convention promoted to `constitution.md`. |

## `specs/agent-ui/*`

| Source | Destination |
|---|---|
| `specs/agent-ui/01-architektur.md` | Feature 007 |
| `specs/agent-ui/02-features.md` | Feature 007 |
| `specs/agent-ui/03-api-routes.md` | Feature 007 |
| `specs/agent-ui/04-frontend-tools.md` | Feature 007 |
| `specs/agent-ui/05-backend-abhängigkeiten.md` | Feature 007 |
| `specs/agent-ui/06-protocols-roadmap.md` | Feature 007 / Feature 008 split |

## `specs/execution/*`

| Source | Destination | Verdict |
|---|---|---|
| `README.md` | `journal/` plus `features/README.md` | historical index |
| `EXECUTION-ORDER.md` | `journal/` plus affected feature tasks | historical cluster board |
| `exec-05-nats-e2ee-pipeline.md` | Feature 006 | implemented, A4 E2E open |
| `exec-05b-messaging-bridges.md` | Feature 006 / backlog for non-Matrix ingestion | planned |
| `exec-05c-agent-isolation.md` | Feature 006 | planned/partial |
| `exec-06-agent-chat-integration.md` | Feature 007 | implemented, live verify open |
| `exec-09-protocols-generative-ui.md` | Feature 008 | mostly built, live roundtrip gap |
| `exec-10-multi-agent.md` | Feature 009 | implemented, A2A live open |
| `exec-11-memory-evolution.md` | Feature 012 | partly built |
| `exec-12-sandbox-security.md` | Feature 013 | phase 1/2 built, decision pending |
| `exec-13-ui-kg-extensions.md` | Feature 010 / Feature 012 | archived |
| `exec-14-DSPy.md` | Feature 015 | gated research |
| `exec-14-pddl-formal-planning.md` | Feature 015 | planned/gated |
| `exec-15-memory-control-ui.md` | Feature 010 | frontend built, backend mixed |
| `exec-16-llm-provider-gateway.md` | Feature 011 | in progress |
| `exec-17-observability-harness-traces.md` | Feature 014 | infra live, spec lag |
| `exec-20-mcp-manager.md` | Feature 008 | evaluation |
| `exec-a2fm-adaptive-routing.md` | Feature 011 | heuristic built, ML router research |
| `exec-blocking.md` | split across Features 004, 006, 007, 012, 014 | cross-cutting |
| `exec-context.md` | Feature 012 | active owner for context |
| `exec-ebm.md` | `research/backlog/` / Feature 014 if activated | research |
| `exec-eval.md` | Feature 014 | runbooks/eval |
| `exec-harness.md` | Feature 014 | partly built |
| `exec-hermes.md` | owning features by row | adoption index |
| `exec-linux-setup-users-2026-04-17.md` | Feature 002 | done |
| `exec-matrix-monitor.md` | Feature 004 | active monitor |
| `exec-media-ingestion.md` | `research/backlog/` | draft |
| `exec-memory.md` | Feature 012 | partly built |
| `exec-notifications.md` | `research/backlog/` | draft |
| `exec-openworldlib.md` | `research/backlog/` | evaluation |
| `exec-personal-kb.md` | Feature 012 | planning |
| `exec-postgres-tuning-2026-04-17.md` | Feature 002 | done |
| `exec-rust.md` | `research/backlog/` | ported/planned |
| `exec-scheduler.md` | Feature 015 | phase 1 done |
| `exec-scheduler2.md` | Feature 015 | phase 2 draft |
| `exec-secrets-bootstrap-2026-04-17.md` | Feature 002 | done |
| `exec-security.md` | Feature 013 | draft/umbrella |
| `exec-skills.md` | Feature 015 | partly built |
| `exec-transformersjs.md` | `research/backlog/` / Feature 007 if title-gen activated | draft |
| `exec-world-model.md` | Feature 012 | planning |
| `exec2-01-matrix-chat-core.md` | Feature 005 | active history |
| `exec2-02-protocol-infra.md` | Feature 005 / Feature 004 blockers | active history |
| `exec2-03-ui-rework-sota.md` | Feature 005 | active history |
| `exec2-03b-advanced-matrix-options.md` | Feature 005 / Feature 004 | planned/backlog |
| `exec2-03c-cinny.md` | Feature 005 | verified |
| `exec2-04-verify-gates.md` | Feature 005 plus Feature 009 A2A/Mentions | verify ledger |
| `superpower-impl-log.md` | `journal/` | chronological log |

## `specs/execution/claude-merge-frontend-chat-ui-2OqmH/*`

| Source | Destination |
|---|---|
| `README.md` | Feature 003 |
| `VERIFY-GATES.md` | Feature 003 plus affected feature gates |
| `exec-01-frontend-merger-scaffold.md` | Feature 003 |
| `exec-02-envfiles-devstack-compose.md` | Feature 002 / Feature 003 |
| `exec-03-linter-fixes.md` | Feature 003 plus touched code owners |
| `exec-04-playwright-verify.md` | Feature 003 |
| `exec-05-ui-viewers-polish.md` | Feature 003 / Feature 011 / research backlog split |

## `specs/execution/archive/*`

| Source | Destination | Verdict |
|---|---|---|
| `exec-02-missing-features.md` | Feature 005 | historical |
| `exec-03-review-fixes.md` | Feature 005 | historical |
| `exec-04-ui-rework.md` | Feature 005 | superseded |
| `exec-07-refactoring.md` | Feature 005 | historical done |
| `exec-08-agent-backend-voice.md` | Feature 007 | superseded/merged |
| `exec-18-unified-agent-schema-SUPERSEDED.md` | `archive/schema-history/` | superseded |
| `exec-19-devstack-consolidation.md` | Features 002, 003, 011, backlog | split/superseded |
| `exec-merge-chat-SUPERSEDED.md` | Feature 003 | superseded |
| `exec-transformers-js-SUPERSEDED.md` | `research/backlog/` | superseded duplicate |
| `opensandbox-gemini-usecases.txt` | Feature 013 | research/evidence |
| `pddl_phase22b_delta.md` | Feature 015 | superseded delta |

## `docs/superpowers/*`

| Source | Destination | Type |
|---|---|---|
| `findings/2026-04-22-open-tasks.md` | `journal/` plus feature tasks | journal/task backlog |
| `findings/2026-04-22-overnight-findings.md` | `journal/` or `research/backlog/` after split | journal/research |
| `findings/2026-04-23-a2fm-paper-research-phase2.md` | Feature 011 research | research |
| `findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md` | ADR-0002 / Feature 014 | ADR |
| `findings/2026-04-23-adr-003-exec-14-dspy-gating.md` | ADR-0003 / Feature 015 | ADR |
| `findings/2026-04-23-adr-004-sandbox-hitl-layer.md` | ADR-0004 / Feature 013 | ADR |
| `findings/2026-04-23-adr-smart-routing-rollout-gate.md` | ADR-0001 / Feature 011 | ADR |
| `findings/2026-04-23-harness-mode-analysis.csv` | Feature 014 evidence | evidence |
| `findings/2026-04-23-harness-mode-analysis.md` | Feature 014 research | research |
| `findings/2026-04-24-env-layout-decision.md` | Feature 002 research or ADR | research/ADR candidate |
| `findings/2026-04-24-memory-umbrella-boundaries.md` | Feature 012 research | research |
| `findings/2026-04-24-observability-tier-strategy.md` | Feature 014 research | research |
| `journal/2026-04-23.md` | `journal/` | journal |
| `journal/README.md` | `journal/README.md` | journal convention |
| `plans/2026-04-21-ag-stack-frontend-merger-plan.md` | Feature 003 history | superseded plan |
| `plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md` | Feature 003 / Feature 008 tasks | completed plan with open gaps |
| `specs/2026-04-21-ag-stack-mapping-design.md` | Feature 003 / Feature 008 plan | design |
