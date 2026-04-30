---
title: Agent Runtime Event and Recovery Contract
status: planned
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 033
---

# Agent Runtime Event and Recovery Contract

## Intent

Matrix needs one runtime event contract for agent runs, tool calls, memory,
RAG/KG, artifacts and subagents. The same contract should feed Agent Chat,
Control UI, Meta-Harness and audit without each subsystem inventing its own
partial event shape.

## Scope

- Runtime event envelope with run/session/turn/span identity.
- Tool, memory, retrieval, KG, artifact and subagent lifecycle events.
- Stale/timeout/error/killed outcome taxonomy.
- Recovery controls for status, pause, kill and replay where supported.
- Redaction and output-tail policy.

## Non-Goals

- Browser live verification in the first no-browser pass.
- Durable background job framework replacement.
- Exposing raw provider reasoning or unredacted tool payloads.

