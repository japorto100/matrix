# Open Tasks — handoff from 2026-04-22 overnight session

Eine priorisierte Liste der 29 Items die am Ende dieser Session noch offen
sind. Companion zu `2026-04-22-overnight-findings.md` (welches Bugs +
Beobachtungen aus diesem Lauf dokumentiert).

**Stand der Gesamt-Liste:** 29 completed / 53 pending / 82 gesamt.
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

| # | Titel | Prio | Scope |
|---|-------|------|-------|
| **#93** | Custom A2UI catalog-extension (ChartWidget/PortfolioCard via `createReactComponent`) | mittel | Heute rendern ChartWidget + PortfolioCard via `ToolOutputRenderer` als tool-result-workaround. Ziel: wrap als first-class A2UI v0.9 catalog-entries in A2uiProvider, so dass `A2UIRenderer` sie native mountet. Unblockt native agent-emission. |
| **#94** | Matrix-chat CopilotKit integration (exec-10 tie-in) | niedrig | CopilotKit ist heute nur in agent-chat (AgentProviders). Ziel: mount in matrix-chat `/matrix` route damit matrix-user AG-UI actions triggern können. |
| **#95** | Route consolidation into /control/* | niedrig | Heute: `/matrix`, `/files/[[...tab]]`, `/memory/[[...tab]]`, `/control/[[...tab]]` separat. Plan-v2 wollte `/control/*` als einziges admin-tab-system. UX-entscheidung, kein funktionaler value. |

#### B) Browser-client blocked — server-side ready, brauchen Playwright+cinny/element rig

Alle 6 teilen den gleichen blocker: matrix-js-sdk browser-client + registered test-users. Ein-mal aufwand (E2E test-rig bauen) entsperrt alle 6 gleichzeitig.

| # | Titel | Scope |
|---|-------|-------|
| **#38** | exec2-04 B1 E2EE base functionality | Verschlüsselter 1-1 chat zwischen registrierten usern |
| **#39** | exec2-04 B2 Cross-Signing + QR flow | Device verification via QR |
| **#40** | exec2-04 B3 Key backup | Rescue-key + server-side key-backup |
| **#51** | exec-10 multi-agent + exec-11 memory evolution | E2E-test der parallelen agent-orchestration + memory-scope-isolation |
| **#60** | exec-05 A4 NATS E2EE E2E-test | E2EE message-flow Tuwunel → NATS → Agent → E2EE back |
| **#61** | exec-10 A2A live-test (HOT) | Agent-to-agent protocol roundtrip (nicht nur NATS fanout) |

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

| ID | Titel | Agent | Warum nicht sofort gefixt |
|---|-------|-------|---------------------------|
| **G4-race** | A/B experiments INSERT/UPDATE fire-and-forget ordering-race | 2 | Low-probability silent-data-loss bei slow DB. Fix braucht ON CONFLICT DO UPDATE refactor in `dispatcher.py` + `router_node.py`. Eigenes ticket. |
| **G1-quality** | 20 common EN keywords im smart_routing → false-positives ("reason", "test", "train", "model", "options" etc) | 2 | Nicht correctness-bug, quality-issue. Braucht keyword-review + evtl. confidence-scoring. Docstring-update als limit-doku oder keyword-rebuild. |
| **§4g.4-COALESCE** | eval_id in ab_experiments ist "sticky" — re-backfill mit neuer eval_id updated nicht | 5 | Intentional per docstring, aber nicht dokumentierter limitation. Braucht docstring-hinweis in scorer + optional flag `force_eval_id_overwrite`. |
| **@vercel/otel dev-mode doc** | Commit-comment für #46 tier-2 behauptet "needs prod build" — agent fand dev-mode läuft auch | 3 | Commit-msg misleading aber kein impl-bug. Journal-entry korrigieren wenn welle sich setzt. |

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
