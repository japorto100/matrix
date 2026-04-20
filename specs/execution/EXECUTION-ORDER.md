# Execution Order — cluster-basierter durchlauf

**Erstellt:** 2026-04-20
**Owner:** niemand — living document
**Scope:** alle `specs/execution/exec-*.md` + `exec2-*.md` (46 active, 2 archiviert)

---

## 0. Lese-regel

Dieses doc ist **ein cluster-index mit priorität**, keine to-do-liste. Konkrete arbeit lebt in den spec-files. Diese datei antwortet: *"welche cluster kommt als nächstes dran?"*

**Cluster-reihenfolge** ist bewusst feature-orientiert statt einzelspec-orientiert — verify-gates, design-questions, und code-completion eines features werden zusammen behandelt, nicht aufgesplittet.

---

## 1. Die 9 cluster

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
- `exec-18-unified-agent-schema` — ⚠️ **OUTDATED** — decision: archive or keep
- `exec-scheduler` — Phase-1 DONE + §8.1 DONE
- `exec-scheduler2` — Draft (Phase-2 + Phase-3)

**Warum zusammen:** exec-18 war der "schema-spec"; inzwischen owned jeder slice seine eigenen migrations. exec-scheduler hat ganz eigene migrations (019/020/021) — klarer counter-beweis dass exec-18 als zentraler schema-spec überholt ist.

**Decision:** agno-introspect-tool als runtime-check statt statisches spec-doc. exec-18 archivieren oder als bounded-context-ADR behalten.

---

## 2. Nach cluster I — weitere specs (Welle 3)

Nach den 9 clustern (A–I) bleiben research/planung-specs:

- `exec-14-pddl-formal-planning` — Geplant (PDDL ist matrix's echte plan-mode-antwort, nicht hermes-skill-port)
- `exec-20-mcp-manager` — Evaluation
- `exec-ebm` — Evaluation / Prototyp (energy-based scoring)
- `exec-world-model` — Planung (global knowledge layers)
- `exec-personal-kb` — Planung (user-curated KB)
- `exec-openworldlib` — Evaluation
- `exec-media-ingestion` — Draft (transferred from archived exec-19)
- `exec-notifications` — Draft
- `exec-rust` — Portiert / Integration geplant
- `exec-skills` — Evaluation / Phase 1 implementierbar (plan-skill landed 2026-04-20)
- `exec-transformersjs` — Entwurf — primary title-gen owner
- `exec-context` — Evaluation / operativer owner
- `exec-blocking` — sammelstelle C1–C11

---

## 3. Status-map — wo steht jeder spec jetzt

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

## 4. Welle-1-playbook — wie ein cluster "abhaken"

Für cluster A (Frontend Merger) und B (Matrix Chat Core) — alles andere folgt dem gleichen pattern:

1. **Read** die relevanten spec-files komplett. Was sagt die VERIFY-GATES-liste?
2. **Discover** — läuft der code wirklich?
   - Frontend: `cd frontend_merger && bun run build` + `bun run dev` + manuelle ui-prüfung
   - Python: `pytest` für das modul
   - Go: `go test -tags goolm ./internal/<module>/...`
3. **Integration-smoke** — spezifisch für dieses cluster:
   - Cluster A: `bun run build` clean + playwright-smoke green
   - Cluster B: `exec2-04` gate-liste durchgehen, tuwunel-compose + matrix-chat-login + text-send + encryption-handshake
   - Cluster C: A4 E2E-test run (publish → subscribe → decrypt)
   - Cluster D: agent-chat SSE-roundtrip (hello → stream → tool-call → response)
   - Cluster E: A2A live-test (agent A delegates to agent B via AgentCard)
   - Cluster F: memory-control-ui backend wiring (list sessions / read KG / search episodes)
   - Cluster G: sandbox-decision + skills-guard-drawer
   - Cluster H: smart-routing §2.D walk-through; C9 ADR; §4g.4 open TODOs
   - Cluster I: exec-18 decision; scheduler Phase-2 scoping
4. **Commit** alle cluster-änderungen als **ein commit** (batch), nicht einzelnen pro file. Status-blocks im spec + verify-gates-checkmarks.
5. **Move** zum nächsten cluster.

---

## 5. Referenz-links

- Aktuelle migrations (ground truth): `python-backend/alembic/versions/001–026`
- Spec-audit 2026-04-20: commit `f518e5d`
- Phase-B/C session chain: `888b329` .. `f761874` (13 commits)
- Agno schema-introspection reference: `_ref/agno/cookbook/01_demo/agents/dash/tools/introspect.py`

---

## 6. Changelog

| Datum | Änderung |
|---|---|
| 2026-04-20 | Erstversion als 3-wellen-plan (verify-gates → Phase-C tail → Welle-3-planung). |
| 2026-04-20 | **Restrukturiert als 9-cluster-flow** (A frontend-merger → B matrix-chat → C NATS → D agent-chat → E multi-agent → F memory → G sandbox → H LLM+observability+harness → I schema+scheduler → Welle-3). Cluster-reihenfolge orientiert an feature-abhängigkeiten, nicht an spec-nummern. |
