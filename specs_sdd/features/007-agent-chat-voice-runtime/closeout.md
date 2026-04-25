---
title: Agent Chat and Voice Runtime Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 007
---

# Closeout

## Built

- Agent Chat frontend components, global overlay/control surface and BFF API
  route files are present in `frontend_merger`.
- `/api/agent/chat`, `/api/agent/approve`, `/api/agent/compression-status`,
  `/api/agent/models` and `/api/agent/completion` exist and pass the frontend
  static gates.
- A2UI/SSE packet handling has Python/frontend test coverage.
- Compression indicator, tool rendering, image preview and shared code/copy
  components exist and build.
- Approval controls, context/degradation rail and markdown sanitizer behavior
  are covered by focused component tests.

## Not Built

- Top-level `/agent` route; this is intentionally not part of the architecture.
- True token-by-token backend streaming.
- Proven LiveKit/STT/TTS end-to-end voice path.
- Proven approve/reject roundtrip through the whole stack.

## Deviations From Plan

- The current streaming path is final-packet-over-SSE, not true token streaming.
- Agent Chat is treated as overlay/control/API surface instead of a standalone
  app route.

## Verify Result

- PASS static: `bun run lint`, `bun run typecheck`, `bun run test` and
  `NEXT_TELEMETRY_DISABLED=1 bun run build` in `frontend_merger`.
- PASS static: `uv run pytest tests/agent/test_streaming_a2ui.py -q` in
  `python-backend`.
- PASS static: `uv run ruff check bridge tests/bridge agent voice` in
  `python-backend`.
- PASS static: `bun run test -- src/features/agent/components/AgentChatEventRail.test.tsx src/features/agent/components/AgentChatMarkdown.test.tsx src/features/agent/components/AgentChatToolBlock.test.tsx` in `frontend_merger`.

## Live Verify Result

Pending: BFF -> Go Gateway -> Python Agent, browser tool rendering,
context/title/compression visibility and LiveKit/STT/TTS voice.

## Follow-Ups

- Live-test text chat through the full stack.
- Live-test approval UI approve/reject.
- Decide when true token streaming is worth promoting from deferred scope.
- Keep voice deferred until LiveKit/STT/TTS dependencies are available for a
  real check.
