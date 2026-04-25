---
title: Frontend Merger Shell Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 003
---

# Gates

- [x] Production build passes.
- [x] Typecheck/lint/test status is current.
- [ ] Playwright smoke covers key routes. Deferred to live/browser verify.
- [ ] `/matrix`, `/control`, `/files`, `/memory` render in local full stack.
  Deferred to live/browser verify.
- [x] Agent Chat is represented as global overlay/API surface plus Control
  agents tabs, not as a required top-level `/agent` page.
- [ ] Full stack smoke uses real env values, not config hints only. Deferred to
  live/browser verify.
- [x] Open v2 items are assigned to Feature 008/010/005 as appropriate.
- [x] Superseded merge docs are referenced only as history.

## Static Evidence

Checked on 2026-04-25:

- `bun run lint` -> PASS
- `bun run typecheck` -> PASS
- `bun run test` -> PASS, 7 test files / 37 tests
- `NEXT_TELEMETRY_DISABLED=1 bun run build` -> PASS with Next.js 16.2.2
  Turbopack

Build routes:

- `/`
- `/matrix`
- `/control/[[...tab]]`
- `/files/[[...tab]]`
- `/memory/[[...tab]]`
- Agent runtime APIs under `/api/agent/*`
