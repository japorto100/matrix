---
title: Control UI Research and Adoption Map
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 010
migrated_from:
  - specs/execution/exec-15-memory-control-ui.md
---

# Research and Adoption Map

## Source Systems

| Source | Adopted Pattern | Kept / Skipped |
|---|---|---|
| `main_docs/specs/architecture/FRONTEND_ARCHITECTURE.md` | shell/BFF/state-layer boundaries and frontend route ownership | reference source; frontend_merger SDD owns current task state |
| `main_docs/specs/data/DATA_ARCHITECTURE.md` | data-zone, data-product and storage-role framing for Control/File/Memory surfaces | reference source; backend ownership remains in feature owners |
| `main_docs/root/UNIFIED_INGESTION_LAYER.md` | ingestion surface boundaries and unstructured content routing | routed to ingestion/memory subfeatures |
| `main_docs/root/storage_layer.md` | persistence/signed URL/storage-layer context | used where Files/Storage surfaces depend on it |
| `control/control_surface/` | tab shell, RBAC/action classes, approval flows, audit pattern, BFF headers | Prisma stripped; storage/auth adjusted to matrix |
| `control/files_surface/` | files UI, viewers, upload/reindex patterns | adopted with package alignment |
| `control/storage/` | Go storage service, signed URLs, metadata store | mounted in Go appservice |
| `_ref/supermemory/packages/memory-graph/` | memory graph package | copied as source; only provenance graph, not Trading KG |
| `_ref/supermemory/apps/web/components/` | memories grid, modal/card/note/search UI patterns | backend/auth/onboarding skipped |
| `_ref/hindsight/` | memory backend source of truth | remains backend, not UI source |
| `paperwatcher/` | ingestion/retrieval/KG ideas | phased adoption, not all implemented |

## Lightweight Defaults

Control/memory surfaces must run on the target weak local machine without
surprise model downloads.

Defaults:

- deterministic embedder or vector-store mock allowed,
- KG pipeline disabled until explicitly enabled,
- extraction layout worker can return 503 skeleton,
- PromptGuard disabled unless explicitly enabled,
- heavy model download scripts are manual opt-in.

Verify:

- no HF/torch model download on normal dev startup,
- disabled heavy workers degrade explicitly,
- UI shows actionable state instead of crashing.

## Paperwatcher Adoption Summary

Already adopted or current:

- extractor base/pymupdf/chunking into ingestion,
- ingestion worker structure,
- hash-based reindex and chunk manifests.

Mapped for later:

- Docling/Marker/MinerU in extraction layout,
- Relik/GLiREL/GLiNER KG extraction,
- RAPTOR tree,
- ColPali visual PDF indexing,
- retrieval quality gate,
- falsification verifier,
- GraphRAG communities,
- conflict detector,
- subgraph pruner.

Skipped:

- academic search/download/storage layer,
- paper synthesis/deep research agents,
- framework-level ragbits adoption,
- duplicate LLM/vector abstractions already owned elsewhere.

## SDD Interpretation

This research stays in Feature 010 only where it affects UI/integration. Backend
retrieval/KG semantics move to Feature 012 when implemented.

## 2026-04-29 Z_ Follow-Up

The new Z_ material expands Control UI scope, but not as a monolith:

- `Z_Additional_For_Tool_Stuff.md` requires both a normal ToolRegistry
  catalog/policy view and an MCP gateway/catalog view. Normal builtin tool
  catalog metadata is owned by Feature 016 and exposed through `/control/tools`;
  external MCP descriptor/resource policy remains delegated to Feature 024.
  2026-04-29 static UI follow-up: `ToolsTab` renders builtin risk, approval
  and progressive-disclosure metadata; `McpTab` renders effective MCP catalog
  approval/risk/denial/visibility state.
- `Z_Semantik_layer and so on.md` requires semantic/metric definition
  inspection delegated to Feature 025.
- `Z_Hermes_Desktop_claw3d.md` supports an ops-room/observatory surface
  delegated to Feature 029.
- `Z_Tool_very interessting Quarkdown.md` supports report artifact inspection
  delegated to Feature 027.

Control UI should expose effective state from owning features. It should not
become the owner of MCP policy, semantic truth, report rendering or agent
runtime logic.
