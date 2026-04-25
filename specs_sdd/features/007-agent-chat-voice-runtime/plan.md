---
title: Agent Chat and Voice Runtime Plan
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 007
migrated_from:
  - specs/execution/exec-06-agent-chat-integration.md
  - specs/execution/archive/exec-08-agent-backend-voice.md
  - specs/execution/exec-hermes.md
adrs: []
---

# Plan

## Architecture

Agent Chat is a runtime feature in `frontend_merger` backed by Go BFF routes
and Python agent services. Voice is an optional runtime path through LiveKit and
STT/TTS providers.

## Critical Files

- `frontend_merger/src/features/agent/**`
- `frontend_merger/src/app/api/agent/**`
- `frontend_merger/src/app/api/audio/**`
- `go-appservice/internal/handlers/http/**`
- `python-backend/agent/**`
- `python-backend/voice/**`

## Migration Strategy

1. Convert old agent-ui specs into architecture and API contracts.
2. Treat archived voice exec as historical implementation source.
3. Split A2UI-specific rendering to Feature 008.
4. Keep Hermes title/compression rows here only where they affect Agent Chat UI.

## Risks

- Browser-only render passing while Go/Python SSE path is broken.
- Voice setup blocking non-voice Agent Chat closure.

