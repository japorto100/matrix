---
title: Agent Chat and Voice Runtime Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 007
---

# Live Verify

## Source Checks

- [ ] `exec-06` phase/gate split matches current tasks.
- [ ] Archived voice exec is treated as code-history, not closed live status.
- [ ] Hermes title/compression rows are linked to the correct open tasks.
- [ ] `specs/agent-ui/*` API/tool/component expectations are represented.

## Text Chat

- [ ] Open Agent Chat.
- [ ] Send a simple text prompt.
- [ ] Confirm current response-streaming behavior.
- [ ] Record whether response is true token streaming or final-packet-over-SSE.
- [ ] Confirm final message state persists in UI.
- [ ] Confirm error state for backend unavailable is actionable.

## Tools and Approvals

- [ ] Trigger a safe tool call.
- [ ] Confirm tool-call block renders.
- [ ] Confirm large tool output is truncated for model but full enough in UI.
- [ ] Trigger approval-required action.
- [ ] Confirm approve/reject UX works.

## Context UI

- [ ] Trigger response with context degradation flags.
- [ ] Confirm EventRail shows relevant flags.
- [ ] Trigger response with memory/world/KB provenance.
- [ ] Confirm provenance is visible and not rendered as unsupported certainty.
- [ ] Title generation updates visible chat/session title.
- [ ] Compression indicator appears when applicable.
- [ ] Manual compression feedback is present or explicitly deferred.

## Voice

- [ ] Join LiveKit room.
- [ ] Record/transcribe short utterance.
- [ ] Receive TTS response.
- [ ] Measure rough latency or mark voice deferred.

## Result

pending
