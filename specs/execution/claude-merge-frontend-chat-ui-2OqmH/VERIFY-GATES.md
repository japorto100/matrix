# Verify-Gates — Branch `claude/merge-frontend-chat-ui-2OqmH`

Pro exec-Slice aus `specs/execution/`: was wurde auf diesem Branch beruehrt,
welche Gates wurden durchlaufen, welche bleiben offen (nur bei dir lokal oder
im naechsten Stream pruefbar).

**Legende:**
- ✓ = auf diesem Branch verifiziert (Command + Ergebnis in exec-01..04)
- ○ = Code/Doku-Aenderung, aber kein Live-Run noetig oder moeglich in VM
- ✗ = User visual check oder voller Stack noetig
- — = nicht beruehrt

## Matrix-Core Execs

### exec-01 Homeserver
- — Nicht beruehrt. Tuwunel v1.6 wird durch neues `docker-compose.yml` (exec-02)
  empfohlen, aber Homeserver-Config selbst unveraendert.
- **Bei dir zu pruefen:** `podman-compose up -d tuwunel` startet Tuwunel v1.6
  ohne `error_on_unknown_config_opts` failures.

### exec-02 Go Appservice + exec-03 Python Agent Bridge
- ✓ `go build ./...` clean
- ✓ `go test -short ./...` 9/9 Packages
- ✓ `golangci-lint run ./...` 0 issues (war 12)
- ○ Live-Gates (Tuwunel AS-Token Handshake, Python-Bridge NATS-Subscribe) —
  brauchen vollen Stack.

### exec-04 Next.js Chat (Matrix)
- ✓ Matrix-Feature in `frontend_merger/src/features/matrix/` gemountet
- ✓ Route `/matrix` rendert mit Config-Hint (keine ENV credentials in VM)
- ✓ Playwright Test #4 gruen
- ✗ Live Matrix Session (Room-Liste, Timeline, Calls, E2EE) — braucht
  Homeserver + Credentials.

## Messaging Stack

### exec-05 NATS E2EE Pipeline / 05b Bridges / 05c Agent Isolation
- — Nicht beruehrt.

## Agent Chat Integration

### exec-06 Agent Chat Integration (Shared Components + Verify)
- ○ Agent-Chat-Feature kopiert in `frontend_merger/src/features/agent/`,
  aber `exec-06` fokussiert auf `nextjs-chat`-Integration. frontend_merger
  ist paralleler Scouting-Harness.
- ✓ Gate "Shared Components": `@shared/` existiert nicht mehr (per
  exec-merge-chat vermerkt 13.04.2026) — im Merger werden Components direkt
  aus `features/*` genutzt.
- ✓ BFF-Routen `/api/agent/{chat,approve,completion,models}` und
  `/api/audio/{synthesize,transcribe}` unter `src/app/api/` gemountet.
- ✓ Verify-Gate Phase 4 (Frontend SOTA):
  - Shiki Syntax Highlighting: react-shiki 0.9 in deps ✓
  - Zustand `useGlobalChat()` provider-free: funktioniert (Playwright #3) ✓
  - Jotai Tool-Collapse Atomic State: atoms.ts vorhanden ✓
  - motion via `motion/react`: imports verifiziert ✓
  - auto-animate 0.9: in deps ✓
- ✗ Phase 2 API Routes Verify (Go Gateway SSE end-to-end): braucht Stack.
- ✗ Phase 3 Voice Verify (LiveKit Room, STT/TTS-Latenz): braucht Stack.

## Generative UI + Multi-Agent

### exec-09 Protocols + Generative UI
- ✓ Tambo: `features/agent/components/tambo/registry.ts` mit ChartWidget +
  PortfolioCard gemountet.
- ✓ CopilotKit: `AgentProviders` wrappt Root-Layout; `runtimeUrl=/api/copilotkit`.
  (Route existiert noch nicht → 404, CopilotKit degradiert silent — offen
  fuer eigenen Slice.)
- ✓ AG-UI a2ui-renderer: Pakete geladen (`@copilotkit/a2ui-renderer`,
  `@a2ui/web/core/src/v0_9`).
- ✓ WebMCP Polyfill: `@agent/lib/webmcp-polyfill` Side-Effect-Import in Layout.
- ○ Live Generative-UI Demo (Agent emittiert Tambo-Component auf
  `#tambo-canvas`): braucht Agent-Service + LLM.

### exec-10 Multi-Agent — —
### exec-11 Memory Evolution — —

## Sandbox / UI / KG

### exec-12 Sandbox Security
- ○ OpenSandbox Compose-Service in `docker-compose.yml` bleibt unter
  `--profile sandbox`. Nicht default.

### exec-13 UI KG Extensions
- ✓ KG-Graph Feature aus `control-ui/src/features/memory/` kopiert nach
  `features/memory/`, inkl. `lib/kg-graph/` + `@xyflow/react` + d3-force deps.
- ✗ Live KG-Graph Render (Nodes/Edges von Python `/api/v1/memory/kg/*`):
  braucht Agent-Service.

### exec-14 PDDL — —

### exec-15 Memory Control UI
- ✓ Control + Files + Memory Features kopiert + Routen verdrahtet:
  - `/control/[[...tab]]` → 8+ Control Surfaces
  - `/files/[[...tab]]`
  - `/memory/[[...tab]]`
- ✓ Playwright Tests #5/#6/#7 gruen (HTTP 200 + TopBar sichtbar).
- ✗ Live Memory Browser Data Load: braucht Gateway + Python memory-service.

## LLM / Observability / Schema / Devstack / MCP

### exec-16 LLM Provider Gateway
- ○ `LITELLM_BASE_URL` etc. in `.env.example` dokumentiert. LiteLLM unter
  `--profile litellm` im compose.
- ✗ User-Model-Picker Wiring (Control-UI ↔ Agent-Chat): braucht backend.

### exec-17 Observability
- ○ `OTEL_*` + `OPENOBSERVE_*` Env-Vars in `.env.example` vermerkt.
- ✗ Live Traces in OpenObserve: braucht observability stack.

### exec-18 Unified Agent Schema — —

### exec-19 Devstack Consolidation
- ✓ **Direkt betroffen:** neue `scripts/dev-stack.sh` (Linux-Port von
  `dev-stack3.ps1`) + `docker-compose.yml` Profile-Split.
- ✓ Postgres-DSN `postgres://postgres@localhost:5433/hindsight_dev`
  dokumentiert (exec-19 fordert "Postgres only, SQLite entfernt").
- ✗ `python -m alembic upgrade head` End-to-End gegen frischen Postgres:
  bei dir zu pruefen.

### exec-20 MCP Manager
- ○ `@mcp-b/global`, `@mcp-b/react-webmcp`, `use-mcp` in deps.
  `useMcpTools` hook + `useWebMcp*` hooks kopiert.
- ✗ Live MCP Server Connection: braucht MCP Server Instanz.

## Memory/Harness/Context/Eval Specs

### exec-memory / exec-world-model / exec-personal-kb / exec-context / exec-harness / exec-eval
- ○ Nicht direkt beruehrt. Aber `python-backend/memory_fusion/fusion_engine.py`
  Pre-existing Syntax-Bug in `list_documents()` (FUSION-Route merger) gefixt
  — siehe `exec-03-linter-fixes.md`. Das ist **code-level eine reale
  Behavior-Aenderung** fuer den FUSION-Route:
  - Vorher: nur SUMMARY wurde gemerged (return auf erster Iteration).
  - Nachher: SUMMARY + VERBATIM werden beide gemerged, dann returned.
- **Bei dir zu pruefen:** `pytest python-backend/memory_fusion/` falls Tests
  fuer `list_documents` existieren — ob die neue Semantik gewollt ist.

## Andere Specs — —

exec-blocking, exec-ebm, exec-notifications, exec-openworldlib, exec-rust,
exec-skills, exec-transformers-js, exec-a2fm-adaptive-routing,
exec2-*, exec-merge-chat: nicht beruehrt.

## Zusammenfassung der tatsaechlich gelaufenen Gates

| Gate | Command | Ergebnis |
|---|---|---|
| Go build | `go build ./...` | ✓ |
| Go vet | `go vet ./...` | ✓ |
| Go tests | `go test -short ./...` | ✓ 9/9 |
| Go lint | `golangci-lint run ./...` | ✓ 0 issues (war 12) |
| Python lint | `ruff check .` | ✓ 0 issues (war 51) |
| Frontend install | `bun install` | ✓ |
| Frontend typecheck | `bunx tsc --noEmit` | ✓ |
| Frontend lint | `bunx biome check ./src` | ✓ |
| Frontend build | `bun run build` | ✓ 25 Routen |
| Frontend standalone | `node .next/standalone/server.js` | ✓ HTTP 200 auf 5 Routen |
| Frontend E2E | `bunx playwright test` (prod) | ✓ 8/8 |
| Compose parse | `python3 -c "import yaml; yaml.safe_load(...)"` | ✓ 12 services, 5 profiles |
| Shell syntax | `bash -n scripts/dev-stack.sh` | ✓ |

## Was auf deiner Seite zu pruefen bleibt

1. `cp frontend_merger/env.example.merger frontend_merger/.env.local` + User Werte
2. `cp go-appservice/.env.example go-appservice/.env.development` + Tokens generieren
3. `cp python-backend/.env.example python-backend/.env` + LLM Keys
4. `podman-compose up -d` — startet Tuwunel v1.6 + NATS + Postgres
5. `./scripts/dev-stack.sh` — alle lokalen Prozesse
6. Visual Smoke in Browser gegen :3003 — Matrix-Room, Agent-Sheet mit echter
   LLM-Antwort, Control-Memory-Graph.
