# Open Tasks — handoff ledger

> **⚠️ READ-ME-FIRST**: Dieses doc hat zwei zeit-schichten. Content **ab §"Post-session state — 2026-04-24 update (voll-katalog, FINAL)"** ist die **einzige authoritative quelle**. Der obere teil (Welle A/B/C "Agent-chat hängt" etc.) ist 2026-04-22 handoff-stand und seither **veraltet** — die meisten dortigen items sind inzwischen landed (siehe `specs/execution/superpower-impl-log.md` für vollen completion-log).
>
> **Quick-jump**:
> - TL;DR-tabelle: siehe §TL;DR direkt unten
> - Current open work (authoritative): §Post-session state FINAL (etwa zeile 230)
> - Historical 2026-04-22 content: §Welle A-G unten (archiviert, NICHT executeable)

---

## TL;DR — 2026-04-24 end-of-session stand

**Completed in superpower session**: Plan v2 Phase-1 + 4 von 7 Phase-2 items, ADRs 001-004, exec-17 observability tier 1+2, 6 exec-ratifications, smart-routing G1-G6+P1, memory umbrella, exec-06 Phase 5 tail. Plan v1 SUPERSEDED, Plan v2 DONE. Full commit-log in `specs/execution/superpower-impl-log.md`.

**Open work = 23 items in 8 kategorien:**

| Kat | Count | Tasks | Next-step |
|---|---|---|---|
| **A** Plan v2 Phase-2 gaps | 3 | #93, #94, #95 | Optional UX-polish |
| **B** Browser-client blocked | 6 | #38, #39, #40, #51, #60, #61 | **Highest leverage** — one rig unblocks all 6 |
| **C** User-skip | 2 | #74 PDDL, #76 EBM | Nicht jetzt, per user-decision |
| **D** Recurring | 1 | #82 monthly monitor | Bleibt in_progress |
| **E** Observability follow-up | 1 | #92 tier-3 browser RUM | Nice-to-have |
| **F** Unfixed verify-findings | 4 | G4-race, G1-quality, COALESCE, @vercel/otel doc | Small fixes |
| **G** Pre-existing noise | 1 | Typos DE allowlist | Wenn typos als CI-gate dazu kommt |
| **H** Infra runtime issues | 5 | Rootlessport race, stale healthchecks, stack-status, creds, commit-doc | Infra-session |

**Recommended next session**: **Build browser-client E2E rig** (one-time playwright+cinny setup) → 6 tasks unblocked at once.

Alternative kleiner start: **H-2 stale healthcheck recreate** (5-min fix) + **F-G4 INSERT/UPDATE race** (ON CONFLICT DO UPDATE refactor, ~1h).

---

## Historical context (archiviert 2026-04-22)

> Unten folgt das original 2026-04-22 handoff-content. Fast alle Welle-A/B/C-items sind seit 2026-04-24 landed. **Lese nur wenn du verstehen willst WARUM wir wo sind, nicht WAS als nächstes zu tun ist.**

Eine priorisierte Liste der 29 Items die am Ende dieser Session noch offen
sind. Companion zu `2026-04-22-overnight-findings.md` (welches Bugs +
Beobachtungen aus diesem Lauf dokumentiert).

**Stand der Gesamt-Liste (2026-04-22):** 29 completed / 53 pending / 82 gesamt. — *veraltet, siehe TL;DR oben für current stand*
**Dieser Doc:** nur die pending. Done-Items stehen in der taskforge
(`TaskList` / `TaskGet`) sowie in commits ab `2f5f977`.

---

## Empfohlene Reihenfolge

Drei Wellen, jede mit klarem Trigger was vor der nächsten erledigt sein muss.

### Welle A — Chat-Pipeline reparieren (entfernt Mehrheit der Blocker)
Bringt Agent-Chat live. Viele andere Tasks hängen davon ab.

1. **`#83 → Next` Agent-chat hängt nach `start`+`message-metadata`**  (`🔬 HIGH`)
   Already wrote timeout-wrap (commit `b90fad3`) — löst `_prepare_system_prompt`
   block. Remaining: LLM-roundtrip hangt in `_run_graph` nach der pre-prep.
   Actions aus `2026-04-22-overnight-findings.md §Backend Python`:
   a) Agent-process mit `AGENT_USE_LITELLM=true` + `LITELLM_BASE_URL=http://localhost:4000` starten
   b) Credential-seed row für `default-dev-user / openrouter` in `agent.user_credentials`
   c) DB pool `HINDSIGHT_DB_POOL_SIZE=10` setzen
   d) Wenn immer noch Hang → explicit debug-log in `llm_node` und `run_agent_loop_with_variant`.
   **Trigger done:** `curl /api/v1/agent/chat -d '{"message":"hi"}'` liefert `text-delta`-packets + `finish`.

2. **`#73` plan-skill live chat-smoke** *(~30 min, braucht #83)*
   Offline-verify PASS schon. Live-smoke: chat mit "lass uns planen bevor wir X angehen"
   → agent-response enthält strukturierten plan (Ziel/Annahmen/Approach/Schritte/Risiken).

3. **`#42 follow-up` A2UI widget live render** *(~1h, braucht #83)*
   Pipeline-infrastruktur verified (static tests pass). Live: chat mit "render widget NVDA"
   → tool-call `render_a2ui_surface` → widget im chat-inline + main-canvas.

4. **`#41 follow-up` Agent Chat integration live** *(~20 min, direkt nach #83)*
   Gleiches wie #42 aber ohne widget: normal text-streaming PASS als green.

### Welle B — Matrix + Cluster-Infra Smoke (live gates die Stack-access brauchen)
Brauchen entweder `setup-users.sh` + `register-appservice.sh` auf laufendem tuwunel,
oder zusätzliche compose-profiles.

5. **`#35 exec2-04 A1` Tuwunel homeserver smoke** *(~20 min)*
   `./scripts/setup-users.sh && ./scripts/register-appservice.sh` — alice + bob
   registriert, appservice handshake ohne `M_EXCLUSIVE`. Unblocks #36, #38, #39, #40.

6. **`#36 exec2-04 A2` Sliding Sync** *(nach #35)*
   Browser: /matrix lädt Raumliste <500ms. DevTools Network: `simplified_msc3575/sync` request.

7. **`#37 exec2-04 A3` LiveKit + lk-jwt-service** *(braucht `--calls` preset)*
   `./scripts/dev-stack.sh --matrix-full` → LiveKit :7880, lk-jwt :8080 up.
   `.well-known/matrix/client` liefert `org.matrix.msc4143.rtc_foci`.

8. **`#38 exec2-04 B1` E2EE base functionality** *(braucht #35+#37 done)*
   Go-appservice `[e2ee] OlmMachine geladen` log, `/keys/upload` PUT via /_matrix/app,
   browser rust-crypto init, send+receive `m.room.encrypted`.

9. **`#39 exec2-04 B2` Cross-Signing + QR Flow** *(braucht #38, Element-X physisch)*
   Physical Element-X device scan QR → SAS fallback. Manual-test only.

10. **`#40 exec2-04 B3` Key Backup** *(braucht #38)*
    `m.megolm_backup.v1` setup, recovery-key export, fresh browser profile restore
    → decrypt works.

### Welle C — Backend fixes + Control-UI walk-through (parallel zu A/B möglich)

11. **`#60 exec-05 A4` NATS E2EE E2E-test** *(~45 min, Cluster C hot)*
    publish via cinny-client → subscribe via go-appservice → decrypt via python-bridge.
    Phase A+B impl, A4 ist **der** offene verify-gate der gesamten
    NATS-pipeline. Commandline-smoke-possible ohne UI.

12. **`#61 exec-10 A2A` live-test** *(~1h, Cluster E HOT)*
    Never live-tested end-to-end. agent-a delegates to agent-b via AgentCard,
    verify round-trip. Code ready aber noch nie dagegen geklickt.

13. **`#62 exec-06 Phase 5 tail`** *(~1.5h)*
    Phase-B P6 CompressionIndicator.tsx (frontend; backend DONE). Title-gen
    async dispatch (primary = transformers.js — braucht @ xenova/transformers).

14. **`#44 exec-15 Memory Browser live data load` — already done partial**
    Already completed in the overnight session (3 layer cards Healthy). Full
    CRUD on /memory needs seeded data — deferred.

15. **`#45 exec-16 User-Model-Picker live in Agent-Chat` — already done**
    Already completed (346 models load from LiteLLM). Composer-side model-switch
    live-test needs chat working (→ depends on Welle A #83).

16. **`#72 Control-UI alle 15 tabs` — already done partial**
    4 tabs verified; 11 remaining walkthroughs (Skills, Sessions, Tasks, Context,
    Security, Sandbox, Audit, Mcp, A2a, Permissions, System). Low-priority,
    same BFF-pattern as tested tabs.

### Welle D — Architectural decisions + ADRs (brauchen sota-contrarian + research)

17. **`#65 Cluster H` exec-16 §2.D smart-routing holistic review** ✅ **DONE 2026-04-23**
    `sota-contrarian stakes=high` complete. ADR-001 filed at
    `docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md`.
    exec-16 §2.D + exec-a2fm.md updated.
    - **`#84 G1`** DE keyword set + hyphen-tokenizer ✅ **DONE 2026-04-23** (commit `0a59a76`)
    - **`#85 G2`** Credential pre-flight check in llm_node.py ✅ **DONE 2026-04-23** (commit `57400f4`)
    - **`#86 G3`** 60s TTL cache on get_user_smart_routing_config ✅ **DONE 2026-04-23** (commit `5061586`)
    - **`#87 G4`** A/B harness routing dimension + migration 027 ✅ **DONE 2026-04-23** (commit `dc539df`)
    - **`#88 G5`** User-visible routing indicator (GDPR disclosure) *(M, 1-2d frontend — PENDING)*
    - **`#89 G6`** Control-UI panel + self-service disable *(M, 2-3d frontend — PENDING)*
    - **`#90 P1`** Inversion: refactor to router_node.py ✅ **DONE 2026-04-23** — router_node.py als eigener Graph-Node zwischen memory_recall und llm_call. Tool-continuation-Loop umgeht router → "first turn only" by graph construction. llm_node ist jetzt consumer-only.
    **Rollout status:** All 4 backend gates + P1 refactor DONE. Frontend gates (G5 indicator, G6 Control-UI) remain. Flip `enabled: true` BLOCKED until G5+G6 ship (frontend work).

18. **`#66 Cluster H` exec-17 C9 ADR — tracing+audit parallel stores** *(~1.5h)*
    OTEL (perf debug) vs audit log (compliance). Should they be same store or parallel?
    Write ADR-0002 aligned with exec-security umbrella.

19. **`#75 Cluster K` exec-14-DSPy contrarian review** *(~2h, `stakes=high`)*
    5 decisions D-1..D-5 gate before any impl. DSPy-compiled NL→PDDL translator.
    Must run contrarian BEFORE any code.

20. **`#74 Cluster K` exec-14 PDDL formal-planning scoping** *(~1h after #75)*
    Scope PDDL for irreversible ops (trading-orders, data-migrations, sandbox-escalations).
    Needs agno-introspect for domain model.

### Welle E — Research / Welle-3 (scoping exercises)

21. **`#76 Welle 3` exec-ebm** — Energy-based scoring prototype (research, exec-harness integration)
22. **`#77 Welle 3` exec-media-ingestion** — image/audio/video/batch pipelines (von archived exec-19)
23. **`#78 Welle 3` exec-notifications** — Matrix push-rule + badge integration
24. **`#79 Welle 3` exec-rust** — Rust integration evaluation (indicator_engine, kg-graph port candidates)
25. **`#80 Welle 3` exec-transformersjs** — Client-side title-gen owner
26. **`#54 exec-memory`** — raw evidence + derived memory routing rules
27. **`#55 exec-world-model/personal-kb/context`** — umbrella triplet

### Welle F — Long-tail work (lower priority)

28. **`#67 Cluster H` exec-harness §4g.4 TODOs + pareto dashboards** *(~3h)*
    eval_id wiring, pareto-dashboards, weights-tuning. harness §4g composite_fitness DONE.

29. **`#68 Cluster H` exec-hermes P6 frontend tail** *(~2h)*
    Phase-1 + B + C DONE. P6 session-rail + session-explorer integration in agent-chat.

30. **`#69 Cluster H` exec-a2fm ML-router research** *(~3h+research)*
    Stufe 0 heuristik landed. Stufe 1 ML-router needs eval-data from harness.
    Quasi-parallel zu #67.

31. **`#70 Cluster I` exec-scheduler2 Phase-2 + Phase-3** *(~4h)*
    Phase-1 + §8.1 DONE. Phase-2 recurring + cross-task deps. Phase-3 distributed.

32. **`#49 exec-20 MCP Manager live connection`** *(~1h, braucht MCP-server)*
    Real MCP server instance → useMcpTools lists tools. WebMCP round-trip.

33. **`#50 exec-12 Sandbox Security smoke`** *(~1h, braucht `--profile sandbox`)*
    OpenSandbox container, file_analyze CSV/XLSX, sandbox_execute python. Isolation check.

34. **`#51 exec-10 Multi-agent + exec-11 Memory Evolution`** *(~2h)*
    Second agent instance (agent-b), isolation verify. memory_add/search with Hindsight.

35. **`#63 Cluster G` exec-12 sandbox-HITL decision** *(~1h, decision doc)*
    Blocks exec-security skills-guard-drawer. Decide auto-approve scope vs always-ask
    vs role-gated.

36. **`#64 Cluster G` exec-security skills-guard-drawer** *(~2h after #63)*
    Impl drawer UI in Control-UI security tab.

37. **`#46 exec-17 Observability traces`** *(~2h, braucht `--profile observability`)*
    OTEL + OpenObserve stack up. Traces from go-appservice + agent. Latency dashboard.

38. **`#53 exec-harness + exec-eval`** *(~2h)*
    Agent harness smoke (local eval loop). ragas/deepeval on small fixture corpus.

### Welle G — Plan v2 Phase-2 (deferred from this run)

39. **`#31 Plan v2 Phase-2` Postgres surfaces persistence** *(~3h)*
    go-appservice `/api/v1/surfaces/{load,save,delete}`. Alembic migration
    `agent.agent_surfaces(schema_version, user_id, surface_id, surface_json, updated_at)`.
    BFF `/api/surfaces/[id]`. Extend `usePersistentSurface` server-sync.

40. **`#32 Plan v2 Phase-2` Ansatz X native A2UI SSE packets** *(~2h after #31)*
    `a2ui.createSurface` / `updateDataModel` / `deleteSurface` packet types to
    `streaming.py`. Wire server-driven streaming.

41. **`#33 Plan v2 Phase-2` a2ui-agent-sdk install + wire** *(~2h)*
    `a2ui-agent-sdk` python package, typed models replace dict envelopes.

42. **`#34 Plan v2 Phase-2` live-data binding TanStack Query** *(~3h)*
    L1 agent-driven updateDataModel (push prices); L2 TanStack Query sub-hooks
    inside a2ui widgets.

43. **`#48 exec-05 UI viewers polish`** *(~3h, braucht `bun add`)*
    Waveform/EXIF/XLSX/DOCX/enhanced-MD renderers. nuqs URL-state for Model-Filter.
    Reasoning-cycle-button im composer.

---

## Abhängigkeitsgraph (ASCII)

```
#83 streaming/chat fix  ────┬──► #73 plan-skill live
                            ├──► #42 A2UI widget live
                            └──► #41 chat live smoke

#35 tuwunel users ──► #36 sliding-sync
                 └──► #38 E2EE ──► #39 cross-sign
                              └──► #40 key-backup
#37 livekit ────────┘

#75 DSPy contrarian ──► #74 PDDL scoping

#63 HITL decision ──► #64 skills-guard-drawer

#31 postgres-surfaces ──► #32 A2UI SSE packets
                      └──► #33 a2ui-agent-sdk
                      └──► #34 live-data binding
```

---

## Was mir bei einer neuen Session empfohlen wäre

1. **Lies `2026-04-22-overnight-findings.md` zuerst** — 27 items mit known-gotchas
   die sonst zu re-debug führen.
2. **Welle A #83 als single-task** in frischer Session. Das ist der höchste
   Wert-per-Aufwand: freigeben der chat-pipeline unblockt 3-5 andere Tasks.
3. **Danach entweder Welle B (Matrix live gates) oder Welle D (ADR writing)**
   je nach Tageszeit / Energie. Welle B braucht hands-on terminal-time,
   Welle D ist schreib-intensiv + gut für ruhige sessions.
4. **Welle E-G nur nach Welle A-D.** Das ist enough-work-für-mehrere-tage.

---

## Archive-refs

- `docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md` — plan v2
- `docs/superpowers/findings/2026-04-22-overnight-findings.md` — gotchas + decisions log
- `specs/execution/claude-merge-frontend-chat-ui-2OqmH/VERIFY-GATES.md` — updated state matrix
- `specs/execution/EXECUTION-ORDER.md` — cluster playbook

**Last-commit-dieses-handoffs:** pushed to `origin/main` @ `8596757`

---

## Post-session state — 2026-04-24 update (voll-katalog, FINAL)

Zwischen dem 2026-04-22 handoff und jetzt wurden **die meisten items gelandet**
(siehe `specs/execution/superpower-impl-log.md` für den vollen cluster-log).
Nach der 2026-04-24 observability-session + 5-agent adversarial verify +
13 fixes in `d4b4432` ist **Plan v2 als DONE markiert**, v1 als SUPERSEDED.

Was **jetzt wirklich noch offen ist** (alles — keine kategorien-diskriminierung):

### Truly open — alle kategorien, 2026-04-24 FINAL

Stand **post `d4b4432`** (5-agent verify + 13 fixes gelandet):

#### A) Plan v2 Phase-2 gaps (extrahiert aus v2 "Deferred" sektion)

| # | Titel | Prio | Scope + Files | First-step |
|---|-------|------|---------------|------------|
| **#93** | Custom A2UI catalog-extension via `createReactComponent` | **mittel** (user-sichtbar) | Heute rendern ChartWidget + PortfolioCard via `ToolOutputRenderer` als tool-result-workaround (custom `GenerativeWidget` interface in `registry.ts`, nicht A2UI-konform). Ziel: wrap als first-class A2UI v0.9 catalog-entries so dass `A2UIRenderer` sie native mountet.<br>**Files**: `frontend_merger/src/features/agent/providers/A2uiProvider.tsx` (wire extended catalog), `frontend_merger/src/features/agent/components/a2ui/registry.ts` (refactor zu A2UI `WidgetDefinition`), neue catalog-extension module.<br>**Payoff**: agent emittiert ChartWidget via native A2UI widget-spec statt dict-envelope. | `bun add @a2ui/catalog-builder` checken, dann `createReactComponent` examples in @copilotkit/a2ui-renderer docs lesen. |
| **#94** | Matrix-chat CopilotKit integration (exec-10 tie-in) | niedrig | CopilotKit ist heute nur in `AgentProviders` gewrappt — aktiv nur in agent-chat sheet. Matrix-chat (`/matrix` route) hat keinen CopilotKit-provider. Ziel: wenn matrix-chat user AG-UI actions triggern wollen (z.B. "open file X" aus chat), braucht es provider + runtime-URL mount pro-route.<br>**Files**: `frontend_merger/src/app/matrix/layout.tsx` (neu wrappen), `exec-10-multi-agent.md` §matrix-ui bridge. | Zuerst clarify: gibt es user-stories die das wirklich brauchen? Vielleicht auch deferred gewollt. |
| **#95** | Route consolidation into /control/* | niedrig | Heute: `/`, `/matrix`, `/files/[[...tab]]`, `/memory/[[...tab]]`, `/control/[[...tab]]`. Plan-v2 idee: alles unter `/control/matrix`, `/control/files`, `/control/memory` bündeln als admin-tab-system.<br>**Files**: migrate directories + GlobalTopBar nav-items + rewrite rules für alte URLs + playwright test updates. | Vor impl: UX-entscheidung mit user — wollen wir das überhaupt? Kein funktionaler value, pure layout-frage. |

#### B) Browser-client blocked — server-side ready, brauchen Playwright+cinny/element rig

Alle 6 teilen den gleichen blocker: matrix-js-sdk browser-client + registered test-users. Ein-mal aufwand (E2E test-rig bauen) entsperrt alle 6 gleichzeitig.

**Vorabbedingung "rig" konkret:**
- Tuwunel homeserver läuft (`--calls` profile + `--tuwunel` flag)
- `scripts/setup-users.sh` registriert alice + bob
- Playwright launches cinny oder element-web mit test-user-login
- Pro test: user-login → message-send → assertions

| # | Titel | Spec | Was verifiziert wird | First-step |
|---|-------|------|----------------------|------------|
| **#38** | exec2-04 B1 E2EE base functionality | exec2-04 §B1 | Alice sendet encrypted message → Bob empfängt + entschlüsselt. Basic megolm session establishment. | Playwright test in `frontend_merger/tests/e2e/e2ee-base.spec.ts` |
| **#39** | exec2-04 B2 Cross-signing + QR flow | exec2-04 §B2 | Alice's 2. device wird via QR-scan verified. Cross-signed keys propagieren. | Nach #38 — braucht alice's session |
| **#40** | exec2-04 B3 Key backup | exec2-04 §B3 | Alice resetet browser → rescue-key wiederherstellt room-keys von server-backup. | Nach #38 + #39 |
| **#51** | exec-10 multi-agent + exec-11 memory evolution | exec-10, exec-11 | Alice schickt message die 2+ agents parallel triggert → beide agents haben isolierte memory-scopes (kein cross-leak). Memory-evolution (reflect, consolidate) läuft asynchron. | Agents: `@agent-alice`, `@agent-bob` pre-materialized in Go bot-agent |
| **#60** | exec-05 A4 NATS E2EE E2E-test | exec-05 §A4 | Encrypted message-flow Tuwunel → go-appservice decrypt → NATS → python-agent → reply → go-appservice encrypt → Tuwunel. Verify audit-trail zeigt beide richtungen. | Nach #38 — braucht encrypted-room-setup |
| **#61** | exec-10 A2A live-test (HOT) | exec-10 §A2A | Agent-to-agent protocol: `@agent-alice` ruft tool bei `@agent-bob` via Google A2A SDK. Roundtrip mit streaming. | Nach #51 — braucht beide agents active |

#### C) User-skip (explizit deferred durch user)

| # | Titel | Warum skip |
|---|-------|------------|
| **#74** | exec-14 PDDL formal-planning | User: "kein PDDL vorerst" (2026-04-23) |
| **#76** | exec-ebm energy-based scoring | User: "kein EBM vorerst" (2026-04-23) |

#### D) Recurring / by-design

| # | Titel | Typ |
|---|-------|-----|
| **#82** | exec-matrix-monitor monthly upstream check | recurring, bleibt in_progress-status |

#### E) Follow-ups aus observability-session (#46 tier-3)

| # | Titel | Prio | Warum separat |
|---|-------|------|---------------|
| **#92** | exec-17 Tier-3 Browser RUM via BFF-proxy | niedrig | Nicht-blocking. Backend-observability (tier 1+2) reicht für ops. Browser-RUM hat security-implikationen (creds-safety) + braucht CSP/CORS/consent-setup + privacy-decision. Eigenes scope. |

#### F) Verify-findings ungefixt (dokumentiert in commit `d4b4432`)

Die 5-agent verify (2026-04-24) hat 17 issues gefunden, 13 davon sofort gefixt. Die verbleibenden 4 sind in einem der folge-runs zu adressieren:

| ID | Titel | Impact | Fix-sketch |
|---|-------|--------|------------|
| **F-G4-race** | A/B experiments INSERT/UPDATE fire-and-forget ordering-race | Low-prob silent-data-loss bei slow DB. Wenn INSERT-task (ab_row_id) nach UPDATE-task (routing_used) läuft → UPDATE findet keine row, no-ops. | Refactor zu `INSERT ... ON CONFLICT (id) DO UPDATE SET routing_used=EXCLUDED.routing_used, ...`. Files: `dispatcher.py` `_insert_ab_row()`, `router_node.py` `_mark_routing()`. ~1h. |
| **F-G1-quality** | Smart_routing keyword-set enthält 20 common EN words | Nicht correctness bug, aber casual queries wie "what is the reason?" / "any options?" / "test this" schlagen in den keyword-filter → routing zu cheap-model wird blockiert → kostenoptimierung wirkungslos für viele prompts. | `smart_routing.py _COMPLEX_KEYWORDS` — review + entfernen: `reason`, `test`, `model`, `train`, `options`, `tool`, `tools`, `plan`, `design`, `review`, `strategy`, `risk`, `claim`, `evidence`, `prompt`, `inference`, `evaluate`, `compare`, `research`. Behalten: multi-word phrases wie `deep analysis`. ~30min. |
| **F-4g4-COALESCE** | `scorer.score_session(eval_id=X)` — wenn row schon `harness_eval_id='A'` hat und X='B' kommt, COALESCE behält 'A' | Silent surprise für re-scoring workflow. Intentional (first-write-wins) aber nicht in docstring. | Option A: add explicit `force_eval_id_overwrite=False` param + docstring note. Option B: CONFLICT update eval_id too. Ich würde Option A — safer default. Files: `scorer.py`. ~20min. |
| **F-@vercel-otel-doc** | Commit `d78ad68` msg sagt "@vercel/otel needs prod build" — verify fand: fires in dev auch | Doc-irritation only, no impl bug. Future reader könnte denken dev-mode bricht — aber tut es nicht. | Nächstes journal-entry korrigieren mit `ref d78ad68 — clarification: instrumentation.ts fires in both next dev and next build; the "needs prod build" remark was wrong`. 5min. |

#### G) Pre-existing noise (nicht session-introduced, sichtbar aber leben-damit)

- **Typos-warnings auf deutsche docstrings** (`ein`, `ist`, `oder`, `Prueft`) — braucht `[default.extend-words]` allowlist in `.typos.toml` wenn wir typos als CI-gate einbauen.

#### H) Infra runtime issues — host/podman env, nicht impl-bugs

Entdeckt beim 2026-04-24 end-of-session status-check. Nicht blocking für aktuelle arbeit, aber sollten wir an einem der nächsten tage zusammen angehen:

- **H-1: Podman rootlessport race** (postgres exit 137 wiederkehrend)
  - Root-cause: podman 1.0.6 + slirp4netns auf Linux Mint 22.3 — race zwischen container-startup und rootlessport host-port-bindung. Container bekommt SIGKILL oder bleibt "up" mit unreachable host port → connection-reset auf DB-writes.
  - Heute: ad-hoc `podman restart postgres` (manchmal 2x).
  - Dokumentiert in project-memory `project_postgres_rootlessport_race.md`.
  - **Prevention empfehlung**: switch network-backend `slirp4netns` → `pasta` via `~/.config/containers/containers.conf` + podman 4.7+. Einmalige config-change, systemweit. Beobachtung: pasta ist in podman docs seit ~2 jahren als "more stable, recommended" markiert.
  - Alternative: systemd-watcher der bei exit=137 auto-restart macht (reaktiv, nicht preventiv).
  - Alternative: `network_mode: host` nur für postgres (umgeht rootlessport-layer — aber breaks port-mapping für andere services).

- **H-2: Stale container-config nach compose-file-change** (openobserve + litellm zeigen "unhealthy" obwohl service real 200 antwortet)
  - Symptom: `podman ps` zeigt `unhealthy`, aber `curl /healthz` returniert 200.
  - Root-cause: healthcheck-definition wird beim container-CREATE eingebrannt. YAML-änderung (mein `d4b4432` fix: `wget` → `/proc/net/tcp` probe) wirkt erst nach recreate.
  - Aktuell betroffen: openobserve, litellm.
  - Fix: `podman-compose up -d --force-recreate openobserve litellm` beim nächsten stack-down/up-cycle. Heute nicht akut — service real gesund, nur self-report broken.

- **H-3: Infra-containers im `Created` / `Exited` state — nicht auto-started mit dev-stack.sh**
  - Current: pgbouncer, valkey, falkordb, lk-jwt, tuwunel, coturn, seaweedfs, garage, cloudflared(-named) alle exited/created.
  - Ist by-design für ein minimal-dev-stack (siehe `--matrix-core` vs `--matrix-full` flags), aber kein status-indicator im dev-stack.sh dass sie AUSGELASSEN wurden vs gebrochen.
  - Follow-up: status-output erweitern um "intentionally-off" vs "unexpectedly-down" zu unterscheiden.

- **H-4: Openobserve basic-auth creds leak-path** (sessin-notiz, nicht akute)
  - OPENOBSERVE_USER/PASSWORD landet derzeit in 3 .env files (root, python-backend, otel-collector via compose-env). Für production: migrate zu vault / docker-secrets statt plain .env. Heute dev-only ok, aber vermerkt.

- **H-5: @vercel/otel dev-mode commit-doc misleading** (aus verify Agent 3)
  - commit `d78ad68` message behauptet "@vercel/otel needs prod build". Verify agent fand: instrumentation.ts fires in `next dev` auch. Commit-msg korrigieren bei nächstem journal-update — kein impl-bug.

#### Kategorisch NICHT auf dieser liste:

- Completed items (siehe `superpower-impl-log.md` für vollen cluster-log mit commit-SHAs)
- Paper-only ratifications (#70, #75, #77-80) — kein code-change, nur spec-state-update
- Hotfixes der session (MCP 500, port collision) — schon in PR-history

---

## Process: Superpowers + exec-*.md sync workflow

Dieser abschnitt ist **prozess-anleitung** für zukünftige sessions. Ziel: `specs/execution/exec-*.md` files bleiben truthful zum code-zustand, verify-gates akkumulieren über zeit statt zu zerfasern, neue exec-files folgen naming-convention.

### 1. Exec-*.md files mit impl-stand synchronisieren

**Trigger**: ein cluster von commits ist gelandet (nicht bei jedem einzel-commit, sonst noise-storm).

**Rezept** (pro exec-file):

```
a) Read exec-NN-topic.md §Status, §Phase-*, §Verify-Gates sections
b) Cross-ref specs/execution/superpower-impl-log.md §2.* cluster
   → finde alle commit-SHAs die diesen exec touched haben
c) Update exec file:
   - §Status line: "ratified YYYY-MM-DD", "LANDED commit-SHA", "pending X"
   - §Phase-N status markers: ✓ done / ○ in-progress / – deferred
   - §Verify-Gates: ✓ gates mit commit-ref, ○ offene gates mit blocker-note
   - §Dependencies: cross-ref zu anderen execs die seither gelandet sind
d) Commit: "docs(exec-NN): sync with impl state through <SHA>"
```

**Wer macht das**: main-Claude, **NICHT** ein subagent. Subagents haben oft nicht context über cross-exec impact. Wenn unsicher: `Agent(subagent_type="sota-explore", prompt="find all commits touching exec-NN topic")` → vor-recherche, dann main macht sync.

### 2. Neue verify-gates identifizieren

**Wann**: nach jedem sota-verify run (wie der 5-agent run vom 2026-04-24).

**Was in verify-gates gehört**:
- Smoke-command + expected output (`curl ... | jq ...`)
- Unit/integration test file + expected pass count
- Cross-service probe wenn E2E (e.g. "POST /api/... → SELECT ... FROM ab_experiments zeigt row mit routing_used=true")

**Was NICHT in verify-gates gehört**:
- Lint/typecheck (das gehört CI config, nicht gate-doc)
- "does it compile" (gate-noise, nichts specifisches)
- "it looks good" (untestbar)

**Format** (in jedem exec-NN-topic.md §Verify-Gates):

```markdown
## Verify-Gates

### Gate 1: <name>
- [x] Landed <commit-SHA>
- Smoke: `curl -sS http://... -d '<payload>'` returns 200 + body contains `X`
- Test: `uv run pytest tests/X.py::test_Y` — N/N pass
- Expected observability: otel span `X` with attribute `Y=Z` visible in openobserve

### Gate 2: ...
```

### 3. Naming-convention für neue exec-*.md files

**Currently im repo** (inkonsistent):
- `exec-NN-topic.md` (z.B. exec-05-nats-e2ee-pipeline.md, exec-17-observability-harness-traces.md)
- `exec-topic.md` ohne nummer (z.B. exec-memory.md, exec-harness.md, exec-rust.md)
- `exec2-NN-topic.md` (exec2-04-verify-gates.md — "exec round 2")
- `exec-topic-YYYY-MM-DD.md` (exec-linux-setup-users-2026-04-17.md — date-stamped one-shots)

**Vorschlag SOTA-naming** (geht nach vorne, keine breaking-renames bestehender):

| Pattern | Wann | Beispiel |
|---|---|---|
| `exec-NN-topic.md` | Core execution slice mit phase-tracking | `exec-18-unified-agent-schema.md` |
| `exec-topic.md` | Cross-cutting thema ohne fixe phasen (memory, harness, rust integration) | `exec-memory.md` |
| `exec-topic-delta-YYYY-MM-DD.md` | Delta gegen ein ursprünglich-geplantes exec (z.B. re-scoping) | `exec-14-dspy-delta-2026-04-23.md` (ersetzt oder ergänzt exec-14-DSPy.md) |
| `exec-topic-YYYY-MM-DD.md` | Date-stamped one-shots ohne follow-up (setup, migrations) | `exec-postgres-tuning-2026-04-17.md` |

**Regel für "neues exec-file erstellen vs existing erweitern"**:

- **Erweitern** existing wenn: neue phase / neue verify-gates eines existierenden topics, spec ist noch unter 2000 zeilen
- **Neues file** wenn: topic über 2000 zeilen gewachsen, ODER andere primary audience (z.B. infra-team vs agent-team), ODER scope-grenzen anders (phase-2 statt phase-1)
- **Delta-file** (`*-delta-*`) wenn: original exec bleibt gültig, aber ein spezifisches sub-scope wurde re-scoped (z.B. contrarian review änderte D-1..D-3 entscheidungen)
- **Niemals**: tag- oder sprint-basierte files ("exec-sprint-5-agent.md" etc) — wird schnell chaos.

**Archive-policy**: wenn ein file superseded wird (wie plan v1), banner setzen + keep file (history). Nur bei echtem dead-end-scope löschen.

### 4. Superpower-subagents-cheat-sheet für spec-arbeit

| Task | Subagent | Warum |
|---|---|---|
| "was ist in diesem exec schon impl-iert?" | `sota-explore` | schnell grep+read über viele files |
| "plan eine neue phase für exec-NN" | `sota-plan` | architect-pattern mit critical-files |
| "ist diese arch-entscheidung stabil?" | `sota-contrarian` | vor irreversiblem code — besonders bei ADRs |
| "hat impl X die exec spec erfüllt?" | `sota-verify` | adversarial probing + test-runs |
| "code-review post-landing" | `superpowers:code-reviewer` | standards + missing-tests audit |

**Anti-pattern**: nicht sota-plan rufen um dann sota-verify zu rufen um dann sota-contrarian zu rufen. Zu viel roundtrip. Für normale features: main-Claude plant + implementiert + verify ruft 1-2 agents parallel am ende.

### 5. Impl-log als source-of-truth für session-history

`specs/execution/superpower-impl-log.md` ist der **temporäre rollup** (current: for this superpower session). Wenn er zu gross wird:

- **Retire-signal**: wenn die meisten §2.* cluster-sektionen in ihre jeweiligen exec-*.md §Status gezogen wurden → breadcrumb-file hinterlassen (`docs/superpowers/findings/YYYY-MM-DD-impl-log-retired.md` mit "content distributed into exec-*, see git log for history") und impl-log löschen.
- **Erneuern-signal**: wenn eine neue multi-day superpower-session startet → neuer impl-log `specs/execution/superpower-impl-log-YYYY-MM-DD.md`, alten archivieren.

Dieser pattern vermeidet dass impl-log zum "zweiten journal" wird.

### Welche cluster vollständig durch sind (seit 2026-04-22)

- ✅ **ADR-001 Smart-Routing rollout gate** — G1-G6 + P1 alle landed
- ✅ **ADR-002 Tracing/Audit parallel stores**
- ✅ **ADR-003 exec-14 DSPy-track gating**
- ✅ **ADR-004 Sandbox-HITL surface-dialog**
- ✅ **Plan v2 Phase-2 (A2UI)** — #31 Postgres surfaces + #32 Ansatz X SSE + #33 a2ui-agent-sdk + #34 live-data binding (alle 4 landed 2026-04-24)
- ✅ **exec-17 Observability tier 1+2** — go + python + Next.js BFF traces in OpenObserve
- ✅ **Bug fixes** — FastMCP /mcp/ 500, lk-jwt port collision (:8080 → :8082)
- ✅ **Memory umbrella boundary review** — 4 specs konsistent
- ✅ **Welle 3 ratifications** — exec-scheduler2, exec-notifications, exec-media-ingestion, exec-rust, exec-hermes Phase-B alle ratifiziert oder landed

### Was als NÄCHSTE session gut wäre

1. **Browser-client E2E test-rig bauen** (unblockt #38, #39, #40, #51, #60, #61 gleichzeitig — 6 items für einmal aufwand). Pattern: Playwright + cinny/element setup + programmatic test user registration.
2. **#93 custom A2UI catalog-extension** (Plan v2 Phase-2 gap, mittel-priorität, user-sichtbar — ChartWidget/PortfolioCard als first-class A2UI widgets statt tool-output-workaround).
3. **Verify-follow-ups F** (G4 race, G1 keyword review, §4g.4 COALESCE docstring) — quick-win tickets.
4. **#92 tier-3 browser RUM** — niedrig priorisiert, nur wenn BFF-tier-2 nicht reicht.
5. **#94 Matrix-chat CopilotKit + #95 route consolidation** — beide UX-entscheidungen, kein funktionaler driver.

### Archive pointer für 2026-04-24 arbeit

- `specs/execution/superpower-impl-log.md` — vollständiger session-rollup (§0 phasen P0-P7, §1 ADRs, §2 impl-cluster incl §2.I observability, §3 smoke, §4 blocked-state)
- `docs/superpowers/findings/2026-04-24-env-layout-decision.md` — root + service .env scope
- `docs/superpowers/findings/2026-04-24-observability-tier-strategy.md` — OTel vs OpenObserve, 3-tier model, #92 rationale
- `docs/superpowers/findings/2026-04-24-memory-umbrella-boundaries.md` — 4-spec cross-check
- **Last-commit post-2026-04-24-session:** pushed to `origin/main` @ `d78ad68`
