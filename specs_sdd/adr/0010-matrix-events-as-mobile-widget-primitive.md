---
title: Matrix Events As Mobile Widget Primitive
status: proposed
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_ids:
  - 005
  - 008
  - 024
  - 030
---

# Context

Feature 030 added policy-gated Matrix widget parsing for `m.widget` and
`im.vector.modular.widgets`. During review we clarified that Element X
iOS/Android and FluffyChat should be treated as the primary mobile
compatibility target, not Element Web-style widget hosting.

Element X's public feature status lists "No Integrations / Widgets / Matrix
apps" for current iOS/Android Element X. FluffyChat has normal Matrix message,
media and room features, but no stable shared agent-widget catalog with
Element X. Therefore there is no mobile widget catalog to clone.

# Decision

Use Matrix events as the primitive equivalent of widgets for mobile-compatible
agent output.

For Matrix rooms:

- every agent "widget" must have a normal Matrix-event representation first:
  text summary, sanitized formatted body, code block, link, media/file
  attachment and provenance/audit refs where relevant;
- `m.widget` / `im.vector.modular.widgets` state events are optional metadata,
  not the primary user experience;
- the Matrix webclient follows the mobile-client intersection by default and
  renders widget events as passive, policy-labelled fallback cards;
- unsafe, unapproved, expired or unsupported widgets never execute in the
  Matrix timeline;
- MCP resource handoffs still pass through Feature 024 policy before any
  widget metadata is emitted.

For rich agent UI:

- MCP Apps, A2UI surfaces, code widgets, tool dashboards, approval forms and
  report viewers belong to the Agent Chat UI / generative UI surface owned by
  Feature 008 and related runtime features;
- provider-specific app SDK patterns may inform design, but Matrix runtime
  contracts remain provider-agnostic.

# Consequences

Feature 030 remains a Matrix compatibility and safety layer rather than a
first-party rich app platform. Feature 005 owns the mobile-safe rendering
primitives. Feature 008 owns rich agent surfaces.

Future work may add an explicitly opt-in experimental iframe host for local
web-only testing, but it must not be required for Element X or FluffyChat
compatibility and must not replace the Matrix-event fallback.

# References

- `Z_matrix_widgets_formulars_and so on.md`
- `Z_Additional_For_Tool_Stuff.md`
- `specs_sdd/features/030-matrix-widget-app-host/`
- `specs_sdd/features/008-agentic-ui-generative-ui-mcp/`
- Element X feature status: `https://github.com/element-hq/element-meta/issues/1915`
- Matrix Widget API package: `https://www.npmjs.com/package/matrix-widget-api`
