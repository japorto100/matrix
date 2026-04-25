---
title: Control UI Subfeatures
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 010
migrated_from:
  - specs/execution/exec-15-memory-control-ui.md
---

# Subfeatures

This file imports the actual slice model from `exec-15` into SDD form.

## Slice 0 — Foundation

Status: frontend done.

Scope:

- Next/React/Tailwind app foundation
- DM Sans + supermemory dark palette
- shadcn/ui component set
- Biome/TypeScript setup
- `GlobalTopBar`
- shell routes for Memory, Control and Files

Open:

- Visual smoke of all surfaces in current `frontend_merger` shell.

## Slice 1 — Files Vertical

Status: frontend + Go storage largely done; E2E pending.

Scope:

- Files tabs and multi-modal viewer
- PDF via `react-pdf`
- audio via `wavesurfer.js`
- video via `hls.js`
- upload via `react-dropzone`
- search via `fuse.js`
- Go storage layer and artifact handler
- SeaweedFS / S3-compatible backend
- signed URL upload/download
- reindex button and confirmation flow

Open:

- PDF upload E2E: upload -> SeaweedFS -> documents list -> preview.
- Audit event write path for file actions.
- Ensure frontend gateway default points to matrix Go appservice, not old main project port.

## Slice 2 — Content Ingestion

Status: frontend + backend write path described as wired, but devstack/E2E still pending.

Scope:

- AddMemoryModal with Note/Link/File/Bridge tabs
- NoteEditor, QuickNoteCard, HighlightsCard, FullscreenNoteModal
- ingestion worker on port 8098
- 4-venv architecture:
  - main agent runtime
  - lightweight ingestion
  - heavy extraction/layout skeleton
  - KG pipeline skeleton
- document/note/link/batch pipelines
- job tracking and status dashboard
- retry/reindex path

Open:

- Alembic upgrade in live Postgres.
- Devstack run.
- PDF/note/link ingestion E2E.
- Dedup/reindex proof.

## Slice 3 — Memory Browser

Status: frontend + backend wired in later slices; timeline/delete added.

Scope:

- EpisodesGrid
- EpisodeCard
- EpisodeFilterBar
- EpisodeDetailSheet
- MemoryHealthCards
- MemoryTimelineView
- delete episode action
- URL state via `nuqs`
- mock fallback when backend unavailable

Open:

- Prove `useEpisodes` and `useMemoryHealth` use real backend, not mocks.
- Verify >50 episodes and timeline performance.
- Verify delete + audit event.

## Slice 4 — KG Visualization

Status: frontend + backend wired; two graph concepts exist.

Scope:

- Episode-memory provenance graph from supermemory memory-graph
- Trading KG using React Flow
- six node types:
  - Stratagem
  - Regime
  - TransmissionChannel
  - Asset
  - Institution
  - BTEMarker
- six edge types:
  - causes
  - inhibits
  - activates
  - precedes
  - transmits
  - signals
- backend `/kg/graph` endpoint
- node/edge CRUD in `memory_engine/kg_store.py`

Open:

- Seed real KG data.
- Verify graph renders real backend nodes.
- Distinguish provenance graph mock shape from Trading KG backend shape.

## Slice 5 — Agent Configuration

Status: frontend + backend mostly wired; some limitations remain.

Scope:

- AgentsTab
- PermissionsTab
- SkillsTab
- SandboxTab
- ToolsTab
- role override patch/reset
- permission matrix cell patch/reset
- skill toggle request
- audit-backed tools/sandbox stats

Open:

- Allowed tools editor remains read-only unless implemented.
- Skills persistence belongs to Feature 015.
- GitHub skill import belongs to Feature 015.
- Sandbox action details belong to Feature 013.

## Slice 6 — System Observability

Status: frontend + backend wired; live stack proof pending.

Scope:

- SystemTab
- AuditTab
- SessionsTab
- McpTab
- A2aTab
- service health pings
- audit filters/export
- session list/kill
- MCP introspection
- A2A delegation log

Open:

- Live all-service health check.
- Session kill against real checkpointer state.
- Audit export filtered rows.
- MCP/A2A live state.

## Slice 7 — Two-Tier UI + Full Backend + Hash Reindex

Status: done at code level; devstack E2E pending.

Scope:

- User/Developer mode toggle
- OverviewTab
- SecurityTab
- ApiModelsTab
- mode-filtered ControlTopNav
- control route proxy through Go
- frontend BFF catch-all routes
- React Query hooks for control/memory
- hash-based incremental reindex
- Phase J code-review fixes
- Phase K code gap closures

Open:

- Phase I devstack E2E.
- Verify no mock fallback during live pass.

## Slice 8 — Agent Chat Integration

Status: planned/deferred.

Scope:

- use control/memory components from Agent Chat
- unify GlobalTopBar surfaces
- route BFFs consistently

Owner:

- Feature 007 for Agent Chat runtime.
- Feature 003 for shell/navigation.

## Slice 9 — Graphiti/Cognee Backend

Status: planned.

Scope:

- GraphitiRetriever
- Cognee integration
- Unified Search API

Owner:

- Feature 012 unless implemented purely as Control UI surface.

## Slice 10 — Computer Use + Artifacts

Status: partially built.

Scope:

- Sandpack preview
- SandboxArtifact
- Playwright/Pilot/WebMCP follow-up

Owner:

- Feature 013 for sandbox/security.
- Feature 008 for WebMCP.

## Slice 11 — Personal KB + World Model Surfaces

Status: planned.

Scope:

- Personal Knowledgebase surfaces
- Global World Model / Ops surfaces
- Context/degradation surfacing

Owner:

- Feature 012 for backend semantics.
- Feature 010 for UI integration verification.

