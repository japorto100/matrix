---
title: Prompt Cache, Request Telemetry and Cache Stability
status: planned
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 032
---

# Prompt Cache, Request Telemetry and Cache Stability

## Intent

Matrix must make provider request behavior observable without becoming tied to
one provider. The agent runtime should normalize cache, usage, request-id and
rate-limit evidence across OpenRouter/OpenAI-compatible, Anthropic-family,
Gemini-family and local/provider-proxy transports where those providers expose
the data.

## Scope

- Provider-agnostic request telemetry envelope.
- Prompt/cache usage counters and last-call/session totals.
- System prompt, tool catalog and transport fingerprints for cache stability.
- Cache-break detection with explainable reasons.
- MCP/tool/skill reload cache impact metadata.
- Control UI and Meta-Harness gates for cache behavior.

## Request Telemetry Contract

`provider-request-telemetry/v1` is provider-agnostic. It stores hashes and
normalized counters, not raw prompts, raw tool schemas, provider headers or
secrets.

Required cache snapshot fields:

- provider, model, router, transport, cache retention and stream strategy
- prompt digest, prompt layout digest and system prompt digest
- tool catalog digest, tool count and sorted tool names
- normalized usage: prompt, input, completion, output, total, reasoning, cache
  read, cache write and explicit unknown fields
- sanitized metadata for request id, provider/local duration and rate-limit
  buckets when providers expose them

Cache-break reasons are explicit for model, transport, cache retention, stream
strategy, system prompt, prompt layout/content and tool catalog changes.
MCP/tool/skill reloads use `agent-cache-impact/v1` so reload provenance remains
separate from a single LLM request.

## Non-Goals

- A provider-specific product dependency.
- Estimating unavailable cache counters as fact.
- Sending provider-only diagnostics into memory, KG claims or user-visible
  artifacts without redaction.
