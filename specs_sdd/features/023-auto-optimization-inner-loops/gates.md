---
title: Auto-Optimization Inner Loops Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Gates

- G001 Search spaces are explicit and bounded.
- G002 Every candidate records full config, changed parameters and baseline.
- G003 Search-set and holdout-set are separate.
- G004 Live-provider loops require explicit request/token/cost caps.
- G005 Generated candidates become Meta-Harness artifacts before promotion.
- G006 No loop writes product code directly.
- G007 Failed/crashed candidates remain visible in the experiment log.
