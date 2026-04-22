# Execution Order — cluster-basierter durchlauf

**Erstellt:** 2026-04-20
**Owner:** niemand — living document
**Scope:** alle `specs/execution/exec-*.md` + `exec2-*.md` (46 active, 2 archiviert)

---

## 0. Lese-regel

Dieses doc ist **ein cluster-index mit priorität**, keine to-do-liste. Konkrete arbeit lebt in den spec-files. Diese datei antwortet: *"welche cluster kommt als nächstes dran?"*

**Cluster-reihenfolge** ist bewusst feature-orientiert statt einzelspec-orientiert — verify-gates, design-questions, und code-completion eines features werden zusammen behandelt, nicht aufgesplittet.

---

## 1. Die 11 cluster (A–K)

Reihenfolge:

```
A  frontend-merger branch-exec  (landed, live-smoke offen)
B  matrix-chat core (exec2-01..04)
C  NATS + E2EE pipeline (exec-05/05b/05c)
D  agent-chat integration (exec-06)
E  protocols + multi-agent (exec-09 + exec-10)  ← A2A live-test heiss
F  memory + memory-control-ui (exec-11 + exec-15 + exec-memory)
G  sandbox + security umbrella (exec-12 + exec-security)
H  LLM gateway + observability + harness + hermes (exec-16 + exec-17 + exec-harness + exec-hermes + exec-a2fm + exec-eval)
I  schema + scheduler (exec-18 + exec-scheduler + scheduler2)
J  Control-UI cross-cutting (frontend_merger/src/features/control/ — 15 tabs spanning clusters E/F/G/H/Welle-3)
K  planning + skill-system (exec-14 PDDL + exec-14-DSPy + exec-skills + plan-skill)
```

Archiviert + nicht-scope: exec-02/03/04/07/08/13/19 + merge-chat + transformers-js-SUPERSEDED. Details in §2.

Welle-3 research specs (nach K): exec-20, exec-ebm, exec-world-model, exec-personal-kb, exec-openworldlib, exec-media-ingestion, exec-notifications, exec-rust, exec-transformersjs, exec-context.

**Passive Monitor-Liste (matrix-spezifisch):** `exec-matrix-monitor.md` — Tuwunel v1.6 stable merge, upstream-bug-tracking (#411/#401/#377/#372), MSC3414/MSC4362, OIDC/MAS, Federation-Prod-Readiness. Re-check monatlich.



### Cluster A — Frontend Merger Branch-Exec (erste priorität)

**Ort:** `specs/execution/claude-merge-frontend-chat-ui-2OqmH/` (branch-exec directory)
**Status:** code merged auf main (2026-04-18), verify-gates + loose ends ungewiss

Deckt alle drei frontend-surfaces ab: agent-chat, matrix-chat, control-ui, plus files + memory. `frontend_merger/` ist der resulting monolith.

Dateien im directory:
- `exec-01-frontend-merger-scaffold.md` — package.json, configs, shell-scaffold, BFF-routes
- `exec-02-envfiles-devstack-compose.md` — `.env.example` × 3, `scripts/dev-stack.sh`, compose update
- `exec-03-linter-fixes.md` — golangci-lint 12→0, ruff 51→0
- `exec-04-playwright-verify.md` — 8/8 playwright smoke green (prod-build)
- `exec-05-ui-viewers-polish.md` — viewer-packages + model-discovery-polish + reasoning-cycle
- `VERIFY-GATES.md` — cross-cutting verify-gate-log

**Warum jetzt:** alle drei frontend-surfaces hängen davon ab. Wenn es offene verify-gates oder loose ends gibt, blockieren sie alles frontend-bezogene in cluster B + D + E. **Lies zuerst VERIFY-GATES.md** um zu sehen was noch offen ist.

---

### Cluster B — Matrix Chat Core (exec2-01..04, im frontend_merger)

**Dateien:**
- `exec2-01-matrix-chat-core` — core features, blocked on C1 (tuwunel MSC3414/MSC4362)
- `exec2-02-protocol-infra` — OIDC/MAS + federation, blocked on C2+C3
- `exec2-03-ui-rework-sota` — UI rework
- `exec2-03b-advanced-matrix-options` — backlog, blocked on C6
- `exec2-03c-cinny` ✅ **Implementierung abgeschlossen** (sota-verify PASS)
- `exec2-04-verify-gates` — sammelstelle für matrix-chat-gates

**Warum direkt nach A:** matrix-chat lebt im frontend_merger (nicht mehr in cinny-fork). Cluster A hat die infra geliefert, Cluster B testet/finalisiert die matrix-chat-features darin.

**Verify-path:** `exec2-04-verify-gates` durchgehen, gates abhaken wo getestet.

---

### Cluster C — NATS + E2EE Pipeline (exec-05 familie)

**Dateien:**
- `exec-05-nats-e2ee-pipeline` — Phase A+B impl, **A4 E2E-test pending**
- `exec-05b-messaging-bridges` — Geplant (email/telegram bridges)
- `exec-05c-agent-isolation` — Geplant (NATS-routing + key-deletion + hybrid E2EE)

**Warum nach B:** matrix-chat sendet über go-appservice → NATS → subscribers. Die pipeline ist das crypto-gateway. Ohne E2E-gate wissen wir nicht ob E2EE-handoff zwischen cinny-client ↔ tuwunel ↔ go-appservice ↔ subscribers wirklich funktioniert.

**Verify-path:** A4 E2E-test ausfahren. Wenn grün → 5b/5c als Welle-3-planning.

**Cross-ref:** `exec-blocking §C8` (JetStream für sync_turn at-least-once, deferred)

---

### Cluster D — Agent Chat Integration (exec-06, shared components)

**Datei:** `exec-06-agent-chat-integration` — Phase 5 in arbeit

**Umfang:**
- Shared components zwischen agent-chat + matrix-chat (composer, threads, etc.)
- SSE streaming proxy (BFF → Go Gateway :8090)
- Phase-B P6 compression-indicator (backend DONE, frontend pending — `§4c`)
- Phase-B P6 title-gen display (backend DONE, primary path = transformers.js — `§4d`)
- `§C7 streaming SOTA upgrade` cross-ref

**Warum nach C:** agent-chat sendet über den gleichen transport (SSE), braucht matrix-chat-composer-components. Cluster C muss stabil sein bevor agent-chat-features dagegen gebaut werden.

**Verify-path:** Phase-5-abschluss + CompressionIndicator.tsx + Title-gen async dispatch.

---

### Cluster E — Protocols, UI-KG, Multi-Agent (exec-09/10/13)

**Dateien:**
- `exec-09-protocols-generative-ui` — Phase 1-3 impl, verify-gates pending
- `exec-10-multi-agent` — Phase 1-4 impl (LangGraph + A2A), **A2A nie live-getestet** ⚠️
- `exec-13-ui-kg-extensions` — Archiviert

**Warum zusammen:** generative UI + multi-agent A2A sind beide agent-chat-integration-upgrades. exec-10 Phase 4 ist A2A-protocol (Google-standard, nicht ACP). Heißester punkt: **A2A live-test**.

**Verify-path:** exec-10 A2A smoke-test zuerst (existierender code, never run end-to-end); exec-09 verify-gates danach.

---

### Cluster F — Memory + Memory-Control-UI (exec-11/15 familie)

**Dateien:**
- `exec-11-memory-evolution` — Geplant
- `exec-15-memory-control-ui` — Frontend Phase 1-3 done, **backend-wiring + Phase 4-6 pending**
- `exec-memory` — Evaluation / laufend (MemPalace vs Hindsight)

**Warum jetzt:** memory-control-ui frontend steht, backend fehlt. Memory-evolution ist das content-projekt darunter.

**Verify-path:** exec-15 backend-wiring zuerst (memory-control-ui funktionsfähig machen), dann exec-11 memory-evolution scoping. exec-memory läuft parallel als evaluation.

**Cross-ref:** `exec-blocking §C11` (MemPalace/Hindsight concrete `on_pre_compress` impls deferred)

---

### Cluster G — Sandbox + Security (exec-12 familie)

**Dateien:**
- `exec-12-sandbox-security` — Phase 1+2 implementiert (03.04.2026), **sandbox-HITL decision pending**
- `exec-security` — Draft (Phase-B P2 creation) — umbrella für redact (DONE), HITL skills-guard (blocked on exec-12), audit-integrity, prompt-injection

**Warum zusammen:** HITL skills-guard drawer ist blocked auf exec-12 sandbox-decision. exec-security ist der umbrella-spec der cross-cut security-themen sammelt.

**Verify-path:** exec-12 sandbox-HITL decision treffen, dann skills-guard-drawer implementation. Redact + prompt-scanner sind schon DONE (Phase-B P3).

---

### Cluster H — LLM + Observability + Harness (exec-16/17, exec-harness, exec-hermes)

**Dateien:**
- `exec-16-llm-provider-gateway` — In Progress (Phase-B P4 DONE, §2.D smart-routing **flagged NEEDS HOLISTIC REVIEW**)
- `exec-17-observability-harness-traces` — Draft (infra live, spec lags; **C9 ADR** offen für tracing+audit parallel-stores)
- `exec-harness` — Draft, §4g DONE (composite_fitness + scorer-wiring)
- `exec-hermes` — Phase-1 + B + C DONE; P6 frontend tail offen
- `exec-a2fm-adaptive-routing` — Draft/Research (Stufe 0 heuristik landed, ML-router pending)
- `exec-eval` — Infra / verify-runbooks (Welle-1-helper!)

**Warum zusammen:** der gesamte LLM-call-pfad vom gateway (exec-16) über observability (exec-17) bis harness-scoring (exec-harness §4g) ist eine unit. Smart-routing + hermes-adoption hängen am selben stack.

**Verify-path:** exec-16 §2.D holistic review (smart-routing 6 open questions), exec-17 C9 ADR schreiben, harness §4g eval_id + pareto-dashboards + weights-tuning (§4g.4 TODOs).

---

### Cluster I — Unified Schema + Scheduler (exec-18, exec-scheduler)

**Dateien:**
- `exec-18-unified-agent-schema` — ✅ **ARCHIVED 2026-04-22** (`archive/exec-18-unified-agent-schema-SUPERSEDED.md`). 26 migrations shipped in slice-owned increments (exec-hermes, exec-scheduler, exec-16, etc.) — no longer relevant as central planning doc. Schema ground-truth is the DB itself; agno-introspection tool captures the runtime state when needed.
- `exec-scheduler` — Phase-1 DONE + §8.1 DONE
- `exec-scheduler2` — Draft (Phase-2 + Phase-3)

**Warum zusammen:** exec-18 war der "schema-spec"; inzwischen owned jeder slice seine eigenen migrations. exec-scheduler hat ganz eigene migrations (019/020/021) — klarer counter-beweis dass exec-18 als zentraler schema-spec überholt ist.

**Decision (2026-04-22):** ✅ exec-18 archiviert nach `archive/`. Ground-truth ist die DB + slice-owned alembic migrations; agno-introspect-tool steht als optionaler runtime-check zur Verfügung wenn gebraucht.

---

### Cluster J — Control-UI (cross-cutting über clusters E/F/G/H/Welle-3)

**Wichtiger struktur-punkt:** control-UI ist **kein einzelner spec**. Die `frontend_merger/src/features/control/` hat mehrere tabs, jeder gehört einem anderen backend-spec. Cluster J ist die **frontend-sammelstelle** — die tabs müssen zusammen verify-tested werden, sonst fehlt integrationsübersicht.

| Tab | Owning backend-spec | Backend-status | Frontend-status |
|---|---|---|---|
| `OverviewTab` | cross-cut, kein dedicated spec | — | Phase-1 done |
| `MemoryTab` (+ KGGraphPage) | `exec-15-memory-control-ui` (cluster F) | Phase 1-3 frontend done, backend-wiring pending | Phase 1-3 done |
| `ApiModelsTab` + `ProviderCard` + `ModelExplorer` | `exec-16-llm-provider-gateway` (cluster H) | In Progress | Phase-1 done |
| `EditApiKeyModal` | `exec-16 §2.7` credentials encryption | DONE | Phase-1 done |
| `UtilityModelsSection` | `exec-16 §2.13` utility models | DONE | Phase-1 done |
| `SpendDashboard` | `exec-16 §2.10` billing insights | Phase-B P4 DONE | Phase-1 done, data-flow needs Phase-C scorer (DONE) |
| `AuditTab` | `exec-17-observability-harness-traces` (cluster H) | Infra live, spec lags | Phase-1 done |
| `SessionsTab` | `exec-18` + exec-hermes `agent.sessions` | DONE | Phase-1 done |
| `AgentsTab` | `exec-10-multi-agent` (cluster E) | Phase 1-4 impl, verify pending | Phase-1 done |
| `SkillsTab` | `exec-skills` | Evaluation / Phase 1 impl | Phase-1 done |
| `SandboxTab` | `exec-12-sandbox-security` (cluster G) | Phase 1+2 impl | Phase-1 done |
| `PermissionsTab` | `exec-12 §permissions` | cross-cut | Phase-1 done |
| `SecurityTab` | `exec-security` (cluster G) | Draft (Phase-B P2 creation) | Phase-1 done |
| `ToolsTab` | cross-cut tool-registry (no owner-spec) | — | Phase-1 done |
| `McpTab` | `exec-20-mcp-manager` (Welle 3) | Evaluation | Phase-1 done |
| `SystemTab` | cross-cut platform (no owner-spec) | — | Phase-1 done |
| `A2aTab` | `exec-10 §A2A` + `agent/a2a/agent_card.py` | Phase 4 impl, A2A never live-tested | Phase-1 done |
| `ContextTab` | `exec-context` | Evaluation | Phase-1 done |

**Warum als eigenes cluster:** each backend-spec updates their own piece, aber der **end-to-end-control-UI-walk-through** (user navigates all tabs, each shows real data from its backend) ist eine eigene verify-dimension die niemand owned. Ohne diesen walk-through fällt auf dass AuditTab leer ist wenn exec-17 infra nicht seedet, SkillsTab leer wenn exec-skills Phase-1 nicht lebt, etc.

**Verify-path:** nach clustern B-H einmal **control-UI E2E-smoke** — durch jeden tab navigieren, datenquelle überprüfen. Items mit "no data" → owning-spec issue.

**Code-ort:** `frontend_merger/src/features/control/ControlPage.tsx` + `ControlTopNav.tsx` + `components/*Tab.tsx` (15 tabs).

---

### Cluster K — Planning + skill-system + DSPy-optimization-layer

**Warum als eigenes cluster:** matrix-plan-mode ist **drei-schichtig**:

1. **Skill-layer (Stufe 0, DONE 2026-04-20):** `agent/skills/global/plan/SKILL.md` — domain-agnostic, prompt-injection-basiert, für einfache planning-tasks. Gehört zu `exec-skills`.
2. **Formal-layer (Stufe 1, planned):** `exec-14-pddl-formal-planning` — PDDL-basierte formal-plan-validierung. Für irreversible operationen (trading-orders, data-migrations, sandbox-escalations). Nicht das gleiche wie die skill-variante.
3. **Optimization-layer (Stufe 2, Draft/Research):** `exec-14-DSPy` — DSPy-compiled NL→PDDL translator + self-improving optimizer (GEPA/MIPRO). Baut auf layer 1. Forschungs-research-trend 2025/26 "hybrid neuro-symbolic planning". DSPy spannt auch in exec-harness / exec-skills / exec-a2fm — umbrella-spec.

**Dateien:**
- `exec-14-pddl-formal-planning` — Geplant (PDDL-based plan validation)
- `exec-14-DSPy` — Draft/Research (DSPy framework evaluation, 5 foundation-papers in `docs/papers/`)
- `exec-skills` — Evaluation / Phase 1 implementierbar (plan-skill landed)
- `agent/skills/global/plan/SKILL.md` — landed skill-definition

**Verify-path:** skill-layer ist live — testen durch chat-prompt ("plane wie ich X angehe"). PDDL-layer braucht exec-14 phase-planning. DSPy-layer hat sota-contrarian stakes=high review als gate vor jeder impl (5 decisions D-1..D-5).

---

## 2. Archive — abgehakt, nicht mehr laufend

Vollständigkeitshalber (user-frage 2026-04-20):

- `archive/exec-02-missing-features.md` — alte phase
- `archive/exec-03-review-fixes.md` — alte review-runde
- `archive/exec-04-ui-rework.md` — superseded durch exec2-03
- **`archive/exec-07-refactoring.md`** — historical refactor-slice, done
- **`archive/exec-08-agent-backend-voice.md`** — voice-integration merged in exec-06 / exec-media-ingestion
- `archive/exec-13-ui-kg-extensions.md` — wörtlich "Archiviert" (content in exec-15 / exec-memory aufgegangen)
- `archive/exec-19-devstack-consolidation.md` — content verteilt auf exec-media-ingestion + exec-transformersjs + `claude-merge-frontend-chat-ui-2OqmH/`
- `archive/exec-merge-chat-SUPERSEDED.md` — merged via branch-exec 2026-04-18
- `archive/exec-transformers-js-SUPERSEDED.md` — duplicate, kanonischer spec ist `exec-transformersjs.md`
- `archive/opensandbox-gemini-usecases.txt` — reference-material
- `archive/pddl_phase22b_delta.md` — delta-log, content in exec-14 aufgegangen

**Damit: exec-07, exec-08, exec-13, exec-19 alle archiviert und nicht mehr scope.** exec-10, exec-14, exec-15 sind aktiv in clusters E, K, F respectively.

---

## 3. Nach cluster K — weitere specs (Welle 3 research/planung)

Nach clustern A–K bleiben research/planung-specs (NICHT in haupt-flow, aber aktiv):

- `exec-20-mcp-manager` — Evaluation (→ ControlUI McpTab, cluster J)
- `exec-ebm` — Evaluation / Prototyp (energy-based scoring, kommt zu exec-harness dazu)
- `exec-world-model` — Planung (global knowledge layers — evidence/claims/adjudication)
- `exec-personal-kb` — Planung (user-curated KB)
- `exec-openworldlib` — Evaluation
- `exec-media-ingestion` — Draft (transferred from archived exec-19)
- `exec-notifications` — Draft
- `exec-rust` — Portiert / Integration geplant
- `exec-transformersjs` — Entwurf — primary title-gen owner (cluster D tail)
- `exec-context` — Evaluation / operativer owner (cross-cut mit cluster H)
- `exec-blocking` — sammelstelle C1–C11 (living)

---

## 4. Status-map — wo steht jeder spec jetzt

**DONE (✅) — keine laufende arbeit:**
- `exec-postgres-tuning-2026-04-17` ✅ implementiert
- `exec-linux-setup-users-2026-04-17` ✅ script ready
- `exec-secrets-bootstrap-2026-04-17` ✅ implementiert
- `exec2-03c-cinny` ✅ sota-verify PASS
- `archive/exec-merge-chat-SUPERSEDED.md` ✅ merged via branch-exec
- `archive/exec-transformers-js-SUPERSEDED.md` ✅ duplicate removed

**Phase-N implementiert, verify-gates ausstehend (🧪):**
- `exec-05` Phase A+B — A4 E2E pending
- `exec-06` Phase 5 in arbeit
- `exec-09` Phase 1-3 impl
- `exec-10` Phase 1-4 impl (A2A live!) **hot**
- `exec-12` Phase 1+2 impl
- `exec-15` frontend Phase 1-3 done
- `exec-17` infra live, spec lags

**In Progress (🔨):**
- `exec-16` (Phase-B P4 DONE, §2.D flagged)
- `exec-hermes` (Phase-B + C DONE, P6 frontend tail)
- `exec-scheduler` (Phase-1 DONE, Phase-2 planung)

**Draft / Evaluation / Geplant (📋):**
- Alle übrigen specs (siehe cluster H, I, plus Welle 3)

**⚠️ Outdated / Decision-pending:**
- `exec-18-unified-agent-schema` — archivieren oder als bounded-context-ADR behalten

---

## 5. Cluster-playbook — wie ein cluster "abhaken"

Für cluster A (Frontend Merger) und B (Matrix Chat Core) — alles andere folgt dem gleichen pattern:

1. **Read** die relevanten spec-files komplett. Was sagt die VERIFY-GATES-liste?
2. **Discover** — läuft der code wirklich?
   - Frontend: `cd frontend_merger && bun run build` + `bun run dev` + manuelle ui-prüfung
   - Python: `pytest` für das modul
   - Go: `go test -tags goolm ./internal/<module>/...`
3. **Integration-smoke** — spezifisch für dieses cluster:
   - Cluster A: `bun run build` clean + playwright-smoke green (done auf branch) + 6 live-smoke items aus VERIFY-GATES.md §177-186 mit user's lokaler .env
   - Cluster B: `exec2-04` gate-liste durchgehen, tuwunel-compose + matrix-chat-login + text-send + encryption-handshake
   - Cluster C: A4 E2E-test run (publish → subscribe → decrypt)
   - Cluster D: agent-chat SSE-roundtrip (hello → stream → tool-call → response)
   - Cluster E: A2A live-test (agent A delegates to agent B via AgentCard) + exec-09 generative-UI gates
   - Cluster F: memory-control-ui backend wiring (list sessions / read KG / search episodes)
   - Cluster G: sandbox-decision + skills-guard-drawer
   - Cluster H: smart-routing §2.D walk-through; C9 ADR; §4g.4 open TODOs
   - Cluster I: exec-18 decision; scheduler Phase-2 scoping
   - **Cluster J: E2E control-UI walk-through** — alle 15 tabs durchnavigieren, prüfen welche leer sind. Leere tabs → zurück ins owning-cluster (E/F/G/H). Dieser schritt findet integration-lücken die kein einzelcluster sieht.
   - Cluster K: plan-skill chat-smoke ("plane wie ich X angehe"); exec-14 PDDL scoping als Welle-3-follow-up
4. **Commit** alle cluster-änderungen als **ein commit** (batch), nicht einzelnen pro file. Status-blocks im spec + verify-gates-checkmarks.
5. **Move** zum nächsten cluster.

---

## 6. Referenz-links

- Aktuelle migrations (ground truth): `python-backend/alembic/versions/001–026`
- Spec-audit 2026-04-20: commit `f518e5d`
- Phase-B/C session chain: `888b329` .. `f761874` (13 commits)
- Agno schema-introspection reference: `_ref/agno/cookbook/01_demo/agents/dash/tools/introspect.py`

---

## 7. Changelog

| Datum | Änderung |
|---|---|
| 2026-04-20 | Erstversion als 3-wellen-plan (verify-gates → Phase-C tail → Welle-3-planung). |
| 2026-04-20 | **Restrukturiert als 9-cluster-flow** (A frontend-merger → B matrix-chat → C NATS → D agent-chat → E multi-agent → F memory → G sandbox → H LLM+observability+harness → I schema+scheduler → Welle-3). Cluster-reihenfolge orientiert an feature-abhängigkeiten, nicht an spec-nummern. |
| 2026-04-20 | **Erweitert auf 11 cluster** nach user-feedback: Cluster J (Control-UI cross-cutting über 15 tabs spanning E/F/G/H/Welle-3) + Cluster K (Planning zwei-schichtig: plan-skill Stufe 0 DONE + exec-14 PDDL Stufe 1 planned) als eigene cluster. Archive-section explizit gelistet (exec-07/08/13/19 alle archiviert). exec-10 + exec-15 prominenter verortet. |
