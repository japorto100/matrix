---
title: Agent Chat Voice Runtime Research
status: draft
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 007
---

# Research

## Runtime Event Downstream Transfer 2026-04-30

References: `_ref/hermes-agent/tools/delegate_tool.py`,
`_ref/claude_code/openclaw/docs/channels/matrix.md` and Feature 033.

Agent Chat should render model/tool/memory/artifact/subagent events from a
structured runtime stream. It must not infer tool calls, cache stats or child
state by scraping assistant text. Matrix voice/media findings from Hermes
(`MSC3245` voice and encrypted-media cache fallback) become downstream gates
for voice and artifact rendering.

