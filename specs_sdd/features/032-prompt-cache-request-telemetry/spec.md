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

## Non-Goals

- A provider-specific product dependency.
- Estimating unavailable cache counters as fact.
- Sending provider-only diagnostics into memory, KG claims or user-visible
  artifacts without redaction.

