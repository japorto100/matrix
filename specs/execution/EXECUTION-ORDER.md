# Execution Order — priorisierter Durchlauf der exec-* specs

**Erstellt:** 2026-04-20
**Owner:** niemand — living document, jeder spec-touch hält diesen hier aktuell
**Scope:** alle `specs/execution/exec-*.md` + `exec2-*.md` (46 active, 2 archiviert)

---

## 0. Lese-regel

Dieses doc ist **ein index mit priorität, keine to-do-liste**. Konkrete arbeit lebt weiter in den spec-files. Dieses doc antwortet auf: *"was ist heute eigentlich dran?"*

Wenn ein spec status-change kriegt → hier 1 zeile updaten.
Wenn ein neuer spec entsteht → hier einordnen.
Wenn ein spec archiviert wird → hier raus.

---

## 1. Durchlauf-plan — 3 Wellen

### Welle 1: Verify-gates + cleanup (JETZT, priorität 1)

Bevor wir neue features bauen: **sichern dass das existing wirklich funktioniert**. Matrix hat mehrere specs im zustand "Phase N implementiert, verify-gates ausstehend". Die müssen erst durch.

| Spec | Was "implementiert" heißt | Verify-gap |
|---|---|---|
| `exec-05-nats-e2ee-pipeline` | Phase A+B implementiert | **A4 E2E-Test ausstehend** |
| `exec-06-agent-chat-integration` | Phase 5 in arbeit | Phase-5-abschluss + gates |
| `exec-09-protocols-generative-ui` | Phase 1-3 implementiert | verify-gates ausstehend |
| `exec-10-multi-agent` | Phase 1-4 implementiert (A2A live!) | verify-gates inkl. A2A live-test |
| `exec-12-sandbox-security` | Phase 1+2 implementiert (03.04.2026) | sandbox-decision für HITL pending |
| `exec-15-memory-control-ui` | Frontend Phase 1-3 done | backend-wiring + Phase 4-6 pending |
| `exec-17-observability-harness-traces` | Draft (infra live, spec lags) | bewusste parallel-stores ADR offen (C9) |

**Zusätzlich in Welle 1 — hausaufgaben:**
- `exec-18-unified-agent-schema` → **outdated-header gesetzt 2026-04-20**. Entscheidung: archivieren oder nur header? Offen.
- `exec2-04-verify-gates` ist die sammelstelle für matrix-chat-gates — durchgehen was davon offen ist.

### Welle 2: Phase-C tail + Option-3 features (HEUTE landed, noch zu finalisieren)

Nach Phase-B (P1–P6) und Phase-C (dispatcher + scorer-worker):

| Item | Wo | Zustand |
|---|---|---|
| Scorer-backfill worker | `exec-scheduler §8.1` | **DONE** 2026-04-20 |
| Smart-routing MVP | `exec-a2fm` + `exec-16 §2.D` | **Code landed, flagged NEEDS HOLISTIC REVIEW** |
| Plan-skill (domain-agnostic) | `exec-skills §0` / `agent/skills/global/plan/` | **DONE** 2026-04-20 |
| Title-gen frontend (transformers.js) | `exec-transformersjs §3.5` | Primary path, pending |
| Compression indicator frontend | `exec-06 §4c` | Backend DONE, frontend pending |
| exec-blocking C7–C11 | `exec-blocking` | Alle dokumentiert, items deferred |

### Welle 3: Planning-work für größere themen (später, nach Welle 1 + 2)

| Thema | Spec | Offen |
|---|---|---|
| Plan-mode (domain-agnostic) | `exec-14-pddl-formal-planning` + `exec-skills` | Skill landed. PDDL-integration ist eigenes projekt. |
| Per-user runtime-isolation | `exec-05c-agent-isolation` + `exec-12-sandbox-security` | Geplant, code fehlt |
| Adaptive routing full (A2FM-paper) | `exec-a2fm` | Draft/Research — Stufe 0 heuristik landed, ML-router pending |
| Energy-based scoring | `exec-ebm` | Evaluation / Prototyp |
| World model | `exec-world-model` | Planung / neuer owner |
| MCP Manager | `exec-20-mcp-manager` | Evaluation |
| Personal KB | `exec-personal-kb` | Planung |
| Media ingestion | `exec-media-ingestion` | Draft — transferred from archived exec-19 §3.5/§3.7 |
| OpenWorldLib | `exec-openworldlib` | Evaluation |
| Rust-integration | `exec-rust` | Portiert / Integration geplant |
| Notifications | `exec-notifications` | Draft |

---

## 2. exec-0 bis exec-19 — status-map

Reihenfolge: **erst hier die verify-gates durchgehen**, dann Welle 2+3.

| # | Spec | Status | Verify-schuldig? | Next action |
|---|---|---|---|---|
| 05 | `exec-05-nats-e2ee-pipeline` | Phase A+B impl | ✅ **A4 E2E-test pending** | Welle 1 priorität 1 |
| 05b | `exec-05b-messaging-bridges` | Geplant | — | nach Welle 1 |
| 05c | `exec-05c-agent-isolation` | Geplant | — | Welle 3 |
| 06 | `exec-06-agent-chat-integration` | Phase 5 in arbeit | ✅ | Welle 1 priorität 2 |
| 09 | `exec-09-protocols-generative-ui` | Phase 1-3 impl | ✅ **verify-gates pending** | Welle 1 priorität 3 |
| 10 | `exec-10-multi-agent` | Phase 1-4 impl (A2A live!) | ✅ **verify-gates pending** | Welle 1 priorität 1 (hot: A2A nie live-getestet) |
| 11 | `exec-11-memory-evolution` | Geplant | — | Welle 3 |
| 12 | `exec-12-sandbox-security` | Phase 1+2 impl | ✅ **sandbox-HITL decision pending** | Welle 1 priorität 4 |
| 13 | `exec-13-ui-kg-extensions` | **Archiviert** | — | skip |
| 14 | `exec-14-pddl-formal-planning` | Geplant | — | Welle 3 |
| 15 | `exec-15-memory-control-ui` | Phase 1-3 frontend done, backend-wiring pending | ✅ | Welle 1 priorität 5 |
| 16 | `exec-16-llm-provider-gateway` | In Progress (Phase-B P4 DONE, §2.D smart-routing flagged) | ✅ (§2.D holistic review) | Welle 2 |
| 17 | `exec-17-observability-harness-traces` | Draft — infra implementiert, spec lags | ✅ (C9 ADR) | Welle 1 priorität 6 |
| 18 | `exec-18-unified-agent-schema` | ⚠️ **OUTDATED** | — | Entscheidung: archivieren oder lassen? |
| 20 | `exec-20-mcp-manager` | Evaluation | — | Welle 3 |

**Pre-0 infra-specs** (abgehakt, keine laufende arbeit):
- `exec-postgres-tuning-2026-04-17` ✅ Implementiert
- `exec-linux-setup-users-2026-04-17` ✅ Script ready
- `exec-secrets-bootstrap-2026-04-17` ✅ Implementiert

**exec-19** (gone) — archiviert als `archive/exec-19-devstack-consolidation.md`. Content verteilt auf exec-media-ingestion + exec-transformersjs + `claude-merge-frontend-chat-ui-2OqmH/`.

---

## 3. exec-hermes + Phase-B/C tracker

Phase-B **alle P1-P6 DONE** (commits `888b329`..`89f3cc6`, 2026-04-20).
Phase-C **dispatcher + scorer DONE** (commits `11373fa`, `3c664d7`, `f027e8f`).

Offene items in exec-hermes §15:
- P6 frontend (`CompressionIndicator.tsx`, `CompressionFeedback.tsx`, async title-gen dispatch) — **Welle 2**
- Phase-D streaming (`exec-blocking C7`) — **Welle 3**
- Phase-B debt items (`exec-blocking C11`) — **Welle 3**
- Concrete MemPalace/Hindsight `on_pre_compress` impls — **Welle 3**

---

## 4. exec2-* (matrix-chat core)

| # | Spec | Status |
|---|---|---|
| 01 | `exec2-01-matrix-chat-core` | In spec; verify-gates in exec2-04 |
| 02 | `exec2-02-protocol-infra` | In spec; OIDC/MAS + federation blocked (exec-blocking C2+C3) |
| 03 | `exec2-03-ui-rework-sota` | In spec |
| 03b | `exec2-03b-advanced-matrix-options` | **Geplant (Backlog)** — blocked on C6 |
| 03c | `exec2-03c-cinny` | ✅ **Implementierung abgeschlossen** (sota-verify PASS) |
| 04 | `exec2-04-verify-gates` | Sammelstelle — geht durch beim Welle-1-sweep |

---

## 5. Specs außerhalb nummerierung

| Spec | Status | Welle |
|---|---|---|
| `exec-a2fm-adaptive-routing` | Draft — Stufe 0 heuristik landed, flagged | 2 |
| `exec-blocking` | Sammelstelle C1–C11 | living |
| `exec-context` | Evaluation / operativer owner | 1 (ADR für thresholds) |
| `exec-ebm` | Evaluation / Prototyp | 3 |
| `exec-eval` | Infra / verify-runbooks | 1 (Welle-1 helper!) |
| `exec-harness` | Draft, §4g DONE | 2 (open: eval_id, dashboards, weights) |
| `exec-hermes` | Phase-1 + B + C DONE | 2 (P6 frontend tail) |
| `exec-media-ingestion` | Draft | 3 |
| `exec-memory` | Evaluation / laufend | 3 (on_pre_compress impls) |
| `exec-notifications` | Draft | 3 |
| `exec-openworldlib` | Evaluation | 3 |
| `exec-personal-kb` | Planung | 3 |
| `exec-rust` | Portiert / Integration geplant | 3 |
| `exec-scheduler` | Phase-1 DONE + §8.1 DONE | 1 (cleanup), 2 (Phase-2) |
| `exec-scheduler2` | Draft (Phase-2 + Phase-3) | 2 (decision-queue) |
| `exec-security` | Draft (Phase-B P2 creation) | 2 |
| `exec-skills` | Evaluation / Phase 1 impl | 2 (plan-skill landed), 3 (Phase 1 impl) |
| `exec-transformersjs` | Entwurf — primary title-gen owner | 2 (title-gen frontend) |
| `exec-world-model` | Planung | 3 |

---

## 6. Welle-1-playbook — wie man einen verify-gate-pass macht

Für jeden spec in Welle 1 (priorität-reihenfolge oben):

1. **Read** den spec einmal durch. Check: status-block, phase-list, was heißt "implementiert".
2. **Discover** — ist der code wirklich da wo der spec sagt?
   ```
   rg -l "<spec-kernmodul>" python-backend/ go-appservice/
   ```
3. **Smoke-test** — kann man den code ausführen?
   - Python: `pytest tests/<module>/`
   - Go: `go test -tags goolm ./internal/<module>/...`
   - Integration: `RUN_INTEGRATION=1 ...` wenn vorhanden
4. **Check verify-gates-liste** im spec. Welche davon sind abhakbar, welche nicht?
5. **Abhak-commit** — status-block updaten, verify-gates-liste mit `[x]` markieren wo genuin geprüft. Commit.
6. **Wenn gate scheitert** → neuer issue/ticket in dem spec (oder exec-blocking wenn blockiert).

Ziel: nach Welle 1 wissen wir für jeden spec: **läuft das wirklich?**

---

## 7. Referenz-links

- Aktuelle migrations (ground truth für schema): `python-backend/alembic/versions/001–026`
- Spec-audit 2026-04-20: commit `f518e5d` (archived 2 specs, filled exec-blocking C7-C11)
- Home-spec cross-refs zu exec-blocking: commit `2db3a66`
- Session-audit + phase-B/C summary: `exec-blocking.md` footer "Session-Audit 2026-04-20"

---

## 8. Changelog

| Datum | Änderung |
|---|---|
| 2026-04-20 | Erstversion. 3-wellen plan. Welle 1 = verify-gates für exec-05/06/09/10/12/15/17. Welle 2 = Phase-C tail + Option-3 features (smart-routing review, plan-skill wiring, frontend components). Welle 3 = isolation, A2FM ML-router, EBM, world-model, personal-kb. |
