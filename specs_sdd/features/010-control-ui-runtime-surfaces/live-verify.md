---
title: Control UI and Runtime Surfaces Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 010
migrated_from:
  - specs/execution/exec-15-memory-control-ui.md
---

# Live Verify

## 2026-04-29 Feature 024-029 Follow-Up

- Tools tab shows ToolRegistry policy summaries, filters and `semantic_lookup`.
- MCP tab shows Feature 024 effective policy/risk state.
- Semantic catalog inspector shows one metric, one KG-linked term and one
  ambiguity/conflict.
- `/control/semantic` opens from the Control nav and shows validation,
  owner/version/source refs, metric scopes and raw-SQL-disabled plan state.
- Ops room shows one live agent session and one Meta-Harness replay.
- `/control/ops?mode=dev` opens from Developer Mode and shows session board,
  tool timeline, blockers, audit link and Matrix handoff link.
- Report artifact list opens one generated report manifest from Feature 027.
- `/control/reports` renders report manifest, output, citation and Matrix
  publication status without invoking a renderer.

## Prerequisites

- Frontend shell running.
- Go appservice reachable.
- Python backend reachable.
- Postgres reachable.
- NATS reachable if bridge/state tabs need it.
- SeaweedFS/storage reachable if files tests are in scope.

## Foundation / Shell

- Open `/control`.
- Open `/memory`.
- Open `/files`.
- Navigate between surfaces via GlobalTopBar.
- Confirm no route crashes.

## User / Developer Mode

- `/control` defaults to User Mode.
- User Mode shows Overview, Agents, Permissions, Skills, Tools, Sessions, Security.
- Developer Mode shows System, API/Models, Sandbox, Audit, MCP, A2A in addition.
- `?mode=dev` opens Developer Mode.
- localStorage fallback persists mode when URL param absent.

## Files Vertical

- Files list renders.
- Upload intent creates signed URL.
- File upload succeeds.
- Uploaded file appears in list.
- PDF preview renders.
- Audio viewer renders when given audio file.
- Video viewer renders when given video file.
- Image viewer renders when given image.
- Reindex dialog requires correct confirmation.
- Reindex request sends confirm token.
- Reindex audit event appears.

## Content Ingestion

- AddMemoryModal opens.
- Note tab ingests note.
- Link tab ingests link.
- File tab ingests uploaded document.
- Bridge tab clearly marks non-active bridges as pending/deferred.
- IngestionStatusPage shows Total/Done/Running/Pending/Failed.
- Failed ingestion can be retried.
- Duplicate content produces dedup behavior or documented absence.

## Memory Browser

- MemoryHealthCards show episodic/KG/vector layer status.
- EpisodesGrid loads live episodes or healthy empty state.
- Filter bar changes URL state.
- Back/forward preserves filters.
- EpisodeDetailSheet opens and shows input/tool/output sections.
- Delete episode confirmation works.
- Delete invalidates grid/timeline.
- Timeline groups entries by day.
- Timeline handles realistic episode count.

## KG Visualization

- `/memory/kg` renders Trading KG.
- KG seed path creates nodes if empty.
- Backend `/kg/graph` returns node/edge counts.
- Type filter returns only requested node type.
- React Flow graph renders real nodes.
- `/memory/graph` provenance graph renders separately.
- Mock badge/fallback appears only when backend unavailable.

## Agent Configuration

- Agents tab shows six trading roles.
- Agent detail sheet opens.
- Edit mode patches `system_prompt`, `memory_access` and `approval_required`.
- Reset prompt/memory removes overlay.
- Permissions matrix renders 6x7 cells.
- Left-click cycles permission level.
- Right-click reset removes override.
- Skills toggle calls backend and shows persisted or pending status.
- Tools tab lists registry/tool schemas.
- Tools tab filters by type, risk and group without layout overflow.
- Tools tab shows `semantic_lookup` as group `semantic` when backend or fallback
  catalog includes it.
- Sandbox tab lists runs or healthy empty state.

## Observability / System

- System tab health checks all configured services.
- API/Models tab loads provider/model/routing/utility state.
- Spend dashboard shows data or explicit DB-required state.
- Audit tab loads events.
- Audit filters work.
- CSV export escapes commas/quotes/newlines.
- JSON export downloads filtered rows.
- Sessions tab shows active sessions or healthy empty state.
- Kill session hidden in User Mode.
- Kill session available in Developer Mode and writes audit event.
- MCP tab shows server/tool state.
- A2A tab shows delegation state or healthy empty state.
- Security tab shows posture and recent events.

## Mock-Fallback Guard

- For each tab, record whether data came from live backend or mock fallback.
- Any mock fallback in live verify becomes a follow-up task.

## 2026-04-30 Added Live Gates

- LV030 Open Control request/cache telemetry and verify counters, unknown fields
  and cache-break reasons from a real agent run.
- LV031 Trigger MCP/tool reload and verify confirm/impact display plus cached
  session invalidation/rebind result.
- LV032 Open runtime sessions view and verify active/stale/finished state plus
  pause/kill/status/replay actions.
- LV033 Open report artifacts list and verify manifest validation, citation
  readiness and originating session/turn refs where available.

## Result

pending
