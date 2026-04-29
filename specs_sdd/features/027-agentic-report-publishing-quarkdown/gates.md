---
title: Agentic Report Publishing Quarkdown Gates
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 027
---

# Gates

- G001 Renderer choice is explicit; Quarkdown is not assumed until fixture
  builds pass.
- [x] G002 Report source, data and output have a manifest in the static
  frontend/backend artifact-list contract.
- [x] G003 Every factual section can cite source refs or mark unsupported content
  in the static report manifest validator.
- [x] G004 Build output is reproducible for the same inputs in the
  `markdown-fallback` renderer fixture.
- [x] G005 Renderer errors are structured and visible to agent and user in the
  static report tool validation result.
- [x] G006 Generated reports cannot execute arbitrary local code by default;
  `report_build` uses only `markdown-fallback` until Quarkdown is promoted.
- [x] G007 Matrix publication uses safe links/attachments, not raw embedded
  script in the static frontend artifact-list contract.
- [x] G008 Meta-Harness report scenario checks citations and unsupported claims
  through the provider-free `report-grounding` command.
- [x] G009 Report artifacts can be traced back to retrieval/KG inputs in the
  static frontend/backend artifact-list contract.
