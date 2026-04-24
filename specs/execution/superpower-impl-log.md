# superpower-impl-log — Rollup of work since superpower-skill activation

> **Status:** lebend. **Geltungsbereich:** alle implementierungen, ADRs,
> entscheidungen, research-reads und bug-fixes seit der superpower-skill
> triggerung am **2026-04-22**. Dieses dokument ist der temporäre zentrale
> status-rollup — später verteilen wir die einträge in die jeweiligen
> `exec-*.md` dateien und entfernen das file.
>
> **Lese-reihenfolge:** §0 für session-phasen-abgrenzung, §1 für die ADRs
> (irreversible entscheidungen zuerst), §2 für die impl-cluster (nach
> commits gruppiert), §3 für infra/smoke/verify, §4 für blocked-state +
> handoff-punkte, §5 für den status pro exec-* spec.
>
> **Quellen-policy:** jeder eintrag zitiert (a) die commit-SHA, (b) betroffene
> dateien, (c) wo der haupt-eintrag später hinwandert (spec-ref).

---

## §0 Session-abgrenzung

| Phase | Zeitraum | Fokus | Commits |
|-------|----------|-------|---------|
| **P0 Research + Planung** | 2026-04-22 | Superpower-skill triggerung, open-tasks triage, overnight findings | `ddcd6fe` `dc539df` |
| **P1 ADRs + Smart-Routing** | 2026-04-23 vormittag | ADR-001..004 ratifizieren, Smart-Routing G1–G6 + P1 | `7163d75` → `89ed88d` |
| **P2 Research phase-2** | 2026-04-23 nachmittag | A²FM paper, L1 mode-analysis, §4g.4 eval_id wiring | `753d2ba` → `c368752` |
| **P3 exec-rollups + ratifications** | 2026-04-23 abend | exec-scheduler2 / exec-notifications / exec-media / exec-rust / exec-hermes ratifizieren | `e86383a` → `2450162` |
| **P4 HITL + frontend integration** | 2026-04-23 nacht | ADR-004, skills-guard-drawer, files-tab unblock, CompressionIndicator, title-gen | `88bfc05` → `6b794e0` |
| **P5 Memory-umbrella** | 2026-04-24 vormittag | 4-spec cross-check, Taxonomie compression/compaction/clear | `76c64b1` |
| **P6 Bug-fixes + Plan-v2 Phase-2** | 2026-04-24 heute | MCP 500 + port-collision gefixt, #31–#34 A2UI voll gelandet | `cb284a2` → `e74caad` |
| **P7 Observability strategy + #46 tier 1+2** | 2026-04-24 heute | env-layout entscheidung (root + service), OTel vs OpenObserve klarstellung, 3-tier model, #46 reframed um Next.js BFF (tier 2), tier 3 split als #92 | `d1454a4` + `d78ad68` — **landed** |

---

## §1 ADRs (irreversibel, erster commit-block)

| ID | Thema | Findings-doc | Commit | Späteres ziel |
|----|-------|--------------|--------|---------------|
| **ADR-001** | Smart-Routing rollout gate (G1–G6 + P1) | `docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md` | `7163d75` `0a59a76` `5061586` `57400f4` `dc539df` `14dbcdf` `89ed88d` | `exec-16 §2.D` |
| **ADR-002** | Tracing + Audit parallel stores (LLM_REQUEST removal) | `docs/superpowers/findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md` | `c45d639` | `exec-17 §C9` |
| **ADR-003** | exec-14 DSPy-track gating via contrarian | `docs/superpowers/findings/2026-04-23-adr-003-exec-14-dspy-gating.md` | `30e109c` `f1123e3` | `exec-14-DSPy.md §-1` |
| **ADR-004** | Sandbox-HITL surface-dialog layer via consent_system | `docs/superpowers/findings/2026-04-23-adr-004-sandbox-hitl-layer.md` | `88bfc05` | `exec-12 §HITL` + `exec-security §skills-guard` |

**Prinzip:** jede ADR wurde vor code-änderung durch `sota-contrarian`
stress-getestet. Alle vier sind durch die session als verdict=`proceed`
gelaufen und haben danach impl-commits getrieben.

---

## §2 Impl-cluster (nach logischer gruppe, nicht chronologisch)

### §2.A Smart-Routing (ADR-001) — rollout gate komplett

| Gate | Commit | Scope | Dateien |
|------|--------|-------|---------|
| **G1** DE keyword set + hyphen-tokenizer | `0a59a76` | bilingual EN+DE, hyphen-wort split | `python-backend/agent/llm/smart_routing.py` |
| **G2** Credential pre-flight | `57400f4` | `user_has_provider_credential` vor switch | `python-backend/agent/security/credentials.py` |
| **G3** Config cache 60s TTL | `5061586` | `@lru_cache` + ttl wrapper | `python-backend/agent/llm/smart_routing.py` |
| **G4** A/B harness routing dim | `dc539df` | alembic `027_ab_experiments_routing_dim.py` + 3 spalten (routing_used / reason / picked) | `python-backend/agent/harness/` + migration |
| **G5** User-visible indicator | `14dbcdf` | SSE `message-metadata` → routingUsed/Reason/Picked → amber pill | `python-backend/agent/graph/runner.py` + `frontend_merger/src/features/agent/components/AgentChatMessage.tsx` |
| **G6** Control-UI panel + disable path | `14dbcdf` | GET/PUT `/user/llm/smart-routing` + SmartRoutingSection | `python-backend/agent/control/user_llm.py` + `SmartRoutingSection.tsx` |
| **P1** Wire-point inversion | `89ed88d` | Router als erste graph-node statt mid-llm-call | `python-backend/agent/graph/nodes/router_node.py` (neu) + `agent_graph.py` + `llm_node.py` + `dispatcher.py` |

**Späteres ziel:** alle einträge → `specs/execution/exec-16-llm-provider-gateway.md §2.D` + `exec-17 §C9`.

### §2.B Harness + eval_id + A²FM

| Eintrag | Commit | Scope |
|---------|--------|-------|
| §4g.4 eval_id wiring | `753d2ba` | scorer `score_session/score_sessions` + evaluator + `/internal/harness/backfill` JSON body — eval_id tracked end-to-end |
| L1 mode_analysis post-hoc labeling | `c368752` | `python-backend/agent/harness/mode_analysis.py` (neu) — CLI skript, labelt traces als exploit/explore/verify mode |
| A²FM research phase-2 re-sequence | `c6c2ecf` | `specs/execution/exec-a2fm-adaptive-routing.md §Phase-2` — L1→L2→L3, PDF in `docs/papers/A2FM-2510.12838v3.pdf` |

**Späteres ziel:** `exec-harness.md §4g.4` + `exec-a2fm-adaptive-routing.md §Phase-2`.

### §2.C exec-06 Phase 5 frontend — CompressionIndicator + title-gen

| Eintrag | Commit | Scope |
|---------|--------|-------|
| title-gen async dispatch | `e0bf944` + `289c844` | `python-backend/agent/titles/generator.py` (neu) + `generate_and_persist_title` + `__all__` export + idempotent UPDATE SQL |
| CompressionIndicator component | `e0bf944` | `frontend_merger/src/features/agent/components/CompressionIndicator.tsx` (neu) — status-dot, 3 stages (ok/compact/compress) |
| BFF `/api/agent/compression-status` | `e0bf944` | `frontend_merger/src/app/api/agent/compression-status/route.ts` |
| go-appservice proxy | `968f432` | `/api/v1/agent/context/compression-status` route |

**Späteres ziel:** `exec-06-agent-chat-integration.md §Phase-5`.

### §2.D Plan v2 Phase-2 (A2UI) — KOMPLETT HEUTE 2026-04-24

Der finale meilenstein — alle 4 tasks gelandet in dieser session.

| # | Titel | Commit | Scope | Dateien |
|---|-------|--------|-------|---------|
| **#31** | Postgres surfaces persistence | `0f7c532` | Alembic `028_agent_surfaces` (user_id, surface_id PK + schema_version + jsonb surface_json + updated_at). Go `/api/v1/surfaces/{load,save,delete}` mit X-Actor-User-Id auth (401/404/204). BFF `/api/surfaces/[id]`. Hook `usePersistentSurface` erweitert (cache-first hydration, server-reconcile, syncState API). | `python-backend/alembic/versions/028_agent_surfaces.py`, `go-appservice/internal/handlers/http/surfaces_handler.go`, `frontend_merger/src/app/api/surfaces/[id]/route.ts`, `frontend_merger/src/features/agent/hooks/usePersistentSurface.ts` + tests |
| **#32** | Ansatz X native A2UI SSE packets | `01ffa9f` (+ `e74caad` rename to `data-a2ui-*`) | 5 dataclasses in `streaming.py`: `A2uiSurfaceStart/Update/UpdateDataModel/SurfaceEnd/DeleteSurface`. TS-types + `toRendererMessage()` adapter. | `python-backend/agent/streaming.py`, `frontend_merger/src/features/agent/lib/a2ui-packets.ts` + tests |
| **#33** | a2ui-agent-sdk install + typed emitter | `3366585` | Google `a2ui-agent-sdk 0.2.1` installiert, selective import (a2ui.schema + a2ui.parser + a2ui.basic_catalog), google-adk/genai/a2a deps installiert aber nicht runtime-geladen (verified per sys.modules probe). Wrapper: `agent/a2ui/` modul mit `A2uiEmitter`, `build_system_prompt`, `translate_sdk_message`, `validate_protocol_messages`. | `python-backend/agent/a2ui/__init__.py`, `python-backend/agent/a2ui/emitter.py`, `python-backend/pyproject.toml`, `python-backend/uv.lock` + tests |
| **#34** | Live-data binding (SSE push + TanStack pull) | `e74caad` | `useA2uiSseSubscriber` hook (`useChat.onData` → `processMessages`). `useA2uiWidgetData` TanStack-Query hook (REST pull für widget on-demand). Shared A2UI store via `A2uiRootProvider` in layout.tsx — feedt sowohl chat-inline canvas als auch landing-page canvas `surfaceId="main"`. | `frontend_merger/src/features/agent/hooks/useA2uiSseSubscriber.ts`, `useA2uiWidgetData.ts`, `useChatSession.ts` (onData wiring), `A2uiCanvas.tsx` + `page.tsx` docs, `useMatrixRTCCall.ts` TS-narrow |

**Wire-format:** typen wurden in #34 von `a2ui-*` zu `data-a2ui-*` umbenannt
— AI-SDK v6's `DefaultChatTransport` würde non-prefixed packets sonst mit
einem zod-union-fehler rejecten. Mit `data-*` prefix landet jeder unserer
packets in `useChat.onData`, von wo der subscriber sie an die renderer-store
weitergibt.

**MCP und A2UI** — entscheidung dokumentiert (session-notiz):
- **A2UI widget data binding braucht KEIN MCP.** SSE-push (#32) für live-data, TanStack-Query/REST (#34) für on-demand pull. MCP-framing wäre overhead ohne gewinn.
- **MCP bleibt für `ToolsTab` (user-configurable MCP servers) + `.mcp.json` (claude-code trace inspection)** — zwei separate concerns.

**Späteres ziel:** `exec-09-protocols-generative-ui.md §Phase-2` + mapping-design §17.

### §2.E exec-security (ADR-004) — Skills-Guard HITL drawer

| Eintrag | Commit | Scope |
|---------|--------|-------|
| Skills-importer suggested_action | `d8bf243` | `POST /api/control/skills/import` 422 body enthält `suggested_action: "hitl_confirm"` bei dangerous verdict |
| SkillsGuardDrawer frontend | `b5984e1` | HITL modal mit verdict + findings + 3 decision-buttons (approve / reject / review-code) |
| ApiError body wrapper | `b5984e1` | `lib/queries/client.ts` — strukturierte error-payloads statt nur message |
| extractSkillsGuardVerdict helper | `b5984e1` | disambiguiert `/skills/import` (multi-reject) vs `/skills/install` (single-skill) body shapes |

**Späteres ziel:** `exec-security.md §skills-guard` + `exec-12-sandbox-security.md §HITL`.

### §2.F exec-ratifications (paper-only diffs, keine neue impl)

| Spec | Commit | Was ratifiziert |
|------|--------|-----------------|
| `exec-scheduler2.md` | `e86383a` | D-1..D-8 decisions ratified-line in §7 |
| `exec-notifications.md` | `462eebd` | ready-to-implement status |
| `exec-media-ingestion.md` | `7743c6d` | ready-to-implement status |
| `exec-rust.md` | `b57cb45` | 3-phase integration plan ratified (Compute-as-Tool → gRPC → WASM) |
| `exec-hermes.md` | `89ed88d` | Phase-B P6 frontend tail DONE |
| `exec-14-DSPy.md` | (ADR-003 commit) | D-1 reframed, D-2/D-3 deferred, Phase-(-1) PoC gate added |
| `exec-security.md` | (ADR-004 commit) | HITL unblocked 2026-04-23 via ADR-004 |

### §2.G Memory-umbrella boundary review

| Eintrag | Commit | Scope |
|---------|--------|-------|
| 4-spec cross-check | `76c64b1` | `docs/superpowers/findings/2026-04-24-memory-umbrella-boundaries.md` — exec-memory + exec-world-model + exec-personal-kb + exec-context sind konsistent, keine überlappungen |

Taxonomie-klärung (session-output, im memory-system gespeichert):

- **Compaction** (≥85% kontext-füllung) — mechanisch, kein archiv
- **Compression** (≥95%) — LLM summary, **MemPalace + Hindsight MUSS vorher archivieren**, sonst info-loss
- **Clear** — user-action, session-lifecycle, derzeit kein auto-archive

**Späteres ziel:** `exec-memory.md §Compression-policy` + `exec-context.md §Taxonomie`.

### §2.H Bug-fixes (heute 2026-04-24)

| Bug | Commit | Root-cause | Fix |
|-----|--------|------------|-----|
| **FastMCP `/mcp/` 500** | `cb284a2` | `streamable_http_app()` returned Starlette sub-app; sein `lifespan` startet den `StreamableHTTPSessionManager`. Fast­API's `app.mount()` propagiert sub-app lifespans NICHT — manager nie gestartet, jede request crasht in ASGI dispatch | (a) sub-apps vor parent erstellen. (b) combined `@asynccontextmanager` via `AsyncExitStack` threading beider `router.lifespan_context`. (c) `create_service_app(lifespan=...)` erweitert. (d) `FastMCP(streamable_http_path="/")` so dass effective path `/mcp/` statt `/mcp/mcp/`. Verified: POST `/mcp/` liefert 200 + `initialize` response mit 24 tools. |
| **Port-collision lk-jwt (:8080) ↔ opensandbox-api-gateway (:8080)** | `cb284a2` | Beide container binden host port 8080 (verschiedene compose profiles, aber latent conflict wenn `--calls` + `--sandbox` gleichzeitig) | Host-port auf 8082 verschoben (container-internal bleibt 8080). Updates in docker-compose.yml + homeserver/tuwunel.v1.6.toml `rtc_transports` + bootstrap-env.py + frontend .env.example + 2 hook-fallbacks entfernt (throw statt localhost-camouflage). |

**Späteres ziel:** `exec-09-protocols-generative-ui.md §MCP-wiring` + `docker-compose.yml` comment-trail.

### §2.I Observability strategy (#46 reframed + #92 split)

Entscheidungen getroffen vor der impl (siehe findings):

| Entscheidung | Findings-doc | Warum |
|---|---|---|
| Env-layout: root `.env` (compose interpolation) + service `.env`s (runtime) — **both, verschiedene scopes** | `2026-04-24-env-layout-decision.md` | Offizielles docker-compose model trennt interpolation von container-env. Nur-root oder nur-service scheitern an service-prozessen außerhalb compose. |
| OTel vs OpenObserve klarstellung: OTel = vendor-neutral standard, OpenObserve = austauschbarer OTLP-receiver | `2026-04-24-observability-tier-strategy.md §1` | Swap zu Jaeger/Tempo/Datadog/Honeycomb = endpoint + auth-header change, kein code-change |
| 3-tier model: backend (done ✓) + Next.js BFF (in #46) + browser RUM (in #92) | `2026-04-24-observability-tier-strategy.md §2` | Tiers 1+2 sind server-side mit gleichem pattern, tier 3 ist security-kritisch + eigenes scope |
| Browser darf NIEMALS direct OTLP senden — BFF-proxy pattern | `2026-04-24-observability-tier-strategy.md §3` | Industry consensus (Grafana, Dash0, Groundcover, Elastic 2026): creds im bundle = leak via DevTools |

#46 scope (revised):
1. ✅ OpenObserve container recreate mit OPENOBSERVE_* aus root `.env` (commit `d1454a4`)
2. ✅ `go-appservice/.env.development` ergänzen — aber dann doch obsolet weil wir durch den collector routen (creds an collector container env). Kept commented für direct-mode switch.
3. ✅ **go-traces E2E smoke** → openobserve UI zeigt `matrix-appservice` spans (otelhttp middleware hinzugefügt in `server.go` — das war der **echte impl-gap**, go hatte OTel-init aber keinen handler-wrap → silent no-traces)
4. ✅ **python-agent-traces E2E smoke** → openobserve zeigt `agent-service` spans (FastAPIInstrumentor war schon da, nur `.env.development` hatte `OTEL_ENABLED=false`)
5. ✅ **Next.js BFF via `@vercel/otel`** (commit `d78ad68`) — `frontend_merger/src/instrumentation.ts`, opt-in, routed via :4318 (HTTP OTLP, @vercel/otel default ist HTTP nicht gRPC — gotcha dokumentiert)
6. ✅ Vendor-portability verify: keine direct OpenObserve-API-calls außerhalb OTel path (nur für ops-queries via curl in session)

**Final smoke verdict (nach commit `d78ad68`):**

| Service | Spans | Path |
|---|---|---|
| `matrix-appservice` (go) | 45 | otelhttp → collector :4317 → openobserve |
| `agent-service` (python) | 180 | FastAPIInstrumentor → collector :4317 → openobserve |
| `frontend-merger-bff` (Next.js) | 90 | @vercel/otel → collector :4318 → openobserve |

**Offene polish-items** (nicht blocking):
- W3C traceparent cross-service propagation — BFF und go haben separate trace_ids, propagation-link muss fine-getuned werden (propagator ist TraceContext auf allen 3 — wahrscheinlich fetch-instrumentation-config). Tracked als #46-close-out-polish.
- Tier 3 browser RUM → **`#92`** (separate task, BFF-proxy pattern für creds-safety).

**Späteres ziel:** `exec-17-observability-harness-traces.md §Phase-2` + `§verify-gates` (prod-build-only for @vercel/otel documented).

---

## §3 Infra, stack-flags, smoke results

### §3.A dev-stack.sh invocations that worked

```bash
./scripts/dev-stack.sh --agent-dev --go --frontend
./scripts/dev-stack.sh --restart=agent     # nach code-änderung in python-backend/
./scripts/dev-stack.sh --restart=go        # nach code-änderung in go-appservice/
./scripts/dev-stack.sh --status
```

### §3.B Container recovery (podman rootlessport race)

**Memory:** `project_postgres_rootlessport_race` — podman postgres crashed
mit exit-137 / connection-reset beim startup auf diesem host. Recovery:

```bash
podman restart postgres   # eventuell zweimal
```

Bei 500 auf DB-writes: **erst postgres-status prüfen** bevor andere ursachen
untersuchen.

### §3.C Smoke verdict (heute 2026-04-24)

| Endpoint | Status | Notiz |
|----------|--------|-------|
| `POST /mcp/` initialize | ✅ 200 | 24 tools registered, session-manager ok |
| `POST /mcp-traces/` initialize | ✅ 200 | traces server up |
| `PUT /api/v1/surfaces/main` (Go) | ✅ 200 | roundtrip mit valid JSON body |
| `GET /api/v1/surfaces/main` (Go) | ✅ 200 | idempotent read |
| `DELETE /api/v1/surfaces/main` (Go) | ✅ 204 | idempotent |
| `PUT /api/surfaces/bff-smoke` (BFF→Go) | ✅ 200 | E2E durchgehend browser→BFF→Go→Postgres |
| `GET /api/v1/surfaces/main` ohne X-Actor-User-Id | ✅ 401 | auth enforced |
| frontend `bun run typecheck` | ✅ 0 errors | — |
| frontend `vitest` (a2ui-related 23 tests) | ✅ 23/23 | alle grün |
| python `pytest` (a2ui-related 22 tests) | ✅ 22/22 | alle grün |

### §3.D Stack restarts this session

Es war **kein** `podman-compose down` nötig — `podman start <name>` reicht
für stopped container, und `dev-stack.sh --restart=<service>` für local processes.

Explizit geblockt durch sandbox-policy:
- `podman rm -f <many>` (mass-removal blocked — richtig so)
- `podman-compose down` (würde shared infra droppen — richtig so)

**Takeaway:** future sessions nutzen selective `podman start X Y Z` + `dev-stack.sh --restart=A,B`.

---

## §4 Blocked-state + handoff

### §4.A Tasks die wirklich offen sind (6 + 1 recurring)

| # | Titel | Blocker | Nächster schritt |
|---|-------|---------|------------------|
| **#38** | E2EE B1 base functionality | cinny/element + registered users | Browser-client test-rig |
| **#39** | E2EE B2 cross-signing + QR flow | cinny/element | Browser-client test-rig |
| **#40** | E2EE B3 key backup | cinny/element | Browser-client test-rig |
| **#51** | Multi-agent + memory evolution E2E | browser-client | Browser-client test-rig |
| **#60** | NATS E2EE E2E-test | browser-client | Browser-client test-rig |
| **#61** | A2A live-test (HOT) | browser-client | Browser-client test-rig |
| **#74** | exec-14 PDDL formal-planning | **user-skip** | — |
| **#76** | exec-ebm energy-based scoring | **user-skip** | — |
| **#82** | exec-matrix-monitor monthly upstream check | **recurring** | bleibt in_progress |

### §4.B Tasks die in dieser session bearbeitet wurden

| # | Titel | Status | Commits |
|---|-------|--------|---------|
| **#46** | exec-17 Observability traces (tiers 1+2) | ✅ completed | `d1454a4` (tier-1 go) + `d78ad68` (tier-2 BFF) |
| **#91** | verify bug fixes e2e | ✅ completed | implicit (MCP `/mcp/` 200 + lk-jwt :8082 verifiziert im run-up) |
| **#92** | exec-17 Tier-3 Browser RUM | pending (neu) | folge-task, separates scope (BFF-proxy, CSP, consent) |

### §4.C User-directives aktiv

Aus der session (in reihenfolge):

1. **"grösseren context jeweils cross exec files lesen, code anschauen… nicht einfach fire and forget"** — differenzierter approach, immer spec + code vor impl
2. **"nicht bei kleinen änderungen immer gitnexus reindex"** — nur bei strukturellen änderungen oder wenn MCP tool "stale" signalisiert
3. **"kein RL, effective LLM training, PDDL vorerst"** — Welle-3 tasks #74, #76 sind skip
4. **"wenn matrix probleme macht kannst du dort stoppen"** — matrix browser-tests nicht erzwingen
5. **"nimm a2a sdk auch mitein"** — a2a-sdk dep bleibt installiert für future exec-10/61
6. **"bun run build und dann bun start"** — prod-build für frontend-tests statt dev-mode

---

## §5 Exec-spec status (stand 2026-04-24 nach heute)

| Spec | Status | Letzter touch | Link |
|------|--------|---------------|------|
| `exec-05-nats-e2ee-pipeline.md` | server-ready, browser-client blocked | 2026-04-23 | |
| `exec-06-agent-chat-integration.md` | Phase 5 tail DONE | `e0bf944` | |
| `exec-09-protocols-generative-ui.md` | **Phase-2 KOMPLETT HEUTE** (#31-34) | `e74caad` | spec braucht noch "Phase-2 landed 2026-04-24" annotation |
| `exec-10-multi-agent.md` | server-ready, browser-client blocked | 2026-04-23 | |
| `exec-12-sandbox-security.md` | HITL landed, ADR-004 | `b5984e1` | |
| `exec-14-DSPy.md` | Phase-(-1) PoC gate, D-1 reframed | ADR-003 | |
| `exec-14-pddl-formal-planning.md` | user-skip | — | |
| `exec-15-memory-control-ui.md` | live-data rendering done | 2026-04-23 | |
| `exec-16-llm-provider-gateway.md` | §2.D smart-routing holistic review done | 2026-04-23 | |
| `exec-17-observability-harness-traces.md` | infra LANDED, verify-gates pending (#46) | `2450162` | |
| `exec-18-unified-agent-schema.md` | archive-or-keep decision DONE | `71` | |
| `exec-19-...` | postgres E2E DONE | | |
| `exec-20-mcp-manager.md` | live connection DONE | | |
| `exec-a2fm-adaptive-routing.md` | Phase-2 re-sequenced L1→L2→L3, PoC gate | `c6c2ecf` | |
| `exec-blocking.md` | C1-C11 triage DONE | | |
| `exec-context.md` | consistent mit memory-umbrella | `76c64b1` | |
| `exec-ebm.md` | user-skip | — | |
| `exec-eval.md` | harness smoke DONE | | |
| `exec-harness.md` | §4g.4 eval_id wiring DONE | `753d2ba` | |
| `exec-hermes.md` | Phase-B P6 frontend DONE | `89anz41` | |
| `exec-matrix-monitor.md` | recurring monthly (#82) | | |
| `exec-media-ingestion.md` | ready-to-implement | `7743c6d` | |
| `exec-memory.md` | raw evidence + derived memory DONE | | |
| `exec-notifications.md` | ready-to-implement | `462eebd` | |
| `exec-personal-kb.md` | consistent mit umbrella | `76c64b1` | |
| `exec-rust.md` | integration plan ratified, 3-phase | `b57cb45` | |
| `exec-scheduler2.md` | D-1..D-8 ratified | `e86383a` | |
| `exec-security.md` | skills-guard-drawer landed (ADR-004) | `b5984e1` | |
| `exec-skills.md` | skills-guard integration DONE | | |
| `exec-transformersjs.md` | title-gen owner delegated | `289c844` | |
| `exec-world-model.md` | consistent mit umbrella | `76c64b1` | |
| `exec2-01..04` | matrix-chat + verify gates | server-side ready, browser-client blocked | |

---

## §6 Verteilungsplan (wenn dieses file retired wird)

Später, wenn impl-log sich beruhigt hat, wandern die abschnitte in die
jeweiligen exec-specs:

- §1 ADRs → `docs/superpowers/findings/` bleibt als source-of-truth; refs
  in die exec-specs die sie betreffen (ADR-001 → exec-16, ADR-002 → exec-17,
  ADR-003 → exec-14-DSPy, ADR-004 → exec-security + exec-12).
- §2.A Smart-Routing → `exec-16 §2.D`
- §2.B Harness/eval_id → `exec-harness §4g.4`, `exec-a2fm §Phase-2`
- §2.C exec-06 Phase 5 → `exec-06 §Phase-5`
- §2.D Plan v2 Phase-2 → `exec-09 §Phase-2` (#31-34 als eigene sub-sektion)
- §2.E Skills-Guard HITL → `exec-security §skills-guard` + `exec-12 §HITL`
- §2.F Ratifications → jeweils im exec-spec oben in der status-zeile
- §2.G Memory-umbrella → `exec-memory §Compression-policy` + `exec-context §Taxonomie`
- §2.H Bug-fixes → `docker-compose.yml` comment + `exec-09 §MCP-wiring`
- §3 Infra/smoke → `docs/superpowers/journal/` oder `exec-*` verify-gates
- §4 Blocked-state → `docs/superpowers/findings/2026-04-22-open-tasks.md` update

Wenn das meiste verteilt ist: **dieses file löschen**, nur einen breadcrumb
in `docs/superpowers/findings/2026-04-24-impl-log-retired.md` lassen (ein-
zeiler "content distributed into exec-*, see git log for history").

---

*Maintained-by: session-log, automatisch erweitern beim nächsten impl-cluster.
Bei konflikten mit spec-files: spec-files gewinnen (this is a rollup, not
the canonical source).*
