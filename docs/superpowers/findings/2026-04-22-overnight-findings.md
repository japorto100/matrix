# Overnight Session Findings — 2026-04-22

Dinge die mir während des Plan-v2 + Verify-Gate-Durchlaufs aufgefallen
sind. Nicht alles ist Bug, einiges ist nur "sollten wir nochmal ansehen".

**Konvention:** `⚠️` = sollte gefixt werden, `ℹ️` = Doku/Bewusstsein,
`🔬` = Research/Decision offen, `✅` = bereits erledigt in diesem Run.

---

## Already fixed in this run ✅

| # | Was | Commit |
|---|---|---|
| ✅ | `streaming.py` ↔ ai-sdk v6 packet-format mismatch (blockiert ALLE chat responses) | `31f2bb5` |
| ✅ | `hsTokenMiddleware` geblockt alle `/api/v1/*` BFF-routes | `88c1f17` |
| ✅ | Frontend default gateway port `:8090` → `:29318` (historisch getrennter Gateway merged into appservice) | `c9bc1e0` |
| ✅ | `/api/files` BFF envelope-mismatch (geht jetzt an `/api/v1/files/overview` + unwrap `{success,data}`) | `3f22908` |
| ✅ | Browser schickte nie `X-Actor-User-Id` → dev-middleware.ts injection | `3f22908` |
| ✅ | `useFrontendTools` crashte ohne `<CopilotKit>` provider | `71d8b84` |
| ✅ | `A2UIRenderer` ignorierte silent unknown `initialTree` prop → jetzt `useA2UIActions().processMessages` | `71d8b84` |

---

## Stack / Infra

### ⚠️ postgres-container port-forward fragility (rootlessport race)
Nach `podman restart postgres` bleibt `0.0.0.0:5433` manchmal unbind obwohl
`podman ps` "healthy" sagt. Braucht zweiten `podman restart` oder ein
Kill/neu-Start der rootlessport-processes. Tritt sporadisch auf — Grund
wahrscheinlich TCP-TIME_WAIT + rootlessport race.

**Action:** In `scripts/dev-stack.sh` eine `wait-for-port 5433` mit 3×
retry einbauen. Oder: upgrade podman (1.0.6 hat bekannte port-forward bugs).

### ⚠️ dev-stack.sh compose-up schlägt silent fehl mit podman-compose 1.0.6
`compose up (default) failed` / `compose up (profiles) failed` ohne
sichtbaren Error. Manuelle `COMPOSE_PROFILES=x podman-compose up -d ...`
klappt. Verdacht: env-variable-passing Verhalten.

**Action:** `dev-stack.sh` sollte compose-output durchreichen statt
"failed"-Einzeiler ausgeben.

### ⚠️ `ingestion-worker unreachable` in AI-Health dashboard
Das `--matrix-chat` preset started ingestion-worker NICHT mit. Die
`AI Health` card in `/control` zeigt deshalb immer "Degraded". Entweder:
- Preset erweitern um ingestion-worker, ODER
- Health-check skipped services nicht als "Degraded" melden

### ⚠️ HuggingFace model re-downloads jedes Mal
Agent lädt `sentence-transformers/all-MiniLM-L6-v2` bei jedem Startup neu.
`HF_HOME=/mnt/cold-storage/models/huggingface` ist per CLAUDE.md konfiguriert
aber scheint nicht in den agent-process zu propagieren.

**Action:** `.env.development` + `dev-stack.sh` stellen sicher dass
`HF_HOME` an python-agent weitergereicht wird.

### ℹ️ Slow DB pool acquire (`[DB POOL] Slow acquire: 0.1–0.2s`)
Pool saturiert bei simultanen LLM + embedding + memory recall. Nicht
fatal, aber latency-spike bei ersten Request nach idle. Pool-size tuning.

---

## Frontend

### ⚠️ Files-Tabs außer Overview: API-shape drift
Images/Audio/Video/Documents/Data tabs iterieren noch über
`data.recent_uploads` aus `/api/files`. Nach meinem Fix liefert `/api/files`
jetzt overview-Shape — recent_uploads ist dabei, aber ohne Pagination.
Tabs funktionieren, verlieren aber Pagination. Mittelfristig: entweder
separaten `/api/files/list?type=image` endpoint ODER frontend sollte
overview + separate page-query kombinieren.

### ⚠️ MCP: failed (0 tools) — permanent
`AgentChatPanel` macht direkte browser requests an
`localhost:29318/api/v1/mcp` — CORS-blocked. Entweder:
- frontend BFF route `/api/mcp` dazwischen schieben, ODER
- go-appservice CORS header für `localhost:3003` hinzufügen, ODER
- retry-loop nach N fails stoppen (aktuell endless retry in dev-console)

### ⚠️ Control-UI `/control/tools` ≠ runtime `ToolRegistry`
Tools-tab zeigt "0 tools" weil er die admin-DB `agent.tool_registry` table
liest, nicht die in-process `ToolRegistry.load()`. Das ist verwirrend.

**Action:** Entweder ToolRegistry nach Startup einmal in die DB syncen
(seed), oder Tools-Tab aus runtime-snapshot aufbauen (agno introspect),
oder doc-comment in der UI erklären dass die tabs unterschiedliche Quellen
sind.

### ℹ️ User/Developer toggle state-preservation
Control-UI hat oben rechts "User | Developer" toggle. Unklar ob state
über route-changes persistiert. Nicht getestet — nice-to-have check.

### ℹ️ Matrix-Seite graceful fail erfordert setup-users pro Session
`/matrix` zeigt "Matrix-Verbindung fehlgeschlagen / Sliding Sync
fehlgeschlagen" weil alice's appservice-registration nicht persistent über
restart ist. Braucht `./scripts/setup-users.sh && ./scripts/register-appservice.sh`
nach jedem stack-start. Oder: config-flag um auto-zu registrieren.

---

## Backend / Python

### 🔬 Agent chat always hangs after `start`+`message-metadata` packets
Direct curl an `/api/v1/agent/chat` liefert konsistent nur die ersten 2
packets (start + message-metadata), dann Stille. Kein error im log.

Code-walk (`agent/graph/runner.py:44-48`): die 2 packets werden VOR
`_prepare_system_prompt(ctx, messages)` emittiert. Diese function macht:
skill-loader fetch → temporal_context → MemoryManager.prefetch → Hindsight
fallback recall. Jede dieser operations kann DB-pool blockieren (siehe
"Slow acquire" warnings) oder HTTP-calls hängen lassen (HF hub).

Vermutete Hauptursachen:
- `_prepare_system_prompt` wartet auf slow memory-recall mit exhausted DB
  pool (nur 2 connections; skill+memory+temporal parallel)
- `get_user_api_key("default-dev-user", "openrouter")` hängt weil
  credential-encrypt table-row fehlt
- HuggingFace sentence-transformers fetch beim ersten memory embedding

**Actions (priorisiert):**
1. `_prepare_system_prompt` mit asyncio.timeout(10s) wrappen → fallback zu
   plain system_prompt bei timeout, damit stream nicht hängt.
2. `AGENT_USE_LITELLM=true` + `LITELLM_BASE_URL` in dev-stack.sh exportieren
   für python-agent process, damit agent alle LLM calls durch LiteLLM routet
   (credentials dort bereits configured, keine DB-lookups nötig).
3. Pre-seed postgres für default-dev-user mit dummy credential-row
   (provider=openrouter, encrypted_key=<via LiteLLM>), damit cred-lookup
   nicht N/A returnt.
4. DB pool size von 2 → 10 für hindsight_api tunen (ENV
   `HINDSIGHT_DB_POOL_SIZE=10`).

### ℹ️ `_snake_to_camel` in streaming.py
Wenn ein packet-field mit underscore _prefix benannt ist (z.B.
`_internal`), serialisiert das fälschlich als `"Internal"`. Kein aktuelles
Problem, aber bei zukünftigen Packets Bewusstsein.

### 🔬 `MessageMetaPacket.metadata` → `messageMetadata` rename downstream
Wir haben `metadata` → `message_metadata` umbenannt in streaming.py. Andere
consumer (scheduler adapter) habe ich updated. Falls es downstream noch
consumer gibt die `metadata` direkt lesen, brechen die jetzt. Regression
check wäre gut.

---

## Specs / Process

### ℹ️ `frontend_merger/src/features/control/mock-data.ts` hardcodes ports
Zwei `:8090` references waren noch in env-preview mock-data. Fixed in
`c9bc1e0`. Aber grundsätzlich: mock-data die echte URLs hardcodiert ist
ein drift-Risiko.

### ℹ️ Root `matrix/package.json` = legacy `nextjs_tailwind_shadcn_ts`
Existiert seit Initial-Commit aber user bestätigte: nur `frontend_merger/`
wird gebraucht. Sollte archiviert werden (Task #58 auf liste).

### ⚠️ `exec-matrix-monitor.md` — monatlicher upstream check
Kein Kalender-hook dafür. Passive monitor-liste (Tuwunel v1.6 merge,
upstream bugs #411/#401/#377/#372, MSC3414, OIDC/MAS) sollte monatlich
angeschaut werden — aktuell nur papier-trail.

---

## Performance / Resource

### ⚠️ Next.js dev mode OOM bei 8 GB
`bun run dev` kompiliert alle 5 routen parallel bei erstem navigate, hit
earlyoom. Für local dev: `next start` mit pre-built bundle statt dev-mode.
Oder route-chunking via turbopack config.

### ℹ️ Tuwunel + Next.js + Python agent + Go + Postgres + Garage + LiteLLM
= ~4 GB bei idle, 6 GB unter load. Bei 8 GB RAM ist Swap-Nutzung normal
(~4.5 GB swap aktuell). Läuft, aber Headroom minimal.

---

## Stuff NOT investigated but noted

- `exec-blocking.md` C1-C11 ist living-doc. Nicht gereviewed in diesem Run.
- `exec2-03c-cinny` ✅ ist laut EXECUTION-ORDER done aber Smoke nicht
  gelaufen seit Merge.
- `exec-20 MCP Manager` useMcpTools hook + WebMCP aber ohne live MCP-server
  — noch nie end-to-end getestet.
- `exec-scheduler` Phase-1 DONE laut doc, smoke nicht gelaufen.
- Cross-signing + Key-Backup + E2EE verify-gates brauchen alle tuwunel +
  element-x physisch.

---

## Agent-chat-specific

### `/api/copilotkit` route erstellt aber nie getestet
In Plan v2 Task 12 gebaut, aber CopilotKit runtime endpoint nie live
angefragt. `NEXT_PUBLIC_COPILOTKIT_ENABLED=false` default heißt der Runtime
wird nie gemounted. Sobald wir CopilotKit-Actions tatsächlich benutzen
wollen (nicht nur register), muss das live getestet werden.

### A2UI "main" canvas persistence Phase-2
`usePersistentSurface` läuft localStorage-only. Cross-device sync braucht
`/api/v1/surfaces/*` im go-appservice — nicht implementiert (Phase-2
deferred, Task #31).

---

**Update-Regel:** Dieses doc ist append-only. Wenn was gefixt wurde, in
"Already fixed" section + commit-hash verschieben statt löschen.
