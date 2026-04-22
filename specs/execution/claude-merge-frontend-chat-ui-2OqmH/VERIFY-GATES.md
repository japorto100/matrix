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

### exec-09 Protocols + Generative UI  *(updated 2026-04-22, plan-v2 merged)*
- ✓ **Tambo komplett entfernt** — ersetzt durch Google A2UI v0.9. Old
  `features/agent/components/tambo/` archiviert nach
  `features/agent/components/a2ui/` + `A2uiCanvas.tsx` + `A2uiProvider.tsx`.
- ✓ CopilotKit: `AgentProviders` env-gated (`NEXT_PUBLIC_COPILOTKIT_ENABLED`),
  `runtimeUrl=/api/copilotkit` — **route existiert jetzt**
  (`src/app/api/copilotkit/route.ts`, OpenAIAdapter → LiteLLM).
- ✓ AG-UI a2ui-renderer: `@copilotkit/a2ui-renderer` + `@a2ui/web_core` v0.9.
- ✓ WebMCP Polyfill: `@agent/lib/webmcp-polyfill` Side-Effect-Import in Layout.
- ✓ **A2UI tree validation** — `a2uiTreeSchema.ts` (Zod + whitelist) guards
  Malformed LLM output.
- ✓ **`render_a2ui_surface` python tool** registered in ToolRegistry.load()
  with TradingTool ABC signature (`execute(tool_input, ctx)`).
- ✓ **Conditional A2UI system-prompt** — keyword-gated injection.
- ✓ **`usePersistentSurface`** — localStorage Phase-1, Postgres sync deferred
  to Phase-2 pending `/api/v1/surfaces/*` in go-appservice.
- ✓ **Playwright tests #9-#12** in `tests/a2ui-integration.spec.ts`.
- ○ Live Generative-UI Demo (Agent emittiert A2UI widget auf main-canvas
  oder chat-inline): Backend-tool verified via unit tests; full LLM
  round-trip blocked on `_prepare_system_prompt` timeout (commit b90fad3
  added guard) + agent dispatcher path — see findings doc.

### exec-10 Multi-Agent — —
### exec-11 Memory Evolution — —

## Sandbox / UI / KG

### exec-12 Sandbox Security
- ○ OpenSandbox Compose-Service in `docker-compose.yml` bleibt unter
  `--profile sandbox`. Nicht default.

### exec-13 UI KG Extensions  *(archived — content in exec-15)*
- ✓ KG-Graph Feature aus `control-ui/src/features/memory/` kopiert nach
  `features/memory/`, inkl. `lib/kg-graph/` + `@xyflow/react` + d3-force deps.
- ✓ **Live page load verified 2026-04-22** — Memory tab renders Knowledge
  Graph card (kuzu, Healthy) + tab link. Full graph-viz with nodes+edges
  blocked on seeded KG data (ingestion-worker not in --matrix-chat preset).

### exec-14 PDDL — —

### exec-15 Memory Control UI  *(live-verified 2026-04-22)*
- ✓ Control + Files + Memory Features kopiert + Routen verdrahtet:
  - `/control/[[...tab]]` → 8 Control Surfaces in sidenav (Overview/Agents/
    Permissions/Skills/Tools/Sessions/Tasks/Context/Security) + 4 Developer
    tabs (Sandbox/Audit/Mcp/A2a/System/Api)
  - `/files/[[...tab]]` + FileCard "Add to Chat" context-menu
  - `/memory/[[...tab]]`
- ✓ Playwright Tests #5/#6/#7 + neue #9-#12 (A2UI integration) gruen.
- ✓ **Live Memory Browser Data Load PASS** — 3 layer cards (Episodic fusion /
  KG kuzu / Vector pgvector) alle Healthy mit Items=0 / Last Sync=never,
  Runtime Context mit Prompt/Completion/Cached/Total Zähler, degradation
  flags (NO_PERSONAL_MEMORY/KB/WORLD_EVIDENCE/WORLD_KG) korrekt. BFF →
  go-appservice → python memory-service wiring verified end-to-end.

## LLM / Observability / Schema / Devstack / MCP

### exec-16 LLM Provider Gateway  *(mostly live 2026-04-22)*
- ✓ `LITELLM_BASE_URL=http://localhost:4000` + `COPILOTKIT_DEFAULT_MODEL`
  dokumentiert in `.env.example`.
- ✓ **LiteLLM tool-call smoke PASS** (plan-v2 Task 0): OpenRouter
  `inclusionai/ling-2.6-flash:free` über LiteLLM → tool_calls mit
  arguments als JSON-string (OpenAI-standard). Streaming SSE deltas
  verified.
- ✓ **Model Explorer live render — 346 / 346 Modelle** geladen über
  LiteLLM `/v1/models` proxied by python-agent.
- ✓ Model Routing Table mit 6 Trading Roles + per-role Override-Dropdown.
- ✗ LiteLLM Spend Tracking: Usage & Spend Panel zeigt "No spend data yet.
  Requires LITELLM_DATABASE_URL to be configured."
- ✗ User-Model-Picker Wiring live in Agent-Chat: backend agent hangt auf
  LLM call (siehe findings doc), streaming-format-fix committed (31f2bb5).

### exec-17 Observability
- ○ `OTEL_*` + `OPENOBSERVE_*` Env-Vars in `.env.example` vermerkt.
- ✗ Live Traces in OpenObserve: braucht observability stack.

### exec-18 Unified Agent Schema — —

### exec-19 Devstack Consolidation — **ARCHIVED 2026-04-18**
- ✓ **Direkt betroffen:** neue `scripts/dev-stack.sh` (Linux-Port von
  `dev-stack3.ps1`) + `docker-compose.yml` Profile-Split.
- ✓ Postgres-DSN `postgres://postgres@localhost:5433/hindsight_dev`
  dokumentiert (exec-19 fordert "Postgres only, SQLite entfernt").
- ✓ **`python -m alembic upgrade head` PASS 2026-04-22** against running
  postgres container — head = `026_smart_routing_config`. Schemas: agent,
  ingestion, scheduler, storage, public.
- **Historie:** Stufe 1-2 (DevStack-Fixes + Matrix-Crypto→Postgres) wurde
  abgeschlossen 2026-04-18. Offene Items wurden extrahiert nach drei
  Eigentümer-Specs:
  - `exec-media-ingestion.md` — §3.5 + §3.7 image/audio/video/batch pipelines
  - `exec-16-llm-provider-gateway.md` §Phase 4.5 — §5c Reasoning/Auto-Mode
  - `exec-05-ui-viewers-polish.md` (this slice) — §3.9 viewer-packages + §5b.6-§5b.10 model-discovery polish + §5c.6 reasoning-composer-button

### exec-05 UI Viewers + Files/Models Polish (this slice, 2026-04-18)

- ○ Neue Spec kreiert aus archiviertem `exec-19 §3.9/§5b.6-§5b.10/§5c.6`.
  Touches auf diesem Branch sind `bun add`-Vorbereitung + Ownership-Klärung
  wo die Features leben (Control-UI vs agent-chat vs features/files/).
- **Bei dir zu pruefen (später Stack-Live):**
  - Waveform / EXIF / XLSX / DOCX / enhanced-MD renderer in Files-Tab.
  - URL-State via nuqs für Model-Filter; Postgres `agent.llm_models_cache`.
  - Reasoning-Cycle-Button (Low/Medium/High/Auto) im Composer + Body-Forward.

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

## Zusammenfassung der tatsaechlich gelaufenen Gates  *(updated 2026-04-22)*

| Gate | Command | Ergebnis |
|---|---|---|
| Go build | `go build -tags goolm ./...` | ✓ |
| Go vet | `go vet -tags goolm ./...` | ✓ |
| Go tests | `go test -tags goolm -short ./...` | ✓ 9/9 packages |
| Go lint | `golangci-lint run ./...` | ✓ 0 issues (war 12) |
| Python lint (my files) | `uv run ruff check agent/tools/a2ui_surface.py …` | ✓ 0 issues |
| Python lint (full) | `uv run ruff check .` | 🟡 73 pre-existing issues in `compute/indicator_engine/*` (N815 mixed-case, F401) — separate slice |
| Python tests | `uv run pytest tests/agent/` | ✓ 304/304 |
| Frontend install | `bun install --ignore-scripts` | ✓ |
| Frontend typecheck | `bunx tsc --noEmit` | ✓ |
| Frontend vitest | `bunx vitest run` | ✓ 20/20 unit tests |
| Frontend build | `bun run build` | ✓ 18 routes (incl. `/api/copilotkit`, `/api/files/save-attachment`) |
| Frontend biome | `bunx biome check ./src` | ✓ 368 files, 0 errors |
| Alembic migrations | `uv run alembic upgrade head` | ✓ head=026_smart_routing_config |
| Compose parse | `python3 -c 'yaml.safe_load(docker-compose.yml)'` | ✓ 21 services, 18 profiles |
| Shell syntax | `bash -n scripts/*.sh` | ✓ |
| LiteLLM tool-call smoke (plan-v2 Task 0) | `curl localhost:4000/v1/chat/completions` | ✓ streaming SSE deltas with tool_calls |
| Frontend prod smoke (plan-v2 Task 15) | `next start` → 5 surfaces via chrome-devtools MCP | ✓ all pages render, gateway URL 29318 |
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
