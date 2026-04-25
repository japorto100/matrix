---
title: Appservice NATS E2EE Bridges Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 006
---

# Sources

## Normative Local Sources

| Source | Role in SDD |
|---|---|
| `specs/execution/exec-05-nats-e2ee-pipeline.md` | Primary implementation history and open A4/E2EE gates. |
| `specs/execution/exec-05b-messaging-bridges.md` | Future bridge backlog and E2BE bridge pattern. |
| `specs/execution/exec-05c-agent-isolation.md` | Subject routing, target-agent routing, thread support, key deletion and hybrid-interface scope. |
| `specs/02-go-appservice.md` | Go appservice architecture, handlers, NATS bridge, E2EE stack. |
| `specs/03-python-agent-bridge.md` | Python bridge as pure NATS consumer and HTTP/SSE agent client. |
| `specs/06-e2ee.md` | E2EE architecture decision: Go handles crypto for current system. |
| `specs/13-e2ee-agent-architecture.md` | Current-state trust model: Go decrypts, Python sees only cleartext via NATS. |
| `specs/16-security.md` | Matrix security summary: agent rooms, URL preview, E2EE trust boundary. |

## External / Protocol Sources

| Source | Use |
|---|---|
| Matrix Application Service protocol | Go appservice registration, namespaces, intents and event handling. |
| mautrix-go | Appservice and E2BE bridge implementation substrate. |
| goolm / OlmMachine | Pure-Go E2EE implementation to avoid libolm/CGO dependency. |
| Matrix MSC4153 | Cross-Signing / identity strategy relevant for Element X compatibility. |
| Matrix MSC4268 / forwarded room keys | Future key-forwarding option for native/per-agent E2EE. |
| vodozemac-python | Future per-agent native E2EE evaluation input, not adopted. |
| NATS / JetStream | Internal event bus; JetStream/TLS/authorization are production hardening. |
| mautrix-whatsapp/signal/telegram/meta/discord | Future external messaging bridge candidates. |
| Matrix Hookshot / maubot | Future DevOps/feed bridge candidates. |

## Adopted Into Matrix

- Go appservice is the only Matrix crypto endpoint for the current architecture.
- Python bridge has no Matrix dependency and no Matrix keys.
- NATS is for asynchronous Matrix event handoff; Agent Chat uses HTTP/SSE and
  Voice uses LiveKit.
- E2BE is accepted for agent rooms: trust the self-operated bridge.
- Key deletion is configurable because agents may need context/history.
- Subject routing and hybrid native E2EE are preparation, not closed behavior.
