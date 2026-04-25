---
title: Control UI Decisions
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 010
migrated_from:
  - specs/execution/exec-15-memory-control-ui.md
---

# Decisions

These decisions are the semantic import of `exec-15` decisions D1-D25. They are
kept here unless promoted to formal ADRs.

## Core UI Decisions

| ID | Decision | Consequence |
|---|---|---|
| D1 | Trading roles use DB overlays over static defaults. | Reset-to-default deletes overlay; role defaults stay in code. |
| D2 | Permission matrix uses DB overlay plus short-lived cache. | Cell edits patch `consent_overrides`; reload clears cache. |
| D3 | Phase 1 is single-tenant but schemas carry `user_id`. | Dev default is `local`; future multi-tenancy is not schema-breaking. |
| D4 | Storage backend is Go appservice, adopted from `control/storage`. | Python/frontends do not hold S3 credentials. |
| D5 | Memory graph uses supermemory d3/canvas package up to ~200 nodes. | WebGL is future-only if graph grows past practical canvas size. |
| D6 | ENV editor is read-only with masking in phase 1. | Writing env values is future work. |
| D7 | No Prisma in frontend. | Frontend BFF proxies to Go/Python; audit uses `agent.audit_events`. |
| D8 | Package manager is Bun. | Match current frontend stack. |
| D9 | UI package sources are copied as source, not consumed as npm packages. | Local code owns imported supermemory/control patterns. |
| D10 | Prefer packages already used by Matrix/Agent frontends. | Avoid duplicate viewer stacks where possible. |
| D11 | TypeScript keeps strict mode but disables `noUncheckedIndexedAccess`. | Compatible with adopted code while preserving other strictness. |

## Storage / Ingestion / Backend Decisions

| ID | Decision | Consequence |
|---|---|---|
| D12 | Capability-based access via signed URLs. | Go appservice is control plane; SeaweedFS carries bytes; Python/browser use signed URLs. |
| D13 | Four Python environments for ingestion/retrieval/KG/layout. | Heavy layout/KG deps do not pollute main agent runtime. |
| D14 | Inter-venv communication is HTTP, not subprocess. | Health checks and independent restart are possible. |
| D15 | Retrieval stays in main venv initially. | Avoid unnecessary split until dependency conflicts require it. |
| D16 | Package organization is phase-based with registries. | Avoid flat paperwatcher-style large core modules. |
| D17 | Strict decoupling between `agent/*` and ingestion/retrieval/KG packages. | Cross-package calls go through HTTP proxies. |
| D19 | Search starts with Postgres `tsvector` + GIN. | Dedicated search service is future work. |
| D21 | Frontend uses catch-all BFF proxy routes. | Avoid many duplicated route files; preserve headers/request IDs. |
| D22 | Mock fallback keeps UI functional when backend is down. | Live verify must prove mocks are not used for real closure. |
| D23 | Reindex uses per-chunk sha256 manifests. | Only changed chunks are re-embedded on reindex. |

## Product / UX Decisions

| ID | Decision | Consequence |
|---|---|---|
| D18 | Control UI has User Mode and Developer Mode. | User mode hides raw infra/admin details; dev mode unlocks system/audit/MCP/A2A/API tabs. |
| D20 | Mode toggle state uses URL as source of truth and localStorage fallback. | Links can force user/dev mode. |
| D24 | Memory highlights engine is deferred. | `mockHighlights` must not be mistaken for live feature closure. |
| D25 | Skills toggle backend originally returned pending status; later skills persistence must remove warning flow. | Feature 015 owns full skills persistence semantics. |

## Current Interpretation

- Memory and KG are **not** normal `/control` tabs. They are own top-level
  surfaces under `/memory` and `/memory/kg`.
- Control UI owns integration visibility. Backend domain behavior remains with
  owning features: LLM in Feature 011, Memory in Feature 012, Security in
  Feature 013, Observability in Feature 014, Scheduler/Skills in Feature 015.
- Mock fallback is a development convenience, never a closeout proof.

