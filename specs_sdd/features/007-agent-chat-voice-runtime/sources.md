---
title: Agent Chat Voice Runtime Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 007
---

# Sources

## Normative Local Sources

| Source | Role in SDD |
|---|---|
| `specs/execution/exec-06-agent-chat-integration.md` | Primary source for shared components, verify gates, context surfacing, title/compression and voice status. |
| `specs/execution/archive/exec-08-agent-backend-voice.md` | Historical source for backend/voice implementation; not live-closeout evidence by itself. |
| `specs/agent-ui/01-architektur.md` | Agent UI architecture baseline. |
| `specs/agent-ui/02-features.md` | Expected Agent UI feature set. |
| `specs/agent-ui/03-api-routes.md` | BFF/API route expectations. |
| `specs/agent-ui/04-frontend-tools.md` | Frontend tool rendering expectations. |
| `specs/agent-ui/05-backend-abhängigkeiten.md` | Backend dependencies and runtime assumptions. |
| `specs/agent-ui/06-protocols-roadmap.md` | Protocol roadmap for Agent UI/A2UI/MCP context. |
| `specs/14-agent-chat-ui-enhancements.md` | UI enhancement backlog. |
| `specs/execution/exec-hermes.md` | Hermes title/compression/manual-feedback provenance. |

## External / Product Sources

| Source | Use |
|---|---|
| AI SDK v6 | Frontend chat transport and devtools behavior. |
| assistant-ui | Candidate replacement/evaluation for thread/message/composer and tool rendering. |
| LiveKit | Voice room/SFU runtime for Agent Voice and Matrix calls. |
| Shiki | Code-block syntax highlighting. |
| Zustand / Jotai / auto-animate / motion | UI state and interaction patterns already adopted in Agent Chat. |
| Hermes-Agent / Hermes-4 paper | Title generation, compression visibility and manual feedback lineage. |
| Transformers.js | Future browser-local title generation path, not current default. |

## Adopted Into Matrix

- Matrix Chat and Agent Chat are separate surfaces: Matrix Chat owns room/social
  communication, Agent Chat owns productive agent work.
- Agent Chat can be a panel in product pages; Matrix Chat has dedicated full
  route.
- Current streaming semantics must be stated honestly until true token streaming
  is implemented.
- Context provenance is user-facing trust surface, not only internal metadata.
- Voice is optional until LiveKit/STT/TTS is live verified.
