---
title: Semantic Coverage Audit
status: review
owner: filip
created: 2026-04-25
updated: 2026-04-25
---

# Semantic Coverage Audit

Question: If someone reads only `specs_sdd/`, would they know what to do as well
as if they read the old `specs/` plus `docs/superpowers/` landscape?

## Verdict

**Yes for SDD/planning and handoff.**

`specs_sdd/` is now at least equal to the old spec tree for understanding scope,
ownership, current state, target state, open work, research provenance and live
verification debt. In several places it is better than the old structure because
it separates:

- implemented vs live-verified;
- active work vs future/backlog;
- superseded history vs current guidance;
- local source files vs paper/repo/product context;
- feature ownership vs cross-feature dependencies.

This does **not** mean the old files should be deleted. They remain immutable
legacy evidence until the user reviews this SDD pass and live-verify evidence is
attached. But for future work, `specs_sdd/` can be used as the primary SDD view.

## Evidence

Structural checks:

- 15 top-level features exist.
- Every feature has the core SDD file set: `spec.md`, `plan.md`, `tasks.md`,
  `live-verify.md`, `closeout.md`.
- Feature files under `specs_sdd/features`: 113.
- High-source features now have either `sources.md` or `research.md`.
- Global source-preservation policy exists in `SOURCES.md`.

File-level audit from the earlier migration remains true:

- `specs/` markdown/text/csv up to depth 3: 92 files, 100% referenced.
- `specs/execution/`: 65 files, 100% referenced.
- `docs/superpowers/`: 17 files, 100% referenced.

The SDD is intentionally much smaller than the legacy corpus because it
condenses and reorganizes instead of copy-pasting. The important semantic
content now lives in feature specs, sources/research, gates and live-verify.

## Feature Readiness From `specs_sdd` Alone

| Feature | Can Work From SDD Alone? | Reason |
|---|---|---|
| 001 Platform Baseline | Yes | accepted baseline, source ledger and gates identify durable architecture vs future ideas. |
| 002 Devstack Bootstrap | Yes | devstack, env, secrets, Postgres and machine-storage rules are sourced and gated. |
| 003 Frontend Merger Shell | Yes | branch evidence, route shell, open full-stack smoke and superseded merge history are separated. |
| 004 Homeserver/Connectivity | Yes | Tuwunel, mobile/connectivity/federation and upstream monitor gates are explicit. |
| 005 Matrix Chat Core | Yes | A-O gate ledger, exec2 sources and live verify flows are preserved. |
| 006 Appservice/NATS/E2EE | Yes | core gateway, E2EE, routing, key deletion, future bridges and hardening are split. |
| 007 Agent Chat/Voice | Yes | text/chat/tool/approval/context/compression/title/voice gates and sources are explicit. |
| 008 Agentic UI/MCP | Yes | A2UI, CopilotKit, MCP, persistence, native packet and widget gaps are captured. |
| 009 Multi-Agent/A2A | Yes | LangGraph, roles, skills, A2A, routing, paper-derived learning and Control UI gates are captured. |
| 010 Control UI | Yes | decisions, slices, research map, task groups and live gates are imported. |
| 011 LLM Gateway/Routing | Yes | gateway, credentials, billing, reasoning, smart-routing and A2FM boundaries are imported. |
| 012 Memory/Context/World/KB | Yes | boundaries, subfeatures, research and tasks preserve the old umbrella semantics. |
| 013 Sandbox/Security/HITL | Yes | OpenSandbox, consent, sanitizer, redaction, ADR-004, Matrix SSRF/XSS and research are captured. |
| 014 Observability/Harness/Evals | Yes | OTel/OpenObserve/Langfuse, audit, harness/eval papers and workpack gates are captured. |
| 015 Scheduler/Skills/Planning | Yes | scheduler, skills, PDDL, DSPy, Hermes and planning gates are captured. |

## Source / Paper Carry-Forward

The migration now preserves source context through one of two paths:

- `sources.md` for provenance ledgers and adopted/rejected context;
- `research.md` for paper synthesis and open research questions.

Current coverage:

| Feature group | Source handling |
|---|---|
| 001-004 | `sources.md` plus gates for baseline/devstack/frontend/homeserver. |
| 005 | Gate-rich Matrix chat docs; no separate `sources.md` yet because exec2 gate files are in frontmatter and live-verify. |
| 006-007 | `sources.md` plus gates for E2EE/NATS and Agent Chat/Voice. |
| 008 | `research.md` for A2UI/MCP/CopilotKit context. |
| 009 | `sources.md` for MetaClaw/Trace2Skill/NLAH/A2A. |
| 010-012 | `research.md` for control, LLM and memory/context/world/KB research. |
| 013-014 | `sources.md` for security/observability papers, products, ADRs and external repos. |
| 015 | `research.md` for scheduler/skills/PDDL/DSPy. |

## What Still Requires Work

The remaining work is execution evidence, not semantic migration:

- live Matrix session and E2EE/NATS handoff;
- Agent Chat text/tool/approval/voice full-stack runs;
- A2A live delegation smoke;
- Control UI tab-by-tab backend walkthrough;
- LiteLLM billing/routing/user-picker live verify;
- memory/context/world/KB runtime verification;
- OpenSandbox and Skills-Guard HITL live verify;
- OpenObserve traces and harness/eval evidence;
- scheduler delivery and real-LLM skill verification.

These are intentionally in `live-verify.md`/`gates.md`, not hidden in old execs.

## Archival Position

Old `specs/` and `docs/superpowers/` can now be treated as **legacy evidence**,
not the working source of truth. Do not delete or move them yet. Archive/cleanup
should wait for user review and feature-by-feature live evidence attachment.

Future edits should land in `specs_sdd/` first. If a legacy file contains a
detail that is missing from SDD, that is a migration bug and should be fixed in
the relevant feature rather than resurrecting the old structure.
