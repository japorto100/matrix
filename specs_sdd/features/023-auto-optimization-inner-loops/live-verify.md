---
title: Auto-Optimization Inner Loops Live Verify
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Live Verify

- LV001 Run deterministic RAG optimization smoke over Feature 022 canaries.
- LV002 Verify artifacts appear under `data/meta_harness/runs/<run>/`.
- LV003 Verify Pareto sees optimized candidates.
- LV004 Run parser/chunking optimization smoke over the ResearchWatcher PDF
  fixture.
- LV005 Verify OpenRouter-free mode refuses to exceed configured request caps.
- LV006 Verify a promoted candidate can be rerun through a real agent
  Meta-Harness scenario.
