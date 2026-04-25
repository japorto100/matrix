---
title: Agent Chat and Voice Runtime
status: implementation_done_live_verify_open
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 007
migrated_from:
  - specs/14-agent-chat-ui-enhancements.md
  - specs/agent-ui/01-architektur.md
  - specs/agent-ui/02-features.md
  - specs/agent-ui/03-api-routes.md
  - specs/agent-ui/04-frontend-tools.md
  - specs/agent-ui/05-backend-abhängigkeiten.md
  - specs/agent-ui/06-protocols-roadmap.md
  - specs/execution/exec-06-agent-chat-integration.md
  - specs/execution/archive/exec-08-agent-backend-voice.md
  - specs/execution/exec-hermes.md
adrs: []
---

# Agent Chat and Voice Runtime

## Current State / Ist

Agent Chat was merged into `frontend_merger` and the BFF routes exist. The old
`exec-06` states that API routes, shared components, context surfacing and many
frontend pieces are code-complete, while full-stack verify remains open. True
token-by-token streaming is explicitly deferred: the backend currently sends a
final text-delta packet through an SSE-shaped path, which the AI SDK treats as
streaming state without real token streaming.

Voice code exists from the archived exec-08 path, but LiveKit/STT/TTS end-to-end
verification is open. Hermes-derived title generation and compression status
backend pieces are done; frontend display, async title dispatch and manual
compression feedback are still follow-up or nice-to-have depending on scope.

## Target State / Soll

Agent Chat is a first-class runtime surface with text chat, tool rendering,
approval flows, context provenance, title/compression visibility and optional
voice. Its status must separate code-complete UI from live backend proof.

## Subfeatures

- 007.1 Agent Chat shell and BFF proxy
- 007.2 Text response streaming semantics
- 007.3 Tool-call rendering and approval flow
- 007.4 Shared markdown, code, media and location components
- 007.5 Context provenance and event rail
- 007.6 Compression indicator and feedback
- 007.7 Session title generation and display
- 007.8 LiveKit voice runtime
- 007.9 Agent Chat vs Matrix Chat panel boundaries

## Gap

- API route and Go Gateway/Python Agent roundtrip still need full-stack live
  verification.
- True token streaming is deferred; current implementation must be documented
  as final-packet-over-SSE until Phase-D changes it.
- Voice needs LiveKit/STT/TTS live verification or explicit deferral.
- Context provenance still needs visible memory/world/KB source rendering beyond
  degradation flags.
- CompressionIndicator frontend and async session-title dispatch remain open
  unless already implemented in current code and verified.
- Manual compression feedback remains nice-to-have unless promoted.
- Primary browser-side title generation belongs to client-side ML backlog.

## Verify

- [ ] Agent chat sends a message and receives streamed response.
- [ ] Tool-call result renders in UI.
- [ ] Approval flow works.
- [ ] Context provenance and degradation flags render correctly.
- [ ] Title/compression state is visible or explicitly deferred.
- [ ] Voice path is either live-verified or explicitly deferred.

## Closeout Criteria

- Archived voice exec is historical only.
- Hermes-owned title/compression entries are either closed or linked as open
  subfeature tasks.
