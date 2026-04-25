---
title: Agent Chat and Voice Runtime Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 007
migrated_from:
  - specs/execution/exec-06-agent-chat-integration.md
---

# Tasks

## Migration / SDD

- [x] T001 Import `specs/agent-ui/*` and `exec-06` into plan/contracts.
- [x] T002 Preserve deferred true-token-streaming caveat from `exec-06`.
- [x] T003 Preserve Hermes title/compression ownership and open frontend split.
- [x] T004 Preserve shared component and context-surfacing verify gates.

## Text Chat Runtime

- [x] T010 Static-verify Agent Chat shell/components build in
  `frontend_merger`.
- T011 Live-verify BFF `/api/agent/chat` route reaches Go Gateway.
- T012 Verify Go Gateway reaches Python agent and returns response.
- [x] T013 Static-test current SSE/A2UI packet handling; live UI final-state
  check remains pending.
- [x] T014 Decide/record whether true token streaming remains deferred.
- [x] T015 Static-verify backend-unavailable error banner exists and is
  dismissible; live failure UX remains pending.
- [x] T016 Static-verify `/api/agent/chat`, `/api/agent/approve`,
  `/api/agent/compression-status`, `/api/agent/models` and
  `/api/agent/completion` route files exist and build.
- [x] T017 Record route boundary: Agent Chat is overlay/control surface plus API
  routes, not top-level `/agent`.

## Tools / Approvals

- [x] T020 Static-verify tool-call block component exists/builds with full UI
  result and model-output split; live render remains pending.
- [x] T021 Static-test approval-required tool opens approval UI.
- T022 Verify approve/reject roundtrip through BFF/Go/Python.
- [x] T023 Verify Skills-Guard approval drawer integration is linked to Feature
  013 rather than duplicated here.

## Shared Components

- [x] T030 Static-verify code/copy components build in Agent Chat scope.
- [x] T031 Static-verify ImagePreview modal exists/builds in Agent Chat.
- T032 Verify LocationEmbed and client-side LocationMap visual render.
- [x] T033 Keep SharedMarkdown deferred unless both Matrix and Agent Chat
  converge enough to justify abstraction.
- [x] T034 Static-test markdown sanitizer blocks XSS.

## Context / Provenance

- [x] T040 Static-test EventRail flags for `NO_WORLD_KG`, `NO_WORLD_EVIDENCE`,
  `NO_PERSONAL_MEMORY`, `NO_PERSONAL_KB`, `WORLD_CLAIM_CONFLICT`.
- T041 Verify assistant answer with personal memory shows provenance.
- T042 Verify assistant answer with world context shows status/provenance.
- T043 Verify existing web sources remain intact when memory/world/KB sources
  are also present.
- [x] T044 Static-test `contextPressure` remains visible but is not the only context
  signal.

## Compression / Titles

- [x] T050 Static-verify `CompressionIndicator` exists/builds; live visible
  behavior remains pending.
- [x] T051 Static-verify compression-status endpoint route exists/builds.
- [x] T052 Decide whether `CompressionFeedback` stays Phase-2 nice-to-have.
- T053 Verify session title display/fallback.
- T054 Verify async title generation dispatch after first assistant response
  or record backend-only status.
- [x] T055 Keep Transformers.js local-title path in client-side ML backlog unless
  promoted.

## Voice

- T060 Verify LiveKit room creation from Agent Chat voice button.
- T061 Verify STT receives user speech.
- T062 Verify agent response uses LLM path.
- T063 Verify TTS response plays.
- T064 Measure rough end-of-speech to response latency or mark voice deferred.
- T065 Verify same LiveKit SFU can serve Matrix Calls and Agent Voice if both
  are in active scope.

## Verify Gates

- [x] Agent Chat frontend code builds and tests.
- Text chat roundtrip works.
- [x] A2UI/SSE packet handling is unit-tested.
- Streaming works in live UI.
- [x] Tool-call render code builds.
- Tool-call render is browser/live checked.
- [x] Context/compression status is explicit at static UI level; title live
  status remains pending.
- Voice path status is explicit.
