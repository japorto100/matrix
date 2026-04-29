---
title: Agentic Report Publishing Quarkdown Live Verify
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 027
---

# Live Verify

- LV001 Build tiny Quarkdown fixture to HTML.
- LV002 Build same fixture to PDF if renderer/runtime supports it locally.
- LV003 Build same fixture to slides/plain text if supported.
- LV004 Generate a report manifest and verify checksums.
- LV005 Run report validator with a missing citation and verify failure.
- LV006 Run agent report-generation scenario from RAG/KG sources.
- LV007 Build generated report and inspect artifacts.
- LV008 Publish safe Matrix link/attachment to a dev room.
- LV009 Open report artifact from Control UI.
- LV009a Open `/control/reports` and verify manifest path, renderer, checksum,
  outputs, citations, validation failures and Matrix publication status render
  without executing a renderer.
- LV010 Run Meta-Harness report-grounding scenario.
- LV011 Verify renderer can be disabled and fallback path still returns
  structured markdown.
- LV012 Verify no provider-specific dependency exists in report generation.
