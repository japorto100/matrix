---
title: Smart Routing Gate Ledger
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 011
migrated_from:
  - docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md
  - specs/execution/superpower-impl-log.md
---

# Smart Routing Gate Ledger

ADR-001 initially blocked smart-routing rollout behind six gates. The later
superpower implementation log records all six gates plus the Phase-1
`router_node` refactor as landed. This file preserves the decision logic and
the remaining verification risks.

## Gate History

| Gate | Meaning | Current SDD State |
|---|---|---|
| G1 | German keyword set + hyphen tokenizer | landed, verify keyword quality |
| G2 | Credential pre-flight before cheap switch | landed, verify single-vendor users |
| G3 | 60s smart-routing config cache | landed, verify load path |
| G4 | A/B harness routing dimension | landed, fix race follow-up |
| G5 | User-visible routing indicator | landed, verify metadata pill |
| G6 | Control-UI panel + disable path | landed, verify user toggle |
| P1 | Move routing into `router_node` | landed, verify first-turn semantics |

## Rollout Rule

Smart routing must remain off-by-default for broad users until the current code
passes live verification with:

- simple prompt routed cheap.
- complex/DE prompt stays strong.
- missing cheap-provider credential stays primary.
- user sees routing disclosure.
- user can disable routing from Control UI.
- A/B row records routing metadata.

## Remaining Follow-Ups

### F-G4 Race

Risk: async insert/update order in A/B experiments can lose routing metadata if
the update runs before the insert. Desired fix: upsert semantics so
`routing_used`, `routing_reason` and `routing_picked` survive either order.

### F-G1 Keyword Quality

Risk: overly common English words such as "reason", "test", "model", "plan",
"review" block cheap routing for casual prompts. Desired fix: keep robust
multi-word complexity phrases and remove broad single-word false positives.

### F-4g4 Scorer Eval ID

Risk: scorer keeps first `harness_eval_id` via COALESCE when rescoring with a
new eval id. Desired default: document first-write-wins and add explicit
overwrite option only if needed.

## A2FM Boundary

This smart router is not the A2FM paper ML router. It is a conservative
heuristic running inside matrix's provider-agnostic LiteLLM architecture. A2FM
informs later audit-labeling and feedback-loop work, not current production
routing semantics.
