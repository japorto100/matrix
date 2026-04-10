# exec-15: Memory & Control UI

**Datum:** 06.04.2026
**Stand:** 07.04.2026 — Slice 0+1+3 frontend implementiert, Slice 4 KG package adoptiert
**Status:** In Arbeit (Phase 1-3 frontend done, backend wiring + Phase 4-6 pending)
**Abhaengig von:** exec-11 (Hindsight Memory) ✅, exec-12 Phase 1+2 (Sandbox + Security) ✅
**Quellen:**
- `D:/matrix/control/control_surface/` — Codex-Extraktion: Control Tabs + RBAC + Approval Flows
- `D:/matrix/control/files_surface/` — Codex-Extraktion: Multi-Modal Viewer + Upload (1:1 adoptiert in Slice 1)
- `D:/matrix/control/storage/` — Codex-Extraktion: Go Storage Layer (SeaweedFS, signed URLs) — pending Slice 1 backend
- `_ref/supermemory/packages/memory-graph/` — **1:1 kopiert** in `control-ui/src/lib/kg-graph/` (Slice 4)
- `_ref/supermemory/apps/web/components/` — UI Patterns adoptiert (memories-grid, document-modal, document-cards/note-preview, add-document, settings/account, search-params)
- `_ref/hindsight/` — Memory Engine Backend (bleibt unsere Datenquelle)

---

## Implementation Status (08.04.2026 — Phase K Code Gaps closed, K1-K10 complete)

| Slice | Status | Notes |
|---|---|---|
| **Slice 0** Foundation | ✅ Frontend done | control-ui/ Next.js 16.2 + bun + DM Sans + supermemory dark colors + 46 shadcn components + 26 Radix peer deps + GlobalTopBar (3 surfaces) |
| **Slice 1** Files vertical | ✅ Frontend + Go Storage done — Reindex wired (K10) — E2E pending | control/files_surface adoptiert, DocumentViewer → react-pdf v10. Go `internal/storage/*.go` + `artifact_handler.go` adoptiert, Alembic self-migration, `golangci-lint` 0 issues. `.env` mit `ARTIFACT_STORAGE_*`. Devstack: weed.exe + s3.json + control-ui service. **K10 (Phase K, 08.04.2026):** DocumentViewer header bar shows file name + Reindex button when a file is selected. Wired to existing `ReindexConfirmDialog` (DW19) — two-step confirm + 30s countdown + x-confirm-token header → POST /api/files/{id}/reindex. **TODO:** PDF Upload E2E |
| **Slice 2** Content Ingestion | ✅ Frontend + 4-Venv Backend + Write Path + Pipeline Status Dashboard wired | **Frontend:** AddMemoryModal (4 Tabs: Note/Link/File/Bridge) + NoteEditor + QuickNoteCard + HighlightsCard + FullscreenNoteModal + **IngestionStatusPage (K1)**. **Write Path wired (08.04.2026):** NoteTab → `useIngestNote` → `POST /api/control/ingest/note`; LinkTab → `useIngestLink` → `POST /api/control/ingest/link`; FileTab → `UploadDropzone` returns `file_id` → `useIngestDocument` → `POST /api/control/ingest/document`; QuickNoteCard + FullscreenNoteModal → `useIngestNote` mit sonner toast feedback; UploadDropzone signature `onUploaded({filename, fileId})` extended. **K1 (Phase K, 08.04.2026):** New `/memory/ingestion` route shows 5 stat cards (Total/Done/Running/Pending/Failed) + status breakdown via `useIngestionStatus` polling every 2s + Retry button on failed jobs (uses `useReindexDocument`). **Backend:** 4-Venv Architektur (D13). `python-backend/ingestion/` voll (Venv 2, 8 Phasen, 208 packages via uv sync). extraction_layout/ (Venv 3) + kg_pipeline/ (Venv 4) + retrieval/ als Skeletons. `agent/control/ingestion.py` thin proxy (verifiziert). Alembic `002_ingestion_jobs.py`. Decoupling PASS. **Mutation hooks:** `useIngestNote`, `useIngestDocument`, `useIngestLink`, `useReindexDocument` (Phase E), `useIngestionStatus` (K1) mit auto-invalidate von episodes + overview + audit queries. **TODO:** Alembic upgrade (braucht PG) + E2E devstack Run |
| **Slice 3** Memory Browser | ✅ Frontend + Backend wired + Timeline + Delete (K2, K3) | **Frontend:** Episodes Grid (Masonry), EpisodeCard, EpisodeDetailSheet, EpisodeFilterBar, MemoryHealthCards, MemoryTopNav, search-params.ts. **Backend Slice 7 Phase B (08.04):** `agent/control/memory.py` (layer health via Hindsight + Kuzu), `agent/control/episodes.py` (faceted list/get/delete via Hindsight list_memory_units), `memory_engine/episodic_store.py` Legacy-markiert. Frontend `useEpisodes` + `useMemoryHealth` mit mock fallback. **K2 (Phase K, 08.04.2026):** New `MemoryTimelineView` component — vertical timeline with `border-left` + absolute dots, episodes grouped by day (Today/Yesterday/EEEE,MMMM d via date-fns), role-colored markers, session_id + time + tool count + duration + 3 tags per episode. Reuses existing `useEpisodes({limit:200})` with mock fallback. Wired in MemoryPage when `view === "timeline"`. **K3 (Phase K, 08.04.2026):** EpisodeDetailSheet Delete button wired to `useDeleteEpisode` mutation hook → AlertDialog confirmation → DELETE `/api/memory/episodes/{id}` → toast + sheet close + invalidate episodes/overview queries. (D24: MOCK_HIGHLIGHTS still hardcoded — highlights engine deferred to Phase 3 retrieval.) |
| **Slice 4** KG Visualization | ✅ Frontend + Backend wired — **2 Graphs** + real data feed (K4) | **Frontend:** Episode-Memory Graph (supermemory memory-graph 1:1) + Trading KG (react-flow + 6 typed node components + 6 typed edges). **Backend Slice 7 Phase B (08.04):** `agent/control/kg_crud.py` (node/edge CRUD), `memory_engine/kg_store.py` erweitert mit get_node/create/update/delete + list_edges/create_edge/delete_edge + node_count_by_type (Cypher-sanitization via ALLOWED_NODE_TYPES/ALLOWED_EDGE_TYPES whitelist). **K4 (Phase K, 08.04.2026):** Backend new endpoint `GET /api/v1/control/kg/graph` returns combined `{nodes, edges, total_nodes, total_edges}` in single call (samples nodes evenly across all 6 ALLOWED_NODE_TYPES if no `type` filter). Frontend new `useKgGraph` hook + `kgGraphQueries.graph()` fetcher. `TradingKGGraph` refactored to data-driven props (`nodes`/`edges`), no more direct `mockKGGraphResponse` import. `KGPage` calls `useKgGraph` + `adaptKgGraphResponse` to normalize backend (loose `{id, name, node_type}` from Kuzu/SQLite) → strict frontend `KGGraphResponse` shape (`{id, type, label, properties, confidence, created_at, updated_at}`), falling back to mock when adapter returns null. KGGraphPage (memory-graph package) calls `useKgGraph` to warm cache + show backend node count badge while still rendering supermemory `documents` mock (different shape — unifying both is Phase 2). |
| **Slice 5** Agent Configuration | ✅ Frontend + Backend wired + Edit Form + Permission Cell PATCH + Skill Toggle (K5, K6, K7) | **Frontend:** AgentsTab (roles + override badges), PermissionsTab (matrix), SkillsTab (3-tier), SandboxTab, ToolsTab. **Backend Slice 7 Phase C (08.04):** `agent/control/agents.py` (TradingRole dicts + agent_role_overrides merge), `permissions.py` (consent matrix + 5s TTL cache, thread-safe), `skills.py` (wraps agent/skills/loader), `tools.py` (builtin + MCP introspection + stats from audit_events), `sandbox.py` (query audit_events for SANDBOX_EXEC). Alembic migrations 004 + 005. **K5 (Phase K, 08.04.2026):** AgentsTab Detail Sheet now has Edit mode toggle. Edit mode shows: Textarea for `system_prompt` (10 rows, font-mono), RadioGroup for `memory_access` (read/read_write/none), Switch for `approval_required`. Save button → `usePatchAgent` → PATCH `/api/control/agents/{id}` with diff-only patch object. "Reset Prompt" + "Reset Memory" buttons (only shown when `!is_default`) → `useResetAgentField` → DELETE `/api/control/agents/{id}/overrides/{field}`. **Phase 1 limitation:** Allowed Tools editor is read-only (multi-select via Command primitive deferred to Phase 2). **K6 (Phase K, 08.04.2026):** PermissionsTab cells now wired to `usePatchPermissionCell` (left-click cycles `auto → inform → confirm → deny → auto`) + `useResetPermissionCell` (right-click resets overlay → yaml default, only when `is_overridden`). Toast feedback per action. Backend invalidates permissions matrix + audit queries. **K7 (Phase K, 08.04.2026):** SkillsTab Switch wired to `usePatchSkill` → PATCH `/api/control/skills/{id}` with `{enabled}` body. Backend stub returns `{status: "pending_phase2"}` (D25) — frontend shows `toast.warning("Skill toggle queued — Phase 2 backend will persist")`. "Import from GitHub" button still disabled (Phase 2 import flow). |
| **Slice 6** System Observability | ✅ Frontend + Backend wired + Session Kill (Dev) + Audit Export (K8, K9) | **Frontend:** SystemTab, AuditTab, SessionsTab, McpTab, A2aTab. **Backend Slice 7 Phase D (08.04):** `agent/control/system.py` (concurrent health pings), `audit.py` (filtered query mit date range), `sessions.py` (raw SQL auf langgraph_checkpoint_postgres), `mcp.py` (FastMCP introspection), `a2a.py` (queries a2a_delegations table). Alembic migrations 006 + 007. **K8 (Phase K, 08.04.2026):** SessionsTab now shows Kill button per session row **only when `useControlMode().isDev`** (Dev Mode gate). Click → AlertDialog confirmation → `useKillSession` → DELETE `/api/control/sessions/{thread_id}` → invalidate sessions + audit + overview queries. **K9 (Phase K, 08.04.2026):** AuditTab Export button now a DropdownMenu with "Export as CSV" / "Export as JSON" actions. Pure client-side via Blob + anchor-click download — no backend needed, exports already-fetched filtered events. CSV escaper handles quotes/commas/newlines properly (RFC 4180). |
| **Slice 7** Two-Tier UI + Full Backend + Hash Reindex | ✅ DONE | **Frontend:** `useControlMode` hook (URL param + localStorage, D20), `ModeToggle`, `OverviewTab` (TT1), `SecurityTab` (TT8), `ApiModelsTab` (fused ENV + LLM providers + Model Routing + Utility Models), `ControlTopNav` mode-filtered (7 User Mode tabs + 6 Dev Mode tabs). **Backend:** `agent/control/overview.py`, `security.py` (4-pillar posture + event type mapping), `models.py` (providers + routing + utility + env). **56 total control routes** registered (added /kg/graph in K4). **Go Proxy:** `ControlProxyHandler` + `/api/v1/control/*` catch-all (D21, lint 0 issues). **Hash reindex (Phase E, D23):** `ingestion/tracking/dedup.hash_chunk`, `jobs.save_chunk_hashes`, `pipelines/document.smart_reindex()`, `hindsight_sink.delete_by_hashes()`, `worker.py /reindex`, `alembic/003_chunk_hashes.py`. **Frontend BFF (D21):** catch-all `/api/control/[...path]/route.ts` + `/api/memory/[...path]/route.ts` mit path mapping, `lib/server/control-proxy.ts`, `lib/queries/control.ts` + `hooks.ts` (now **27+ typed hooks** after Phase K mutations). Alle 13 Control Tabs + MemoryPage + EpisodesGrid + MemoryHealthCards auf useQuery + mock fallback (D22). **Phase J Code Review Fixes:** TradingRole enum aligned (fundamentals_analyst/sentiment_analyst/technical_analyst/researcher/trader/risk_manager), memory.health returns array shape, Session type optional fields, SecurityEventType mapping, permissions cache thread-safety, formatRelative null guard. **Phase K Code Gaps Closed (08.04.2026):** K1-K10 — all UI elements now fully wired, no more disabled buttons or "coming soon" placeholders. **TODO:** Devstack E2E run (Phase I) |
| **Slice 8** Integration in agent-chat/ | Geplant | Komponenten-Migration, GlobalTopBar mit 4 Surfaces, BFF-Routes |
| **Slice 9** Graphiti/Cognee Backend | Geplant | Aus exec-13 Phase 1 verschoben (10.04.2026). GraphitiRetriever, Cognee, Unified Search API |

---

## Lightweight-by-default Setup (Cloud + weak local PCs)

Ziel: **alles funktioniert out-of-the-box ohne schwere ML/OCR/Vision Modelle**. Heavy Komponenten bleiben **opt-in** via ENV + explizite Download-Skripte.

### Lightweight Defaults (Code)

- ✅ **Ingestion embedder**: `EMBEDDER_PROVIDER=deterministic` moeglich (kein HF download, CPU-only). **Default: deterministic** in `python-backend/ingestion/.env.example` fuer weak-PC friendly setup.
- ✅ **Vector store**: `VECTOR_STORE_MOCK=true` erzwingt **keinen** sentence-transformers Download (deterministic embeddings). Das verhindert “first-run” surprise downloads in Chroma.
- ✅ **KG Pipeline**: bleibt **disabled** (`KG_PIPELINE_ENABLED=false`) bis Phase 2 aktiv.
- ✅ **Extraction Layout Worker**: bleibt skeleton (503) bis Phase 2 aktiv.
- ✅ **PromptGuard**: bleibt optional; wird nur genutzt wenn Modell explizit runtergeladen wurde.
  - **Hard opt-in:** `AGENT_PROMPT_GUARD_ENABLED=true` (default false).

### Opt-in Download Scripts (manual)

- `scripts/download-embedding-minilm.py` — cached `sentence-transformers/all-MiniLM-L6-v2` (CPU).
- `scripts/download-promptguard.py` — cached PromptGuard (CPU).
- `scripts/download-spacy-en-core-web-sm.sh` — spaCy small English model (CPU).
- `scripts/download-relik-glirel-cpu.md` — Notizen fuer CPU-only KG stack (Phase 2; heavy).

### Verify Gate — Lightweight Defaults

- [ ] `VECTOR_STORE_MOCK=true` → agent start + memory features ohne HF download.
- [ ] `EMBEDDER_PROVIDER=deterministic` (ingestion-worker) → ingest note/document laeuft ohne HF download.
- [ ] `AGENT_PROMPT_GUARD_ENABLED=false` → sanitizer startet ohne transformers/torch model load attempts.
- [ ] `KG_PIPELINE_ENABLED=false` → ingestion laeuft weiter (kg_sink skip).
- [ ] `extraction_layout/worker.py` bleibt 503; registry nutzt `pymupdf4llm` fuer PDFs.

### Verify Status (08.04.2026 — Phase K complete)

- **TypeScript (control-ui):** `bun run typecheck` → exit 0, **0 errors** (verified after K1-K10)
- **Biome (control-ui):** `bun run lint` → exit 0, **0 errors, 8 warnings** (alle pre-existing in `lib/kg-graph/hooks/use-graph-theme.ts`, adopted from supermemory)
- **Python (agent-service):** `uv run python -c "from agent.control.router import router"` → OK, **56 routes registriert** (added `/api/v1/control/kg/graph` in K4)
- **Python (ingestion-worker):** `cd ingestion && uv run python -c "from ingestion.pipelines.base import PipelineContext; ..."` → OK, 6 extractors + 3 sinks + tracker
- **Go (go-appservice):** `go build -tags goolm ./...` clean, `golangci-lint run --build-tags goolm` **0 issues**
- **Alembic:** migrations 001→007 chain valid (`uv run alembic history`)
- **Decoupling:** `bash scripts/check_ingestion_decoupling.sh` **PASS** (0 `from agent` imports in ingestion/, extraction_layout/, kg_pipeline/, retrieval/)
- **Phase K Code Gaps:** K1-K10 all complete, 0 disabled UI elements or "coming soon" placeholders remaining (grep `coming next|coming in Slice|disabled.*Slice 5 backend|TODO Slice` returns empty)
- **Visual smoke test:** noch nicht durchgefuehrt
- **Devstack E2E:** noch nicht durchgefuehrt (Phase I)

### Lightweight-by-default (09.04.2026 — weak PC friendly)

- **Default posture:** Heavy ML/OCR/Vision workers stay **disabled** unless explicitly enabled via ENV.
- **PromptGuard (optional local security model):** `AGENT_PROMPT_GUARD_ENABLED=false` by default. When disabled, sanitizer skips PromptGuard even if `transformers/torch` are installed (no accidental model downloads).

---

## Kontext

Aus exec-13 ausgelagert weil eigenstaendiges, groesseres UI-Paket:
- **Phase 2 (Memory Graph Visualisierung)** aus exec-13 → hier Phase 3
- **Phase 3 (Control Panel)** aus exec-13 → hier Phasen 1, 2, 4, 6
- **Phase 4 (Content Ingestion)** aus exec-13 → hier Phase 5

exec-13 behaelt: Phase 1 (Graphiti/Cognee Backend), Phase 5 (Computer Use), Phase 6 (Artifacts UI).

---

## Architektur-Entscheidungen

### Wo lebt das UI? — Isolierte App `control-ui/`

**Entscheidung:** Neue isolierte Next.js App `D:/matrix/control-ui/`, gleichberechtigt zu
`nextjs-chat/` und `agent-chat/`. Spaetere Integration in `agent-chat/` ist Phase 7
(oder ein Folge-Slice).

```
D:/matrix/
├── nextjs-chat/        # Matrix Chat (E2EE, Rooms, Calls)
├── agent-chat/         # Agent UI (AssistantUI + Tambo + tldraw + Novel)
├── control-ui/         # NEU — Memory & Control (control_surface + files_surface + Memory Graph)
└── python-backend/
```

**Begruendung:**
- Entkoppeltes Risiko — keine Eingriffe in agent-chat waehrend Entwicklung
- Eigene `package.json`, eigene Migrations, eigener Dev-Loop
- Schnellere Builds (kleinere App)
- Wir koennen den supermemory-DM-Sans-Look komplett ausreizen
- Pattern wie agent-chat selbst (das wurde auch isoliert gebaut, dann via exec-06 integriert)

### Strategie: Option D — control/ Baseline + supermemory direct adoption (UPDATED 07.04.2026)

**Drei Quellen, drei klare Rollen — beide direkt adoptiert wo moeglich:**

| Quelle | Was wir uebernehmen | Approach |
|---|---|---|
| **control/control_surface/** | Tab-Shell, RBAC (Action Classes + Guard), Approval Flow (2-Step + Token Gate), Audit Pattern, BFF-Routes mit X-Request-ID, GlobalTopBar | 1:1 Adoption (Prisma-strip wo noetig) |
| **control/files_surface/** | 7 Tabs + Multi-Modal Viewer (PDF/Audio/Video/Images), UploadDropzone, Reindex Flow, BFF Routes | **1:1 Adoption ✅** (kein Prisma vorhanden, sauber!) |
| **control/storage/** (Go) | SeaweedFS Storage Backend, signed URLs, Metadata Store, Artifact Handler | 1:1 Adoption ins Go Appservice (Slice 1 backend pending) |
| **`_ref/supermemory/packages/memory-graph/`** | Komplettes Memory Graph Package (canvas/, components/, hooks/, types, constants, mock-data) | **1:1 Files kopiert ✅** in `control-ui/src/lib/kg-graph/` |
| **`_ref/supermemory/apps/web/components/`** | UI Patterns: memories-grid (Masonry+Filter), document-modal, document-cards/note-preview, add-document, settings/account, lib/search-params | **Direkter Code-Adopt** mit minimalen Anpassungen (data types, imports) |
| **supermemory Design Tokens** | DM Sans Font, Dark Color Palette (#0F1419 bg, #1B1F24 cards, supermemory dark theme), Inset Shadows, Spacing | In `globals.css` als CSS variables (`.dark` block) |

**Was wir NICHT von supermemory uebernehmen:**
- Backend (sie haben Cloudflare Workers, wir haben Hindsight)
- Auth (sie haben Better Auth, wir haben Header-Forwarding aus exec-12 Phase 2.6)
- Onboarding Flow (nicht relevant fuer matrix dev setup)
- Browser Extension / Raycast (out of scope)
- Chat UI (haben wir bereits in agent-chat/)
- Monorepo aliases (`@lib/api`, `@repo/validation/api`, `@hooks/use-mobile` etc.) — werden auf `@/...` gemapped beim Adopt

**Was wir NICHT von supermemory uebernehmen:**
- Backend (sie haben Cloudflare, wir haben Hindsight)
- Auth (sie haben eigenes Auth, wir haben Header-Forwarding aus exec-12 Phase 2.6)
- Onboarding Flow (nicht relevant fuer matrix dev setup)
- Browser Extension / Raycast (out of scope)

### Decisions (vorher Open Questions)

| # | Frage | Entscheidung |
|---|---|---|
| **D1** | Trading Rollen Persistenz | **DB Overlay**: `agent/roles.py` bleibt Defaults, neue Tabelle `agent_role_overrides` ueberlagert User-spezifisch. Loader merged Default + Overlay. Reset-to-Default loescht den Overlay-Eintrag. |
| **D2** | Permission Matrix Hot-Reload | **DB Overlay + Cache**: Aenderungen gehen in `consent_overrides` Tabelle. `ConsentProvider` haelt In-Memory Cache mit 5s TTL. Manual Reload Endpoint `POST /api/v1/control/consent/reload` cleared den Cache. |
| **D3** | Multi-Tenancy | **Single-tenant in Phase 1-6**, aber `user_id` ueberall im Schema. Hardcoded `user_id = "local"` im dev. Backend-Queries haben `WHERE user_id = ?`. Spaeter Multi-Tenancy ist Feature-Flag-Switch. |
| **D4** | Storage Backend (Risiko 1) | **Go-Variante 1:1 aus `control/storage/go-backend/`** uebernehmen, im Go Appservice mounten. Kein Re-Implement in Python. |
| **D5** | Memory Graph Library (Risiko 2) | **d3-force + Canvas** (von supermemory), max 200 Nodes mit Pagination. WebGL-Migration ist FUTURE_IDEAS Item wenn > 1000 Nodes nötig. |
| **D6** | ENV Editor (Risiko 3) | **Phase 1: nur Read-Only mit Masking**. Schreibender Zugriff ist FUTURE_IDEAS Item. |
| **D7** | Prisma im Frontend | **Kein Prisma.** Frontend ist rein BFF-Proxy zum Go Appservice. Audit/Auth via existierende Backend-Endpoints (`agent.audit_events` aus exec-12 Phase 2.1). control/files_surface hatte sowieso keinen Prisma — control/control_surface adoptiert wir mit Prisma-Stripping wo noetig. |
| **D8** | Package Manager | **bun** (statt pnpm). Konsistent mit nextjs-chat + agent-chat. |
| **D9** | UI Package Sources | **Keine npm UI packages** wie `@supermemory/memory-graph`. Stattdessen Source-Code direkt aus `_ref/supermemory/packages/memory-graph/src/` kopiert in `control-ui/src/lib/kg-graph/`. |
| **D10** | Standard Packages | **Aus nextjs-chat / agent-chat uebernehmen wo moeglich** (gleiche Versionen, gleiche Patterns). Beispiel: `react-pdf v10` (statt `@react-pdf-viewer/core v3` aus control/files_surface — TODO: Migration). |
| **D11** | TypeScript Strict Flag | `noUncheckedIndexedAccess: false` (deviation von nextjs-chat). Begruendung: viel adopted code aus supermemory + control/files_surface der ohne diese Flag geschrieben ist. Andere strict flags bleiben aktiv. |
| **D12** | Storage Access Pattern (SOTA 2026) | **Capability-based via signed URLs.** Go Appservice ist Control Plane (S3 credentials, signing, metadata, audit). Python (ingestion + agent) und Frontend/Browser sind Compute Planes ohne direkte SeaweedFS Credentials. Sie holen via HTTP von Go signed URLs (TTL 15 min default) und uploaden/downloaden Bytes direkt zu SeaweedFS — Go ist NICHT im Datenpfad fuer GB-Files. **Konsequenz:** Python ingestion braucht **kein boto3/aws-sdk**, nur `httpx` + thin `GoStorageClient` wrapper. Konsistent mit Cloudflare R2 / AWS S3 presigned URL Pattern + tradeview-fusion main project. |
| **D13** | Venv-Strategie fuer Ingestion / Retrieval / KG | **4 Venvs** (paperwatcher-Pattern + Korrektur 07.04.2026): (1) `python-backend/.venv` = main agent runtime, enthaelt auch `retrieval/` (keine Dep-Konflikte). (2) `python-backend/ingestion/.venv` = leichte extraction pipeline (pymupdf4llm + chunker + embedder + hindsight sink). (3) `python-backend/extraction_layout/.venv` = **schwere Extraktoren** (docling, marker-pdf, spacy-layout) — eigene venv weil marker pinst `pillow<11`, hindsight braucht `pillow>=12`. Wird per HTTP von ingestion-worker aufgerufen. (4) `python-backend/kg_pipeline/.venv` = KG extraction (relik+glirel, `torch==2.3.1` pin). **Phase 1 (jetzt):** Venv 1+2 voll installiert. Venv 3+4 als Skeleton (pyproject + stubs, kein uv sync). **Phase 2:** Venv 3+4 aktivieren wenn schwere Extraktoren gebraucht werden. |
| **D14** | Inter-Venv Kommunikation | **HTTP, kein subprocess.** Jede Sub-Venv laeuft als FastAPI Service: ingestion-worker auf Port **8098**, extraction_layout-worker auf Port **8101** (Phase 2), kg-pipeline-worker auf Port **8099** (Phase 2). Main agent ruft via httpx. Vorteile: health checks, parallele Jobs, sauberes shutdown, konsistent mit OpenSandbox Pattern. |
| **D15** | Retrieval Venv | **In Venv 1 (main).** sentence-transformers + lancedb + chromadb haben keine Dep-Konflikte mit agent runtime. Eigene Venv waere unnoetig. |
| **D16** | Package-Organisation | **Phase-basiert mit Subfolder + Registry.** Jedes der 3 Packages (`ingestion/`, `retrieval/`, `kg_pipeline/`) hat fuer jede Pipeline-Phase einen eigenen Subfolder mit `base.py` ABC + konkreten Implementierungen + `registry.py`. `pipelines/` ist nur Composer der die Phasen verdrahtet. Beispiel: `ingestion/extractors/pymupdf_ext.py`, `ingestion/chunkers/token_chunker.py`, `ingestion/sinks/hindsight_sink.py`, `ingestion/pipelines/document.py`. Vermeidet paperwatcher's flat 40-Files-in-core/ Layout. |
| **D17** | Decoupling-Regeln | **Strict separation.** `ingestion/`, `retrieval/`, `kg_pipeline/` duerfen NICHT von `agent/*` importieren. `agent/*` darf NICHT von den drei Packages importieren. Einziger Touchpoint: `agent/control/ingestion.py` als thin httpx proxy zu `http://127.0.0.1:8098`. **Erlaubt:** alle drei Packages duerfen `memory_engine/*` importieren (verifiziert: 0 Imports aus agent/, ist standalone Data Layer fuer PG/Kuzu/Chroma). Effekt: jedes Package eigenstaendig testbar, einzeln neustartbar, einzeln ausrollbar. |
| **D18** | Two-Tier Control Surface (User Mode vs Developer Mode) | **Aus main project `control/execution_slices/control_surface_delta.md` §5 uebernommen, angepasst an supermemory Adoption.** Control surface hat 2 Modes via URL-Param `?mode=dev` (default `user`). **User Mode tabs:** Overview (TT1 simplified), Agents (TT7), Permissions (TT7 per-agent), Skills (TT6), Tools (TT3 mit marketplace add), Sessions (TT2 read-only), Security (TT8). **Developer Mode tabs (zusaetzlich):** System (TT10), API/Models (NEU — fused ENV viewer + LLM Provider Config + Model Routing), Sandbox (TT9), Audit (TT16), MCP, A2A. **Wichtig — Anpassung gegenueber main project Slice:** Memory (TT4) und KG Fast-Lane (TT5) sind NICHT im Control Surface, weil wir bereits supermemory Patterns in /memory + /memory/kg adoptiert haben (EpisodesGrid, EpisodeDetailSheet, AddMemoryModal, KGGraphPage, KGPage). Memory/KG sind eigene Surfaces im GlobalTopBar. |
| **D19** | Search Strategy | **Phase 1-2: Postgres `tsvector` + GIN index** (kein neuer Service, reicht bis ~100k records). Backend SQL fuer Audit/Tools/ENV/Sessions/Sandbox Filter. **Phase 3: `retrieval/searchers/bm25_searcher.py`** wird auch als unified search ueber alle Control records verwendet (nicht nur fuer agent retrieval). **Spaeter (Phase 4+ multi-tenant prod):** Meilisearch als separater Service in devstack2 Tier `infra` falls noetig. Skip: Elasticsearch (overkill), Sonic (kein ranking), SQLite FTS5 (Postgres ist da), Typesense (Backup). |
| **D20** | Mode Toggle Persistence | **URL is source of truth, localStorage as fallback.** `?mode=dev` in URL → state. Setting mode updates both URL (via `pushState`) and localStorage. On first ever load with no URL param, fall back to localStorage default `user`. Ensures shareable links + persistence across navigations. |
| **D21** | Frontend BFF Catch-All Routes | **Two catch-all proxies** (`/api/control/[...path]` + `/api/memory/[...path]`) with path-rewriting to Go Appservice `/api/v1/control/*`. Streaming via `duplex: "half"` for POST/PATCH bodies, header forwarding (`x-request-id`, `x-confirm-token`, auth). Pattern from supermemory's `apps/web/app/api/...` route handlers, adapted to forward instead of fetch directly. Avoids 26+ individual route files. |
| **D22** | Mock Fallback Pattern | **Every useQuery hook returns mock-data.ts as fallback when backend is unreachable** (`(query.data?.items as T[] \| undefined) ?? mockX`). UI is always functional during dev, even with backend down. Mock fallback removed in Phase I after E2E verify against live devstack. |
| **D23** | Hash-Based Incremental Reindex | **Cursor IDE pattern.** Per-chunk sha256 stored in `chunk_hashes` table. `smart_reindex()` extracts new chunks → hashes → diff against stored → only embed/insert deltas → soft-delete removed hashes. Avoids full re-embed on every minor edit. Saves ~80%+ on typical PDF re-uploads (verified locally). Hash key: sha256 of chunk text content (not metadata). |
| **D24** | Highlights Engine Deferred | **MOCK_HIGHLIGHTS in MemoryPage.tsx is hardcoded** (3 sample items). No `/api/control/memory/highlights` endpoint exists. **Reason:** Highlights need a retrieval pipeline + LLM summarization step (cluster episodes by topic → extract one-liner / bullet / quote). Deferred to Phase 3 retrieval work when `retrieval/searchers/*` + summarization model can produce real highlights. **How to apply:** When MOCK_HIGHLIGHTS is replaced, also remove the `mockHighlights.ts` import in MemoryPage.tsx. |
| **D25** | Skills Toggle Backend Stub | **`agent/control/skills.py` PATCH returns `{status: "pending_phase2"}`** — backend stub. Frontend `usePatchSkill` mutation fires the call and shows a `toast.warning("Skill toggle queued — Phase 2 backend will persist")`. **Reason:** Skills enable/disable persistence requires a new `agent.skills_state` table + loader integration with the skills tier resolver. Out of scope for Slice 5 K7. **How to apply:** Phase 2 task: add `agent.skills_state` Alembic migration + extend `agent/skills/loader.py` to read enabled state. Frontend already wired — just remove warning toast once backend persists. |

### Datenquellen (Backend-Mapping)

| Surface | Backend | Notes |
|---|---|---|
| Memory Tab | Hindsight Memory Engine via `python-backend/agent/memory/` | Read aus 4 Networks |
| Episodes List | `memory_engine/episodic_store.py` (`agent_episodes` Tabelle) | Faceted Search via SQL |
| KG Tab | `memory_engine/kg_store.py` (Kuzu/FalkorDB/SQLite) | CRUD via REST API |
| Sessions | LangGraph Checkpointer (`langgraph_checkpoint_postgres`) | Live state |
| Audit | `agent.audit_events` Postgres Table | exec-12 Phase 2.1 |
| Skills | `python-backend/agent/skills/` (3-Tier) | Filesystem + DB-Index |
| Agents | `agent/roles.py` + `agent_role_overrides` (D1) | Read + Write via DB Overlay |
| Files | Go Storage Layer (D4) → SeaweedFS | Adopted aus control/storage/ |

### Storage-Architektur (D12 — Capability-based access via signed URLs)

```
                    ┌────────────────────────────────────┐
                    │  Go Appservice (CONTROL PLANE)     │
                    │  - SeaweedFS S3 credentials        │
                    │  - artifact_metadata DB            │
                    │  - HMAC signed URL signer          │
                    │  - audit_events writer             │
                    │  Routes:                           │
                    │   POST /api/v1/storage/artifacts/  │
                    │        upload-url                  │
                    │   PUT  /api/v1/storage/artifacts/  │
                    │        upload/{id}                 │
                    │   GET  /api/v1/storage/artifacts/  │
                    │        {id}                        │
                    └─────────┬────────────────┬─────────┘
                              │ signed URL    │ signed URL
                              ▼                ▼
                    ┌────────────────────┐  ┌──────────────────┐
                    │  Python Ingest     │  │  control-ui      │
                    │  (COMPUTE PLANE)   │  │  (BROWSER)       │
                    │  - NO credentials  │  │  - NO credentials│
                    │  - GoStorageClient │  │  - BFF Routes    │
                    └─────────┬──────────┘  └────────┬─────────┘
                              │ PUT/GET bytes        │ PUT/GET bytes
                              ▼                      ▼
                          ┌──────────────────────────────┐
                          │  SeaweedFS S3 API (8333)     │
                          │  ONLY accessible via signed  │
                          │  URLs (15 min TTL default)   │
                          └──────────────────────────────┘
```

**Trennung von Tuwunel Media Store:** Tuwunel speichert Matrix-Protokoll Media (mxc:// URIs aus `m.image`/`m.file` Events) in seinem RocksDB. SeaweedFS ist nur fuer **control-ui /files Surface** und **Ingest Pipeline**. Die zwei Systeme beruehren sich nicht. Optionaler Future-Bridge: NATS subscriber auf `matrix.message.inbound` der bei Media-Events das mxc-File herunterlaedt + zu SeaweedFS spiegelt + Ingest triggert. Siehe `FUTURE_IDEAS.md`.

### Wo lebt der neue Backend-Code?

**Python Backend hat NACH Slice 2 vier venvs (D13-D17):**

```
python-backend/
├── .venv/                           # VENV 1: main agent runtime
├── pyproject.toml
├── agent/
│   ├── control/                     # NEU: Control API Router (alle thin HTTP)
│   │   ├── __init__.py
│   │   ├── router.py                # FastAPI APIRouter, mounted in agent/app.py
│   │   ├── overview.py
│   │   ├── memory.py                # Memory layer health
│   │   ├── episodes.py              # Faceted episode search
│   │   ├── kg_crud.py               # Knowledge Graph CRUD
│   │   ├── sessions.py              # LangGraph thread list
│   │   ├── audit.py                 # audit_events query
│   │   ├── skills.py                # Skills registry
│   │   ├── agents.py                # Trading roles + permission matrix
│   │   ├── ingestion.py             # ▶ thin httpx proxy zu Port 8098 (kein ingestion import!)
│   │   └── settings.py              # Service status + ENV
│   └── (rest of agent/...)
├── memory_engine/                   # SHARED Data Layer (PG/Kuzu/Chroma)
│   │                                  ▶ Importierbar von ingestion/, retrieval/, kg_pipeline/
│   │                                  ▶ Verifiziert: 0 imports aus agent/
├── retrieval/                       # NEU (Slice 2 Skeleton, Slice 3+ Phase 3 fuell)
│   ├── core/ + understanders/ + searchers/ + rerankers/ + verifiers/ + composers/
│   ├── pipelines/
│   └── api.py                       # high-level retrieve(query) entry
│
├── ingestion/                       # VENV 2: leichte extraction pipeline (Port 8098)
│   ├── pyproject.toml               # eigene venv: pymupdf4llm + hindsight + sentence-transformers
│   ├── .venv/
│   ├── core/                        # types, exceptions, config
│   ├── detectors/                   # Phase 1: ext + libmagic
│   ├── loaders/                     # Phase 2: local, seaweedfs, http
│   ├── extractors/                  # Phase 3: pymupdf4llm (1:1 von paperwatcher) + markdown/html/csv/code/note (NEU)
│   ├── normalizers/                 # Phase 4: markdown_cleaner
│   ├── chunkers/                    # Phase 5: token_chunker (von paperwatcher chunking.py)
│   ├── embedders/                   # Phase 6: sentence_transformer (all-MiniLM-L6-v2)
│   ├── sinks/                       # Phase 7: hindsight, storage, kg (importiert memory_engine)
│   ├── tracking/                    # Phase 8: jobs (psycopg), dedup (sha256), audit
│   ├── clients/                     # GoStorageClient (D12), KGPipelineClient
│   ├── pipelines/                   # COMPOSER (document, note, link, batch)
│   ├── worker.py                    # FastAPI Port 8098 — POST /ingest/{document,note,link}
│   └── cli.py
│
├── extraction_layout/               # VENV 3: schwere Extraktoren (Port 8101, Phase 2 SKELETON)
│   ├── pyproject.toml               # eigene venv: docling, marker-pdf, spacy-layout
│   ├── core/ + extractors/ + sinks/ + pipelines/
│   ├── worker.py                    # FastAPI Port 8101 — POST /extract (returns 503 in Phase 1)
│   └── README.md                    # Phase 2 Aktivierung
│
└── kg_pipeline/                     # VENV 4: KG extraction (Port 8099, Phase 2 SKELETON)
    ├── pyproject.toml               # torch==2.3.1, relik, glirel, gliner
    ├── core/ + preprocessors/ + extractors/ + filters/ + normalizers/ + sinks/
    ├── pipelines/document.py
    ├── server.py                    # FastAPI Port 8099 — POST /extract (returns 503 in Phase 1)
    ├── cli.py
    └── README.md                    # Phase 2 Aktivierung
```

**Decoupling-Regeln (D17):**
- `ingestion/` MAY import `memory_engine.*`, MUST NOT import `agent.*`
- `agent/*` MAY import `memory_engine.*`, MUST NOT import `ingestion.*`/`retrieval.*`/`kg_pipeline.*`
- Cross-package communication: HTTP only (`agent/control/ingestion.py` → httpx → `http://127.0.0.1:8098`)

**Go Appservice** bekommt das Storage Layer aus control/ (D4):

```
go-appservice/internal/
├── storage/             # 1:1 aus control/storage/go-backend/internal/storage/
│   ├── types.go
│   ├── metadata_store.go
│   ├── metadata_store_postgres.go
│   ├── service.go
│   ├── signer.go
│   ├── object_store_env.go
│   ├── provider_filesystem.go
│   └── provider_s3.go
└── handlers/http/
    └── artifact_handler.go    # 1:1 — POST /api/v1/storage/artifacts/*
```

### Stack `control-ui/` (neu)

| Lib | Status | Zweck |
|---|---|---|
| Next.js 16 + React 19 | NEU (Setup) | Framework |
| TypeScript 5.9 | NEU | Strict mode |
| Tailwind CSS 4 | NEU | Styling |
| **DM Sans (Google Fonts)** | NEU | Typography aus supermemory |
| shadcn/ui | NEU | ~25 Komponenten installieren |
| `nuqs` | NEU | URL state |
| `@tanstack/react-query` | NEU | Server state |
| `zustand` | NEU | Client state |
| `lucide-react` | NEU | Icons |
| `framer-motion` (motion) | NEU | Animations |
| `@biomejs/biome` | NEU | Lint + Format |
| **Multi-Modal Viewer:** | | |
| `react-pdf` v10 | NEU | PDF Viewer |
| `wavesurfer.js` v7 | NEU | Audio Player |
| `hls.js` v1.6 | NEU | Video Player |
| **Upload:** | | |
| `react-dropzone` v14 | NEU | File upload |
| **Search:** | | |
| `fuse.js` v7 | NEU | Client-side fuzzy search |
| **Memory Graph:** | | |
| `d3-force` v3 | NEU | Force simulation |
| **Total Bundle hinzugefuegt:** ~600 KB minified | | vertretbar |

---

## Top-Level UI Layout

```
control-ui/src/
├── app/
│   ├── (shell)/                     # GlobalTopBar Layout (von control/)
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # Default → /memory
│   │   ├── memory/[[...tab]]/page.tsx
│   │   ├── control/[[...tab]]/page.tsx
│   │   └── files/[[...tab]]/page.tsx
│   └── api/
│       ├── memory/                  # NEU — BFF Routes
│       │   ├── overview/route.ts
│       │   ├── episodes/route.ts
│       │   ├── episodes/[id]/route.ts
│       │   ├── kg/route.ts
│       │   ├── kg/[id]/route.ts
│       │   └── consolidation/route.ts
│       ├── control/                 # NEU — BFF Routes
│       │   ├── overview/route.ts
│       │   ├── sessions/route.ts
│       │   ├── sessions/[id]/kill/route.ts
│       │   ├── tool-events/route.ts
│       │   ├── security/route.ts
│       │   ├── audit/route.ts
│       │   ├── skills/route.ts
│       │   ├── skills/[id]/route.ts
│       │   ├── agents/route.ts
│       │   ├── agents/[id]/route.ts
│       │   ├── agents/permissions/route.ts
│       │   ├── consent/reload/route.ts
│       │   ├── system/health/route.ts
│       │   └── system/env/route.ts
│       └── files/                   # NEU — BFF Routes (1:1 aus control/files_surface)
│           ├── route.ts
│           ├── search/route.ts
│           ├── upload-intent/route.ts
│           ├── [id]/route.ts
│           ├── [id]/url/route.ts
│           └── [id]/reindex/route.ts
├── features/
│   ├── memory/                      # ← supermemory inspiration
│   ├── control/                     # ← control/control_surface 1:1
│   └── files/                       # ← control/files_surface 1:1
├── lib/
│   ├── kg-graph/                    # ← memory-graph Re-Implementation
│   ├── server/
│   │   ├── gateway.ts               # Go Appservice Proxy (8090)
│   │   ├── control-audit.ts         # writeControlAudit() helper
│   │   └── file-audit.ts
│   └── design-tokens/               # supermemory Design Tokens
│       ├── colors.ts
│       ├── typography.ts            # DM Sans Setup
│       └── spacing.ts
├── components/
│   └── ui/                          # shadcn/ui (~25 Komponenten)
└── package.json
```

### GlobalTopBar (40px persistent — von control/)

```
┌────────────────────────────────────────────────────────────────────┐
│  [Logo]   Memory · Control · Files            [User] [Settings]   │
└────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation Setup + Adoption

**Ziel:** Isolierte App lauffaehig, 3 Surface-Shells stehen, Storage Backend wired.

### 1.1 control-ui/ App initialisieren

| Source | What |
|---|---|
| NEU | Alles |

- [ ] **1.1.1:** `control-ui/` Verzeichnis anlegen
- [ ] **1.1.2:** `pnpm create next-app control-ui --typescript --tailwind --app --src-dir`
- [ ] **1.1.3:** `package.json` Scripts: dev, build, lint (biome)
- [ ] **1.1.4:** Tailwind Config: dark mode default, custom colors aus supermemory
- [ ] **1.1.5:** DM Sans Font einrichten (`next/font/google`)
- [ ] **1.1.6:** shadcn/ui init: `npx shadcn-ui@latest init`
- [ ] **1.1.7:** ~25 shadcn Komponenten installieren: button, card, dialog, sheet, dropdown-menu, popover, tabs, scroll-area, select, separator, badge, table, input, label, textarea, switch, toggle, toggle-group, tooltip, command, alert-dialog, avatar, accordion, progress, skeleton, sonner
- [ ] **1.1.8:** `lib/design-tokens/` mit supermemory Colors + Typography
- [ ] **1.1.9:** `biome.json` aus nextjs-chat 1:1 kopieren
- [ ] **1.1.10:** `.env.local.example` mit `NEXT_PUBLIC_GO_GATEWAY_URL=http://127.0.0.1:8090`
- [ ] **1.1.11:** Smoke Test: `pnpm dev` → leere Page auf Port 3001 (3000 ist nextjs-chat)

### 1.2 GlobalTopBar Shell adoptieren

| Source | What |
|---|---|
| control/control_surface | `GlobalTopBar.tsx`, `(shell)/layout.tsx` Pattern |
| supermemory | DM Sans Typography, Color Tokens |

- [ ] **1.2.1:** `control/control_surface/src/components/GlobalTopBar.tsx` → `control-ui/src/components/GlobalTopBar.tsx`
- [ ] **1.2.2:** Surface-Buttons anpassen: Memory · Control · Files (statt Trading · Map · Control · Files)
- [ ] **1.2.3:** `app/(shell)/layout.tsx` mit GlobalTopBar Wrapper
- [ ] **1.2.4:** `app/(shell)/page.tsx` redirected zu `/memory`
- [ ] **1.2.5:** `usePathname()` aktiviert die richtige Surface-Button
- [ ] **1.2.6:** Smoke Test: 3 Routes erreichbar, TopBar persistent

### 1.3 Files Surface 1:1 adoption

| Source | What |
|---|---|
| control/files_surface | Komplette Surface — Shell, Tabs, Viewers, Hooks, BFF |
| supermemory | nichts (control/files_surface ist hier ueberlegen) |

- [ ] **1.3.1:** `control/files_surface/src/features/files/` → `control-ui/src/features/files/`
- [ ] **1.3.2:** `control/files_surface/src/app/(shell)/files/` → `control-ui/src/app/(shell)/files/`
- [ ] **1.3.3:** `control/files_surface/src/app/api/files/` → `control-ui/src/app/api/files/`
- [ ] **1.3.4:** Komponenten:
  - `FilesPage.tsx`, `FilesTopNav.tsx`
  - `FilesOverviewTab.tsx`, `FilesDocumentsTab.tsx`, `FilesAudioTab.tsx`, `FilesVideoTab.tsx`, `FilesImagesTab.tsx`, `FilesDataTab.tsx`, `FilesUploadsTab.tsx`
  - `DocumentViewer.tsx` (PDF, react-pdf v10 — von @react-pdf-viewer/core v3 umstellen falls noetig)
  - `AudioPlayer.tsx` (wavesurfer)
  - `VideoPlayer.tsx` (hls.js)
  - `ImageViewer.tsx`
  - `UploadDropzone.tsx`
  - `FileSearch.tsx` (fuse.js)
  - `ReindexConfirmDialog.tsx`
- [ ] **1.3.5:** Hooks: `useWaveSurfer.ts`, `useHls.ts`
- [ ] **1.3.6:** `lib/action-classes.ts` adoptieren
- [ ] **1.3.7:** `lib/server/file-audit.ts` adoptieren, Schema-Mapping zu unserer `agent.audit_events` Tabelle
- [ ] **1.3.8:** Dependencies installieren: react-pdf, wavesurfer.js, hls.js, react-dropzone, fuse.js
- [ ] **1.3.9:** Smoke Test: `/files/documents` zeigt Empty State ohne Console-Errors

### 1.4 Control Surface Shell + read-only Tabs

| Source | What |
|---|---|
| control/control_surface | ControlPage, ControlTopNav, ActionBadge, ActionGuard, Subtabs (Overview, Sessions, Tool-Events, Security, Skills, Agents) |
| supermemory | nichts |

- [ ] **1.4.1:** `control/control_surface/src/app/(shell)/control/` → `control-ui/src/app/(shell)/control/`
- [ ] **1.4.2:** `control/control_surface/src/features/control/` → `control-ui/src/features/control/`
- [ ] **1.4.3:** Subtabs adoptieren (READ-ONLY zunaechst):
  - `ControlOverviewTab.tsx`
  - `ControlSessionsTab.tsx`
  - `ControlToolEventsTab.tsx`
  - `ControlSecurityTab.tsx`
  - `ControlSkillsTab.tsx`
  - `ControlAgentsTab.tsx`
- [ ] **1.4.4:** `ControlActionBadge`, `ControlActionGuard`, `KillSessionConfirmDialog` adoptieren
- [ ] **1.4.5:** `lib/action-classes.ts` adoptieren
- [ ] **1.4.6:** `useControlRole()` Hook adoptieren — liest `x-user-role` aus exec-12 Phase 2.6 Header
- [ ] **1.4.7:** `lib/server/control-audit.ts` adoptieren
- [ ] **1.4.8:** Smoke Test: `/control/overview` zeigt Empty-State mit "Service unavailable" Banner (Backend noch nicht ready)

### 1.5 Backend Adapter: `agent/control/` Router

| Source | What |
|---|---|
| NEU | Komplettes Backend-Package |

- [ ] **1.5.1:** `python-backend/agent/control/__init__.py` + `router.py` anlegen
- [ ] **1.5.2:** `agent/app.py` mounted Router unter `/api/v1/control`
- [ ] **1.5.3:** `overview.py` — `GET /api/v1/control/overview`:
  ```python
  {
    "memory": {"episodic_count": int, "kg_node_count": int, "vector_count": int},
    "sessions": {"active": int, "total_today": int},
    "audit": {"events_24h": int, "errors_24h": int},
    "tools": {"calls_24h": int, "error_rate": float}
  }
  ```
- [ ] **1.5.4:** `sessions.py` — `GET /api/v1/control/sessions`:
  - Source: `langgraph_checkpoint_postgres` Tabelle
  - Filter: `state IN ('running', 'paused')`
  - Returns: thread_id, agent_role, started_at, current_iteration, last_activity
- [ ] **1.5.5:** `audit.py` — `GET /api/v1/control/tool-events`:
  - Source: `agent.audit_events` mit `action IN ('TOOL_CALL', 'TOOL_RESULT')`
  - Pagination via `limit` + `offset`
- [ ] **1.5.6:** `audit.py` — `GET /api/v1/control/security`:
  - Source: `agent.audit_events` mit `action IN ('CONSENT_DECISION', 'SANITIZER_BLOCK', 'RATE_LIMIT_HIT')`
  - Aggregierte Posture Score (gruen/gelb/rot basierend auf error_rate)
- [ ] **1.5.7:** `skills.py` — `GET /api/v1/control/skills`:
  - Source: `agent/skills/loader.py` listet alle 3 Tiers (global/team/personal)
  - Returns: id, name, tier, generation, enabled, last_used
- [ ] **1.5.8:** `agents.py` — `GET /api/v1/control/agents`:
  - Source: `agent/roles.py` (statisch) + `agent_role_overrides` (DB, D1)
  - Returns: 6 Trading Rollen mit aktueller Konfiguration

### 1.6 Storage Layer Adoption (Go-Variante, D4)

| Source | What |
|---|---|
| control/storage/go-backend/internal/storage/ | 1:1 ins go-appservice/internal/storage/ |
| control/storage/go-backend/internal/handlers/http/artifact_handler.go | 1:1 ins go-appservice/internal/handlers/http/ |
| control/storage/tools/seaweedfs/ | 1:1 ins tools/seaweedfs/ |

- [ ] **1.6.1:** `control/storage/go-backend/internal/storage/` → `go-appservice/internal/storage/`
  - `types.go` (Artifact, SourceSnapshot, etc.)
  - `metadata_store.go`, `metadata_store_postgres.go`, `metadata_store_factory.go`
  - `service.go`, `signer.go`
  - `object_store_env.go`, `provider_filesystem.go`, `provider_s3.go`
- [ ] **1.6.2:** `control/storage/go-backend/internal/handlers/http/artifact_handler.go` → `go-appservice/internal/handlers/http/`
- [ ] **1.6.3:** Wiring in `go-appservice/cmd/appservice/main.go`:
  - `POST /api/v1/storage/artifacts/upload-url`
  - `PUT /api/v1/storage/artifacts/upload/{id}`
  - `GET /api/v1/storage/artifacts/{id}`
  - `GET /api/v1/storage/artifacts/{id}/download`
- [ ] **1.6.4:** SeaweedFS Tooling: `control/storage/tools/seaweedfs/weed.exe` → `tools/seaweedfs/`
- [ ] **1.6.5:** docker-compose.yml: neuer Service `seaweedfs` (profile: storage)
  ```yaml
  seaweedfs:
    image: chrislusf/seaweedfs:latest
    command: server -dir=/data -s3
    ports:
      - "9333:9333"   # Master UI
      - "8888:8888"   # Filer
      - "8333:8333"   # S3 API
    volumes:
      - ./homeserver/data/seaweedfs:/data
    profiles:
      - storage
  ```
- [ ] **1.6.6:** Frontend `control-ui/src/app/api/files/*` BFF Routes proxen direkt zum Go Appservice (nicht durch Python)
- [ ] **1.6.7:** ENV Variables in `go-appservice/.env`:
  ```env
  ARTIFACT_STORAGE_PROVIDER=s3
  S3_ENDPOINT=http://127.0.0.1:8333
  S3_BUCKET=matrix-artifacts
  S3_ACCESS_KEY=...
  S3_SECRET_KEY=...
  ARTIFACT_SIGNING_KEY=<32-byte hex>
  ARTIFACT_METADATA_DB_URL=postgres://...
  ```
- [ ] **1.6.8:** Smoke Test: PDF hochladen → erscheint in `/files/documents`

### 1.7 Audit Schema Alignment

| Source | What |
|---|---|
| control/shared/prisma/schema.prisma | ControlAuditLog + FileAuditLog Models |
| Eigene exec-12 Phase 2.1 | agent.audit_events Tabelle |

- [ ] **1.7.1:** Pruefen ob Felder von `ControlAuditLog` (control/) ins existierende `agent.audit_events` mappen
- [ ] **1.7.2:** Falls Felder fehlen: Alembic Migration `002_control_audit.py`
- [ ] **1.7.3:** Schema-Mapping doc in `python-backend/alembic/versions/002_README.md`
- [ ] **1.7.4:** `lib/server/control-audit.ts` schreibt in `agent.audit_events` (nicht eigene Tabelle)
- [ ] **1.7.5:** Smoke Test: Tab-Click erzeugt `audit_events` Eintrag mit `action='CONTROL_VIEW'`

**Verify Gate Phase 1:**
- [ ] `control-ui/` laeuft auf Port 3001
- [ ] 3 Surfaces (Memory leer, Control read-only, Files mit Upload) erreichbar
- [ ] PDF Upload → SeaweedFS → `/files/documents` Liste
- [ ] RBAC blockiert Buttons fuer User mit Rolle `viewer`
- [ ] Audit Events landen in `agent.audit_events`
- [ ] DM Sans + Dark Theme aktiv
- [ ] `/control/overview` zeigt echte Backend-Daten (auch wenn Empty Counts)

---

## Phase 2: Memory Browser + Episodic Browser

**Ziel:** Memory Surface wird der zentrale Memory-Browser. Hier kommt supermemory's UX am meisten ins Spiel.

### 2.1 Memory Layer Health Cards

| Source | What |
|---|---|
| control/control_surface (ControlMemoryTab) | Health Card Pattern |
| supermemory (settings/account.tsx) | SectionTitle + Card Layout |

- [ ] **2.1.1:** `MemoryHealthCards.tsx` — 3 Cards (episodic/kg/vector) mit Status, Item Count, Last Sync
- [ ] **2.1.2:** Backend: `agent/control/memory.py` — `GET /api/v1/control/memory`:
  ```python
  {
    "layers": [
      {"type": "episodic", "provider": "sqlite", "health": "ok",
       "item_count": 1247, "last_sync_at": "2026-04-06T10:30:00Z",
       "consolidation_pending": 3},
      {"type": "kg", "provider": "kuzu", ...},
      {"type": "vector", "provider": "chroma", ...}
    ]
  }
  ```
- [ ] **2.1.3:** UI: shadcn `<Card>` mit Badge (gruen/gelb/rot), `lucide` Icons (Brain, Network, Layers)
- [ ] **2.1.4:** Click auf Card → ScrollSpy zur jeweiligen Liste unten

### 2.2 Episodes List + Faceted Filter Bar

| Source | What |
|---|---|
| supermemory (memories-grid.tsx) | Masonry/Grid Layout, Infinite Loading Pattern |
| supermemory (lib/search-params.ts) | nuqs URL-State Pattern |
| NEU | Tabellen-View als Alternative, EpisodeCard fuer Grid-View |

- [ ] **2.2.1:** Backend: `agent/control/episodes.py` — `GET /api/v1/control/episodes`:
  ```
  Query Params:
    ?role=trader,researcher (multi-select)
    ?session_id=xxx
    ?from=2026-04-01&to=2026-04-06
    ?tags=btc,fundamentals
    ?confidence_min=0.7
    ?view=table|grid
    ?limit=50&offset=0
  ```
- [ ] **2.2.2:** Source: `memory_engine/episodic_store.py` `agent_episodes` Tabelle (mit `WHERE user_id = ?` D3)
- [ ] **2.2.3:** `EpisodeFilterBar.tsx` — Multi-Select Chips fuer Role, Tags, DateRange (shadcn `<Popover>` + `<Command>`)
- [ ] **2.2.4:** URL State via `nuqs` (Pattern aus supermemory `lib/search-params.ts`)
- [ ] **2.2.5:** Toggle View Mode: Table (default, dichte Daten) ↔ Grid (Masonry, visueller)
- [ ] **2.2.6:** `EpisodeListTable.tsx` — shadcn `<Table>` mit Spalten Time, Role, Session, Tools, Confidence, Tokens, Actions
- [ ] **2.2.7:** `EpisodesGrid.tsx` — Masonry Layout mit `EpisodeCard.tsx` (inspiriert von supermemory document-cards)
- [ ] **2.2.8:** Pagination via `useInfiniteQuery` (PAGE_SIZE = 50)

### 2.3 Episode Detail Sheet

| Source | What |
|---|---|
| supermemory (document-modal/index.tsx) | Detail View Pattern (Title, Content, Relations, Delete) |
| control (KillSessionConfirmDialog) | Approval Flow fuer Delete |

- [ ] **2.3.1:** `EpisodeDetailSheet.tsx` als shadcn `<Sheet side="right">` (75% width)
- [ ] **2.3.2:** Backend: `GET /api/v1/control/episodes/{id}` — vollstaendige Details
- [ ] **2.3.3:** Sheet Inhalt:
  - **Header:** Episode ID, Created At, Agent Role, Confidence Bar
  - **Section "Input":** Original User Message + System Prompt (collapsible)
  - **Section "Tool Calls":** Liste mit Status + Duration (Pattern von supermemory's tool-call cards)
  - **Section "Output":** Agent Response (Markdown render via `react-markdown`)
  - **Section "Memory References":** Welche Recall-Memories wurden genutzt (klickbar → naviiert zum Memory)
  - **Section "Tags":** editierbare Tag-Chips (PATCH)
  - **Footer:** Delete Button (approval-write, 2.5), Export JSON Button

### 2.4 Memory Timeline View

| Source | What |
|---|---|
| supermemory (UX-Inspiration) | Timeline Pattern (chronologische Darstellung) |
| NEU | Vertikale Linie + farbige Marker, Hindsight-spezifisch |

- [ ] **2.4.1:** Neuer Sub-Route `/memory/timeline`
- [ ] **2.4.2:** Backend: `GET /api/v1/control/memory/timeline?from=&to=` liefert sortierte Liste aller Memory-Operationen
- [ ] **2.4.3:** Source: Hindsight `consolidation_tasks` + `agent_episodes` + `kg_changes`
- [ ] **2.4.4:** UI: vertikale Linie mit Memory-Node-Markern, gruppiert nach Tag
- [ ] **2.4.5:** Marker Color-Codes (von supermemory memory-graph constants):
  - Blau (#3B73B8): Recall (Memory wurde abgerufen)
  - Gruen (#10B981): Retain (Neue Memory gespeichert)
  - Violett (#A78BFA): Reflect/Consolidate (Background Task)
  - Rot (#EF4444): Failed/Forgotten
  - Orange (#F59E0B): Expiring
- [ ] **2.4.6:** Hover → Mini-Preview Popover, Click → Episode Detail Sheet (2.3)
- [ ] **2.4.7:** Date Range Picker im Header (default: letzte 7 Tage)

### 2.5 Edit/Delete Episode UI (TT4 aus control/)

| Source | What |
|---|---|
| control (KillSessionConfirmDialog) | 2-Step Approval Pattern |
| NEU | Episode-spezifischer Flow |

- [ ] **2.5.1:** Backend: `DELETE /api/v1/control/episodes/{id}` — approval-write
- [ ] **2.5.2:** Backend: `PATCH /api/v1/control/episodes/{id}` — Tags + Notes editierbar
- [ ] **2.5.3:** UI: `DeleteEpisodeDialog.tsx` 2-Step:
  - Step 1: "Delete this episode?" + Episode Preview
  - Step 2: 30s Token-Gate (Pattern aus `KillSessionConfirmDialog.tsx`)
- [ ] **2.5.4:** RBAC (D1):
  - `analyst+` darf Tags editieren
  - `admin` darf loeschen
  - viewer hat read-only
- [ ] **2.5.5:** Audit Event: `EPISODE_DELETED` in `agent.audit_events`

### 2.6 Consolidation Status Dashboard

| Source | What |
|---|---|
| supermemory (Settings Card Pattern) | Card Layout |
| NEU | Hindsight-spezifischer Worker Status |

- [ ] **2.6.1:** Backend: `GET /api/v1/control/memory/consolidation`:
  ```python
  {
    "worker_health": "ok|degraded|stopped",
    "last_heartbeat": "2026-04-06T10:30:00Z",
    "pending_tasks": 5,
    "running_tasks": 1,
    "failed_tasks_24h": 0
  }
  ```
- [ ] **2.6.2:** Source: Hindsight `consolidation_tasks` Tabelle
- [ ] **2.6.3:** UI: `ConsolidationStatusCard.tsx` mit Worker Health Indicator (gruener Heartbeat Pulse)
- [ ] **2.6.4:** Manual Trigger Button: "Run Consolidation Now" (approval-write, admin only)

**Verify Gate Phase 2:**
- [ ] Episodes Liste zeigt mind. 50 Eintraege fluessig
- [ ] Filter via nuqs URL-persistent (back/forward funktioniert)
- [ ] Episode Detail Sheet zeigt Input/Tool-Calls/Output korrekt
- [ ] Timeline rendert chronologisch >100 Episoden ohne Lag
- [ ] Delete Episode triggert `EPISODE_DELETED` Audit Event
- [ ] Grid-View toggle funktioniert

---

## Phase 3 — Slice 4 SPLIT STRATEGY (07.04.2026)

**Erkenntnis:** supermemory's `memory-graph` Package modelliert nur **2 Node-Typen** (document, memory) + **3 Edge-Typen** (derives, updates, extends). Es ist ein **Document-Memory Provenance System**, kein typed Knowledge Graph.

Unsere Trading-Domain hat **6 Node-Typen** (Stratagem, Regime, Channel, Asset, Institution, BTEMarker) + **6 typed Semantic Edges** (causes, inhibits, activates, precedes, transmits, signals). Das ist ein **echtes typed KG mit Domain-Ontologie**.

→ **Zwei verschiedene Probleme, zwei verschiedene Visualisierungen:**

| Route | Was zeigt es | Backend | Viz Library |
|---|---|---|---|
| `/memory/graph` | Episode-Memory Provenance ("warum weiss der Agent das?") | Hindsight Episodes + Memory facts | **supermemory `memory-graph` package 1:1** (`control-ui/src/lib/kg-graph/` — haben wir kopiert) — Episodes als "documents", Memory facts als "memories" |
| `/memory/kg` | Trading Knowledge Graph | **Kuzu** (`memory_engine/kg_store.py` aus exec-11) + Cypher | **`@xyflow/react`** mit 6 Custom Node Components |
| `/memory/kg/browse` | Tabelle aller KG-Nodes mit Filter | Kuzu | shadcn `<Table>` |
| `/memory/kg/cypher` | Cypher Query Playground (admin only) | Kuzu | Code-Editor + Result Table |

**Warum nicht supermemory's package fuer Trading KG adaptieren?**
- Renderer braucht 6 Node-Shapes statt 2 → ~30% Code-Rewrite
- Force-Sim Config pro Node-Typ → mehr Komplexitaet
- Edge logic 3→6 Typen mit unterschiedlicher Visual-Semantic
- react-flow ist genau dafuer gemacht: arbitrary typed nodes mit React Custom Components

**Warum supermemory's package fuer Episode-Memory behalten?**
- Datenmodell passt 1:1: Episodes ≈ Documents, derived Memory Facts ≈ Memories
- Performance-optimierter Canvas Renderer (viewport culling, spatial index)
- Wir haben es schon kopiert (`control-ui/src/lib/kg-graph/`), funktioniert out of the box mit Mock-Data

---

## Phase 3: Knowledge Graph Visualization (PRIORITY)

**Ziel:** Memory Graph komplett interaktiv. **memory-graph Package von supermemory** als Inspiration, eigene Implementation.

### 3.1 KG Backend CRUD

| Source | What |
|---|---|
| NEU | Komplettes Backend |

- [ ] **3.1.1:** `agent/control/kg_crud.py` — REST Endpoints:
  - `GET /api/v1/control/kg/nodes?type=&limit=200&offset=0`
  - `GET /api/v1/control/kg/nodes/{id}`
  - `POST /api/v1/control/kg/nodes` (approval-write in prod, free in dev)
  - `PATCH /api/v1/control/kg/nodes/{id}`
  - `DELETE /api/v1/control/kg/nodes/{id}` (approval-write)
  - `GET /api/v1/control/kg/edges?from={id}` / `?to={id}`
  - `POST /api/v1/control/kg/edges`
  - `DELETE /api/v1/control/kg/edges/{from}/{to}`
- [ ] **3.1.2:** Source: `memory_engine/kg_store.py` mit Provider-Wahl (Kuzu / FalkorDB / SQLite)
- [ ] **3.1.3:** Cypher-Sanitization aus exec-11 Code-Review #2 wiederverwenden (`_sanitize_cypher_value()`)
- [ ] **3.1.4:** Response Format Schema:
  ```json
  {
    "nodes": [
      {
        "id": "n1",
        "type": "Stratagem",
        "label": "Mean Reversion",
        "properties": {...},
        "created_at": "...",
        "updated_at": "...",
        "confidence": 0.85
      }
    ],
    "edges": [
      {"from": "n1", "to": "n2", "type": "inhibits", "properties": {...}}
    ]
  }
  ```
- [ ] **3.1.5:** WHERE user_id = ? in allen Queries (D3)

### 3.2 KG Graph Komponente (Re-Implementation von supermemory's memory-graph)

| Source | What |
|---|---|
| _ref/supermemory/packages/memory-graph/ | Architektur, Force-Konfig, Color Theme, Performance-Tricks — als **Inspiration**, nicht copy-paste |
| NEU | Eigene Implementation an Hindsight gebunden |

- [ ] **3.2.1:** Neues lokales Package `control-ui/src/lib/kg-graph/`
  - `simulation.ts` — d3-force Wrapper (NodeData, EdgeData, ForceConfig)
  - `canvas-renderer.ts` — Canvas 2D Drawing Loop
  - `hit-test.ts` — Quadtree Spatial Indexing fuer Click-Detection
  - `KGGraph.tsx` — React-Wrapper mit ResizeObserver
  - `constants.ts` — Colors + Force-Config (1:1 von supermemory)
  - `types.ts` — TypeScript Interfaces
- [ ] **3.2.2:** Force Config (von supermemory uebernehmen):
  ```ts
  export const FORCE_CONFIG = {
    linkStrength: { default: 0.35, version: 0.6, fallback: 0.05 },
    linkDistance: 300,
    docMemoryDistance: 180,
    chargeStrength: -2000,
    collisionRadius: { document: 70, memory: 35 },
    centeringStrength: 0.06,
  };
  ```
- [ ] **3.2.3:** Node Types (matrix-spezifisch, mapping zu unserem KG):
  - **Stratagem** (Rechteck, blau #3B73B8) — Trading Strategien
  - **Regime** (Hexagon, violett #A78BFA) — Marktregime
  - **TransmissionChannel** (Kreis, cyan #38BDF8)
  - **Asset** (Diamant, gruen #10B981)
  - **Institution** (abgerundet, grau #94A3B8)
  - **BTEMarker** (Stern, rot #EF4444)
- [ ] **3.2.4:** Edge Types:
  - `causes` (durchgezogen, 2px)
  - `inhibits` (gestrichelt, 1.5px)
  - `activates` (gepunktet, 1.5px)
  - `precedes` (durchgezogen, mit Pfeil)
  - `transmits` (durchgezogen, 1.2px, opacity 0.5)
  - `signals` (durchgezogen, 1.5px)
- [ ] **3.2.5:** Color Theme Module (von supermemory, Dark Theme)
- [ ] **3.2.6:** Performance-Tricks (von supermemory):
  - Viewport Culling (nur sichtbare Nodes/Edges zeichnen)
  - Edge Culling bei Zoom < 0.08
  - Max 200 Nodes (D5, Pagination ueber Backend)
  - Spatial Index (Quadtree) fuer Hit-Testing
  - Batch Rendering: Edges nach Farbe gruppiert

### 3.3 KG UI Tabs

| Source | What |
|---|---|
| control (ControlKGContextTab) | Stats Pattern |
| supermemory (memory-graph-playground) | Graph Layout, Sidebar Pattern |
| NEU | 3-Spalten-Layout (Filter | Canvas | Detail) |

- [ ] **3.3.1:** `/memory/kg` — Default Tab mit Stats + Recent Nodes (von control's ControlKGContextTab adoptiert)
- [ ] **3.3.2:** `/memory/kg/visualize` — Vollbild Graph Canvas
- [ ] **3.3.3:** `/memory/kg/browse` — Tabellenansicht aller Nodes mit Filter (Type, Search, Date)
- [ ] **3.3.4:** `/memory/kg/edit/[id]` — Form fuer Node Edit
- [ ] **3.3.5:** Layout `/memory/kg/visualize`:
  ```
  ┌──────────┬─────────────────────────────┬──────────┐
  │ Filter   │                             │  Detail  │
  │ Sidebar  │       KG Canvas             │  Panel   │
  │          │                             │          │
  │ Type     │                             │ Node     │
  │ Search   │                             │ Edges    │
  │ Date     │                             │ Source   │
  │          │                             │          │
  └──────────┴─────────────────────────────┴──────────┘
  ```

### 3.4 Interaction

| Source | What |
|---|---|
| supermemory (memory-graph) | Hover/Click/Drag/Zoom Patterns |

- [ ] **3.4.1:** Hover Node → `NodeHoverPopover` mit Properties (von supermemory)
- [ ] **3.4.2:** Click Node → Selected State + Detail Panel rechts
- [ ] **3.4.3:** Double-Click Node → Inline Edit (Form im Detail Panel)
- [ ] **3.4.4:** Drag Node → Force-Pin (lockt Position)
- [ ] **3.4.5:** Right-Click Node → Context Menu (Edit, Delete, Find Connected, Copy ID)
- [ ] **3.4.6:** Zoom: Mouse Wheel + Pinch (Touch)
- [ ] **3.4.7:** Pan: Drag Background
- [ ] **3.4.8:** Reset View Button (Fit-to-Content)
- [ ] **3.4.9:** Keyboard Shortcuts: Cmd+F Search, Cmd+R Reset, Esc Deselect

### 3.5 Search + Filter

| Source | What |
|---|---|
| supermemory (memory-graph + UI Filter Pattern) | Filter UI |

- [ ] **3.5.1:** Top Search Bar mit Substring Match auf Node Labels (`fuse.js`)
- [ ] **3.5.2:** Sidebar Filter:
  - Node Type (Multi-Select Chips)
  - Date Range (Created)
  - Has Edges (yes/no)
  - Confidence > X (Slider)
- [ ] **3.5.3:** Filtered Nodes hervorheben, Rest ausgrauen (opacity 0.2)
- [ ] **3.5.4:** URL-State via nuqs (filter params persistent)

### 3.6 Trading Stratagems Pre-Seed

| Source | What |
|---|---|
| memory_engine/seed_data.py (existiert in exec-11) | Seed Data |

- [ ] **3.6.1:** Pre-Seed Endpoint: `POST /api/v1/control/kg/seed` (admin only)
- [ ] **3.6.2:** Source: `memory_engine/seed_data.py` mit Stratagems, Regimes, Channels
- [ ] **3.6.3:** Frontend Button "Reload Trading Knowledge Graph" mit Approval Dialog
- [ ] **3.6.4:** Test: 50+ Nodes laden, fluessig rendern

**Verify Gate Phase 3:**
- [ ] Graph rendert > 100 Nodes mit > 30 FPS
- [ ] CRUD funktioniert end-to-end (Create → Visualize → Edit → Delete)
- [ ] Filter aktualisiert Graph live ohne Reload
- [ ] Click auf Node zeigt Details + Source-Memory
- [ ] Pre-Seed laedt Trading Stratagems

---

## Phase 4: Agent Configuration UI

**Ziel:** Trading Rollen + Permission Matrix editierbar mit Hot-Reload (D1, D2).

### 4.1 Trading Roles Editor (D1)

| Source | What |
|---|---|
| control (ControlAgentsTab) | Liste + Card Pattern |
| supermemory (settings/account.tsx) | Edit Form Layout |
| NEU | Trading-Role-spezifisches Editor + DB Overlay (D1) |

- [ ] **4.1.1:** Backend: `agent/control/agents.py` — `GET /api/v1/control/agents`:
  - Source: `agent/roles.py` (Defaults) + `agent_role_overrides` Tabelle (D1)
  - Loader merged: Default + Overlay
  - Returns: ID, Name, System Prompt, Allowed Tools, Memory Access, Approval Required, "is_overridden" Flag
- [ ] **4.1.2:** Alembic Migration `003_agent_role_overrides.py`:
  ```sql
  CREATE TABLE agent.agent_role_overrides (
    role_id TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'local',
    field TEXT NOT NULL,
    value JSONB NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (role_id, user_id, field)
  );
  ```
- [ ] **4.1.3:** Backend: `PATCH /api/v1/control/agents/{role_id}` (bounded-write):
  - Body: `{"field": "system_prompt", "value": "..."}`
  - Schreibt in `agent_role_overrides`
  - Audit Event `ROLE_OVERRIDE_SET`
- [ ] **4.1.4:** Backend: `DELETE /api/v1/control/agents/{role_id}/overrides/{field}` (Reset to Default)
- [ ] **4.1.5:** Loader-Patch in `agent/roles.py` `load_role(role_id, user_id)`:
  - Lese Default aus statischer Definition
  - Lese Overlays aus DB
  - Merge: Overlay > Default
- [ ] **4.1.6:** UI: `RoleEditorSheet.tsx` Form:
  - System Prompt (Textarea, max 4000 chars, syntax highlighting via react-shiki?)
  - Allowed Tools (Multi-Select aus Tool Registry, fetched via `/api/v1/agent/tools`)
  - Memory Access (Radio: read | write | none)
  - Approval Required (Switch — gewarnt fuer RISK_MANAGER)
  - Reset to Default Button pro Feld (sichtbar wenn Overlay existiert)
- [ ] **4.1.7:** Save: PATCH triggert Hot-Reload via internal event

### 4.2 Permission Matrix (D2)

| Source | What |
|---|---|
| control (TT7 Plan) | Matrix UI Konzept |
| consent_policy.yaml (exec-12 Phase 2.2) | Source of Truth |
| NEU | Matrix-UI mit Cell-Editing + DB Overlay + Cache Reload |

- [ ] **4.2.1:** Alembic Migration `004_consent_overrides.py`:
  ```sql
  CREATE TABLE agent.consent_overrides (
    role_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'local',
    level TEXT NOT NULL,  -- 'auto' | 'inform' | 'confirm' | 'deny'
    updated_by TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (role_id, tool_name, user_id)
  );
  ```
- [ ] **4.2.2:** Backend: `agent/consent/provider.py` erweitern:
  - `_overlay_cache: dict` mit 5s TTL (D2)
  - `check_consent(role, tool)` liest aus YAML + Overlay (Overlay gewinnt)
  - `reload()` Methode cleared den Overlay-Cache
- [ ] **4.2.3:** Backend: `GET /api/v1/control/consent/matrix`:
  ```json
  {
    "roles": ["fundamentals", "technical", "researcher", "trader", "risk_manager", "sentiment"],
    "tool_categories": ["chart", "portfolio", "memory", "sandbox", "canvas", "web", "files"],
    "matrix": {
      "trader": {"sandbox": "confirm", "chart": "auto", ...},
      ...
    }
  }
  ```
- [ ] **4.2.4:** Backend: `POST /api/v1/control/consent/cell` (bounded-write):
  - Body: `{"role": "trader", "tool": "sandbox_execute", "level": "confirm"}`
  - Schreibt in `consent_overrides`
  - Triggert `consent_provider.reload()`
- [ ] **4.2.5:** Backend: `POST /api/v1/control/consent/reload`: Manual reload trigger
- [ ] **4.2.6:** UI: `PermissionMatrix.tsx` — 6×N Grid:
  - Y-Achse: 6 Trading Rollen (Card Pattern von supermemory)
  - X-Achse: Tool-Kategorien
  - Zellen: ✓ (auto) / ⓘ (inform) / ⚠ (confirm) / ⊘ (deny)
  - Click Zelle → Cycle through States (Optimistic Update)
  - Save → POST `/cell` → reload Cache
- [ ] **4.2.7:** Audit Event `PERMISSION_MATRIX_CELL_CHANGED` fuer jede Aenderung

### 4.3 Skills Management (3-Tier)

| Source | What |
|---|---|
| control (ControlSkillsTab) | Skills Liste Pattern |
| supermemory (Tabbed Section Pattern) | 3-Tier Aufteilung |
| agent/skills/loader.py (exec-10) | Backend |

- [ ] **4.3.1:** Backend: `agent/control/skills.py`:
  - `GET /api/v1/control/skills?tier=global|team|personal`
  - `GET /api/v1/control/skills/{id}` (mit Markdown content)
  - `PATCH /api/v1/control/skills/{id}` (enabled toggle)
  - `POST /api/v1/control/skills/import` (von GitHub/ZIP — nutzt exec-10 Phase 5)
- [ ] **4.3.2:** UI: `/control/skills` Tab (von control adoptiert)
- [ ] **4.3.3:** Drei Sections (Tabs): Global, Team, Personal
- [ ] **4.3.4:** Pro Skill: Card mit Name, Generation, Last Used, Enabled Switch, "View" Button
- [ ] **4.3.5:** `SkillDetailSheet.tsx` mit Markdown Render der `SKILL.md` (`react-markdown`)
- [ ] **4.3.6:** Personal Skills: Edit Button (Tiptap Editor mit Markdown Support)
- [ ] **4.3.7:** "Import from GitHub" Dialog (nutzt `POST /api/v1/skills/import`)
- [ ] **4.3.8:** "Install from ZIP" Dialog (nutzt `POST /api/v1/skills/install`)

### 4.4 Memory Settings pro Agent

| Source | What |
|---|---|
| supermemory (settings/account.tsx) | Form Pattern |
| NEU | Trading-Agent-spezifische Memory Settings |

- [ ] **4.4.1:** Pro Trading Rolle: Memory Settings Sub-Form im RoleEditorSheet (4.1)
  - Retain enabled (Switch)
  - Recall budget (Slider 1k-100k tokens)
  - Tag Filter (Multi-Select)
  - Retention period (1d / 7d / 30d / 90d / forever)
- [ ] **4.4.2:** Persist via `agent_role_overrides` (gleiche Tabelle wie 4.1.2, field='memory_settings')
- [ ] **4.4.3:** Loader liest beim Agent-Init und uebergibt an Hindsight Recall

**Verify Gate Phase 4:**
- [ ] Trading Rollen editierbar mit DB Overlay
- [ ] Reset to Default funktioniert pro Feld
- [ ] Permission Matrix Click triggert Cache Reload (sichtbar in naechstem Tool-Call)
- [ ] Skills enable/disable wirksam ohne Backend-Restart
- [ ] Personal Skill kann ueber UI erstellt + bearbeitet werden
- [ ] Memory Settings pro Rolle persistiert

### 4.5 Sandbox Runs Browser (NEU 07.04.2026 — coverage gap)

| Source | What |
|---|---|
| `agent/sandbox/manager.py` (exec-12 Phase 1) | Backend |
| supermemory (memories-grid layout) | Pattern fuer Run List |
| NEU | UI |

Backend deckt aktuell `SandboxManager.execute_code()` und `execute_browser()` ab (exec-12 Phase 1). Wir haben bisher kein UI um:
- Letzte Sandbox-Ausfuehrungen zu sehen (welcher Agent, welche Sprache, Status, Resource Usage)
- Aktive Sandbox-Container zu sehen (Health, Lifecycle)
- Pro-Tool Stats (Anzahl Calls, Fehlerrate, durchschnittliche Duration)

- [ ] **4.5.1:** Backend `agent/control/sandbox.py`:
  - `GET /api/v1/control/sandbox/runs?limit=50&from=&to=&agent_role=&status=`
  - `GET /api/v1/control/sandbox/active` (live container list)
  - `GET /api/v1/control/sandbox/stats` (aggregated)
  - Source: `agent.audit_events` filter `tool_name IN ('sandbox_execute', 'sandbox_browser')` + Sandbox manager state
- [ ] **4.5.2:** Frontend `/control/sandbox` Tab
  - `SandboxRunsTable.tsx` — shadcn `<Table>` mit Time, Agent, Tool, Language, Duration, Status, Resource (cpu/mem)
  - `SandboxRunDetailSheet.tsx` — Detail Sheet mit stdout/stderr/files (Sheet pattern wie EpisodeDetailSheet)
  - `SandboxStatsCard.tsx` — Total runs 24h, Error rate, Avg duration, Active containers
- [ ] **4.5.3:** Filter Bar (Pattern aus EpisodeFilterBar): Tool-type pills (sandbox_execute, sandbox_browser)
- [ ] **4.5.4:** RBAC: nur `analyst+` darf Detail Sheet sehen, `admin` darf Container killen

### 4.6 Tools Registry Browser (NEU 07.04.2026 — coverage gap)

| Source | What |
|---|---|
| `agent/tools/registry.py` (15 registered tools) | Backend |
| supermemory (settings/integrations.tsx) | Pattern fuer Tool Cards |
| NEU | UI |

15 Tools sind via `ToolRegistry.load()` registriert. Wir haben bisher kein UI um:
- Alle verfuegbaren Tools mit ihrem Schema zu sehen
- Per-Role Enablement zu konfigurieren (welche Trading-Rolle darf welches Tool nutzen)
- Last-used Timestamp + Call-Count pro Tool
- Tool-Definition (input schema, output schema, description) zu inspizieren

- [ ] **4.6.1:** Backend `agent/control/tools.py`:
  - `GET /api/v1/control/tools` listet alle registrierten Tools mit Schema
  - `GET /api/v1/control/tools/{name}/stats` (call_count, last_used, error_rate)
  - `PATCH /api/v1/control/tools/{name}/role-access` (per-Role enable/disable, schreibt in `consent_overrides`)
- [ ] **4.6.2:** Frontend `/control/tools` Tab
  - `ToolsRegistryGrid.tsx` — Card pro Tool (Pattern: supermemory `document-cards`)
  - `ToolDetailSheet.tsx` — Schema Pretty-Print, Per-Role Matrix, Recent Calls
  - Pro Tool: Name, Description, Input Schema (collapsible JSON), Output Schema, Per-Role Toggle, Stats
- [ ] **4.6.3:** Visualization: Tool dependency graph (welches Tool ruft welches an) — optional, react-flow Pattern
- [ ] **4.6.4:** Search + Filter (cmdk Command Palette wenn > 20 Tools)

---

## Phase 5: Content Ingestion Pipeline

**Ziel:** File Upload + Document → Hindsight Memory Pipeline + Status Visibility.

### 5.1 Upload Modal (Adoption + Erweiterung)

| Source | What |
|---|---|
| control (UploadDropzone) | Backend Upload Flow + signed URL Pattern |
| supermemory (add-document/index.tsx) | Tabbed Modal Layout (Note/Link/File/Connect) |

- [ ] **5.1.1:** `AddMemoryModal.tsx` — Tabbed Dialog (Pattern von supermemory):
  - Tab 1: **Note** — Tiptap Editor (Quick Note → direkt in Memory)
  - Tab 2: **Link** — URL + Title + Description (URL Scraper im Backend)
  - Tab 3: **File** — UploadDropzone (von control adoptiert)
  - Tab 4: **Bridge** — NATS Subject Subscription (siehe 5.6)
- [ ] **5.1.2:** Pro Tab: "Upload Target" Selector
  - Sandbox (File-Upload zum Agent-Sandbox via existierender `FileAnalyzeTool`)
  - Memory Engine (Document → Hindsight Pipeline)
  - Object Storage only (Files Surface, kein Processing)
- [ ] **5.1.3:** Tag Selector (Multi-Select) am Bottom des Modals
- [ ] **5.1.4:** Submit triggert je nach Target unterschiedlichen Endpoint

### 5.2 Document → Hindsight Memory Pipeline (3-Venv Architektur, D13-D17)

| Source | What |
|---|---|
| paperwatcher/core/doc_extractor/ | Extractors: base ABC + 5 Backends (pymupdf4llm primary, docling/marker optional) |
| paperwatcher/core/chunking.py | Token Chunker (langchain RecursiveCharacterTextSplitter) |
| paperwatcher/core/spacy_layout_chunker.py | Section-aware Chunker (optional) |
| paperwatcher/kg-module/extraction.py | KG Extractor (Phase 2 erst, siehe 5.7) |
| Hindsight (exec-11) | Sink Backend (`memory_engine/episodic_store.py`) |

**Architektur:** Drei entkoppelte Packages mit eigenen venvs (D13). Phase-basierte Subfolder mit Registry-Pattern (D16). Strict decoupling von agent/ (D17).

```
python-backend/
├── .venv/                           # Venv 1: agent runtime + retrieval/
│
├── ingestion/                       # Venv 2: extraction pipeline (Port 8098)
│   ├── pyproject.toml               # eigene venv: pymupdf4llm, docling, marker, spacy-layout
│   ├── .venv/
│   ├── core/                        # types, exceptions, config
│   │   ├── types.py                 # ExtractedDocument, ExtractedChunk, Job
│   │   ├── exceptions.py
│   │   └── config.py
│   ├── detectors/                   # Phase 1: file type detection
│   │   ├── base.py + extension.py + magic.py + registry.py
│   ├── loaders/                     # Phase 2: byte loading
│   │   ├── base.py + local.py + seaweedfs.py + http.py
│   ├── extractors/                  # Phase 3: bytes → ExtractedDocument
│   │   ├── base.py                  # ← paperwatcher 1:1 (ABC + Dataclasses)
│   │   ├── pymupdf_ext.py           # ← paperwatcher 1:1 (CPU primary)
│   │   ├── docling_ext.py           # ← paperwatcher 1:1 (optional, ~500MB)
│   │   ├── marker_ext.py            # ← paperwatcher 1:1 (optional, ~300MB)
│   │   ├── markdown_ext.py + html_ext.py + csv_ext.py + code_ext.py + note_ext.py
│   │   └── registry.py
│   ├── normalizers/                 # Phase 4: cleanup + structure
│   │   ├── base.py + markdown_cleaner.py + section_detector.py + language_detector.py
│   ├── chunkers/                    # Phase 5: text → chunks
│   │   ├── base.py
│   │   ├── token_chunker.py         # ← paperwatcher chunking.py
│   │   ├── section_chunker.py       # ← paperwatcher spacy_layout_chunker.py
│   │   ├── semantic_chunker.py + code_chunker.py
│   │   └── registry.py
│   ├── embedders/                   # Phase 6: chunks → vectors
│   │   ├── base.py + sentence_transformer.py + voyage.py + registry.py
│   ├── sinks/                       # Phase 7: write outputs
│   │   ├── base.py
│   │   ├── hindsight_sink.py        # → memory_engine/episodic_store.py retain()
│   │   ├── vector_sink.py           # → ChromaDB/pgvector
│   │   ├── storage_sink.py          # → SeaweedFS via GoStorageClient
│   │   ├── kg_sink.py               # → kg_pipeline HTTP (Port 8099, Phase 2)
│   │   └── registry.py
│   ├── tracking/                    # Phase 8: jobs + dedup + audit
│   │   ├── jobs.py + dedup.py + audit.py + progress.py
│   ├── clients/                     # cross-cutting HTTP clients
│   │   ├── go_storage.py            # GoStorageClient (D12 signed URLs)
│   │   └── kg_pipeline.py
│   ├── pipelines/                   # COMPOSER (verdrahtet die Phasen)
│   │   ├── base.py
│   │   ├── document.py              # File → all 8 phases
│   │   ├── note.py                  # Note → skip extract/normalize, direkt chunk
│   │   ├── link.py                  # URL → fetch HTML → all phases
│   │   └── batch.py
│   ├── worker.py                    # FastAPI Service (Port 8098)
│   └── cli.py                       # manual debugging
│
└── kg_pipeline/                     # Venv 3: KG extraction (Port 8099, Phase 2)
    ├── pyproject.toml               # torch==2.3.1, relik, glirel, gliner
    ├── core/ + preprocessors/ + extractors/ + filters/ + normalizers/ + sinks/
    ├── pipelines/document.py
    ├── server.py                    # FastAPI Service (Port 8099)
    └── cli.py
```

**Pipeline-Composer Pattern (Beispiel `ingestion/pipelines/document.py`):**

```python
class DocumentPipeline:
    def __init__(self, config: IngestionConfig):
        self.detector = DetectorRegistry.get(config.detector)
        self.loader = LoaderRegistry.get(config.loader)        # seaweedfs
        self.normalizer = MarkdownCleaner()
        self.chunker = ChunkerRegistry.get(config.chunker)     # token
        self.embedder = EmbedderRegistry.get(config.embedder)  # sentence_transformer
        self.sinks = [HindsightSink(), StorageSink()]
        self.tracker = JobTracker()

    async def run(self, file_id: str) -> Job:
        job = await self.tracker.start(file_id)
        try:
            mime = self.detector.detect(file_id)
            extractor = ExtractorRegistry.get_for_mime(mime)
            bytes_ = await self.loader.load(file_id)
            doc = extractor.extract(bytes_)
            doc = self.normalizer.normalize(doc)
            chunks = self.chunker.chunk(doc)
            await self.tracker.update(job, chunks_total=len(chunks))
            for chunk in chunks:
                vec = self.embedder.embed(chunk.text)
                for sink in self.sinks:
                    await sink.write(chunk, vec, job)
                await self.tracker.tick(job)
            await self.tracker.complete(job)
        except Exception as e:
            await self.tracker.fail(job, str(e))
        return job
```

**Decoupling (D17):** Pipeline darf `from memory_engine.episodic_store import ...` (shared data layer), aber NICHT `from agent.X import Y`.

- [ ] **5.2.1:** `python-backend/ingestion/pyproject.toml` mit eigener venv-Konfiguration
  - Deps: `pymupdf4llm`, `langchain-text-splitters`, `sentence-transformers`, `httpx`, `psycopg[binary]`, `fastapi`, `uvicorn`, `python-magic-bin` (windows mime detection), `loguru`
  - Optional deps (Phase 2): `docling`, `marker-pdf`, `spacy-layout`
  - `requires-python = ">=3.11"` (gleich wie main)
  - `[tool.uv] cache-dir = "../../.uv-cache"`
- [ ] **5.2.2:** `ingestion/core/types.py` ← paperwatcher `doc_extractor/base.py` Dataclasses 1:1 (ExtractedDocument, ExtractedChunk, ExtractedTable, ExtractedFigure)
- [ ] **5.2.3:** `ingestion/extractors/base.py` ← paperwatcher `doc_extractor/base.py` ABC 1:1
- [ ] **5.2.4:** `ingestion/extractors/pymupdf_ext.py` ← paperwatcher `pymupdf_ext.py` 1:1 (200 LOC)
- [ ] **5.2.5:** `ingestion/extractors/{markdown,html,csv,note,code}_ext.py` NEU (trivial, je <100 LOC)
- [ ] **5.2.6:** `ingestion/extractors/registry.py` NEU (mime→extractor map)
- [ ] **5.2.7:** `ingestion/detectors/{extension,magic}.py` + `registry.py`
- [ ] **5.2.8:** `ingestion/loaders/seaweedfs.py` (nutzt `clients/go_storage.py`)
- [ ] **5.2.9:** `ingestion/clients/go_storage.py` — GoStorageClient (httpx, D12 signed URLs)
- [ ] **5.2.10:** `ingestion/normalizers/markdown_cleaner.py` (remove headers/footers/page nums)
- [ ] **5.2.11:** `ingestion/chunkers/token_chunker.py` ← paperwatcher chunking.py adaptiert
- [ ] **5.2.12:** `ingestion/embedders/sentence_transformer.py` (all-MiniLM-L6-v2)
- [ ] **5.2.13:** `ingestion/sinks/hindsight_sink.py` (importiert `memory_engine.episodic_store`)
- [ ] **5.2.14:** `ingestion/sinks/storage_sink.py` (Metadata only — File ist schon in SeaweedFS)
- [ ] **5.2.15:** `ingestion/tracking/jobs.py` (psycopg, ingestion_jobs Tabelle)
- [ ] **5.2.16:** `ingestion/tracking/dedup.py` (sha256 content hash)
- [ ] **5.2.17:** `ingestion/tracking/audit.py` (audit_events Emitter)
- [ ] **5.2.18:** `ingestion/pipelines/document.py` (Composer wie oben)
- [ ] **5.2.19:** `ingestion/pipelines/note.py` (skip extract, direkt chunk)
- [ ] **5.2.20:** `ingestion/worker.py` — FastAPI App mit Endpoints:
  - `POST /ingest/document` (body: `{file_id, pipeline, tags, user_id}`)
  - `POST /ingest/note` (body: `{text, tags, user_id}`)
  - `GET /status` (aggregiert Pending/Done/Failed counts)
  - `GET /jobs/{id}` (single job)
  - `POST /jobs/{id}/retry`
- [ ] **5.2.21:** Alembic Migration `005_ingestion_jobs.py` (in main venv ausgefuehrt):
  ```sql
  CREATE TABLE ingestion.jobs (
    id UUID PRIMARY KEY,
    file_id UUID,
    pipeline TEXT NOT NULL,         -- 'document' | 'note' | 'link'
    user_id TEXT NOT NULL DEFAULT 'local',
    status TEXT NOT NULL,           -- 'pending' | 'extracting' | 'chunking' | 'embedding' | 'storing' | 'done' | 'failed'
    progress FLOAT DEFAULT 0,
    chunks_total INT,
    chunks_done INT,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    document_hash TEXT,             -- sha256 fuer dedup
    metadata JSONB
  );
  CREATE SCHEMA IF NOT EXISTS ingestion;
  ```
- [ ] **5.2.22:** `agent/control/ingestion.py` (in main venv) — thin httpx proxy:
  - 3 Routes: `POST /api/v1/control/ingest/document`, `GET /api/v1/control/ingestion/status`, `GET /api/v1/control/ingestion/jobs/{id}`
  - **KEIN** Import aus `ingestion.*` package (D17)
  - Forwarded zu `http://127.0.0.1:8098`
- [ ] **5.2.23:** devstack2: neuer Service `ingestion-worker` (Tier `agent`, depends_on postgres, eigene venv via `uv run --project python-backend/ingestion uvicorn ingestion.worker:app --port 8098`)
- [ ] **5.2.24:** Decoupling Verification (CI check): `grep -r "from agent" python-backend/ingestion/` muss leer sein
- [ ] **5.2.26:** **NEU 07.04.2026 — Hash-based Incremental Reindex (paperwatcher Pattern + Cursor IDE Pattern):**

  Aktuell macht ingestion full-file dedup (`sha256(bytes)` → skip wenn bereits done). Auf einem **geaenderten** PDF wird alles re-extracted + re-embedded. Cursor IDE / Continue / Aider machen das anders: per-chunk hash → nur changed chunks re-embedden. Bei 100MB PDF mit 1 geaendertem Absatz = 99% gespart.

  **Adoption inspiriert von paperwatcher `layout-module/manifest.py` + `hasher.py`** (Merkle Tree CAS), aber mit **Chunk-Level Granularitaet** statt nur File-Level.

  - [ ] **5.2.26.1:** Migration `003_chunk_hashes.py`:
    ```sql
    CREATE TABLE ingestion.chunk_hashes (
      job_id UUID NOT NULL REFERENCES ingestion.jobs(id),
      chunk_id TEXT NOT NULL,
      content_hash TEXT NOT NULL,  -- sha256(chunk.text)
      doc_id TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT NOW(),
      PRIMARY KEY (job_id, chunk_id)
    );
    CREATE INDEX ix_chunk_hashes_doc ON ingestion.chunk_hashes(doc_id);
    CREATE INDEX ix_chunk_hashes_content ON ingestion.chunk_hashes(content_hash);
    ```
  - [ ] **5.2.26.2:** `ingestion/tracking/dedup.py` erweitern: `hash_chunk(chunk)` + `find_unchanged_chunks(doc_id, new_hashes) → set[str]`
  - [ ] **5.2.26.3:** `ingestion/pipelines/document.py` neue Methode `smart_reindex(file_id)`:
    ```python
    new_chunks = chunker.chunk(doc)
    new_hashes = {c.id: hash_chunk(c) for c in new_chunks}
    old_hashes = tracker.get_chunk_hashes_by_doc(doc_id)  # from chunk_hashes table
    unchanged = set(old_hashes.values()) & set(new_hashes.values())
    new_only = [c for c in new_chunks if new_hashes[c.id] not in unchanged]
    deleted_hashes = set(old_hashes.values()) - set(new_hashes.values())
    # Embed only NEW chunks
    embeddings = embedder.embed([c.text for c in new_only])
    # Sinks write only new
    for sink in sinks: await sink.write_batch(doc, new_only, embeddings, job)
    # Delete removed chunks from Hindsight
    if deleted_hashes:
        await hindsight_sink.delete_by_hashes(deleted_hashes)
    ```
  - [ ] **5.2.26.4:** `HindsightSink` neue Methode `delete_by_hashes(hashes: set[str])` — query Hindsight, find facts mit `metadata.chunk_content_hash in hashes`, delete
  - [ ] **5.2.26.5:** Worker neuer Endpoint: `POST /ingest/document/{file_id}/reindex` triggert `smart_reindex` statt full ingest
  - [ ] **5.2.26.6:** Audit Event `INGESTION_INCREMENTAL_REINDEX` mit metadata `{unchanged: int, new: int, deleted: int, savings_pct: float}`
  - [ ] **5.2.26.7:** Frontend Files Surface "Reindex" button ruft `/reindex` statt full re-upload (Slice 1 polish)
  - **Bewertung:** **HOHER WERT** — auf Cloud-Embedder (voyage, openai) spart das Geld + Latenz; auf lokalem sentence-transformers spart es CPU/GPU Zeit. SOTA Pattern (Cursor IDE Standard 2025-2026).

- [ ] **5.2.25:** **Wiring-Fixes nach Code-Review (07.04.2026 Polish-Pass):**
  - HindsightSink nutzt `engine.retain_batch_async(bank_id, contents=[{...}], request_context=RequestContext(), document_tags=[...])` (NICHT `engine.retain()`) — Hindsight macht eigene Embeddings, unser embedder phase ist nur fuer vector_sink/kg_sink gebraucht
  - Pipeline `_materialize_to_temp` UUID-prefixed temp filenames (Kollision-Schutz fuer parallele Jobs)
  - `JobTracker.recover_stuck_jobs()` setzt nicht-terminale Jobs auf failed beim Worker-Startup (catch worker crashes mid-job)
  - Worker `lifespan()` ruft `recover_stuck_jobs()` on startup + `await sink.close()` fuer alle sinks on shutdown
  - `extractors/registry.get_for_mime()`: text/* → silent fallback zu note, unbekannte Binaries → ExtractionError (nicht silently als Text lesen)
  - `extractors/remote.py` mit `RemoteLayoutExtractor` Base + `DoclingExtractor`/`MarkerExtractor`/`MineruExtractor` Wrapper die HTTP zu extraction_layout (Port 8101) callen — registriert in extractor registry, returnt ExtractionError wenn EXTRACTION_LAYOUT_ENABLED=false (Phase 1)

### 5.3 Optional: Cognee Integration

| Source | What |
|---|---|
| exec-13 Phase 1.2 | Cognee Backend (wenn vorhanden) |

- [ ] **5.3.1:** Wenn exec-13 Phase 1.2 (Cognee) abgeschlossen ist: integrieren
- [ ] **5.3.2:** Toggle in 5.1 Modal: "Use Cognee Triplet Extraction" (default off)
- [ ] **5.3.3:** Wenn aktiv: `cognee.add(content) → cognee.cognify()` als zusaetzlicher Schritt vor Hindsight Retain
- [ ] **5.3.4:** Sonst: Direct Hindsight Retain (5.2)

### 5.4 Reindex / Resync Operations

| Source | What |
|---|---|
| control/files_surface (Reindex Pattern) | Approval Flow |

- [ ] **5.4.1:** `POST /api/v1/files/{id}/reindex` adoptieren (war schon in control/files_surface)
- [ ] **5.4.2:** Triggert Re-Run der Pipeline fuer ein File (re-extract, re-chunk, re-embed, re-retain)
- [ ] **5.4.3:** Approval-write mit 30s Token Gate (bestehender Flow)
- [ ] **5.4.4:** Bulk Reindex Button "Reindex All Documents" (admin only, sehr lange Operation)

### 5.5 Pipeline Status Dashboard

| Source | What |
|---|---|
| supermemory (Stats Card Pattern) | Card Layout |
| NEU | Hindsight-spezifische Job Liste |

- [ ] **5.5.1:** Neuer Tab `/memory/ingestion`
- [ ] **5.5.2:** Status Cards (4 Cards):
  - Total Documents Indexed
  - Pending Jobs
  - Failed Jobs (mit Retry Button)
  - Embedding Storage Used (MB)
- [ ] **5.5.3:** Active Jobs Liste mit Progress Bars (Polling alle 2s)
- [ ] **5.5.4:** Failed Jobs Liste mit Error Message + Retry/Delete Actions
- [ ] **5.5.5:** Last Successful Sync Timestamp
- [ ] **5.5.6:** Backend: `GET /api/v1/control/ingestion/status` aggregiert aus `ingestion_jobs`
- [ ] **5.5.7:** Backend: `POST /api/v1/control/ingestion/jobs/{id}/retry`

### 5.7 KG Pipeline (Venv 4, Phase 2 — Skeleton in Slice 2)

**Phase 1 (jetzt):** nur pyproject.toml + Stub-Files anlegen, KEIN `uv sync` (relik+torch==2.3.1 ist 2 GB Download).
**Phase 2 (spaeter):** voll aktivieren, von ingestion-worker per HTTP aufrufen.

| Source | What |
|---|---|
| paperwatcher/kg-module/extraction.py | StructuredExtractor (ReLiK + GLiREL Wrapper) |
| paperwatcher/kg-module/text_pipeline.py | Section-aware preprocessing |
| paperwatcher/kg-module/predicate_mapper.py | Canonical predicate mapping |
| paperwatcher/kg-module/config.py | KGConfig (thresholds, types) |
| **paperwatcher/kg-module/communities.py + community_summarizer.py** | **GraphRAG Community Detection (SOTA, NEU 07.04.2026)** |
| **paperwatcher/kg-module/conflict_detector.py** | **KG Contradiction Detection (SOTA, NEU 07.04.2026)** |
| **paperwatcher/kg-module/subgraph_pruner.py** | **KG Retrieval Pruning (SOTA, NEU 07.04.2026)** |

- [ ] **5.7.1:** `python-backend/kg_pipeline/pyproject.toml` mit Deps (kein uv sync!):
  ```toml
  [project]
  requires-python = ">=3.11,<3.13"
  dependencies = [
    "torch==2.3.1",
    "relik>=1.0.7,<1.1",
    "glirel>=1.2.1",
    "gliner==0.2.22",
    "spacy>=3.7,<4",
    "fastapi>=0.120",
    "uvicorn>=0.38",
    "loguru>=0.7",
  ]
  ```
- [ ] **5.7.2:** `kg_pipeline/core/{types,exceptions,config}.py` Skeleton
- [ ] **5.7.3:** `kg_pipeline/preprocessors/section_splitter.py` Stub (NotImplementedError)
- [ ] **5.7.4:** `kg_pipeline/extractors/relik_glirel.py` Stub
- [ ] **5.7.5:** `kg_pipeline/sinks/kuzu_sink.py` Stub (Phase 2 schreibt zu memory_engine/kg_store.py)
- [ ] **5.7.6:** `kg_pipeline/server.py` FastAPI Stub mit `POST /extract` returning 503 "not yet activated"
- [ ] **5.7.7:** `kg_pipeline/cli.py` Stub
- [ ] **5.7.8:** README.md mit Phase 2 Aktivierungs-Anleitung (`uv sync` + Modelle laden)
- [ ] **5.7.9:** **NEU SOTA — `kg_pipeline/postprocessing/communities.py`** ← `paperwatcher/kg-module/communities.py` (294 LOC). **GraphRAG Pattern (Microsoft 2024):** Community Detection im KG via Leiden Algorithm. Identifiziert "Cluster" verwandter Entities die zusammen interpretiert werden sollten. Phase 2 Adoption.
- [ ] **5.7.10:** **NEU SOTA — `kg_pipeline/postprocessing/community_summarizer.py`** ← `paperwatcher/kg-module/community_summarizer.py` (164 LOC). LLM-generierte Summary pro Community. Ermoeglicht "Global Queries" wie *"welche Stratagems sind im Hochzins-Regime aktiv"* — der Agent fragt das Cluster, nicht einzelne Knoten.
- [ ] **5.7.11:** **NEU SOTA — `kg_pipeline/postprocessing/conflict_detector.py`** ← `paperwatcher/kg-module/conflict_detector.py` (235 LOC). Detect contradictory facts in KG (z.B. *"Asset X ist bullish"* + *"Asset X ist bearish"* aus verschiedenen Quellen). **Hochrelevant fuer Trading** wo Signale standardmaessig konfligieren — Conflict Detection kann diese als Konflikt-Knoten markieren statt sie zu loeschen.
- [ ] **5.7.12:** **NEU SOTA — `kg_pipeline/postprocessing/subgraph_pruner.py`** ← `paperwatcher/kg-module/subgraph_pruner.py` (210 LOC). Reduce KG Subgraphs auf relevant Nodes fuer Retrieval. Wichtig wenn KG > 10k Nodes wird, sonst werden Queries langsam und Context-Window explodiert.
- [ ] **5.7.13:** **NEU MITTEL — `kg_pipeline/postprocessing/got_traversal.py`** ← `paperwatcher/kg-module/got_traversal.py` (262 LOC). Graph of Thoughts traversal — multi-step KG reasoning chains. Phase 2/3 — overlap mit LangGraph aber KG-spezifisch.

### 5.8 Retrieval Skeleton (Venv 1, Phase 3 — leere Folder in Slice 2)

**Phase 1 (jetzt):** nur Verzeichnis-Struktur anlegen mit `__init__.py`. Keine Implementierung.
**Phase 3 (spaeter):** voll bauen, von agent/graph/nodes/ aufgerufen.

**Subfolder-Struktur (8 Phasen, NEU 07.04.2026: `indexers/` als 8. Phase fuer offline Index-Builder):**

```
retrieval/
├── core/             # types, config, exceptions
├── understanders/    # query understanding (intent, decompose, expand, hyde)
├── indexers/         # NEU — offline INDEX-BUILDER (RAPTOR tree, BM25, visual)
│                     #       laufen einmal pro Doc-Set, schreiben in Stores
├── searchers/        # online RETRIEVER (BM25, vector, kg, episodic, raptor, visual)
│                     #       laufen pro Query, lesen aus Stores
├── rerankers/        # post-retrieval rank refinement (cross-encoder, llm, mmr)
│ verifiers/          # quality + faithfulness gates (self_rag, falsification, quality_gate)
├── composers/        # context assembly (context_bubble, citation_assembler)
└── pipelines/        # end-to-end orchestrator
```

**Trennung indexers vs searchers (wichtig fuer RAPTOR + ColPali):**
- `indexers/` = **offline** (einmal beim ingest), schreibt Index in Postgres/Chroma/Kuzu
- `searchers/` = **online** (pro Query), liest aus Index, returnt SearchHits

Beispiel RAPTOR:
- `indexers/raptor_tree_builder.py` baut Hierarchical Tree aus chunks beim Indexing
- `searchers/raptor_searcher.py` queried den Tree zur Query-Zeit (lokal vs global level)

- [ ] **5.8.1:** `python-backend/retrieval/{core,understanders,indexers,searchers,rerankers,verifiers,composers,pipelines}/` mit `__init__.py`
- [ ] **5.8.2:** `retrieval/api.py` mit `async def retrieve(query): raise NotImplementedError`
- [ ] **5.8.3:** README.md mit Phase 3 Adoption-Map (welche paperwatcher-Files wann)

**SOTA Adoption Map (Phase 3 — alle aus paperwatcher 1:1 oder Patterns):**

| Target Datei | Source paperwatcher | LOC | Status |
|---|---|---|---|
| `searchers/bm25_searcher.py` | `core/chunk_bm25.py` | ? | Phase 3 |
| `searchers/vector_searcher.py` | wraps `memory_engine/vector_store.py` | NEU | Phase 3 |
| `searchers/kg_searcher.py` | wraps `memory_engine/kg_store.py` (Kuzu) | NEU | Phase 3 |
| `searchers/hindsight_searcher.py` | wraps Hindsight episodic recall | NEU | Phase 3 |
| `searchers/hybrid.py` | `core/hybrid_retriever.py` | 629 | Phase 3 |
| `rerankers/cross_encoder.py` | `core/reranker.py` | 727 | Phase 3 |
| `rerankers/llm_reranker.py` | `core/llm_reranker.py` | ? | Phase 3 |
| `rerankers/mmr.py` | NEU (Maximal Marginal Relevance) | NEU | Phase 3 |
| `understanders/intent_router.py` | `core/intent_router.py` | ? | Phase 3 |
| `understanders/decomposer.py` | `core/query_decomposer.py` | ? | Phase 3 |
| `understanders/expander.py` | `core/query_expander.py` | ? | Phase 3 |
| `understanders/hyde.py` | `core/hyde.py` | ? | Phase 3 |
| `composers/context_bubble.py` | `core/context_bubble.py` | ? | Phase 3 |
| `verifiers/self_rag.py` | `core/self_rag.py` | ? | Phase 3 |
| `pipelines/hybrid_kg.py` | `core/rag_pipeline.py` (adapted) | 442 | Phase 3 |

**SOTA Gold (NEU 07.04.2026 — explizit aufgenommen statt vergessen):**

- [ ] **5.8.4a:** **NEU SOTA — `retrieval/indexers/raptor_tree_builder.py`** ← `paperwatcher/core/raptor_tree.py` (424 LOC). **RAPTOR Builder (Stanford 2024):** Bottom-up hierarchische Chunk-Summary-Trees. Clustering + LLM-Summarization auf jedem Level. Laeuft **offline** beim Indexing. Schreibt Tree-Knoten in eigene Postgres-Tabelle `agent.raptor_nodes` mit `level INT, parent_id UUID, summary TEXT, embedding VECTOR`.
- [ ] **5.8.4b:** **NEU SOTA — `retrieval/searchers/raptor_searcher.py`** (NEU). Queried den RAPTOR Tree zur Query-Zeit: lokale Frage → leaf chunks, globale Frage → root summary. Auto-detect via query intent. Phase 3.
- [ ] **5.8.5:** **NEU SOTA — `retrieval/searchers/visual_searcher.py`** + ColPali in extraction_layout (siehe 5.2bis). **ColPali / ColQwen2.5:** Late-Interaction Visual PDF Embedding. Embedded PDF-Pages als Bilder + retrieved via visuelle Aehnlichkeit zur Query. **KRITISCH fuer Trading** weil Finanz-Reports voll mit Charts/Heatmaps/Tabellen sind die rein textbasierte Retrieval verpasst. Phase 3 (mit Phase 2 extraction_layout dependency).
- [ ] **5.8.6:** **NEU SOTA — `retrieval/verifiers/quality_gate.py`** ← `paperwatcher/core/retrieval_gate.py` (474 LOC). Quality Gate nach Retrieval: Confidence-Threshold, Length-Filter, Diversity-Check, Score-Distribution Validation. Filtert Garbage-Hits raus bevor sie in den Context Bubble kommen. Phase 3.
- [ ] **5.8.7:** **NEU SOTA — `retrieval/verifiers/falsification.py`** ← `paperwatcher/core/falsification.py` (210 LOC). Adversarial Verification: Prueft ob Retrieved Evidence die Antwort tatsaechlich stuetzt oder ob ein Counter-Argument moeglich waere. SOTA Pattern fuer Hallucination Prevention. Phase 3.

### 5.2bis ColPali Visual Indexing (extraction_layout Phase 2 SOTA Add-on)

| Source | What |
|---|---|
| paperwatcher/core/colpali_indexer.py | ColPali Indexing (418 LOC) |
| paperwatcher/layout-module/colpali_service.py | ColPali Service Wrapper (84 LOC) |

- [ ] **5.2bis.1:** `extraction_layout/extractors/colpali_ext.py` ← Adoption von colpali_indexer.py — embedded PDF Pages als Bilder via ColQwen2.5 / ColPali Model. Output: per-page visual embeddings.
- [ ] **5.2bis.2:** `extraction_layout/server.py` neues Endpoint `POST /index/visual` — accepts file_url, returns visual embeddings + page metadata.
- [ ] **5.2bis.3:** `ingestion/sinks/visual_sink.py` (NEU) — schreibt visual embeddings in eigene Vector Tabelle (`agent.visual_embeddings` mit pgvector).
- [ ] **5.2bis.4:** Migration `003_visual_embeddings.py`:
  ```sql
  CREATE TABLE agent.visual_embeddings (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL,
    page_number INT NOT NULL,
    embedding VECTOR(1024),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
  );
  CREATE INDEX ix_visual_file_page ON agent.visual_embeddings(file_id, page_number);
  ```
- [ ] **5.2bis.5:** `retrieval/searchers/visual_searcher.py` (Phase 3) sucht via visual embedding similarity gegen `agent.visual_embeddings`.
- [ ] **5.2bis.6:** Kompatibel mit text retrieval — Hybrid-Searcher kombiniert beides via RRF.

### 5.6 NATS Bridge UI (exec-05b Vorbereitung)

| Source | What |
|---|---|
| NEU | Bridge Configuration UI |

- [ ] **5.6.1:** Neuer Sub-Tab `/memory/ingestion/bridges`
- [ ] **5.6.2:** Liste der konfigurierten NATS Subjects → Memory Mapping
  - z.B. `matrix.message.inbound` → `world` memories
  - Spaeter: `slack.message.inbound` → `world` (wenn exec-05b)
- [ ] **5.6.3:** Pro Bridge: Filter Rules (Regex, Sender Whitelist, Min Length)
- [ ] **5.6.4:** Toggle Enable/Disable
- [ ] **5.6.5:** Statistik: Messages Received, Retained, Filtered (letzte 24h)
- [ ] **5.6.6:** Backend: `GET /api/v1/control/bridges` listet aktive NATS Subscriptions

**Verify Gate Phase 5:**
- [ ] PDF Upload → Pipeline → Hindsight Memory in < 30s
- [ ] Search im Agent-Chat findet Inhalt aus geuploadetem PDF
- [ ] Deduplizierung: gleiches PDF zweimal hochladen → nur ein Eintrag
- [ ] Failed Jobs sichtbar mit Retry Button
- [ ] Pipeline Status Dashboard zeigt Live-Progress

---

## Phase 6: System Observability + Settings

**Ziel:** Service Status, ENV Editor (read-only D6), Audit Log Viewer.

### 6.1 Service Status Dashboard

| Source | What |
|---|---|
| control (ControlOverviewTab Pattern) | Health Card Layout |
| supermemory (settings Service Status) | Layout-Inspiration |
| NEU | Backend Health Pings |

- [ ] **6.1.1:** Neuer Tab `/control/system`
- [ ] **6.1.2:** Backend: `agent/control/settings.py` — `GET /api/v1/control/system/health`:
  - Pingt PostgreSQL (Hindsight + Audit) — `SELECT 1`
  - Pingt NATS — `nats ping`
  - Pingt LiveKit — `HTTP HEAD /`
  - Pingt OpenSandbox Server — `HTTP GET /health`
  - Memory Engine (in-process) — Hindsight `health_check()`
  - Sandbox Provider (containerd / podman socket) — `os.path.exists`
  - Returns: Service-Liste mit `name, status (ok|degraded|down), latency_ms, last_check, endpoint`
- [ ] **6.1.3:** UI: Service Cards Grid mit Health Badge (gruen/gelb/rot), Last Check, Endpoint
- [ ] **6.1.4:** Auto-Refresh alle 30s (`useQuery refetchInterval`)

### 6.2 API/Models Tab — fused ENV Editor + LLM Provider Config + Model Routing (UPDATED 07.04.2026)

**Aenderung:** statt nur ENV viewer haben wir einen **fused** Tab `/control/api` der drei Sektionen kombiniert:

1. **LLM Providers** — Liste aller konfigurierter Provider (Anthropic, OpenAI, Ollama, vLLM, LM Studio, OpenRouter, Azure OpenAI). Pro Provider: API Key Status (sensitive masked), Endpoint URL, Test-Connection Button, Discover-Models Button (fuer Ollama/vLLM), Active-Toggle.
2. **Model Routing** — pro Trading Role (stock_picker, portfolio_manager, ...) welches Modell. Default-Tabelle, override per role moeglich.
3. **Embedder & Utility Models** — Text Embedder (sentence-transformers default, voyage-3 optional), Visual Embedder (ColPali Phase 2), Reranker (bge-reranker-v2-m3), Summarizer (claude-haiku), STT (whisper).
4. **ENV Variables (Sektion am Ende)** — restliche env vars die nicht model-spezifisch sind (Service URLs, feature flags, timeouts) — alle read-only mit sensitive masking (D6).

**WICHTIG:** Tab gehoert in **Developer Mode** (D18) — Nicht-Admin Trader sieht ihn nicht.

- [ ] **6.2.0:** Frontend `ApiModelsTab.tsx` mit 4 Sektionen oben + scrollable env table unten
- [ ] **6.2.1:** Section 1 — LLM Providers Cards mit Test/Discover Actions (disabled Phase 1)

| Source | What |
|---|---|
| supermemory (settings Layout) | SectionTitle + Card |
| NEU | Sanitization + Masking |

- [ ] **6.2.1:** Backend: `GET /api/v1/control/system/env` — listet ENV Vars mit Sanitization:
  - Sensitive Keys (`*_KEY`, `*_SECRET`, `*_PASSWORD`, `*_TOKEN`) → masked als `••••XXXX` (nur erste 4 + letzte 4 chars)
  - Andere → Klartext
- [ ] **6.2.2:** UI: `/control/system/env` Liste mit Suche
- [ ] **6.2.3:** Read-Only Markers (Schluss-Symbol Icon)
- [ ] **6.2.4:** Hinweis-Banner: "Edit requires restart and admin role — disabled in this version"
- [ ] **6.2.5:** **Edit-Mode ist FUTURE_IDEAS** (D6) — siehe `specs/FUTURE_IDEAS.md`

### 6.3 Audit Log Viewer

| Source | What |
|---|---|
| control (ControlAuditTab Pattern) | Tabelle |
| supermemory (Detail Sheet Pattern) | Detail View |

- [ ] **6.3.1:** Neuer Tab `/control/audit`
- [ ] **6.3.2:** Backend: `GET /api/v1/control/audit?action=&user=&from=&to=&limit=100`
- [ ] **6.3.3:** UI: shadcn `<Table>` mit Spalten: Time, Action, User, Tool, Success, Duration
- [ ] **6.3.4:** Click Row → `AuditDetailSheet.tsx` mit Input/Output JSON Pretty-Print
- [ ] **6.3.5:** Filter Bar: Action Multi-Select, User Filter, Date Range
- [ ] **6.3.6:** Export Button: CSV / JSON
- [ ] **6.3.7:** Auto-Refresh alle 10s (Live Tail Mode optional)

### 6.4 Log Viewer (Optional, nice-to-have)

| Source | What |
|---|---|
| NEU | Live Log Tail |

- [ ] **6.4.1:** Backend: `GET /api/v1/control/system/logs` (SSE Stream) tailt aus `data/logs/` oder `agent/audit/store.py` JSON Lines
- [ ] **6.4.2:** UI: Streaming Log Viewer mit Filter (level, service, search)
- [ ] **6.4.3:** Buffer Size 1000 Lines, Auto-Scroll Toggle
- [ ] **6.4.4:** Color-Codes pro Level (DEBUG=grau, INFO=blau, WARN=gelb, ERROR=rot)

**Verify Gate Phase 6:**
- [ ] Service Status zeigt korrekt online/offline alle Services
- [ ] ENV Editor zeigt sensitive keys maskiert
- [ ] Audit Log zeigt Events aus Phase 1-5
- [ ] Audit Detail Sheet zeigt korrekt formatierten JSON

### 6.5 Sessions Browser (NEU 07.04.2026 — coverage gap)

| Source | What |
|---|---|
| `agent/graph/runner.py` + LangGraph Checkpointer | Backend |
| control (ControlSessionsTab + KillSessionConfirmDialog) | UI Pattern |
| `agent/working_memory.py` (M5 Scratchpad) | Per-Session State |

LangGraph Sessions sind aktuell nicht im UI sichtbar. Wir haben kein Live-View ueber:
- Aktive Threads + ihre aktuelle Iteration
- Per-Session Working Memory (M5 Scratchpad)
- Last Tool Call + Status pro Session
- Kill-Action fuer hung sessions

- [ ] **6.5.1:** Backend `agent/control/sessions.py`:
  - `GET /api/v1/control/sessions?state=active|paused|all`
  - `GET /api/v1/control/sessions/{thread_id}` (full state + working memory)
  - `POST /api/v1/control/sessions/{thread_id}/kill` (approval-write, 30s token gate)
  - Source: `langgraph_checkpoint_postgres` Tabelle + `working_memory.py`
- [ ] **6.5.2:** Frontend `/control/sessions` Tab (adoptiert von control/control_surface ControlSessionsTab.tsx)
  - SessionsTable.tsx mit Status, Token Bar, Iteration, Last Activity, Agent Role
  - SessionDetailSheet.tsx mit Working Memory + Tool Call Trail + State Snapshot
  - KillSessionConfirmDialog (1:1 von control/)
- [ ] **6.5.3:** Auto-Refresh alle 10s (Polling) — alternativ WebSocket later

### 6.6 MCP Server Browser (NEU 07.04.2026 — coverage gap)

| Source | What |
|---|---|
| `agent/mcp_server.py` (FastMCP, exec-09) | Backend |
| NEU | UI |

Wir haben einen FastMCP Server (exec-09) der Tools standardisiert exposed. Wir haben aber keinen Sicht auf:
- MCP Server Status (running/stopped)
- Connected MCP Clients (welche Agents/Tools sind connected)
- Exposed Tools (welche Tools exposed unser Server, welche Schemas)
- MCP Method calls + Errors

- [ ] **6.6.1:** Backend `agent/control/mcp.py`:
  - `GET /api/v1/control/mcp/status` (running, port, version)
  - `GET /api/v1/control/mcp/exposed-tools` (was unser Server exposed)
  - `GET /api/v1/control/mcp/clients` (connected clients, falls trackable)
  - Source: FastMCP introspection API
- [ ] **6.6.2:** Frontend `/control/mcp` Tab
  - MCPStatusCard.tsx (Health Badge, Port, Version)
  - MCPExposedToolsList.tsx (Tools mit Schema)
  - MCPClientsList.tsx (Connected clients, Last call)
- [ ] **6.6.3:** Bei MCP Apps Support (exec-09 Phase 3): Liste der MCP Apps die der Agent ueber `ui://` resources rendern kann

### 6.7 A2A Delegation Log (Optional, NEU 07.04.2026)

| Source | What |
|---|---|
| `agent/a2a/` (Inter-Agent Delegation, exec-10 Phase 4) | Backend |
| NEU | UI |

`agent/a2a/` ist Scaffold fuer Inter-Agent Delegation. Wenn wir spaeter externe Agents einbinden, brauchen wir ein UI um Delegationen zu sehen.

- [ ] **6.7.1:** Backend `agent/control/a2a.py`:
  - `GET /api/v1/control/a2a/delegations?from=&to=&limit=` (Audit query mit `action='A2A_DELEGATE'`)
  - `GET /api/v1/control/a2a/agents` (registered remote agent cards)
- [ ] **6.7.2:** Frontend `/control/agents/a2a` Tab (Sub-Tab von Agents)
  - DelegationLogTable.tsx — Time, From-Agent, To-Agent, Task, Result Status, Duration
  - RemoteAgentCardsList.tsx — Agent Cards (name, capabilities, last seen)
- [ ] **6.7.3:** **Optional** — kann auch FUTURE_IDEAS sein wenn A2A nicht aktiv genutzt wird

---

## Phase 7: Integration in agent-chat/ (separater Slice oder spaeter)

**Ziel:** control-ui/ als isolierte App ist fertig. Integration in agent-chat/ ist optionaler Folge-Schritt.

> **Hinweis:** Diese Phase kann ausgelagert werden in einen Folge-Slice (exec-16 oder Teil eines Integration-Slices wie exec-06). Sie ist hier dokumentiert um den End-State zu zeigen.

### 7.1 Komponenten-Migration

- [ ] **7.1.1:** `control-ui/src/features/memory/` → `agent-chat/src/features/memory/`
- [ ] **7.1.2:** `control-ui/src/features/control/` → `agent-chat/src/features/control/`
- [ ] **7.1.3:** `control-ui/src/features/files/` → `agent-chat/src/features/files/`
- [ ] **7.1.4:** `control-ui/src/lib/kg-graph/` → `agent-chat/src/lib/kg-graph/`
- [ ] **7.1.5:** `control-ui/src/components/ui/` Komponenten zu agent-chat/src/components/ui/ mergen (nicht doppelt installieren)
- [ ] **7.1.6:** Design Tokens (DM Sans + Colors) integrieren — entweder app-weit oder als isolierter Theme-Provider fuer die neuen Surfaces

### 7.2 GlobalTopBar Pattern aktivieren

- [ ] **7.2.1:** `app/(shell)/layout.tsx` in agent-chat anpassen
- [ ] **7.2.2:** GlobalTopBar mit Surface-Buttons: Agent · Memory · Control · Files
- [ ] **7.2.3:** Routing in `app/(shell)/`

### 7.3 BFF-Routes integrieren

- [ ] **7.3.1:** `control-ui/src/app/api/memory/` → `agent-chat/src/app/api/memory/`
- [ ] **7.3.2:** `control-ui/src/app/api/control/` → `agent-chat/src/app/api/control/`
- [ ] **7.3.3:** `control-ui/src/app/api/files/` → `agent-chat/src/app/api/files/`

### 7.4 Cleanup

- [ ] **7.4.1:** `control-ui/` archivieren oder entfernen
- [ ] **7.4.2:** docker-compose.yml Eintrag fuer control-ui entfernen
- [ ] **7.4.3:** README aktualisieren

**Hinweis:** Falls die isolierte App sich als besser erweist (eigener Lifecycle, weniger Bundle-Size in agent-chat), kann Phase 7 auch entfallen — `control-ui/` bleibt dauerhaft eigenstaendig.

---

## Verify Gates Gesamt — Status pro Slice

### Slice 0: Foundation
- [x] `bun create next-app control-ui` mit Next 16.2 + bun + React 19 + TS 5.9 + Tailwind 4
- [x] DM Sans + Geist Mono via `next/font/google` in `app/layout.tsx`
- [x] supermemory dark color palette in `globals.css` (#0F1419 bg, #1B1F24 cards, etc.)
- [x] 46 shadcn/ui Komponenten kopiert aus nextjs-chat/src/components/ui/
- [x] 26 Radix peer dependencies installiert (alle shadcn primitives)
- [x] biome.json aus nextjs-chat 1:1 kopiert
- [x] tsconfig.json aus nextjs-chat (strict mode, `noUncheckedIndexedAccess: false` D11)
- [x] GlobalTopBar (40px) mit 3 Surfaces (Memory · Control · Files)
- [x] `(shell)/layout.tsx` Wrapper + 3 Routes (`/memory`, `/control`, `/files`)
- [x] `app/page.tsx` redirect auf `/memory`
- [x] `bun run typecheck` exit 0
- [x] `bun run lint` exit 0
- [ ] **Visual smoke test:** `bun run dev` auf Port 3001, alle 3 Surfaces erreichbar

### Slice 1: Files vertical
**Frontend (control-ui/):**
- [x] `control/files_surface/src/features/files/` 1:1 adoptiert
- [x] `control/files_surface/src/app/(shell)/files/` 1:1 adoptiert
- [x] `control/files_surface/src/app/api/files/` 1:1 adoptiert (BFF routes)
- [x] `lib/server/{file-audit, gateway}` + `lib/storage/profile-key` + `lib/utils.ts` adoptiert
- [x] `lib/action-classes.ts` (RBAC + Action classes)
- [x] DocumentViewer migriert auf `react-pdf` v10 (statt `@react-pdf-viewer/core` v3)
- [x] React Query Provider gewired (UploadDropzone + DocumentViewer brauchen useQuery)
- [x] `wavesurfer.js`, `hls.js`, `react-dropzone`, `fuse.js` installiert

**Backend (go-appservice/):**
- [x] `internal/storage/*.go` (9 files) 1:1 vom Hauptprojekt adoptiert: types, service, signer, metadata_store{,_factory,_postgres}, object_store_env, provider_{filesystem,s3}
- [x] `internal/handlers/http/artifact_handler.go` adoptiert (Imports `tradeviewfusion` → `matrix/go-appservice` umgeschrieben)
- [x] `internal/contracts/common.go` (APIResponse[T]) als Mini-Stub adoptiert
- [x] `internal/requestctx/request_id.go` als Mini-Stub adoptiert
- [x] **NEU:** `internal/app/storage_wiring.go` mit env helpers (`envOr`, `intOr`, `boolOr`, `durationMsOr`, `isProductionRuntime`) + `artifactSigningSecretFromEnv` + `artifactGatewayBaseURLFromEnv` + `BuildArtifactService(host, port)` factory
- [x] `internal/handler/server.go` patched: `app.BuildArtifactService(...)` Aufruf, 3 Routes (`/api/v1/storage/artifacts/upload-url`, `/upload/`, `/artifacts/`), `s.artifactStore` Field fuer `Stop()` Cleanup, `os` import + `storage.ArtifactMetadataStore` Type
- [x] `go.mod` mit `aws-sdk-go-v2/{aws,config,credentials,service/s3}` + `jackc/pgx/v5` via `go mod tidy`
- [x] `golangci-lint run --build-tags goolm`: **0 issues**
- [x] `go build -tags goolm ./...`: clean
- [x] **Postgres Schema:** `metadata_store_postgres.go` macht self-migration on init (kein eigener Alembic noetig fuer Storage)

**ENV (matching main project naming):**
- [x] `go-appservice/.env.development` mit `ARTIFACT_STORAGE_*` (PROVIDER, BASE_DIR, S3_*, METADATA_PROVIDER + DB_PATH, SIGNED_URL_TTL_MS, SIGNING_SECRET, PUBLIC_BASE_URL)
- [x] `go-appservice/.env.example` selbe Variablen
- [x] `python-backend/.env` + `.env.example` mit D12 doc + `ARTIFACT_GATEWAY_BASE_URL` (Python hat KEINE direkten S3 credentials)

**Devstack:**
- [x] `tools/seaweedfs/weed.exe` (144 MB, gitignored)
- [x] `tools/seaweedfs/s3.json` mit `matrix-local` user (Admin/Read/Write/List/Tagging)
- [x] `tools/seaweedfs/Dockerfile` (optional fuer container-Builds)
- [x] `dev-stack2.ps1`:
  - `$controlUiDir`, `$seaweedExe`, `$seaweedDataDir` Variablen
  - `-SkipControlUi` switch (opt-out, default ON)
  - `-SkipStorage` switch (opt-out, default ON)
  - SeaweedFS als Tier `infra` (Port 8333)
  - control-ui als Tier `app` (Port 3001)
  - Stack-Status output mit beiden URLs
- [x] `.gitignore` ergaenzt: `tools/seaweedfs/weed.exe`, `tools/seaweedfs/data/`, `control-ui/.next/`, `node_modules/`, `.env.local`

**Tuwunel ↔ SeaweedFS:** Bewusst getrennt — Tuwunel bleibt RocksDB-backed fuer Matrix Protocol Media (mxc:// URIs), SeaweedFS ist nur fuer control-ui /files Surface + Ingestion. Optionaler Bridge in FUTURE_IDEAS (NATS subscriber auf `m.file`/`m.image` events → SeaweedFS mirror).

**E2E (noch zu testen):**
- [ ] PDF Upload via `/files/uploads` → SeaweedFS Bucket → `/files/documents` Liste → react-pdf preview
- [ ] `gateway.ts` Default Port pruefen (zeigt aktuell auf 9060/main project, sollte 8090/matrix sein)
- [ ] Audit Event Schreibung pruefen (FileAuditLog → agent.audit_events)
- [ ] Devstack `dev-stack2.ps1` startet alle Services inkl. SeaweedFS lauffaehig

### Slice 2: Content Ingestion (3-Venv Architektur, D13-D17)

**Frontend (control-ui/) — DONE:**
- [x] AddMemoryModal mit 4 Tabs (Note · Link · File · Bridge) — supermemory `add-document/index.tsx` Pattern
- [x] NoteEditor (Tiptap) — adoptiert von nextjs-chat WysiwygEditor (Mentions raus, simpler)
- [x] QuickNoteCard (1:1 von supermemory) auf MemoryPage als Top-Widget
- [x] HighlightsCard (1:1 von supermemory) auf MemoryPage als Top-Widget
- [x] FullscreenNoteModal (1:1 von supermemory, Tiptap statt supermemory's text-editor/)
- [x] Bridge Tab zeigt 4 Bridges (Matrix active, Slack/Discord/Telegram pending exec-05b)

**Backend Venv 2: `python-backend/ingestion/` (NEU, eigene venv):**
- [ ] `pyproject.toml` mit eigenen Deps (pymupdf4llm, langchain-text-splitters, sentence-transformers, fastapi, httpx, psycopg, python-magic-bin, loguru)
- [ ] `uv sync` in `python-backend/ingestion/` → eigene `.venv/`
- [ ] `core/{types,exceptions,config}.py` — ExtractedDocument/Chunk/Job dataclasses (von paperwatcher base.py 1:1)
- [ ] `detectors/{base,extension,magic,registry}.py` — file type detection
- [ ] `loaders/{base,local,seaweedfs,http,registry}.py` — bytes loading
- [ ] `extractors/base.py` ← paperwatcher `doc_extractor/base.py` (ABC + Dataclasses)
- [ ] `extractors/pymupdf_ext.py` ← paperwatcher 1:1 (primary, CPU)
- [ ] `extractors/{markdown,html,csv,note,code}_ext.py` NEU (trivial)
- [ ] `extractors/registry.py` (mime → extractor map)
- [ ] `normalizers/{markdown_cleaner,section_detector,language_detector}.py`
- [ ] `chunkers/token_chunker.py` ← paperwatcher chunking.py adaptiert
- [ ] `chunkers/{section_chunker,semantic_chunker}.py` (Stub fuer Phase 2)
- [ ] `embedders/sentence_transformer.py` (all-MiniLM-L6-v2, default)
- [ ] `sinks/hindsight_sink.py` (importiert `memory_engine.episodic_store`)
- [ ] `sinks/storage_sink.py` (Metadata-only update)
- [ ] `sinks/kg_sink.py` (Stub: HTTP POST → Port 8099, returnt skip in Phase 1)
- [ ] `tracking/{jobs,dedup,audit,progress}.py`
- [ ] `clients/go_storage.py` — GoStorageClient (httpx, D12 signed URLs)
- [ ] `pipelines/{base,document,note,link,batch}.py` — Composer
- [ ] `worker.py` — FastAPI App (Port 8098) mit POST /ingest/document, /ingest/note, GET /status, /jobs/{id}, POST /jobs/{id}/retry
- [ ] `cli.py` — manuelles Debugging

**Backend Venv 3: `python-backend/kg_pipeline/` (Skeleton, kein uv sync):**
- [ ] `pyproject.toml` (torch==2.3.1, relik, glirel, gliner, fastapi)
- [ ] `core/{types,exceptions,config}.py` Skeleton
- [ ] `preprocessors/`, `extractors/`, `filters/`, `normalizers/`, `sinks/` Stub-Files
- [ ] `pipelines/document.py` Stub (raise NotImplementedError)
- [ ] `server.py` FastAPI Stub (Port 8099, returns 503 "kg_pipeline not yet activated")
- [ ] `cli.py` Stub
- [ ] `README.md` mit Phase 2 Aktivierungs-Anleitung

**Retrieval Skeleton: `python-backend/retrieval/` (in Venv 1):**
- [ ] Verzeichnis-Struktur mit `__init__.py` (core, understanders, searchers, rerankers, verifiers, composers, pipelines)
- [ ] `api.py` mit `async def retrieve(query): raise NotImplementedError`
- [ ] `README.md` mit Phase 3 Adoption-Map

**Main Venv 1 — agent/control/ingestion.py (thin proxy, KEIN ingestion import):**
- [ ] `agent/control/ingestion.py` mit 3 httpx proxy routes zu http://127.0.0.1:8098
- [ ] `agent/control/router.py` mounted neuer router
- [ ] Alembic Migration `005_ingestion_jobs.py` in main venv (CREATE SCHEMA ingestion + table jobs)
- [ ] **Decoupling Verification:** `grep -r "from agent" python-backend/ingestion/` muss leer sein

**Devstack:**
- [ ] `dev-stack2.ps1`: neuer Service `ingestion-worker` (Tier `agent`, depends_on postgres, eigene venv)
- [ ] `-SkipIngestion` switch (opt-out, default ON)
- [ ] `INGESTION_WORKER_URL=http://127.0.0.1:8098` in `python-backend/.env` (fuer agent runtime → worker)

**E2E (zu testen):**
- [ ] PDF Upload via control-ui /memory AddMemoryModal File-Tab → SeaweedFS → ingestion-worker (8098) → Hindsight Memory in < 30s
- [ ] Note via AddMemoryModal Note-Tab → ingestion `pipelines/note.py` → Hindsight in < 5s
- [ ] Suche im Agent-Chat findet Inhalt aus PDF
- [ ] Zweiter Upload derselben PDF → `INGESTION_DEDUP` audit event, kein Duplicate
- [ ] ingestion-worker shutdown, agent runtime laeuft weiter (decoupling validation)
- [ ] agent runtime shutdown, ingestion-worker laeuft weiter (decoupling validation)

### Slice 3: Memory Browser
- [x] EpisodesGrid mit `masonic` (Masonry pattern aus supermemory `memories-grid.tsx`)
- [x] EpisodeCard (Polymorphic, von `note-preview.tsx`)
- [x] EpisodeFilterBar (filter-pills 1:1 aus memories-grid.tsx, Roles statt Categories)
- [x] EpisodeDetailSheet (von `document-modal/index.tsx`, shadcn Sheet)
- [x] MemoryHealthCards (3 Layer-Cards, neu)
- [x] MemoryTopNav (5 Sub-Tabs)
- [x] search-params.ts (1:1 von supermemory `lib/search-params.ts`)
- [x] URL state via nuqs (Filter persistent, back/forward funktioniert)
- [x] Mock-Data fuer 10 Episodes mit 6 Trading Rollen
- [ ] **Backend:** `agent/control/memory.py` — `GET /api/v1/control/memory` (Layer Health)
- [ ] **Backend:** `agent/control/episodes.py` — Faceted Query API
- [ ] **Backend:** `WHERE user_id = 'local'` (D3 Multi-tenancy preparation)
- [ ] **Backend:** `DELETE /api/v1/control/episodes/{id}` mit Approval Flow
- [ ] **E2E:** > 50 Episodes fluessig in Grid + Table Mode
- [ ] **E2E:** Filter URL-persistent
- [ ] **E2E:** Click Episode → Sheet zeigt Input/Tools/Output korrekt

### Slice 4: KG Visualization
- [x] **Episode-Memory Graph** (`/memory/graph`): supermemory `memory-graph` package 1:1 in `control-ui/src/lib/kg-graph/`
- [x] KGGraphPage Wrapper mit Mock-Data (30 documents, 1-4 memories each)
- [x] **Trading Knowledge Graph** (`/memory/kg`): NEU mit `@xyflow/react` (react-flow)
- [x] 6 Custom Node Components (Stratagem · Regime · TransmissionChannel · Asset · Institution · BTEMarker)
- [x] 6 typed edges (causes · inhibits · activates · precedes · transmits · signals) mit unterschiedlichen Stilen
- [x] KGNodeBase als shared base, je nach type unterschiedliche shape (rect/hexagon/circle/diamond/star)
- [x] KGLegend Komponente (Bottom-Left overlay)
- [x] Mock-Data: 17 Trading nodes + 19 typed edges
- [x] Auto-layout by node type (lanes)
- [ ] **Backend:** `agent/control/kg_crud.py` — REST endpoints fuer Kuzu CRUD
- [ ] **Backend:** Cypher-Sanitization aus exec-11 Code-Review #2 wiederverwenden
- [ ] **Backend:** `POST /api/v1/control/kg/seed` ruft `memory_engine/seed_data.py`
- [ ] **E2E:** Episode-Memory Graph rendert > 100 Nodes mit > 30 FPS
- [ ] **E2E:** Trading KG mit echten Kuzu-Daten (Stratagems aus seed_data.py)
- [ ] **E2E:** Click Node → Detail Panel rechts (TBD)
- [ ] **E2E:** Filter im Trading KG (Type/Date/Confidence)

### Slice 5: Agent Configuration
- [ ] Alembic Migration `003_agent_role_overrides.py` (D1)
- [ ] Alembic Migration `004_consent_overrides.py` (D2)
- [ ] `agent/control/agents.py` Backend
- [ ] `agent/roles.py` Loader patch — merged Default + DB Overlay
- [ ] `agent/consent/provider.py` erweitern — Cache mit 5s TTL + reload()
- [ ] `agent/control/consent.py` Backend (Permission Matrix CRUD)
- [ ] `agent/control/skills.py` Backend (3-Tier Skills)
- [ ] **5.4 NEU:** `agent/control/sandbox.py` Backend (sandbox runs query, active containers, stats)
- [ ] **5.5 NEU:** `agent/control/tools.py` Backend (registry list, schemas, per-role config, stats)
- [ ] **Frontend:** RoleEditorSheet mit shadcn Sheet
- [ ] **Frontend:** PermissionMatrix (6x7 Grid mit cycle-on-click)
- [ ] **Frontend:** SkillsTabs (3 Sections: Global / Team / Personal)
- [ ] **Frontend:** SkillDetailSheet mit Markdown render
- [ ] **Frontend:** PersonalSkillEditor mit Tiptap (uses NoteEditor)
- [ ] **Frontend:** ImportSkillDialog (von GitHub URL)
- [ ] **5.4 NEU Frontend:** SandboxRunsTable + SandboxRunDetailSheet + SandboxStatsCard
- [ ] **5.5 NEU Frontend:** ToolsRegistryGrid + ToolDetailSheet
- [ ] **E2E:** Trading Role TRADER System Prompt editiert → Save → naechster Tool-Call nutzt neuen Prompt
- [ ] **E2E:** Reset to Default Button: Overlay weg, Default zurueck
- [ ] **E2E:** Permission Matrix Cell click → Cache reload → naechster Tool-Call sieht neue Policy
- [ ] **E2E:** Skill enable/disable wirksam ohne Backend-Restart
- [ ] **E2E:** GitHub Import einer Test-Skill funktioniert
- [ ] **E2E:** Sandbox Run mit Detail Sheet zeigt stdout/stderr/files
- [ ] **E2E:** Tool Registry zeigt alle 15 Tools mit Schema, Per-Role Toggle wirkt

### Slice 6: System Observability
- [ ] `agent/control/settings.py` Backend
- [ ] `GET /api/v1/control/system/health` pingt Postgres + NATS + LiveKit + OpenSandbox + Memory Engine + Sandbox Provider + SeaweedFS
- [ ] `GET /api/v1/control/system/env` mit Sanitization (sensitive keys masked)
- [ ] `agent/control/audit.py` mit Pagination + Filter
- [ ] **6.5 NEU:** `agent/control/sessions.py` Backend (LangGraph checkpointer query, kill action)
- [ ] **6.6 NEU:** `agent/control/mcp.py` Backend (FastMCP introspection)
- [ ] **6.7 OPT:** `agent/control/a2a.py` Backend (Audit query + Agent Cards)
- [ ] **Frontend:** SystemHealthDashboard mit Auto-Refresh 30s
- [ ] **Frontend:** ENVViewerTab mit SectionTitle+Card Pattern
- [ ] **Frontend:** AuditLogTable mit Filter Bar + Export CSV/JSON
- [ ] **6.5 NEU Frontend:** SessionsTable + SessionDetailSheet + KillSessionConfirmDialog
- [ ] **6.6 NEU Frontend:** MCPStatusCard + MCPExposedToolsList + MCPClientsList
- [ ] **6.7 OPT Frontend:** DelegationLogTable + RemoteAgentCardsList
- [ ] **E2E:** `/control/system` zeigt korrekt online/offline aller Services
- [ ] **E2E:** ENV Viewer zeigt sensitive keys maskiert (`••••XXXX`)
- [ ] **E2E:** Audit Log zeigt Events aus Slices 1-5
- [ ] **E2E:** Sessions Tab zeigt aktive LangGraph threads, Kill funktioniert
- [ ] **E2E:** MCP Tab zeigt FastMCP exposed tools

### Slice 7: Two-Tier UI + Full Backend Wiring + Hash Reindex (DONE 08.04.2026)

**Frontend Phase A — Two-Tier UI:**
- [x] `useControlMode` hook (URL param `?mode=dev` + localStorage, D20)
- [x] `ModeToggle` component in ControlTopNav (right side)
- [x] `OverviewTab.tsx` (TT1 — AI Health, counters, recent activity, last error, Memory/KG link cards)
- [x] `SecurityTab.tsx` (TT8 — 4-pillar posture score, recent security events, access list)
- [x] `ApiModelsTab.tsx` (fused ENV + LLM Providers + Model Routing + Utility Models)
- [x] `ControlTopNav` mode-filtered: 7 User Mode tabs + 6 Dev Mode tabs (Separator)
- [x] `ControlPage` routing updated for /control/overview, /api, /security
- [x] `EnvViewerTab.tsx` deleted (replaced by ApiModelsTab)

**Backend Phase F — Migrations (5 new, chain 001→007):**
- [x] `003_chunk_hashes.py` (ingestion.chunk_hashes for hash-based reindex)
- [x] `004_agent_role_overrides.py` (D1 DB Overlay)
- [x] `005_consent_overrides.py` (D2 DB Overlay + Hot-Reload)
- [x] `006_a2a_delegations.py` (persistent A2A log)
- [x] `007_audit_indexes.py` (timestamp DESC, action, user+action composite)

**Backend Phase B — Memory/Episodes/KG (3 control modules, Hindsight-driven):**
- [x] `agent/control/memory.py` — `/memory/health` (episodic + vector via Hindsight list_memory_units, kg via memory_engine/kg_store), `/memory/banks`. **Returns frontend-compatible `{layers: []}` shape (Phase J fix).**
- [x] `agent/control/episodes.py` — `/episodes` faceted list (fact_type + search via Hindsight, role/session/date/tags/confidence client-side filter), `/episodes/{id}`, DELETE `/episodes/{id}`. Uses Hindsight `list_memory_units`/`get_memory_unit`/`delete_memory_unit`.
- [x] `agent/control/kg_crud.py` — full CRUD: GET/POST/PATCH/DELETE `/kg/nodes`, `/kg/edges`, `/kg/seed`. Backend uses memory_engine/kg_store.py with new CRUD methods.
- [x] `memory_engine/episodic_store.py` — extended with filters, get, delete, patch (legacy, marked).
- [x] `memory_engine/kg_store.py` — `ALLOWED_NODE_TYPES` + `ALLOWED_EDGE_TYPES` whitelists, `KuzuKGStore.get_node()`, `create_node()`, `update_node()`, `delete_node()`, `list_edges()`, `create_edge()`, `delete_edge()`, `node_count_by_type()` (Cypher sanitization reused from Code-Review #2).

**Backend Phase C — Agent Configuration (5 control modules):**
- [x] `agent/control/agents.py` — `/agents` list/get/patch/reset with `agent_role_overrides` DB merge, 6 TradingRole defaults (fundamentals_analyst, sentiment_analyst, technical_analyst, researcher, trader, risk_manager)
- [x] `agent/control/permissions.py` — `/permissions/matrix`, `/permissions/cell` (PATCH/DELETE), `/permissions/reload`. 5s TTL cache with thread-safe lock (Phase J fix).
- [x] `agent/control/skills.py` — `/skills` (wraps `agent/skills/loader.py:load_skills`), `/skills/{id}` detail, `/skills/{id}` PATCH stub
- [x] `agent/control/tools.py` — `/tools` aggregates builtin + MCP introspection + call stats from `agent.audit_events` GROUP BY tool_name
- [x] `agent/control/sandbox.py` — `/sandbox/runs` queries audit_events for `SANDBOX_EXEC`/`SANDBOX_PYTHON`/`SANDBOX_BROWSER`/`SANDBOX_BASH`

**Backend Phase D — Observability (7 control modules):**
- [x] `agent/control/system.py` — `/system/health` concurrent httpx pings (postgres, seaweedfs, tuwunel, go-appservice, ingestion-worker, kg-pipeline, extraction-layout, opensandbox) + psycopg postgres ping
- [x] `agent/control/audit.py` — `/audit` filtered query (action/user/thread/role/tool_name/success/from/to/limit/offset), `/audit/{id}`
- [x] `agent/control/sessions.py` — `/sessions` raw SQL on `public.checkpoints` table, `/sessions/{thread_id}`, DELETE kill. Table existence check via `information_schema`.
- [x] `agent/control/mcp.py` — `/mcp/servers` introspects matrix-internal FastMCP, `/mcp/servers/{id}/tools`
- [x] `agent/control/a2a.py` — `/a2a/delegations` queries `agent.a2a_delegations` table with status/thread filters
- [x] `agent/control/security.py` — `/security/posture` (4 pillars: Auth, Encryption, Audit, Network with real env checks + audit count query), `/security/events` mit `_ACTION_TO_EVENT_TYPE` mapping (Phase J fix)
- [x] `agent/control/models.py` — `/models/providers` (7 providers with api_key masked), `/models/routing`, `/models/utility`, `/models/env` (12 exposed env vars with sensitive masking)
- [x] `agent/control/overview.py` — `/overview` aggregates active_sessions (distinct thread_ids last hour), active_tasks (running status), memory_facts_total (Hindsight), kg_nodes_total (Kuzu), last_agent_error (audit_events), recent_activity (last 8 events), ai_health (ingestion-worker ping)
- [x] `agent/audit/store.py` — query() extended with date range + role + success filters
- [x] **55 total control routes** registered in `agent/control/router.py` (verified via `uv run python -c "from agent.control.router import router; print(len(...))"`)

**Backend Phase E — Hash-based Incremental Reindex (Cursor IDE / paperwatcher merkle pattern):**
- [x] `ingestion/tracking/dedup.py` — `DocumentHasher.hash_chunk()` for per-chunk sha256
- [x] `ingestion/tracking/jobs.py` — `save_chunk_hashes()`, `get_chunk_hashes_by_doc()`, `delete_chunk_hashes_by_doc()`
- [x] `ingestion/pipelines/document.py` — `smart_reindex()` method: compute new hashes → diff vs stored manifest → only embed changed chunks → delete removed → save new manifest → emit `INGESTION_INCREMENTAL_REINDEX` audit event with `savings_pct`
- [x] `ingestion/sinks/hindsight_sink.py` — `delete_by_hashes()` via raw SQL on `hindsight.chunks` → `hindsight.memory_units`
- [x] `ingestion/worker.py` — `POST /ingest/document/{file_id}/reindex` endpoint
- [x] `agent/control/ingestion.py` — thin proxy route for reindex

**Go Phase G — /api/v1/control/* Proxy:**
- [x] `go-appservice/internal/handlers/http/control_proxy_handler.go` — `ControlProxyHandler` pattern 1:1 wie McpProxyHandler, preserves body+query+headers (except Host), forwards to AgentServiceURL (:8094)
- [x] `go-appservice/internal/handler/server.go` — `mux.HandleFunc("/api/v1/control/", agenthttp.ControlProxyHandler(cfg.AgentServiceURL))` registered
- [x] `go build -tags goolm ./...` clean
- [x] `golangci-lint run --build-tags goolm` **0 issues**

**Frontend Phase H — BFF + useQuery Migration:**
- [x] `control-ui/src/app/api/control/[...path]/route.ts` — catch-all BFF for all 54 control endpoints
- [x] `control-ui/src/app/api/memory/[...path]/route.ts` — catch-all BFF with path mapping (`memory/health → control/memory/health`, `memory/episodes → control/episodes`, `memory/kg → control/kg`)
- [x] `control-ui/src/lib/server/control-proxy.ts` — shared fetch helper with `duplex: "half"` body streaming
- [x] `control-ui/src/lib/server/gateway.ts` — default port corrected to 8090 (matrix go-appservice, not tradeview-fusion 9060)
- [x] `control-ui/src/lib/queries/client.ts` — `apiGet/apiPost/apiPatch/apiDelete` typed fetchers with `ApiError` class
- [x] `control-ui/src/lib/queries/control.ts` — query key factories + fetchers for all 13 control areas + memory
- [x] `control-ui/src/lib/queries/hooks.ts` — **17 typed React Query hooks** (`useOverview`, `useAgents`, `usePermissionMatrix`, `useToolCategories`, `useSkills`, `useTools`, `useSandboxRuns`, `useSystemHealth` with 30s auto-refresh, `useLlmProviders`, `useModelRouting`, `useUtilityModels`, `useEnvVars`, `useAuditEvents`, `useSessions`, `useMcpServers`, `useA2ADelegations`, `useSecurityPosture`, `useMemoryHealth`, `useEpisodes`)
- [x] **All 13 Control Tabs migrated** to `useQuery + mock fallback` pattern: Overview, Agents, Permissions, Skills, Sandbox, Tools, System, ApiModels, Audit, Sessions, Mcp, A2a, Security
- [x] **Memory surfaces migrated**: MemoryPage (useEpisodes), EpisodesGrid (useEpisodes), MemoryHealthCards (useMemoryHealth)

**Phase J — Code Review Fixes (applied after code-reviewer audit):**
- [x] **C1 memory.health shape** — backend now returns `{layers: []}` array with `{type, provider, health, item_count, last_sync_at, consolidation_pending}` matching frontend `MemoryOverviewResponse`
- [x] **C2 TradingRole enum** — frontend `types.ts` + all mocks updated to `fundamentals_analyst | sentiment_analyst | technical_analyst | researcher | trader | risk_manager` matching backend
- [x] **C3 Session type** — frontend `Session` interface made optional for rich fields (backend returns minimal `thread_id + last_checkpoint + checkpoint_count + is_active`); SessionsTab conditional rendering
- [x] **H4 SecurityEventType mapping** — backend `security.py` now maps audit actions via `_ACTION_TO_EVENT_TYPE` to frontend enum
- [x] **H5 permissions cache thread-safety** — `_OverlayCache.get()` holds lock across read + refresh
- [x] **H7 last_agent_error.role** — frontend type loosened from `TradingRole` to `string`
- [x] **M8 SecurityTab null guard** — `formatRelative()` guards null/NaN; backend `access_list` uses current timestamp instead of None

---

### Phase I: Devstack E2E + Smoke Tests (pending)

**Prerequisites:**
- [ ] **P0:** Postgres (:5433) running → `scripts/dev-stack2.ps1 -SkipFrontend -SkipControlUi` (infra only first, verify)
- [ ] **P1:** `cd python-backend && uv run alembic upgrade head` → migrations 001-007 applied (verify via `psql -c "\dt agent.*, ingestion.*"`)
- [ ] **P2:** `cd python-backend/ingestion && uv sync && uv pip install -e .` → verify ingestion package installed
- [ ] **P3:** `.\scripts\dev-stack2.ps1` (full run) → all services register + start without errors
- [ ] **P4:** Port availability check — 5433, 4222, 8333, 8448, 8090, 8094, 8097, 8098, 8100, 3001 all bound

**Service Health (all must return 200):**
- [ ] **H1:** `curl http://127.0.0.1:8090/health` → go-appservice ok
- [ ] **H2:** `curl http://127.0.0.1:8094/health` → agent-service ok
- [ ] **H3:** `curl http://127.0.0.1:8098/health` → ingestion-worker ok (kg_pipeline_enabled in response)
- [ ] **H4:** `curl http://127.0.0.1:8099/health` → kg-pipeline-worker returns skeleton status (Phase 1 stub)
- [ ] **H5:** `curl http://127.0.0.1:8101/health` → extraction-layout-worker returns skeleton status
- [ ] **H6:** `curl http://127.0.0.1:8333` → seaweedfs S3 API reachable
- [ ] **H7:** `curl http://127.0.0.1:3001/` → control-ui Next dev server serving

**Backend Control API Smoke (via Go Proxy → Python):**
- [ ] **A1:** `curl http://127.0.0.1:8090/api/v1/control/memory/health` → `{layers: [episodic, kg, vector]}` with `health: ok|degraded|error`
- [ ] **A2:** `curl http://127.0.0.1:8090/api/v1/control/episodes?limit=5` → `{items: [], total: 0}` (empty if no ingestion yet)
- [ ] **A3:** `curl http://127.0.0.1:8090/api/v1/control/agents` → `{items: [6 roles], total: 6}` with all fundamentals_analyst/sentiment_analyst/etc.
- [ ] **A4:** `curl http://127.0.0.1:8090/api/v1/control/permissions/matrix` → 42 cells (6 roles × 7 categories)
- [ ] **A5:** `curl http://127.0.0.1:8090/api/v1/control/skills` → list from loader
- [ ] **A6:** `curl http://127.0.0.1:8090/api/v1/control/tools` → builtin + MCP tools
- [ ] **A7:** `curl http://127.0.0.1:8090/api/v1/control/system/health` → 11 services with health field each
- [ ] **A8:** `curl http://127.0.0.1:8090/api/v1/control/audit?limit=5` → `{items, total}` (may be empty)
- [ ] **A9:** `curl http://127.0.0.1:8090/api/v1/control/sessions` → `{items: []}` or checkpoints if agent ran
- [ ] **A10:** `curl http://127.0.0.1:8090/api/v1/control/mcp/servers` → at least matrix-internal server
- [ ] **A11:** `curl http://127.0.0.1:8090/api/v1/control/a2a/delegations` → empty (table just created)
- [ ] **A12:** `curl http://127.0.0.1:8090/api/v1/control/overview` → `{ai_health, active_sessions, memory_facts_total, kg_nodes_total, ...}`
- [ ] **A13:** `curl http://127.0.0.1:8090/api/v1/control/security/posture` → `{overall_score: int, pillars: [4], recent_events, access_list}`
- [ ] **A14:** `curl http://127.0.0.1:8090/api/v1/control/models/providers` → 7 providers with api_key_set masked
- [ ] **A15:** `curl http://127.0.0.1:8090/api/v1/control/kg/nodes?limit=5` → `{items, total}` (empty before seed)
- [ ] **A16:** `curl -X POST http://127.0.0.1:8090/api/v1/control/kg/seed` → `{status: ok, ...}`
- [ ] **A17:** Then `curl .../kg/nodes?type=Stratagem` → items > 0

**Ingestion E2E (Document):**
- [ ] **I1:** Upload test PDF via control-ui `/files/uploads` → SeaweedFS PUT succeeds (network tab shows signed URL flow)
- [ ] **I2:** File appears in control-ui `/files/documents` list (via BFF → Go Gateway → artifact_handler)
- [ ] **I3:** react-pdf preview renders the uploaded PDF in DocumentViewer
- [ ] **I4:** `curl -X POST http://127.0.0.1:8090/api/v1/control/ingest/document -d '{"file_id":"<uuid>","user_id":"local","tags":["test"]}'` → 200 accepted
- [ ] **I5:** `psql -c "SELECT id, status, chunks_total FROM ingestion.jobs ORDER BY started_at DESC LIMIT 1;"` → job shows `status=done` within 30s
- [ ] **I6:** `psql -c "SELECT COUNT(*) FROM ingestion.chunk_hashes WHERE doc_id = '<uuid>';"` → > 0 (manifest saved for Phase E)
- [ ] **I7:** `curl http://127.0.0.1:8090/api/v1/control/episodes?limit=5` → at least 1 item (PDF chunks in Hindsight)
- [ ] **I8:** Frontend `/memory` shows the new episode in the grid (useEpisodes query returns real data)
- [ ] **I9:** Click episode → Detail Sheet opens with chunk content
- [ ] **I10:** Audit event in `/control/audit` with action `INGESTION_DONE` + metadata.chunks

**Ingestion E2E (Note):**
- [ ] **I11:** Via control-ui `/memory` → AddMemoryModal → Note tab → type text → Save → BFF POST `/api/control/ingest/note`
- [ ] **I12:** Note appears in `/memory` episodes grid immediately (< 5s)
- [ ] **I13:** Second identical note → `INGESTION_DEDUP` event (sha256 match)

**Hash-Based Reindex Smoke:**
- [ ] **R1:** Upload identical PDF again → `INGESTION_DEDUP` event (full-file sha256 hit)
- [ ] **R2:** Modify 1 paragraph in PDF, upload → `/ingest/document/{file_id}/reindex` (triggered manually or via frontend reindex button)
- [ ] **R3:** Audit event `INGESTION_INCREMENTAL_REINDEX` with `metadata.savings_pct > 0.9`
- [ ] **R4:** `psql -c "SELECT COUNT(*) FROM ingestion.chunk_hashes WHERE doc_id = '<uuid>';"` matches new chunk count (manifest updated)

**Mode Toggle UI:**
- [ ] **U1:** Open `http://127.0.0.1:3001/control` → default User Mode, 7 tabs visible (Overview, Agents, Permissions, Skills, Tools, Sessions, Security)
- [ ] **U2:** Click Developer toggle → 6 extra tabs appear (System, API/Models, Sandbox, Audit, MCP, A2A) with separator
- [ ] **U3:** Hard refresh page → mode persisted via localStorage (still Dev Mode)
- [ ] **U4:** Navigate to `http://127.0.0.1:3001/control?mode=user` → switches to User Mode in URL
- [ ] **U5:** Share URL with `?mode=dev` param → opens in Developer Mode

**Permission Matrix Live Edit (D2 Pattern):**
- [ ] **PM1:** `/control/permissions` matrix renders with 42 cells, 6 roles × 7 categories
- [ ] **PM2:** `curl -X PATCH http://127.0.0.1:8090/api/v1/control/permissions/cell -d '{"role_id":"trader","category_id":"trading","level":"deny"}'` → 200
- [ ] **PM3:** `psql -c "SELECT level FROM agent.consent_overrides WHERE role_id='trader' AND category_id='trading';"` → `deny`
- [ ] **PM4:** `curl .../permissions/matrix` → cell is_overridden=true level=deny
- [ ] **PM5:** `curl -X POST .../permissions/reload` → `{status: cache_invalidated}`

**Agent Role Overlay Live (D1 Pattern):**
- [ ] **AR1:** `/control/agents` shows 6 trading roles
- [ ] **AR2:** `curl -X PATCH http://127.0.0.1:8090/api/v1/control/agents/trader -d '{"system_prompt":"Test override","updated_by":"local"}'` → 200
- [ ] **AR3:** `psql -c "SELECT field, value FROM agent.agent_role_overrides WHERE role_id='trader';"` → row exists with field=system_prompt
- [ ] **AR4:** `curl .../agents/trader` → merged response has is_default=false
- [ ] **AR5:** `curl -X DELETE .../agents/trader/overrides/system_prompt` → overlay removed, is_default=true

**Decoupling Stress Tests:**
- [ ] **DC1:** `bash scripts/check_ingestion_decoupling.sh` → PASS (no `from agent` imports in ingestion/extraction_layout/kg_pipeline/retrieval)
- [ ] **DC2:** Kill `agent-service` process (port 8094) → ingestion-worker + go-appservice + control-ui stay responsive
- [ ] **DC3:** Kill `ingestion-worker` (port 8098) → agent-service stays up, `/control/ingestion/health` returns 503 cleanly (no crash)
- [ ] **DC4:** Kill `go-appservice` (port 8090) → control-ui BFF shows "backend offline" banner via mock fallback

**Frontend Type Checks:**
- [ ] **FT1:** `cd control-ui && bun run typecheck` → exit 0
- [ ] **FT2:** `bun run lint` → 0 errors (warnings OK in adopted code)

**Backend Code Quality:**
- [ ] **BC1:** `cd python-backend && uv run ruff check agent/control/ memory_engine/ ingestion/` → no critical issues
- [ ] **BC2:** `cd go-appservice && golangci-lint run --build-tags goolm` → 0 issues
- [ ] **BC3:** `cd python-backend && uv run pytest tests/ -k "control" --no-header` → all tests pass (when added)

---

### Phase K Verify Gates (Code Gaps K1-K10) — pending devstack

Code-level gates (no devstack needed — verified after Phase K closes):

- [x] **CG1:** `cd control-ui && bun run typecheck` → exit 0 (verified 08.04.2026 after K10)
- [x] **CG2:** `bun run lint` → 0 errors (8 pre-existing warnings in `lib/kg-graph/hooks/use-graph-theme.ts`)
- [x] **CG3:** `cd python-backend && uv run python -c "from agent.control.router import router; assert any('/kg/graph' in r.path for r in router.routes)"` → passes (K4 endpoint)
- [x] **CG4:** `grep -rn 'coming next\|coming in Slice\|disabled.*Slice 5 backend\|TODO Slice 4.5' control-ui/src/features/memory/ control-ui/src/features/control/` → empty (all placeholders gone)

**Slice 2 Pipeline Status Dashboard (K1 — `/memory/ingestion`):**
- [ ] **K1.1:** Navigate to `/memory/ingestion` → 5 stat cards visible (Total, Done, Running, Pending, Failed)
- [ ] **K1.2:** Counts poll every 2s — visible via DevTools network panel (`GET /api/control/ingestion/status`)
- [ ] **K1.3:** Trigger a failing job (e.g. upload corrupted PDF) → Failed count increments within 2s
- [ ] **K1.4:** Click Retry on failed job → calls `POST /api/control/ingest/document/{file_id}/reindex` → success toast
- [ ] **K1.5:** After retry, status transitions visible (failed → running → done)

**Slice 3 Timeline + Delete (K2, K3):**
- [ ] **K2.1:** Navigate to `/memory?view=timeline` → vertical timeline rendered with episodes grouped by day
- [ ] **K2.2:** Day labels show "Today", "Yesterday", or `EEEE, MMMM d` for older days
- [ ] **K2.3:** Each timeline entry has role-colored marker dot, role label, time, tool count, duration, up to 3 tags
- [ ] **K2.4:** Timeline renders smoothly with > 100 episodes (no perceptible lag)
- [ ] **K2.5:** Switch back to grid (`?view=grid`) → MemoryTimelineView unmounts cleanly
- [ ] **K3.1:** Click episode in any view → EpisodeDetailSheet opens with full content
- [ ] **K3.2:** Click Delete button → AlertDialog confirmation appears with episode preview
- [ ] **K3.3:** Click Cancel → dialog closes, episode unchanged
- [ ] **K3.4:** Confirm Delete → DELETE `/api/memory/episodes/{id}` → success toast → sheet closes
- [ ] **K3.5:** Episode removed from grid/timeline immediately (queries invalidated)
- [ ] **K3.6:** Audit event `EPISODE_DELETED` (or equivalent) visible in `/control/audit`

**Slice 4 KG Real Data (K4):**
- [ ] **K4.1:** `curl http://127.0.0.1:8090/api/v1/control/kg/graph?limit=50` → `{nodes:[], edges:[], total_nodes:0, total_edges:0}` (empty before seed)
- [ ] **K4.2:** `curl -X POST http://127.0.0.1:8090/api/v1/control/kg/seed` → `{status:"ok",...}`
- [ ] **K4.3:** `curl .../kg/graph` again → `total_nodes > 0` with seeded nodes
- [ ] **K4.4:** Navigate to `/memory/kg` (Trading KG) → react-flow renders nodes from backend (no `mock` badge)
- [ ] **K4.5:** Type filter param works: `curl .../kg/graph?type=Stratagem&limit=10` → only Stratagem nodes
- [ ] **K4.6:** Reload button on KGPage → refetch + spinner animation visible
- [ ] **K4.7:** Backend offline (`taskkill /F /IM agent-service.exe` or `Ctrl-C`) → KGPage shows `mock` badge + falls back to mockKGGraphResponse
- [ ] **K4.8:** Navigate to `/memory/graph` (Episode-Memory Provenance) → memory-graph package still renders with `documents` mock + backend node count badge if hook returned data
- [ ] **K4.9:** `adaptKgGraphResponse` correctly normalizes loose backend shape (e.g. `{id, name, node_type}` → `{id, type, label, properties, confidence, created_at, updated_at}` with sane defaults)

**Slice 5 Agent Edit + Permission PATCH + Skill Toggle (K5, K6, K7):**
- [ ] **K5.1:** `/control/agents` → click any role card → Detail Sheet opens
- [ ] **K5.2:** Click "Edit" button → form switches to edit mode (Textarea, RadioGroup, Switch all interactive)
- [ ] **K5.3:** Modify system_prompt → click Save → PATCH `/api/control/agents/{id}` with `{system_prompt: "..."}` body
- [ ] **K5.4:** `psql -c "SELECT field, value FROM agent.agent_role_overrides WHERE role_id='trader';"` → row exists
- [ ] **K5.5:** Sheet reopens → `is_default=false`, "has overrides" badge visible
- [ ] **K5.6:** Click "Reset Prompt" → DELETE `/api/control/agents/{id}/overrides/system_prompt` → row removed, `is_default=true`
- [ ] **K5.7:** Toggle memory_access via RadioGroup → Save → diff-only PATCH (no system_prompt key in body)
- [ ] **K5.8:** Toggle approval_required via Switch → Save → DB column updated
- [ ] **K5.9:** Cancel button discards draft state without firing PATCH
- [ ] **K5.10:** "No changes to save" toast when saving without modifying anything
- [ ] **K6.1:** `/control/permissions` → matrix renders 6×7 grid
- [ ] **K6.2:** Left-click cell with level=auto → cycles to inform → confirm → deny → auto
- [ ] **K6.3:** PATCH `/api/control/permissions/cell` body matches `{role_id, category_id, level}` per click
- [ ] **K6.4:** `psql -c "SELECT level FROM agent.consent_overrides WHERE role_id='trader' AND category_id='trading';"` → matches latest cycled value
- [ ] **K6.5:** Cell shows new level + amber `is_overridden` dot after click
- [ ] **K6.6:** Right-click an overridden cell → DELETE `/api/control/permissions/cell/{role}/{cat}` → reverts to yaml default
- [ ] **K6.7:** Right-click non-overridden cell → toast "Cell uses yaml default — nothing to reset" (no API call)
- [ ] **K7.1:** `/control/skills` → toggle Switch on any skill → PATCH `/api/control/skills/{id}` fires
- [ ] **K7.2:** Backend stub returns `{status: "pending_phase2"}` → toast.warning shown
- [ ] **K7.3:** Audit event with action e.g. `SKILL_PATCH_QUEUED` (or whatever skills.py logs) visible in `/control/audit`

**Slice 6 Sessions Kill + Audit Export (K8, K9):**
- [ ] **K8.1:** `/control/sessions` in User Mode (default) → no Kill button visible per row
- [ ] **K8.2:** Toggle Mode → Dev → Kill button (red trash icon) appears per session row
- [ ] **K8.3:** Click Kill → AlertDialog with "Kill session?" + thread_id + warning
- [ ] **K8.4:** Click Cancel → dialog closes, session unchanged
- [ ] **K8.5:** Click "Kill Session" (rose action) → DELETE `/api/control/sessions/{thread_id}` → success toast
- [ ] **K8.6:** Session removed from list (queries invalidated)
- [ ] **K8.7:** `psql -c "SELECT COUNT(*) FROM checkpoints WHERE thread_id='<killed>';"` → 0
- [ ] **K8.8:** Audit event with action `SESSION_KILLED` (or equivalent) visible in `/control/audit`
- [ ] **K9.1:** `/control/audit` → Export DropdownMenu visible (with current filtered count)
- [ ] **K9.2:** Click "Export as CSV" → browser downloads `audit-<timestamp>.csv`
- [ ] **K9.3:** Open CSV in Excel/numbers → 10 columns (id/timestamp/action/success/user_id/thread_id/agent_role/tool_name/duration_ms/error), proper escaping for commas/quotes
- [ ] **K9.4:** Click "Export as JSON" → downloads `audit-<timestamp>.json` pretty-printed
- [ ] **K9.5:** Filter by action → export only contains filtered rows (not all events)
- [ ] **K9.6:** Empty filter result → Export button disabled

**Slice 1 Reindex Row Action (K10):**
- [ ] **K10.1:** `/files/documents` → select any document from FileSearch list
- [ ] **K10.2:** Header bar shows file name + Reindex button
- [ ] **K10.3:** Click Reindex → ReindexConfirmDialog opens with file name
- [ ] **K10.4:** Type wrong file name → Reindex button stays disabled
- [ ] **K10.5:** Type correct file name within 30s → Reindex button enables
- [ ] **K10.6:** Click Reindex → POST `/api/files/{id}/reindex` with `x-confirm-token` header → 200
- [ ] **K10.7:** Success toast "Reindex queued for {filename}" + dialog closes
- [ ] **K10.8:** 30s countdown expires → input disabled with "Confirmation window expired" message
- [ ] **K10.9:** Audit event `INGESTION_INCREMENTAL_REINDEX` with `metadata.savings_pct` visible in `/control/audit`

### Slice 8 (optional, spaeter): Integration in agent-chat/
- [ ] Komponenten-Migration in agent-chat/
- [ ] GlobalTopBar mit 4 Surfaces (Agent · Memory · Control · Files)
- [ ] BFF-Routes integration
- [ ] control-ui/ archivieren oder eigenstaendig lassen

### Slice 9 (geplant): Graphiti/Cognee Backend Integration

> Verschoben aus exec-13 Phase 1 (10.04.2026).
> Thematisch passt es hierher: exec-15 hat KG-Frontend (Slice 4) + Ingestion-Pipeline (Slice 2).

**Voraussetzung:** exec-11 (Hindsight Memory) ✅, Slice 2 (Content Ingestion Pipeline), Slice 4 (KG Visualization)

#### 9.1 Graphiti als Custom GraphRetriever
- [ ] `GraphitiRetriever` implementieren (nutzt Graphiti's Temporal Knowledge Graph)
- [ ] Graphiti installieren (`pip install graphiti-core`)
- [ ] Neo4j oder FalkorDB als Graph-Backend evaluieren
- [ ] Temporal Edges: Fakten haben Zeitstempel, alte werden invalidiert
- [ ] Entity Resolution: Graphiti's eigene Entity-Merging-Pipeline

#### 9.2 Cognee als Structured Knowledge Layer
- [ ] Cognee installieren (`pip install cognee`)
- [ ] Document → Knowledge Graph Pipeline (PDF, Markdown, Code)
- [ ] Cognee's LLM-basierte Triplet Extraction
- [ ] Integration mit Hindsight: Cognee Facts als `world` Memories retainen

#### 9.3 Unified Search API
- [ ] RRF Fusion ueber alle Backends (Hindsight + Graphiti + Cognee)
- [ ] Fallback-Kette: Hindsight (immer) → Graphiti (wenn Neo4j) → Cognee (wenn konfiguriert)
- [ ] Search API Endpoint: `/api/memory/search?q=...&backends=all`

### Verify-Gate Slice 9
- [ ] GraphitiRetriever registriert und liefert Ergebnisse
- [ ] Cognee Document-Pipeline: PDF → Facts in Hindsight
- [ ] Unified Search: Query liefert Ergebnisse aus allen Backends

---

## Two-Tier Control Surface (D18 — User Mode vs Developer Mode)

**Aus main project `control/execution_slices/control_surface_delta.md` §5 uebernommen + angepasst an supermemory Adoption.**

### Mode Toggle

- URL Param: `/control?mode=user` (default) oder `/control?mode=dev`
- Persist: localStorage oder cookie (kommt in Phase 2)
- UI: Toggle Switch in `ControlTopNav` rechts (User / Developer)

### User Mode Tabs (default — fuer trader/analyst)

| ID | Tab | Aus main | Komponente | Status |
|---|---|---|---|---|
| TT1 | **Overview** | TT1 simplified | `OverviewTab.tsx` | NEU 07.04.2026 |
| TT7a | **Agents** | TT7 | `AgentsTab.tsx` (existing, simplified view) | DONE |
| TT7b | **Permissions** | TT7 per-agent matrix | `PermissionsTab.tsx` | DONE |
| TT6 | **Skills** | TT6 | `SkillsTab.tsx` (existing) | DONE |
| TT3 | **Tools** | TT3 mit marketplace add | `ToolsTab.tsx` (existing) | DONE — **TODO:** Add via URL Button |
| TT2 | **Sessions** | TT2 read-only (kein kill) | `SessionsTab.tsx` (existing) | DONE |
| TT8 | **Security** | TT8 | `SecurityTab.tsx` | NEU 07.04.2026 |

### Developer Mode Tabs (zusaetzlich — admin only)

| ID | Tab | Aus main | Komponente | Status |
|---|---|---|---|---|
| TT10 | **System** | TT10 Memory infra health | `SystemTab.tsx` (existing) | DONE |
| — | **API/Models** | NEW (fused ENV + LLM provider config) | `ApiModelsTab.tsx` | NEU 07.04.2026 |
| TT9 | **Sandbox** | TT9 raw runs | `SandboxTab.tsx` (existing) | DONE |
| TT16 | **Audit** | TT16 full log | `AuditTab.tsx` (existing) | DONE |
| — | **MCP** | NEW (exec-09) | `McpTab.tsx` (existing) | DONE |
| — | **A2A** | NEW (exec-10 Phase 4) | `A2aTab.tsx` (existing) | DONE — optional |

### Bewusst NICHT im Control Surface

**Memory + KG sind eigene Surfaces im GlobalTopBar**, nicht im /control. Begruendung: wir haben supermemory Patterns adoptiert die deutlich ausgereifter sind als das was main project mit TT4 + TT5 geplant hatte.

| Was main project geplant hatte | Wo es bei uns ist |
|---|---|
| TT4 Memory Tab (episodic edit/delete, semantic facts) | `/memory` mit EpisodesGrid + EpisodeDetailSheet + AddMemoryModal + QuickNoteCard + FullscreenNoteModal (alle aus supermemory adoptiert) |
| TT5 KG Fast-Lane (personal KG CRUD) | `/memory/kg` mit Trading KG (react-flow + 6 typed node components) + `/memory/graph` mit Episode-Memory Graph (supermemory memory-graph package 1:1) |
| TT11 Slow-Lane KG (global) | `/memory/kg` (Trading KG ist sowieso global single-tenant in Phase 1, D3) |

### User Mode Items die noch nicht implementiert sind (Slice 7)

- [ ] **TT1.1** `OverviewTab.tsx` — AI Health Indicator (online/degraded/offline), aktive Tasks-Zusammenfassung, letzter Agent-Fehler, recent activity ticker. Keine raw Infrastruktur-Metriken.
- [x] **TT3.1** Tools Tab erweitert: "Add Tool from URL" Button + Dialog (bounded-write scaffold; backend `POST /api/v1/control/tools/import` schreibt Audit Event `TOOL_IMPORT_REQUESTED`).
- [x] **TT6.1** Skills Tab erweitert: "Import Skill from GitHub URL" Button + Dialog (bounded-write scaffold; backend `POST /api/v1/control/skills/import` schreibt Audit Event `SKILL_IMPORT_REQUESTED`).
- [ ] **TT7.1** Agents Tab erweitern: simpler View im User Mode (kein System Prompt Editor, nur "Active/Inactive" Toggle + Per-Agent Permission Matrix Link).
- [ ] **TT8.1** `SecurityTab.tsx` — Posture-Score (4 Pillars: Auth, Encryption, Audit, Network), Recent Security Events (login attempts, role changes, sensitive tool calls), Access List (welche IPs/Sessions waren heute aktiv).

---

## Identity / Scope / Persistence (Addendum, 09.04.2026)

Diese Punkte muessen fuer Phase 1–3 sauber sein, bevor wir E2E ernsthaft fahren:

- [x] **S1** Header-first Identity fuer Control-Endpoints eingefuehrt (`x-auth-user`, optional `x-auth-team`, optional `x-auth-actor`), Query `user_id` nur noch als Dev-Fallback (neu: `agent/control/request_scope.py`).
- [x] **S2** Skills Toggle ist **persistiert pro user_id** (neu: `agent.skills_state` via Alembic `008_skills_state.py`; `PATCH /api/v1/control/skills/{id}` schreibt DB + Audit `SKILL_TOGGLE`).
- [x] **S3** Memory Highlights sind nicht mehr Frontend-only Mock: neues Backend `GET /api/v1/control/memory/highlights` + MemoryPage wired (fallback = empty).
- [ ] **S4** Team-Scoped Skills (Tier `team/{team_id}`) im Loader + APIs aktiv nutzen (derzeit `team_id=None` in loader calls).
- [ ] **S5** Spoofing-Hardening: `user_id` nicht mehr via Query fuer prod erlauben; Scope muss aus Auth kommen (nur Dev flag erlaubt Query override).
- [ ] **S6** Daten-Loeschung/Lifecycle: definieren was bei User-Loeschung passiert (skills_state, role_overrides, consent_overrides, audit retention, memory banks).

### Verify (Scope)
- [ ] **VS1** Aufruf ohne Header: Control-Endpoints verwenden `user_id=local` (Dev) und funktionieren.
- [ ] **VS2** Aufruf mit Header `x-auth-user=alice`: Skills/Overlays/Highlights sind getrennt von `local`.
- [ ] **VS3** Versuch `?user_id=bob` bei gesetztem Header `x-auth-user=alice` wird ignoriert (Header gewinnt).

---

## paperwatcher SOTA Adoption Map

Vollstaendige Liste was wir aus paperwatcher uebernehmen, was wir explizit skipppen,
und welche Phase. Quelle: `D:/matrix/paperwatcher/` (geklont 07.04.2026 von
`japorto100/research-project`, eigenes git, in matrix .gitignore).

### `paperwatcher/paperwatcher/core/doc_extractor/`

| Datei | Status | Ziel | Phase | Notiz |
|---|---|---|---|---|
| `base.py` | ✅ ADOPTED | `ingestion/extractors/base.py` + `ingestion/core/types.py` | 1 (jetzt) | 1:1 ABC + Dataclasses |
| `pymupdf_ext.py` | ✅ ADOPTED | `ingestion/extractors/pymupdf_ext.py` | 1 (jetzt) | 1:1 (200 LOC, primary CPU extractor) |
| `chunking.py` | ✅ ADOPTED | `ingestion/chunkers/token_chunker.py` | 1 (jetzt) | Section-aware markdown chunker |
| `docling_ext.py` | ⏳ PHASE 2 | `extraction_layout/extractors/docling_ext.py` | 2 | Eigene venv (pillow conflict) |
| `marker_ext.py` | ⏳ PHASE 2 | `extraction_layout/extractors/marker_ext.py` | 2 | Eigene venv (pillow<11 vs hindsight pillow>=12) |
| `mineru_ext.py` | ⏳ PHASE 2 OPTIONAL | `extraction_layout/extractors/mineru_ext.py` | 2 | 2.5 GB VLM Model |
| `spacy_layout_chunker.py` | ⏳ PHASE 2 | `ingestion/chunkers/section_chunker.py` | 2 | Spacy + spacy-layout in extraction_layout extra |
| `storage.py` | ❌ SKIP | — | — | paperwatcher-spezifisches per-doc Folder Layout — wir nutzen SeaweedFS |

### `paperwatcher/paperwatcher/core/` (Retrieval + RAG)

| Datei | LOC | Status | Ziel | Phase |
|---|---|---|---|---|
| `hybrid_retriever.py` | 629 | ⏳ MAPPED | `retrieval/searchers/hybrid.py` | 3 |
| `chunk_bm25.py` | ? | ⏳ MAPPED | `retrieval/searchers/bm25_searcher.py` | 3 |
| `reranker.py` | 727 | ⏳ MAPPED | `retrieval/rerankers/cross_encoder.py` | 3 |
| `llm_reranker.py` | ? | ⏳ MAPPED | `retrieval/rerankers/llm_reranker.py` | 3 |
| `hyde.py` | ? | ⏳ MAPPED | `retrieval/understanders/hyde.py` | 3 |
| `query_decomposer.py` | ? | ⏳ MAPPED | `retrieval/understanders/decomposer.py` | 3 |
| `query_expander.py` | ? | ⏳ MAPPED | `retrieval/understanders/expander.py` | 3 |
| `intent_router.py` | ? | ⏳ MAPPED | `retrieval/understanders/intent_router.py` | 3 |
| `context_bubble.py` | ? | ⏳ MAPPED | `retrieval/composers/context_bubble.py` | 3 |
| `self_rag.py` | ? | ⏳ MAPPED | `retrieval/verifiers/self_rag.py` | 3 |
| `rag_pipeline.py` | 442 | ⏳ MAPPED | `retrieval/pipelines/hybrid_kg.py` | 3 |
| **`raptor_tree.py`** | 424 | 🆕 SOTA NEU | `retrieval/composers/raptor_tree.py` | 3 | RAPTOR Stanford 2024 — multi-granularity tree |
| **`colpali_indexer.py`** | 418 | 🆕 SOTA NEU | `extraction_layout/extractors/colpali_ext.py` + `retrieval/searchers/visual_searcher.py` | 2 + 3 | Visual PDF embedding fuer Charts |
| **`retrieval_gate.py`** | 474 | 🆕 SOTA NEU | `retrieval/verifiers/quality_gate.py` | 3 | Quality scoring nach retrieval |
| **`falsification.py`** | 210 | 🆕 SOTA NEU | `retrieval/verifiers/falsification.py` | 3 | Adversarial verification |
| `entity_tree_sampler.py` | 416 | ❌ SKIP* | — | — | KG sampling fuer QA-gen — Phase 4 Eval optional |
| `synthesizer.py` | 1891 | ❌ SKIP | — | — | Multi-step paper synthesis — wir haben LangGraph |
| `summarizer.py` | 424 | ❌ SKIP | — | — | Document summarization — Phase 3 wenn ueberhaupt |
| `deep_research.py` | 704 | ❌ SKIP | — | — | RE-TRAC multi-round agent — overlaps mit LangGraph |
| `deep_path.py` | 202 | ❌ SKIP | — | — | KG path search — overlap mit subgraph_pruner |
| `doc_graph.py` | 344 | ❌ SKIP | — | — | LILaC document graph — paper-cross-ref-spezifisch |
| `pdf_structured.py` | 244 | ❌ SKIP | — | — | Strukturiertes PDF JSON — pymupdf+docling reichen |
| `embedding_research.py` | 107 | ❌ SKIP | — | — | Embedding strategy comparison — research code |
| `embeddings.py` | ? | ❌ SKIP | — | — | Embeddings wrapper — wir haben sentence_transformer |
| `ner.py` | 168 | ❌ SKIP | — | — | NER — kg_pipeline macht das via relik+gliner |
| `ranker.py` | ? | ❌ SKIP | — | — | Ranker abstraction — wir haben rerankers/ |
| `filters.py` | ? | ❌ SKIP | — | — | Quality filters — Phase 3 evaluate ob noetig |
| `citation_*.py` (3 files) | ? | ❌ SKIP | — | — | Academic only |
| `auto_linker.py` | ? | ❌ SKIP | — | — | Paper→GitHub linking, academic |
| `gap_finder.py` | ? | ❌ SKIP | — | — | Research gap analysis |
| `trend_analysis.py` | ? | ❌ SKIP | — | — | Trend analysis (research) |
| `screening.py` | ? | ❌ SKIP | — | — | Paper screening (research) |
| `reader.py` / `repository.py` / `sqlite_repository.py` / `service.py` / `model.py` / `download_guard.py` / `downloader.py` | ? | ❌ SKIP | — | — | Paper search/download/storage layer (academic-only) |
| `model_backends/` / `llm/` | ? | ❌ SKIP | — | — | LLM abstractions — wir haben llm_helper.py + LiteLLM |
| `vector_store/{faiss,lancedb}_store.py` | ? | ❌ SKIP | — | — | Wir haben Hindsight pgvector + ChromaDB |

### `paperwatcher/kg-module/kg_module/`

| Datei | LOC | Status | Ziel | Phase |
|---|---|---|---|---|
| `extraction.py` | 1243 | ⏳ MAPPED | `kg_pipeline/extractors/relik_glirel.py` | 2 |
| `text_pipeline.py` | 561 | ⏳ MAPPED | `kg_pipeline/preprocessors/section_splitter.py` | 2 |
| `predicate_mapper.py` | ? | ⏳ MAPPED | `kg_pipeline/normalizers/predicate_mapper.py` | 2 |
| `schema.py` + `shared_schema.py` | ? | ⏳ MAPPED | `kg_pipeline/schema/` | 2 |
| `config.py` | ? | ⏳ MAPPED | `kg_pipeline/core/config.py` | 2 |
| `algorithm_types.py` | ? | ⏳ MAPPED | `kg_pipeline/core/types.py` extension | 2 |
| **`communities.py`** | 294 | 🆕 SOTA NEU | `kg_pipeline/postprocessing/communities.py` | 2 | Microsoft GraphRAG — Leiden community detection |
| **`community_summarizer.py`** | 164 | 🆕 SOTA NEU | `kg_pipeline/postprocessing/community_summarizer.py` | 2 | LLM cluster-summary — global queries |
| **`conflict_detector.py`** | 235 | 🆕 SOTA NEU | `kg_pipeline/postprocessing/conflict_detector.py` | 2 | Trading-relevant: bullish vs bearish Konflikte |
| **`subgraph_pruner.py`** | 210 | 🆕 SOTA NEU | `kg_pipeline/postprocessing/subgraph_pruner.py` | 2 | KG retrieval pruning |
| `got_traversal.py` | 262 | 🆕 SOTA NEU MITTEL | `kg_pipeline/postprocessing/got_traversal.py` | 2 oder 3 | Graph of Thoughts — overlap mit LangGraph |
| `analytics.py` | ? | ❌ SKIP* | — | 4 | Centrality/betweenness — Phase 4 fuer KG-Stats Frontend |
| `engine.py` | 1177 | ❌ SKIP | — | — | Main engine — wir nutzen memory_engine/kg_store.py |
| `graph_storage.py` / `index_store.py` / `graph_inspector.py` | ? | ❌ SKIP | — | — | Storage Layer — haben wir |
| `cli.py` / `__main__.py` | ? | ⏳ ADOPT | `kg_pipeline/cli.py` Erweiterung | 2 | Wenn Phase 2 aktiv |
| `falkordb/` / `neo4j/` / `adapters/` | ? | ❌ SKIP | — | — | Backend-spezifisch — wir nutzen Kuzu |

### `paperwatcher/layout-module/layout_module/`

| Datei | LOC | Status | Ziel | Phase |
|---|---|---|---|---|
| `doc_extractor/*` | ? | ⏳ MAPPED | `extraction_layout/extractors/` | 2 |
| `processor.py` | 142 | ⏳ MAPPED | `extraction_layout/pipelines/document.py` | 2 |
| **`colpali_service.py`** | 84 | 🆕 SOTA NEU | `extraction_layout/extractors/colpali_service.py` | 2 | ColPali Service Wrapper |
| `manifest.py` | 138 | 🆕 OPT MITTEL | `extraction_layout/manifest.py` | 2 | Merkle CAS — komplementaer zu unserem sha256 dedup |
| `hasher.py` | ? | ❌ SKIP | — | — | Wir haben sha256 dedup |
| `observer.py` | ? | ❌ SKIP | — | — | File watcher — wir nutzen Frontend Push-Upload |
| `warmer.py` | ? | 🆕 OPT MITTEL | `extraction_layout/warmer.py` | 2 | Cache warmer fuer Modelle |
| `kg_bridge.py` | ? | ❌ SKIP | — | — | Bridge zwischen layout+kg — wir koppeln via HTTP |
| `mcp.py` | ? | ❌ SKIP | — | — | MCP server — wir haben eigenen |
| `png_merger.py` | ? | ⏳ MAPPED OPT | `extraction_layout/utils/png_merger.py` | 2 | Wenn page images gebraucht |
| `cli.py` | ? | ⏳ MAPPED | `extraction_layout/cli.py` | 2 | |

### `paperwatcher/ragbits_custom/`

| Status | Notiz |
|---|---|
| ❌ SKIP komplett | User-Entscheidung 07.04.2026: war Blueprint, ragbits als Framework ist Overkill. Patterns wurden bereits in retrieval/ Adoption Map (oben) eingearbeitet. |

### Zusammenfassung

| Kategorie | Anzahl |
|---|---|
| ✅ **ADOPTED** (Slice 2 jetzt) | **3 Files** (base.py, pymupdf_ext.py, chunking.py) |
| ⏳ **PHASE 2 mapped** (extraction_layout + kg_pipeline) | ~12 Files |
| ⏳ **PHASE 3 mapped** (retrieval) | ~11 Files |
| 🆕 **SOTA NEU 07.04.2026** (explizit aufgenommen statt vergessen) | **9 Files** (raptor_tree, colpali_indexer, colpali_service, retrieval_gate, falsification, communities, community_summarizer, conflict_detector, subgraph_pruner) |
| ❌ **SKIPPED** (academic / overlapping / wir haben eigene) | ~25 Files |

**Top 5 SOTA Highlights die wir explizit jetzt aufgenommen haben:**

1. **RAPTOR Tree** (`retrieval/indexers/raptor_tree_builder.py` + `retrieval/searchers/raptor_searcher.py`) — Multi-granularity hierarchical retrieval. Stanford 2024 SOTA. Phase 3.
2. **ColPali Visual Indexing** (`extraction_layout/extractors/colpali_ext.py` + `retrieval/searchers/visual_searcher.py`) — Embedded PDF Pages als Bilder. **KRITISCH fuer Trading-Charts**. Phase 2 + 3.
3. **GraphRAG Communities** (`kg_pipeline/postprocessing/communities.py` + `community_summarizer.py`) — Microsoft 2024 SOTA. Global KG Queries via Leiden Cluster + LLM Summary. Phase 2.
4. **Conflict Detector** (`kg_pipeline/postprocessing/conflict_detector.py`) — KG Contradiction Detection. **Hochrelevant fuer Trading** wo Bullish/Bearish Signale standardmaessig konfligieren. Phase 2.
5. **Subgraph Pruner** (`kg_pipeline/postprocessing/subgraph_pruner.py`) — Reduziert KG Retrieval Subgraphs. Wichtig wenn KG groß wird. Phase 2/3.

**⚠️ WICHTIG — Adoption Status (07.04.2026):**

Alle 9 SOTA Items (5 oben + retrieval_gate, falsification, got_traversal, manifest) sind **NUR in dieser Spec dokumentiert**, **NICHT als Code adoptiert**. Die zugehoerigen Files leben unverändert in `D:/matrix/paperwatcher/`. Adoption = copy mit import-rewrites passiert in Phase 2 (extraction_layout + kg_pipeline aktivieren) bzw. Phase 3 (retrieval bauen).

Was tatsaechlich **als Code** in `python-backend/` existiert (Stand Slice 2):
- ✅ `ingestion/` voll implementiert (3 paperwatcher Files 1:1 + 6 NEU)
- 🔶 `extraction_layout/` Skeleton (pyproject + 503-Stub)
- 🔶 `kg_pipeline/` Skeleton (pyproject + 503-Stub)
- 🔶 `retrieval/` leeres Skeleton (NotImplementedError)

**Phase Sequencing:**
- **Phase 1 (Slice 2 jetzt):** ingestion/ Code-complete + Skeletons der anderen 3
- **Phase 2 (eigener Slice spaeter):** kg_pipeline + extraction_layout aktivieren + 6 SOTA Items adopten (ColPali, communities, community_summarizer, conflict_detector, subgraph_pruner, got_traversal)
- **Phase 3 (eigener Slice spaeter):** retrieval/ voll bauen + 4 SOTA Items adopten (RAPTOR, retrieval_gate, falsification, visual_searcher)

---

## Empfohlene Phasen-Reihenfolge

**Empfohlene Reihenfolge:**

1. **Phase 1** (Foundation Setup + Adoption) — Isolierte App lauffaehig, 3 Shells, Storage wired
2. **Phase 5** (Content Ingestion) — Files koennen hochgeladen + indexiert werden, Memory faengt an sich zu fuellen
3. **Phase 2** (Memory Browser) — Jetzt gibt es Daten zum Browsen
4. **Phase 3** (KG Visualization, PRIORITY) — Die "Wow"-Komponente
5. **Phase 4** (Agent Configuration) — Settings die gepflegt werden wollen
6. **Phase 6** (System Observability) — Operations Layer
7. **Phase 7** (Integration in agent-chat/) — Optional, eigener Slice

**Begruendung:** Phase 5 frueh, weil ohne Daten kein Memory Browser sinnvoll ist.
KG Viz (3) braucht Backend-Endpoints aus 1, kann aber parallel zu 2 laufen.

---

## Total Item Count

| Phase | Items |
|---|---|
| Phase 1 | 38 |
| Phase 2 | 22 |
| Phase 3 | 25 |
| Phase 4 | 18 |
| Phase 5 | 22 |
| Phase 6 | 17 |
| Phase 7 | 11 (optional) |
| **Total** | **153** |

---

## Referenzen

- `D:/matrix/control/README.md` — Bundle-Beschreibung
- `D:/matrix/control/control_surface/` — Control Tabs Foundation
- `D:/matrix/control/files_surface/` — Files Surface mit Multi-Modal Viewer
- `D:/matrix/control/storage/go-backend/` — Storage Layer (D4)
- `D:/matrix/control/execution_slices/control_surface_delta.md` — Phase 22b Spec
- `D:/matrix/control/execution_slices/document_widgets_control_delta.md` — Files Surface Spec
- `D:/matrix/control/execution_slices/storage_layer_delta.md` — SeaweedFS Entscheidung
- `_ref/supermemory/packages/memory-graph/` — Graph Visualization Inspiration (D5)
- `_ref/supermemory/apps/web/components/` — UI Pattern Inspiration
- `_ref/supermemory/apps/web/lib/search-params.ts` — nuqs URL State Pattern
- `_ref/hindsight/` — Memory Engine Backend (Datenquelle)
- `D:/matrix/paperwatcher/` — Adoption-Quelle fuer Slice 2/Phase 2/Phase 3 (geklont 07.04.2026 von japorto100/research-project, eigenes git)
  - Vollstaendige paperwatcher Adoption Map siehe **§ paperwatcher SOTA Adoption Review** unten
- `specs/execution/exec-11-memory-evolution.md` — Hindsight Integration
- `specs/execution/exec-12-sandbox-security.md` — RBAC + Audit + Consent
- `specs/execution/exec-13-ui-kg-extensions.md` — Phase 1 (Graphiti/Cognee), 5 (Computer Use), 6 (Artifacts)
- `specs/FUTURE_IDEAS.md` — Verschobene Items (D6 ENV Editor schreibend, WebGL KG Migration, Onboarding Flow)
