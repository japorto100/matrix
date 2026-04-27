---
title: ADR Index
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-26
---

# ADR Index

ADRs capture binding decisions that affect future specs. Research notes and
session findings do not become ADRs automatically.

## Candidate ADRs From Legacy Sources

| ADR | Source | Topic | Target Feature |
|---|---|---|---|
| 0001 | `docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md` | Smart routing rollout gate | 011 |
| 0002 | `docs/superpowers/findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md` | Tracing + audit parallel stores | 014 |
| 0003 | `docs/superpowers/findings/2026-04-23-adr-003-exec-14-dspy-gating.md` | DSPy gated proceed | 015 |
| 0004 | `docs/superpowers/findings/2026-04-23-adr-004-sandbox-hitl-layer.md` | Sandbox HITL layer | 013 |
| 0005 | `specs_sdd/adr/0005-agent-learning-stack-boundaries.md` | Agent learning stack boundaries | 012, 015, 016, 017 |
| 0006 | `specs_sdd/adr/0006-mempalace-postgres-pgvector.md` | MemPalace Postgres/pgvector runtime | 012, 011 |
| 0007 | `specs_sdd/adr/0007-alembic-current-schema-governance.md` | Alembic current-schema registry and drift gates | 018, 012, 017, 019 |

## ADR Rule

When an ADR is accepted, all affected feature specs must be updated in the same
change. ADRs explain why; feature specs define what is now true.
