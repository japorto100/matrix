---
title: Frontend Merger and Shell Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 003
---

# Closeout

## Built

- `frontend_merger` is the active merged UI shell.
- Matrix, Files, Memory and Control have App Router page entries.
- Agent Chat is mounted globally through `AgentProviders` and
  `GlobalChatOverlay`, with runtime APIs under `/api/agent/*`.
- Plan-v2 A2UI/CopilotKit follow-ups are assigned to Feature 008.
- Control/runtime surface follow-ups are assigned to Feature 010.

## Not Built

- No standalone `/agent` page is required by the current architecture.
- Browser/full-stack live route smoke remains deferred.
- Route consolidation remains deferred.

## Deviations From Plan

- The old top-level `/agent` route expectation was corrected: Agent Chat is an
  overlay/API surface and Control tab concern, not a separate shell page.

## Verify Result

- PASS: `bun run lint`
- PASS: `bun run typecheck`
- PASS: `bun run test` (7 files, 37 tests)
- PASS: `NEXT_TELEMETRY_DISABLED=1 bun run build` (Next.js 16.2.2 Turbopack)

## Live Verify Result

Deferred per current work order.

## Follow-Ups

- Run browser/full-stack route smoke when live verify resumes.
- Keep any A2UI/CopilotKit provider runtime gaps in Feature 008.
- Keep Control UI backend/data gaps in Feature 010.
