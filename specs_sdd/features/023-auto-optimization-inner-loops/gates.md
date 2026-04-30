---
title: Auto-Optimization Inner Loops Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-30
feature_id: 023
---

# Gates

## 2026-04-29 Expanded Candidate Spaces

- Tool-policy candidates from Feature 024 cannot weaken security gates.
- Semantic-layer candidates from Feature 025 cannot mutate definitions during a
  run.
- Browser-RAG candidates from Feature 026 record runtime/model metadata.
- Visual-memory candidates from Feature 028 record source refs and confidence.

- G001 [partial-pass] Search spaces are explicit and bounded for the first
  deterministic RAG retrieval-mode sweep; parser/memory/tool search spaces
  remain open.
- G002 [pass-initial] Every deterministic RAG inner-loop candidate records full
  config, changed parameters and baseline metadata.
- G003 [pass-initial] Search-set and holdout-set are separate.
  - 2026-04-27: Feature 022 exposes explicit `search`/`holdout` canaries.
    Feature 023 default inner-loop uses the search split and records
    `holdout/protected` plus protected-input validation instead of optimizing
    against holdout data.
- G004 [pass-initial] Live-provider loops require explicit request/token/cost
  caps; provider-call budget smoke blocks when quota env is not enabled.
- G005 [pass-initial] Generated candidates become Meta-Harness artifacts before
  promotion.
- G006 [pass-initial] No loop writes product code directly.
- G007 Failed/crashed candidates remain visible in the experiment log.
- G008 [pass-static] Skill/tool candidates cannot relax Feature 015 lifecycle
  constraints: pinned skills remain write-protected, usage sidecar evidence is
  read-only for optimization, and promotion/archive decisions must pass Feature
  016 Meta-Harness before product mutation.
