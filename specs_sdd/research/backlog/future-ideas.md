---
title: Future Ideas Backlog Split
status: active_backlog
owner: filip
created: 2026-04-25
updated: 2026-04-25
migrated_from:
  - specs/FUTURE_IDEAS.md
---

# Future Ideas Backlog Split

This file replaces `specs/FUTURE_IDEAS.md` as the SDD-facing index. The legacy
file remains unchanged as evidence and chronology.

## Feature-Owned Backlog

| Idea | Owner | Status |
|---|---|---|
| Agent Chat interactive code blocks with Sandpack | Feature 007 / Feature 013 | deferred; OpenSandbox server path is the current execution primitive. |
| Agent Chat generated PPTX/PDF/Excel artifacts | Feature 007 / Feature 010 | deferred until structured report generation is common. |
| Agent Chat Spectacle presentation mode | Feature 007 | deferred; tabs/accordions and artifact links are enough for now. |
| Authenticated Matrix media / MSC3916 migration | Feature 005 / Feature 006 | deferred dev hardening; production media path must revisit this. |
| ConnectRPC/gRPC for Go-Python IPC | Feature 001 / Feature 007 / Feature 011 | deferred until bidirectional typed streaming has real demand. |
| Remote A2A agents | Feature 009 | deferred after local role delegation is live-verified. |
| Agent loop stop/resume and pause/resume | Feature 007 / Feature 009 / Feature 014 | design backlog; requires durable tool/checkpoint state. |
| Standalone memory service on port 8093 | Feature 012 | deferred until multi-process memory sharing is needed. |
| RL trainer / PRM / LoRA activation | Feature 015 / Feature 014 | gated by real trajectory volume and eval evidence. |
| E2EE production hardening, key backup, PQXDH | Feature 006 / Feature 013 | production-hardening backlog after current gateway path is live-proven. |
| Tuwunel media store to SeaweedFS ingestion bridge | Feature 010 / Feature 012 | useful ingestion bridge; not part of the core Matrix event path. |

## Research-Only Until Re-Triaged

| Idea | Reason |
|---|---|
| Backend conversion via Gotenberg | Needs production document-preview demand and an added service. |
| PowerPoint client preview | Low current data fit; PDF/Excel dominate expected files. |
| Additional mobile-specific ideas | Empty source section; no active scope. |
| Additional privacy/security ideas | Empty source section; Feature 013 is the active owner. |
| Additional infrastructure/deployment ideas | Empty source section; Feature 002 owns concrete ops. |
| Additional developer-tool ideas | Empty source section; Feature 001 owns tooling invariants. |

## Rule

Future ideas become implementation work only when copied into a feature
`tasks.md` with owner, acceptance criteria and verify strategy.
