---
title: Control UI and Runtime Surfaces Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-26
feature_id: 010
migrated_from:
  - specs/execution/exec-15-memory-control-ui.md
  - specs/execution/exec-13-ui-kg-extensions.md
---

# Tasks

## Phase A — Migration

- [x] T001 Create SDD feature shell.
- [x] T002 Import exec-15 decisions into `decisions.md`.
- [x] T003 Import exec-15 slice model into `subfeatures.md`.
- [x] T004 Import research/adoption map into `research.md`.
- [x] T005 Import exact old verify IDs into `live-verify.md` where still active.
- [x] T006 Summarize built code state into `closeout.md`.

## Slice 0 — Foundation

- [x] T010 Static-verify shell route and top nav in current `frontend_merger`.
- T011 Browser-verify design tokens and layout are still aligned after
  merger.
- [x] T012 Ensure old standalone `control-ui/` assumptions are translated to
  `frontend_merger`.
- [x] T013 Document Control UI as inspection/admin/data-display surface, not an
  agent tool surface by default.
- T014 During live verify, flag every Control action that looks executable and
  route runtime semantics to the owning feature before it can become an agent
  tool.

## Slice 1 — Files Vertical

- T020 Verify files route/list renders.
- T021 Verify signed upload URL request.
- T022 Verify upload to SeaweedFS/S3-compatible store.
- T023 Verify uploaded file appears in files list.
- T024 Verify PDF preview through `react-pdf`.
- T025 Verify audio/video/image/data viewers where packages are installed.
- T026 Verify reindex confirmation flow and audit event.
- T027 Route media ingestion beyond files UI to research backlog or Feature 012.

## Slice 2 — Content Ingestion

- T030 Verify AddMemoryModal Note/Link/File/Bridge tabs.
- T031 Verify note ingestion path.
- T032 Verify link ingestion path.
- T033 Verify document ingestion path.
- T034 Verify ingestion status dashboard polling.
- T035 Verify retry failed job.
- T036 Verify dedup/reindex chunk hash manifest.
- T037 Confirm heavy layout/KG workers are disabled by default.

## Slice 3 — Memory Browser

- T040 Verify MemoryHealthCards use live backend.
- T041 Verify EpisodesGrid uses live backend.
- T042 Verify filters persist in URL.
- T043 Verify EpisodeDetailSheet content.
- T044 Verify delete episode flow and audit event.
- T045 Verify MemoryTimelineView performance with realistic count.
- T046 Remove or clearly label mock fallback during live verify.

## Slice 4 — KG Visualization

- T050 Verify `/kg/graph` backend endpoint.
- T051 Verify KG seed path.
- T052 Verify Trading KG renders backend nodes and edges.
- T053 Verify node-type filter.
- T054 Verify provenance graph state separately from Trading KG.
- T055 Route Graphiti/Cognee backend work to Feature 012 unless UI-only.

## Slice 5 — Agent Configuration

- T060 Verify AgentsTab role list.
- T061 Verify role edit patch and reset.
- T062 Verify PermissionsTab cell cycle and reset.
- T063 Verify SkillsTab toggle state and backend persistence/stub status.
- [x] T064 [done-static] Verify ToolsTab registry and import request state.
  - 2026-04-29: `/control/tools` now exposes builtin ToolRegistry catalog
    policy metadata: group, risk, approval mode, progressive-disclosure level
    and schema/description hashes.
- T065 Verify SandboxTab run list/detail state.
- T066 Route full skills semantics to Feature 015.
- T067 Route sandbox execution semantics to Feature 013.

## Slice 6 — System Observability

- T070 Live-verify SystemTab health for all configured services.
- T071 Live-verify AuditTab filters and export.
- T072 Live-verify SessionsTab list/detail/kill in dev mode.
- T073 Live-verify McpTab server/tool state.
- T074 Live-verify A2aTab delegation/AgentCard state.
- T075 Route observability backend gaps to Feature 014.

## Slice 7 — Two-Tier UI + Hash Reindex

- T080 Verify User Mode tab list.
- T081 Verify Developer Mode tab list.
- T082 Verify URL mode param overrides localStorage.
- T083 Verify hash reindex flow from files UI.
- [x] T084 Static-verify BFF catch-all route exists; live header/body/query
  preservation remains pending.
- T085 Verify no “coming soon” placeholders remain except documented
  deferred items.

## Slice 8+ Deferred Surfaces

- T090 Decide Agent Chat integration owner with Feature 007.
- T091 Decide Graphiti/Cognee backend scope with Feature 012.
- T092 Decide Computer Use / Artifacts scope with Features 008 and 013.
- T093 Decide Personal KB / World Model surfaces with Feature 012.
- [x] T094 [done-static] Add effective MCP catalog/risk/policy surface from Feature 024.
  - 2026-04-29: Control `McpTab` consumes the effective MCP catalog endpoint
    and renders approval, risk, denial and visibility state.
- [x] T094a [done-static] Add normal builtin tool catalog/risk/policy metadata
  from Feature 016/`Z_Additional_For_Tool_Stuff.md`.
- [x] T094b [done-static] Upgrade frontend ToolsTab as effective ToolRegistry
  inspector.
  - 2026-04-29: `ToolsTab` now shows enabled/guarded/high-risk/semantic summary
    cards, risk and group filters, group badges, provider metadata and last-seen
    timestamps. The fallback catalog includes Feature 025 `semantic_lookup`.
- [x] T095 [done-static] Add semantic catalog and metric/claim definition
  inspector from Feature 025.
  - 2026-04-29: `/control/semantic` renders the Feature 025 semantic catalog,
    validation state, alias collision count, KG/RAG term metadata, metric
    owner/scope/freshness/source refs and a read-only metric-plan inspector.
- [x] T096 [done-static] Add agent ops-room entrypoint from Feature 029: live
  sessions, tool state, approvals and replay.
  - 2026-04-29: `/control/ops` is available in Developer Mode and renders a
    dense 2D board from existing Sessions/Tools/Audit query surfaces with
    active/waiting/blocked/replay lanes, tool risk badges, blockers, audit link
    and Matrix handoff link. Live stream and Meta-Harness replay endpoints stay
    Feature 029 backend work.
- [x] T097 [done-static] Add report artifact list from Feature 027 with
  source/manifest links.
  - 2026-04-29: `/control/reports` renders a read-only report artifact index
    with manifest path, renderer/version, checksum, outputs, citations,
    validation failures and Matrix publication readiness. It uses the
    provider-agnostic Feature 027 contract and consumes `/api/v1/control/reports`
    when report manifests exist.

## Verify Gates

- Every Control UI tab has live data, actionable empty state or owning-feature gap.
- Every mock fallback is identified during live verify.
- All deferred slice work has a feature owner.
