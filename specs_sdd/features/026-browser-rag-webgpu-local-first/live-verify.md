---
title: Browser RAG WebGPU Local First Live Verify
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 026
---

# Live Verify

- LV001 Open Matrix UI and verify browser capability probe.
- LV002 Load small embedding model in worker and verify main thread remains
  responsive.
- LV003 Disable WebGPU or force fallback and verify WASM/server fallback.
- LV004 Index a small local message/document set.
- LV005 Run lexical-only search and inspect results.
- LV006 Run dense local search and inspect metadata.
- LV007 Run hybrid search and verify RRF merge.
- LV008 Rerank top 10 hits and verify latency stays bounded.
- LV009 Verify stale index invalidation after model metadata change.
- LV010 Verify local/private query path does not call server.
- LV011 Verify server fallback path records that server retrieval was used.
- LV012 Run Feature 022 canaries through browser-vs-backend comparison.
- LV013 Test mobile/narrow viewport with model load/error states.
- LV014 Verify local model cache can be cleared from settings.
