---
title: Knowledge Graph Closeout
status: open
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 017
---

# Closeout

Open. This feature was split out on 2026-04-26 so KG-specific bitemporal claim
modeling does not stay hidden inside Feature 012.

Close only when:

- KG bitemporal claim schema is implemented and tested.
- Corrections preserve historical truth and current-truth queries are safe.
- Retrieval combines semantic similarity with temporal/access decay.
- KG claims require evidence refs before promotion.
- Memory-Fusion integration proposes claims without silently promoting them.
- Control UI can inspect claim status, validity, history and provenance.
