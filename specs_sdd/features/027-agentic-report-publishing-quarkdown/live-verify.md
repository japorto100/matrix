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
- LV004 [done-static-live-smoke] Generate a report manifest and verify checksums.
- LV005 [done-static-live-smoke] Run report validator with a missing citation
  and verify failure.
- LV005a Ask an agent to call `report_validate` on a missing-citation report
  and verify the structured failure reaches the chat/tool trace.
- LV006 Run agent report-generation scenario from RAG/KG sources.
- LV007 Build generated report and inspect artifacts.
- LV007a Ask an allowed role to call `report_build` and verify artifacts appear
  under `MATRIX_REPORT_ARTIFACT_DIR` without invoking Quarkdown.
- LV008 Publish safe Matrix link/attachment to a dev room.
- LV009 Open report artifact from Control UI.
- LV009a Open `/control/reports` and verify manifest path, renderer, checksum,
  outputs, citations, validation failures and Matrix publication status render
  without executing a renderer.
- LV009b Generate a report under `MATRIX_REPORT_ARTIFACT_DIR` and verify
  `/api/v1/control/reports` returns the manifest with validation status.
- LV010 [done-static-live-smoke] Run Meta-Harness report-grounding scenario.
  - 2026-04-29: provider-free static command exists; full live run through an
    agent chat trace remains tied to LV006/LV007a.
- LV011 Verify renderer can be disabled and fallback path still returns
  structured markdown.
- LV012 Verify no provider-specific dependency exists in report generation.
