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

- [ ] T010 Verify Agent Chat shell renders in `frontend_merger`.
- [ ] T011 Verify BFF `/api/agent/chat` route reaches Go Gateway.
- [ ] T012 Verify Go Gateway reaches Python agent and returns response.
- [ ] T013 Verify current SSE-shaped path updates UI and final state correctly.
- [ ] T014 Decide/record whether true token streaming remains deferred.
- [ ] T015 Verify backend-unavailable state is actionable in UI.

## Tools / Approvals

- [ ] T020 Verify tool-call block rendering with full UI result and truncated
  model output.
- [ ] T021 Verify approval-required tool opens approval UI.
- [ ] T022 Verify approve/reject roundtrip through BFF/Go/Python.
- [ ] T023 Verify Skills-Guard approval drawer integration is linked to Feature
  013 rather than duplicated here.

## Shared Components

- [ ] T030 Verify shared CodeBlock with Shiki and copy button.
- [ ] T031 Verify ImagePreview modal in Agent Chat.
- [ ] T032 Verify LocationEmbed and client-side LocationMap visual render.
- [ ] T033 Keep SharedMarkdown deferred unless both Matrix and Agent Chat
  converge enough to justify abstraction.
- [ ] T034 Verify markdown sanitizer blocks XSS.

## Context / Provenance

- [ ] T040 Verify EventRail flags for `NO_WORLD_KG`, `NO_WORLD_EVIDENCE`,
  `NO_PERSONAL_MEMORY`, `NO_PERSONAL_KB`, `WORLD_CLAIM_CONFLICT`.
- [ ] T041 Verify assistant answer with personal memory shows provenance.
- [ ] T042 Verify assistant answer with world context shows status/provenance.
- [ ] T043 Verify existing web sources remain intact when memory/world/KB sources
  are also present.
- [ ] T044 Verify `contextPressure` remains visible but is not the only context
  signal.

## Compression / Titles

- [ ] T050 Verify `CompressionIndicator` frontend status if implemented, else
  record as open.
- [ ] T051 Verify compression-status endpoint integration.
- [ ] T052 Decide whether `CompressionFeedback` stays Phase-2 nice-to-have.
- [ ] T053 Verify session title display/fallback.
- [ ] T054 Verify async title generation dispatch after first assistant response
  or record backend-only status.
- [ ] T055 Keep Transformers.js local-title path in client-side ML backlog unless
  promoted.

## Voice

- [ ] T060 Verify LiveKit room creation from Agent Chat voice button.
- [ ] T061 Verify STT receives user speech.
- [ ] T062 Verify agent response uses LLM path.
- [ ] T063 Verify TTS response plays.
- [ ] T064 Measure rough end-of-speech to response latency or mark voice deferred.
- [ ] T065 Verify same LiveKit SFU can serve Matrix Calls and Agent Voice if both
  are in active scope.

## Verify Gates

- [ ] Agent Chat route renders.
- [ ] Text chat roundtrip works.
- [ ] Streaming works.
- [ ] Tool-call render works.
- [ ] Context/title/compression status is explicit.
- [ ] Voice path status is explicit.
