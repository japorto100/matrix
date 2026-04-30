---
title: Agent Runtime Event Recovery Live Verify
status: planned
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 033
---

# Live Verify

- LV001 Run a tool-using agent turn and verify Agent Chat shows model, tool and
  artifact events as structured cards.
- LV002 Run a memory-writing turn and verify memory events are visible but
  redacted.
- LV003 Enable gated single-hop subagent lane and verify child lifecycle,
  output summary and parent memory handoff.
- LV004 Kill or timeout a child run and verify explicit outcome appears in
  Control UI and trace artifacts.
- LV005 Replay a completed trace in Meta-Harness without provider calls.
