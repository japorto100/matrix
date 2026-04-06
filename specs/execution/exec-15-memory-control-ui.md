# exec-15: Memory & Control UI

**Datum:** 06.04.2026
**Status:** Geplant
**Abhaengig von:** exec-11 (Hindsight Memory) ✅, exec-12 Phase 1+2 (Sandbox + Security) ✅
**Quellen:**
- `D:/matrix/control/control_surface/` — Codex-Extraktion: Control Tabs + RBAC + Approval Flows
- `D:/matrix/control/files_surface/` — Codex-Extraktion: Multi-Modal Viewer + Upload
- `D:/matrix/control/storage/` — Codex-Extraktion: Go Storage Layer (SeaweedFS, signed URLs)
- `_ref/supermemory/packages/memory-graph/` — d3-force + Canvas Graph Package (Re-Implementation)
- `_ref/supermemory/apps/web/` — Design Tokens + Memory UX Patterns
- `_ref/hindsight/` — Memory Engine Backend (bleibt unsere Datenquelle)

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

### Strategie: Option D — control/ Baseline + supermemory Tokens + memory-graph Re-Implementation

**Drei Quellen, drei klare Rollen:**

| Quelle | Was wir uebernehmen | Aufwand |
|---|---|---|
| **control/control_surface/** | Tab-Shell, RBAC (Action Classes + Guard), Approval Flow (2-Step + Token Gate), Audit Pattern, BFF-Routes mit X-Request-ID | 1:1 Adoption |
| **control/files_surface/** | 7 Tabs + Multi-Modal Viewer (PDF/Audio/Video/Images), UploadDropzone, Reindex Flow, BFF | 1:1 Adoption |
| **control/storage/** (Go) | SeaweedFS Storage Backend, signed URLs, Metadata Store, Artifact Handler | 1:1 Adoption ins Go Appservice |
| **supermemory Design Tokens** | DM Sans Font, Color Palette (#0F1419 bg, #1B1F24 cards), Inset Shadows, Spacing | Token-Datei + Tailwind Config |
| **supermemory memory-graph Package** | d3-force + Canvas Setup, Force-Konfig, Color Theme, Performance-Tricks | **Re-Implementation** (nicht copy-paste, an Hindsight Backend angebunden) |
| **supermemory UX Patterns punktuell** | Add Document Modal Layout, Settings SectionTitle+Card, Masonry Grid mit Infinite Loading | Pattern uebernehmen, nicht Code |

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

### Wo lebt der neue Backend-Code?

**Python Backend** bekommt einen neuen Router unter `python-backend/agent/control/`:

```
python-backend/agent/control/
├── __init__.py
├── router.py            # FastAPI APIRouter, mounted in agent/app.py
├── overview.py          # Aggregated stats (memory + sessions + audit + tools)
├── memory.py            # Memory layer health + episodes + consolidation
├── episodes.py          # Faceted episode search + edit/delete
├── kg_crud.py           # Knowledge Graph CRUD
├── sessions.py          # LangGraph thread list + kill
├── audit.py             # audit_events query (filtered)
├── skills.py            # Skills registry + enable/disable
├── agents.py            # Trading roles + permission matrix (D1, D2)
├── ingestion.py         # Document → Hindsight pipeline
└── settings.py          # Service status + ENV (read-only, D6)
```

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

### 5.2 Document → Hindsight Memory Pipeline

| Source | What |
|---|---|
| NEU | Komplette Pipeline |
| Hindsight (exec-11) | Memory Storage Backend |

- [ ] **5.2.1:** Backend: `python-backend/agent/control/ingestion.py`
- [ ] **5.2.2:** Endpoint: `POST /api/v1/control/ingest/document`
  - Body: `{"file_id": "uuid", "extract_strategy": "semantic" | "fixed", "tags": [...], "user_id": "..."}`
- [ ] **5.2.3:** Async Worker (asyncio Task, kein Celery vorerst):
  - File aus Object Storage laden (signed URL aus Phase 1.6)
  - Parser pro MIME-Type:
    - PDF → `pypdf` (oder `pdfplumber`)
    - DOCX → `python-docx`
    - Markdown → `markdown` lib
    - HTML → `beautifulsoup4`
    - CSV → `pandas`
    - JSON → `json` + chunking on key boundaries
  - Semantic Chunking via `langchain.text_splitter SemanticChunker` (oder `RecursiveCharacterTextSplitter` als Fallback)
  - Embeddings via `sentence-transformers all-MiniLM-L6-v2` (existiert schon in pyproject)
  - Hindsight `retain()` mit `fact_type='world'`, `tags=[...]`, `user_id=...`
  - Status Updates in `ingestion_jobs` Tabelle
- [ ] **5.2.4:** Alembic Migration `005_ingestion_jobs.py`:
  ```sql
  CREATE TABLE agent.ingestion_jobs (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'local',
    status TEXT NOT NULL,  -- 'pending' | 'parsing' | 'chunking' | 'embedding' | 'storing' | 'done' | 'failed'
    progress FLOAT,  -- 0.0 - 1.0
    chunks_total INT,
    chunks_done INT,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    document_hash TEXT  -- sha256 fuer Dedup
  );
  ```
- [ ] **5.2.5:** Deduplizierung: `document_id = sha256(content)` — gleiches File → kein Re-Insert (Skip mit Audit Event)
- [ ] **5.2.6:** Metadata: filename, upload_date, user_id, source_url als Hindsight Tags

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

### 6.2 ENV Variables Editor (Read-Only, D6)

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

## Verify Gates Gesamt

| Gate | Phase | Inhalt |
|---|---|---|
| Gate 1 | Phase 1 | control-ui/ laeuft, 3 Surfaces Shells, Storage Backend wired |
| Gate 2 | Phase 2 | Memory Browser mit Filter+Pagination+Detail Sheet+Timeline |
| Gate 3 | Phase 3 | KG Visualization rendert > 100 Nodes mit > 30 FPS, CRUD funktioniert |
| Gate 4 | Phase 4 | Trading Rollen + Permission Matrix editierbar mit Hot-Reload |
| Gate 5 | Phase 5 | Document Upload → Hindsight Memory E2E in < 30s, Dedup, Status Dashboard |
| Gate 6 | Phase 6 | Service Status, ENV Editor (read), Audit Log Viewer |
| Gate 7 | Phase 7 | (Optional) Integration in agent-chat/ |

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
- `specs/execution/exec-11-memory-evolution.md` — Hindsight Integration
- `specs/execution/exec-12-sandbox-security.md` — RBAC + Audit + Consent
- `specs/execution/exec-13-ui-kg-extensions.md` — Phase 1 (Graphiti/Cognee), 5 (Computer Use), 6 (Artifacts)
- `specs/FUTURE_IDEAS.md` — Verschobene Items (D6 ENV Editor schreibend, WebGL KG Migration, Onboarding Flow)
