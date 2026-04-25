---
title: Memory, Context, World Model and Personal KB Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
---

# Live Verify

## Personal Memory

- [ ] Start Python backend with memory dependencies.
- [ ] Query memory health endpoint/control contract.
- [ ] Confirm episodic/vector/KG layer states.
- [ ] Store a test memory or observation if supported.
- [ ] Retrieve that memory through recall/search path.
- [ ] Retain raw user input and confirm it is evidence, not derived truth.
- [ ] Retain derived observation and confirm source/evidence backlink.
- [ ] Try KB-like artifact in personal-memory path and confirm reject/bridge
  behavior.
- [ ] Try world-like claim in personal-memory path and confirm reject/bridge
  behavior.

## Context Runtime

- [ ] Run an Agent Chat turn.
- [ ] Inspect prompt/context metrics.
- [ ] Confirm static/dynamic prompt block order matches spec.
- [ ] Confirm missing layer flags are visible.
- [ ] Trigger or simulate compaction threshold if safe.
- [ ] Confirm provenance/evidence survives compaction expectations.
- [ ] Confirm pre-save/backstop happens before lossy compression where testable.

## World Model

- [ ] Add or inspect world evidence record if implemented.
- [ ] Confirm claim/KG/adjudication path or mark planned.
- [ ] If a world claim exists: retrieve claim with evidence/status/provenance.

## Personal KB

- [ ] Capture a personal KB item if implemented.
- [ ] Retrieve KB item in runtime context if implemented.
- [ ] If a KB artifact exists: retrieve it as KB, not world truth.
- [ ] Mark unimplemented surfaces as planned, not broken.

## Eval

- [ ] Run Hindsight shared-corpus eval or document blocker.
- [ ] Run MemPalace shared-corpus eval or document blocker.
- [ ] Run fusion shared-corpus eval or document blocker.
- [ ] Run memory_fusion E2E smoke or document blocker.

## Result

pending
