---
title: Semantic Layer Metrics Claims Live Verify
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 025
---

# Live Verify

- LV001 Start dev stack and inspect semantic catalog health.
- LV002 Ask agent "what is revenue?" and verify definition is sourced.
- LV003 Ask for two similar metrics and verify ambiguity handling.
- LV004 Ask for a metric value with insufficient permissions and verify denial.
- LV005 Ask for a metric value with permission and verify provenance/freshness.
- LV006 Ask for a document concept that maps to RAG and KG refs.
- LV007 Submit a user correction and verify it creates a pending proposal.
- LV008 Promote a correction and verify previous definition remains historical.
- LV009 Open Control UI semantic catalog and verify owner/status/conflicts.
- LV010 Run Meta-Harness semantic-layer scenario with train/holdout prompts.
- LV011 Verify traces show semantic lookup before answer generation.
- LV012 Verify no provider-specific prompt or model dependency is required.
