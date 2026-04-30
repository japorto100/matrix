---
title: Observability Harness Evals Research
status: draft
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 014
---

# Research

## Runtime Event / Cache Transfer 2026-04-30

Local references:

- `_ref/hermes-agent/tools/delegate_tool.py`
- `_ref/hermes-agent/cli.py`
- `_ref/claude_code/openclaw/src/agents/cache-trace.ts`
- `_ref/claude_code/openclaw/src/agents/pi-embedded-runner/prompt-cache-observability.ts`
- `_ref/claude_code/openclaw/src/agents/subagent-lifecycle-events.ts`
- `_ref/claude_code/openclaw/src/agents/subagent-run-liveness.ts`

Findings to transfer:

- Observability needs structured runtime events, not parsing final assistant
  messages.
- Cache stability is an eval target: tool ordering, system prompt digest and
  provider transport changes can be detected without browser live tests.
- Subagent lifecycle needs explicit started/completed/error/timeout/killed/stale
  outcomes with run/session identity.
- Event payloads must be capped/redacted and replayable by Meta-Harness.

2026-04-30 implementation note: `TraceExpectations` now understands nested
runtime events inside audit metadata, not just top-level audit actions. This
lets provider-free scenarios verify request/cache and runtime-event redaction
before browser/live-provider lanes: required event names prove completeness,
required metadata keys prove useful diagnostics, and forbidden wildcard keys
catch raw prompts, raw headers, authorization values, resolved secrets or
unredacted request telemetry.

The same gate vocabulary now includes required/forbidden metadata values. This
matters for subagent observability because a trace that merely says
`subagent.delegation.completed` is insufficient. The evaluator can assert
isolated context mode, parent-only memory policy and child tool allowlist
membership while rejecting direct memory-write tools or raw parent history in
runtime-event metadata.

Stream gates now also have explicit downstream artifact assertions. A
RAG/KG scenario can require `tool-output-available`, a renderer-capable tool and
specific artifact filenames, while trace gates require the corresponding
source/citation runtime events. This keeps observability tied to what Agent Chat
can actually render, not only to retrieval scores.
