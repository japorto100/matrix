# Control Surface Delta

> **Stand:** 14. Maerz 2026 (Rev. 4)
> **Phase:** 22b - Control Surface (Ops/Runtime Layer)
> **Zweck:** Execution-Owner fuer die integrierte Control-Flaeche im TradeView-Frontend (Mission-Control-inspiriert, produkt- und security-konform).
> **Aenderungshistorie:**
> - Rev. 1 (13.03.2026): Initialer Slice erstellt, basierend auf `docs/FRONTEND_CONTROL.md` inkl. Ist-Zustand, RBAC/Action-Klassen, Verify-Gates
> - Rev. 2 (13.03.2026): Phase-1-Implementierung eingetragen; erledigte ACs + Verify-Gates markiert; offene RBAC/Approval/Tab-ACs hervorgehoben
> - Rev. 3 (14.03.2026): **Phase 2 Tabs + BFF + RBAC implementiert** — AC7 (ToolEvents), AC8 (Memory/KG), AC10 (Skills/Agents/Evals) code-complete; 6 neue BFF-Routes; `action-classes.ts` mit `isAllowed()` + Rollenmatrix (AC15-AC16)
> - Rev. 4 (14.03.2026): **Two-Tier Control Surface Architecture** — User Mode vs Developer Mode definiert; Fast-Lane KG als Priority-Item; Memory-Paper-Referenz; ReactFlow v2-Marker; Per-Agent Permission Matrix; Klärungen zu Context/KG, RBAC, Skills, Tools
> - Rev. 5 (14.03.2026): **AC20 implementiert** — `ControlAuditLog` Prisma-Modell; `src/lib/server/control-audit.ts` (writeControlAudit, never-throws, mirrors writeFileAudit); Kill-Session-BFF schreibt Audit bei ok/failed/gateway-unavailable

---

## Implementierungsstand (Rev. 2)

### Abgeschlossen — Phase 1 (Navigation + read-only Observability)

TypeCheck (tsc --noEmit): 0 Fehler. Biome: 0 Fehler.

| Datei | Verantwortung |
|---|---|
| `src/features/trading/TradingHeader.tsx` | Control-Button neben Map (AC1) |
| `src/features/agent-chat/components/AgentChatHeader.tsx` | Chat-seitiger Control-Entry (AC2) |
| `src/app/control/page.tsx` | Redirect → `/control/overview` (AC3) |
| `src/app/control/layout.tsx` | Layout-Shell |
| `src/app/control/[[...tab]]/page.tsx` | Catch-all Subtab-Route (AC4) |
| `src/features/control/ControlPage.tsx` | Shell + pathname-basiertes Routing |
| `src/features/control/components/ControlTopNav.tsx` | URL-driven Tab-Nav (AC4) |
| `src/features/control/components/subtabs/ControlOverviewTab.tsx` | Runtime/Memory/Security Summary (AC5) |
| `src/features/control/components/subtabs/ControlSessionsTab.tsx` | Session-Liste + TokenBar (AC6) |
| `src/features/control/components/subtabs/ControlSecurityTab.tsx` | Posture + Events (AC9 partial) |
| `src/features/control/components/subtabs/ControlPlaceholderTab.tsx` | Stub fuer ausstehende Tabs |
| `src/app/api/control/overview/route.ts` | BFF read-only, no-store, X-Request-ID, degraded-fallback |
| `src/app/api/control/sessions/route.ts` | BFF read-only, no-store, degraded-fallback |
| `src/app/api/control/security/route.ts` | BFF read-only, no-store, degraded-fallback |

### Offen — Phase 2 (RBAC + weitere Tabs + Approval)

- Tool Events Tab (AC7), Memory Tab (AC8), KG/Context Tab (AC8)
- Skills/Agents/Evals Tabs (AC10)
- BFF-Endpunkte: tool-events, memory, kg-context, skills, agents, evals (AC11)
- RBAC Action-Klassen serverseitig erzwingen (AC15–AC16)
- bounded-write UI-Markierung + Allowlist (AC17)
- approval-write Flow (AC18)
- forbidden hard-block (AC19)
- Audit-Felder fuer mutierende Actions (AC20)
- Rate-Limit/Abuse-Schutz fuer Control-Endpunkte (AC23)
- Go Gateway: `/api/v1/control/*` Gegenseite (alle Tabs)

---

## 0. Execution Contract

### Scope In

- Control Entry im Trading Header (primaer) und im Agent Chat (sekundaer)
- neue Control-Route inkl. URL-getriebener Subtab-Navigation
- Subtabs fuer Overview, Sessions, Tool Events, Memory, KG/Context, Security, Skills, Agents, Evals
- read-only Default mit expliziter Klassifizierung (`read-only`, `bounded-write`, `approval-write`, `forbidden`)
- Control-BFF Endpunkte unter `/api/control/*` mit Auth/RBAC/Audit- und Request-ID-Weitergabe
- sichtbare Degradation-/Health-Signale (SSE, Memory/KG, Security posture, policy decisions)
- Mission-Control Patterns als Blueprint (Adapt, kein 1:1 Port)

### Scope Out

- Vollport von Mission Control UI/API
- neue Agent-Business-Logik im Python Runtime Layer
- Umstellung des globalen Auth-Stacks (NextAuth/Proxy/Gateway bleibt)
- trading-kritische Mutationen direkt aus Control (Orders/Portfolio-Execution)
- Tenant-Multi-Workspace-Neudesign als separates Plattformprojekt (nur vorbereitende v1 Hooks hier)

### Priorisierungsregel (verbindlich)

1. Navigation + read-only Observability zuerst
2. Security/RBAC/Action-Klassen technisch erzwingen
3. bounded-write/approval-write Flows nur mit Audit + Approval
4. optionales v2 (workspaceId, advanced integrations) nachgelagert

### Mandatory Upstream Sources

- `docs/FRONTEND_CONTROL.md`
- `docs/AGENT_SECURITY.md`
- `docs/AGENT_TOOLS.md`
- `docs/GO_GATEWAY.md`
- `docs/AGENT_HARNESS.md`
- `docs/CONTEXT_ENGINEERING.md`
- `docs/MEMORY_ARCHITECTURE.md`
- `docs/specs/execution/frontend_enhancement_delta.md`
- `docs/specs/execution/agent_harness_runtime_delta.md`

### Baseline (aktuell)

- Control-Surface ist vorhanden:
  - `src/app/control/[[...tab]]/page.tsx` — URL-getriebenes Subtab-Routing
  - `src/features/control/` — ControlPage + ControlTopNav + 3 aktive Subtabs + Placeholder
  - `src/app/api/control/overview|sessions|security/` — BFF-Endpunkte
- Header-Entry in `TradingHeader.tsx` vorhanden
- Chat-Entry in `AgentChatHeader.tsx` vorhanden
- Ziel-Aufrufkette bleibt verbindlich:
  - `UI -> Next BFF -> Go Gateway -> Downstream Services`

---

## 1. Offene Deltas

### A. Entry Points und Routing

- [x] **AC1** `TradingHeader` um Control-Entry erweitert (neben Map, `SlidersHorizontal`-Icon, `data-testid="link-control"`)
- [x] **AC2** `AgentChatPanel` um sekundaeren Control-Entry erweitert (`AgentChatHeader.tsx`, Deep-Link auf `/control` und `/control/security`)
- [x] **AC3** Route-Shell unter `src/app/control/*` angelegt (page + layout)
- [x] **AC4** URL als Source-of-Truth fuer Subtabs implementiert (`[[...tab]]` catch-all + `usePathname` in `ControlTopNav` + `ControlPage`)

### B. Control IA und Subtabs (v1 read-only first)

- [x] **AC5** Overview Tab mit Runtime-/Health-Summary umgesetzt (SSE, Memory/KG, Security posture, Sessions, Tool-Errors) — `ControlOverviewTab.tsx`; degraded-Zustand sichtbar wenn Gateway nicht erreichbar
- [x] **AC6** Sessions Tab mit lifecycle Sicht umgesetzt (status, TokenBar, filter, drilldown-ready) — `ControlSessionsTab.tsx`
- [x] **AC7** `ControlToolEventsTab.tsx` — collapsible timeline (ChevronRight/Down toggle); Status-Badge ok/error/running; durationMs + agentId + errorCode im expanded view; degraded-Banner — 14.03.2026
- [x] **AC8** `ControlMemoryTab.tsx` (layer cards: episodic/kg/vector, health badge, itemCount, lastSyncAt) + `ControlKGContextTab.tsx` (nodeCount/edgeCount stats, recentNodes list, health badge) — 14.03.2026
- [x] **AC9** Security Tab mit blocked/approved Events, posture score, trend-Indikator — `ControlSecurityTab.tsx` (read-only; bounded-write/approval-write ausstehend)
- [x] **AC10** `ControlSkillsTab.tsx` (id/name/version/enabled/lastUsed) + `ControlAgentsTab.tsx` (status-dot, role, sessionCount) + `ControlEvalsTab.tsx` (score bar, passed/failed/running icon) — alle read-only v1 — 14.03.2026

### C. BFF/API Contract und Datenpfade

- [x] **AC11** Control-BFF Endpunkte unter `/api/control/*` vollständig: overview, sessions, security (Phase 1) + tool-events, memory, kg-context, skills, agents, evals (Phase 2, 14.03.2026) — alle mit X-Request-ID, no-store, 5s Timeout, degraded-Fallback
- [x] **AC12** Request-IDs durchgaengig propagiert (`X-Request-ID` in allen 3 BFF-Routen erzeugt/weitergereicht und in Response zurueckgegeben)
- [x] **AC13** no-store + degraded-Antwortform standardisiert — alle 3 BFF-Routen liefern strukturiertes degraded-JSON mit `degraded_reasons[]` wenn Gateway nicht erreichbar
- [x] **AC14** BFF-Routen leiten an Go Gateway `/api/v1/control/*` weiter; kein Browser-Direktpfad — **Go-Gegenseite noch nicht implementiert** (liefert HTTP-Fehler -> degraded-Fallback greift)

### D. RBAC, Action-Klassen, Approval

- [x] **AC15** `src/features/control/lib/action-classes.ts` — `ControlAction` + `ControlActionClass` Typen; `CONTROL_ACTION_CLASSES` Map; `getControlActionClass()` + `isAllowed(action, userRole)` — 14.03.2026
- [x] **AC16** `ACTION_CLASS_MIN_ROLE` Map (viewer/trader/admin/superadmin); `isAllowed()` prüft ROLE_ORDER Index — 14.03.2026
- [x] **AC17** `ControlActionBadge.tsx` — visuelle Badge-Komponente (read/write/approval/forbidden) an jedem Mutations-Button; Kill-Session-Button in `ControlSessionsTab` zeigt "approval"-Badge — 14.03.2026
- [x] **AC18** `KillSessionConfirmDialog.tsx` — approval-write: Typ Session-ID + 30s Countdown; `POST /api/control/sessions/[id]/kill` BFF (403 ohne `x-confirm-token`); invalidiert `["control","sessions"]` nach Erfolg — 14.03.2026
- [x] **AC19** `ControlActionGuard.tsx` — wraps Mutations-Buttons: `forbidden` → null (hard-block), Rolle unter Minimum → Lock-Icon + Badge, erlaubt → children; nutzt `useControlRole()` + `isAllowed()` — 14.03.2026

### E. Auditierbarkeit und Security Hardening

- [x] **AC20** Audit-Felder fuer mutierende Control-Actions erzwingen — 14.03.2026
  - `ControlAuditLog` Prisma-Modell (action, actionClass, actorUserId, actorRole, requestId, target, status, errorCode, expiresAt)
  - `src/lib/server/control-audit.ts`: `writeControlAudit()` — Prisma-Nullable-Safe, never-throws, mirrors `writeFileAudit` pattern
  - `POST /api/control/sessions/[id]/kill`: schreibt Audit-Eintrag bei ok (204), failed (Gateway-Error), und GATEWAY_UNAVAILABLE (503)
  - `bun run db:generate` ausgefuehrt — Prisma Client regeneriert
- [ ] **AC21** Security-Ereignisse trennen (general platform vs. control action signals) — ausstehend
- [x] **AC22** Operator-taugliche Fehlerpfade: keine silent failures, kein full-page crash — alle Tabs zeigen strukturierte Fehler-/Degradation-Zustande (AlertCircle + Message)
- [ ] **AC23** Rate-Limit/Abuse-Schutz fuer mutierende Endpunkte — ausstehend

### F. Tenant/Workspace Vorbereitung

- [ ] **AC24** v1 actor-scoping in allen Control-Endpunkten — ausstehend (X-User-Role wird weitergeleitet, scopebasierte Filterung im Gateway offen)
- [ ] **AC25** v2 Hook: optionale `workspaceId` im Contract — ausstehend

---

## 2. Verify-Gates

### Code-complete (ohne Stack verifizierbar)

- [x] **AC.V1** Header-Entry funktioniert (`TradingHeader` -> `/control/overview`) ohne Bruch bestehender Navigation — `data-testid="link-control"` vorhanden
- [x] **AC.V2** Chat-Entry funktioniert (`AgentChatHeader` -> `/control` + `/control/security` Deep-Link)
- [x] **AC.V3** Subtab-Routing bleibt bei Reload stabil und direkt teilbar — URL ist source-of-truth via `[[...tab]]` catch-all + `usePathname`
- [x] **AC.V4** Overview und Sessions zeigen lauffaehige read-only Daten inkl. Fehler-/Leerlaufzustand — degraded JSON wenn Gateway offline; leere Session-Liste mit Leer-State-Icon
- [x] **AC.V7** Kein browser-direkter Tool-Wirkpfad vorhanden — alle BFF-Routen leiten an Gateway weiter; kein direkter Runtime-Aufruf aus Browser
- [x] **AC.V8** Action-Klassen im UI sichtbar — `ControlActionBadge` an Kill-Session-Button; `ControlActionGuard` erzwingt Rolle client-seitig; BFF-seitig 403 ohne confirm-token (14.03.2026)
- [x] **AC.V9** approval-write flow: `KillSessionConfirmDialog` (Session-ID tippen + 30s TTL) + BFF 403-Gate — code-complete (14.03.2026)
- [x] **AC.V10** Viewer-Rolle sieht Kill-Button als Lock-Icon; Admin-Rolle sieht aktiven Button — code-complete via `isAllowed()` + ROLE_ORDER (14.03.2026)
- [x] **AC.V11** Control-Endpunkte liefern konsistente Fehlerstruktur + `X-Request-ID` — alle 9 BFF-Routen implementiert (overview/sessions/security + tool-events/memory/kg-context/skills/agents/evals)

### Live-Verify — Stack noetig

- [ ] **AC.V5-LV** Phase-2-Tabs live: ToolEvents-Timeline, Memory-Layer-Cards, KG-NodeCount, Skills-Rows, Agents-Status, Evals-ScoreBar — alle zeigen reale Gateway-Daten oder degraded-Banner — Stack + Go `/api/v1/control/*` noetig
- [ ] **AC.V6-LV** Security Tab vollstaendig: blocked/approved/policy-signale aus Go-Backend — Live-Verify Stack noetig
- [ ] **AC.V9-LV** Kill-Session end-to-end: Confirm-Dialog → BFF 403 ohne Token, 204 mit Token → `ControlAuditLog` Eintrag in dev.db nachweisbar (requestId, actorRole, status=ok) — Stack noetig
- [ ] **AC.V13-LV** `ControlAuditLog` Tabelle in dev.db vorhanden + Eintrag bei Kill-Session (ok/failed) und GATEWAY_UNAVAILABLE — Stack noetig (Prisma-Modell + `writeControlAudit` code-complete 14.03.2026)

### Ausstehend — blockiert auf Backend

- [ ] **AC.V12** Tenant/Workspace-v1 Schutz: keine Cross-Scope Daten ohne Berechtigung — ausstehend (AC24, Gateway-seitig)

---

## 3. Evidence Requirements

- Screenshot/Recording fuer AC.V1-AC.V4 (Navigation, Subtabs, Datenzustand, Fehlerzustand)
- Technischer Nachweis fuer AC.V7 (Request-Trace/Codepfad, keine Browser-Direktmutation)
- Testnachweis fuer AC.V8-AC.V10 (Rollenmatrix + Action-Klassen + Approval/Forbidden)
- API Contract Samples fuer alle 9 `/api/control/*` Routen (happy path + error + degraded)
- Live-Verify: Phase-2-Tab-Daten aus Go-Gateway (AC.V5-LV)
- Live-Verify: Security-Tab-Signale (AC.V6-LV)
- Live-Verify: Kill-Session end-to-end + `ControlAuditLog` Eintrag nachweisbar (AC.V9-LV + AC.V13-LV)
- Kurzer Nachweis `v1 actor scope` und `v2 workspaceId hook` (AC24/AC25)
- Referenzabgleich:
  - `docs/FRONTEND_CONTROL.md` (Entry Points, IA, Matrix)
  - `docs/AGENT_SECURITY.md` / `docs/GO_GATEWAY.md` (Policy- und Gateway-Boundary)

---

## 4. Propagation Targets

- `docs/specs/EXECUTION_PLAN.md`
- `docs/specs/FRONTEND_ARCHITECTURE.md`
- `docs/specs/execution/frontend_enhancement_delta.md`
- `docs/specs/execution/agent_harness_runtime_delta.md`
- `docs/FRONTEND_CONTROL.md`

---

## 4.1 Externe Referenz evaluiert (mcp-manager)

- Quelle wurde extrahiert und fuer Architektur-Review bereitgestellt:
  - `D:/tradingview-clones/_tmp_ref_review/extraction_candidates/mcp-manager`
- Referenz ist als Blueprint zu behandeln (Adapt), **kein** 1:1 Port in TradeView Fusion.
- In die Two-Tier-Weiterarbeit einbeziehen:
  - **TT3 Tools**: per-app Tool-Filter + Token-Budget + Approval-Gate Muster
  - **TT6 Skills**: Registry/Allowlist/Approval-Patterns fuer User-vs-Admin Scope
  - **TT8 Security**: Auth/Secret/Governance- und Policy-Signale als Security-Tab Inputs
  - **TT16 Full Audit Logs**: mutierende Aktionen durchgaengig auditierbar machen
- Evaluationsfokus: Uebernahme der Governance-, Audit-, Filter- und Discovery-Patterns in
  `UI -> Next BFF -> Go Gateway -> Downstream Services`.

---

## 5. Two-Tier Control Surface Architecture

> **Stand:** 14. Maerz 2026 (Rev. 4)
> **Entscheid:** Die Control-Surface wird in zwei klar getrennte Modi aufgeteilt — User Mode (default) und Developer Mode (admin-Rolle). Beide Modi teilen dieselbe Route `/control`, werden aber durch Rollen-Gate + optionalen Dev-Toggle differenziert.

---

### Hintergrund und Motivation

Die ursprüngliche Control-Surface war zu stark an Mission Control / Operator-Console orientiert (Kill Session, raw Tool Events, Memory-Infrastruktur, KG-Admin, Evals). Das ist fuer einen Trader/Analyst nicht relevant. Gleichzeitig braucht der Nutzer echte AI-Kontrolle: eigene Memory verwalten, KG einsehen, Agents konfigurieren, Tools aktivieren. Diese Erkenntnis fuehrt zur Zwei-Tier-Architektur.

---

### User Mode (default — viewer / analyst / trader)

Ziel: AI-Kontrolle fuer den normalen Nutzer — vertrauen, verstehen, konfigurieren.

#### Offene Deltas (User Mode)

- [ ] **TT1** **Overview (vereinfacht)** — AI-Health-Indikator (online/degraded/offline), aktive Tasks-Zusammenfassung, letzter Agent-Fehler. Keine raw Infrastruktur-Metriken.
- [ ] **TT2** **Sessions (read-only)** — "Was macht der Agent gerade fuer mich?" — Session-Status, Token-Druck, laufende Tasks. Kein Kill-Button im User Mode.
- [ ] **TT3** **Tools** — Uebersicht verfuegbarer Tools (aktiviert/deaktiviert), Toggle per Tool, Tool hinzufuegen via Marketplace/URL (ChatGPT-Plugin-Stil). User sieht nur seine eigenen Tools. *Diskussion: Tool-Add durch User: denkbar mit Approval-Gate (Security-Scan vor Aktivierung). Kein silent install.*
- [ ] **TT4** **Memory** — Persoenliche Memory UI: episodische Eintraege einsehen, bearbeiten, loeschen. Semantische Facts anzeigen. Bulk-Delete moeglich. **Referenz: https://arxiv.org/pdf/2603.07670 — Memory-Architektur-Paper (backend-relevant, UI-Konzepte uebertragbar, v.a. episodic/semantic/procedural split).**
- [ ] **TT5** **KG (Fast-Lane — PRIORITY ITEM)** — Persoenlicher User-KG als eigene UI. Nodes/Edges einsehen, erstellen, loeschen. Auth/Encryption bereits vorhanden (Phase 1). UI fehlt noch vollstaendig. *Fast-Lane KG = frontend user overlay. Slow-Lane KG = backend global graph (Developer Mode). Context-Tab entfaellt fuer User — KG IS der Kontext des Users.* **=> Als Priority-Item markiert: Fast-Lane-KG-UI ist naechster groesserer Frontend-Baustein nach Control-Phase-2.**
- [ ] **TT6** **Skills** — Eigene Skills aktivieren/deaktivieren. User sieht nur seine Skills. *Diskussion: User-Add von Skills: ambivalent. Power-User koennte eigene Skills via URL/Marketplace hinzufuegen — Approval-Gate (Security-Scan, bounded-write) empfohlen. Kein globales Skill-Deploy durch User.*
- [ ] **TT7** **Agents** — Eigene Agents: aktivieren/deaktivieren, Rolle anpassen, Tools pro Agent konfigurieren. **Per-Agent Permission Matrix** (welche Daten darf dieser Agent sehen? Portfolio? Orders? External APIs?) — das ist das User-facing RBAC, nicht globales Rollenmanagement. *Diskussion: Visual Workflow Editor (ReactFlow / n8n-Stil) als v2-Feature — eigene Sub-Surface oder Agents-Sub-Tab. SOTA-Referenzen: LangGraph Studio, Flowise, n8n. => Als v2-Marker vermerkt.*
- [ ] **TT8** **Security** — Posture-Score, Zugriffsliste, letzte Sicherheits-Alerts fuer den User. *Dieses Tab macht definitiv Sinn fuer User (Compliance, Vertrauen).*

---

### Developer Mode (admin-Rolle — Toggle oder `/control?mode=dev`)

Ziel: Infrastruktur-Observability und System-Administration.

*Diskussion: Ob Developer Mode als Query-Param-Toggle (`?mode=dev`, nur sichtbar fuer admin-Rolle) oder als separater `/admin`-Route implementiert wird, ist offen. Query-Param-Toggle ist einfacher (gleiche Shell), `/admin` ist sauberer getrennt. Empfehlung: separater `/admin` wenn Scope waechst, Toggle reicht fuer v1.*

#### Offene Deltas (Developer Mode)

- [ ] **TT9** Kill Session + Raw Tool Events Timeline — Prozess-Management, Developer-Debug-View. Nur admin-Rolle.
- [ ] **TT10** Memory-Infrastruktur-Health — Layer-Health (episodic/kg/vector), purge-all. Infrastruktur-Admin.
- [ ] **TT11** Slow-Lane KG (globaler Backend-Graph) — alle User-Daten, Schema-Admin. Nur admin.
- [ ] **TT12** Alle Skills aller User — global deploy, policy. Nur admin.
- [ ] **TT13** Agent Policy Setting + Cross-Agent-Rules — globale Guardrails, policy enforcement.
- [ ] **TT14** Evals Runs + QA-Workflows — testing, drift-detection. Developer/QA-territory.
- [ ] **TT15** RBAC Role Distribution (global) — Rollen verteilen, User-Rollen aendern. Bleibt in `/api/admin/users` (bereits vorhanden).
- [ ] **TT16** Full Audit Logs — alle Mutations, alle User, zeitlich geordnet.

---

### Klärungen aus der Diskussion (14.03.2026)

| Frage | Entscheid |
|---|---|
| Context-Tab vs KG-Tab | Fuer User zusammengefuehrt: KG = der Kontext des Users. "Context" als separates Debug-Tab nur Developer Mode (runtime context window, token usage, loaded chunks). |
| RBAC fuer User | Nicht globales Rollenmanagement. Per-Agent-Permission-Matrix im Agents-Tab. User bestimmt welche Daten ein Agent sehen darf. |
| User kann Tools hinzufuegen? | Ja, mit Approval-Gate (Security-Scan). Kein silent install. bounded-write. |
| User kann Skills hinzufuegen? | Ambivalent. Power-User: ja mit Gate. Normaler User: nur activate/deactivate. |
| ReactFlow / n8n fuer Agents? | v2. Als strategischer Marker vermerkt. Eigene Sub-Surface oder Agents-Sub-Tab. |
| Kill Session im User Mode? | Nein. Nur Developer Mode. User Mode Sessions-Tab ist read-only. |
| Evals fuer User? | Nein. Developer Mode / QA. |
| Memory Paper | https://arxiv.org/pdf/2603.07670 — backend-relevant, UI-split-Konzepte (episodic/semantic/procedural) fuer Memory-Tab-Design verwertbar. |

---

### Verify-Gates (Two-Tier)

- [ ] **TT.V1** User Mode zeigt keine Kill-Session / Dev-only Aktionen — `ControlActionGuard` blockiert, keine UI-Elemente sichtbar fuer viewer/trader-Rolle
- [ ] **TT.V2** Fast-Lane KG UI (TT5) zeigt persoenliche Nodes/Edges und erlaubt CRUD — Live-Verify (Stack + KG-Backend noetig)
- [ ] **TT.V3** Memory Tab (TT4) zeigt episodische Eintraege, Edit + Delete funktional — Live-Verify (Stack noetig)
- [ ] **TT.V4** Tools Tab (TT3) zeigt verfuegbare Tools, Toggle aktiviert/deaktiviert deterministisch — Live-Verify
- [ ] **TT.V5** Agents Tab (TT7) zeigt per-Agent Permission Matrix, User kann Permissions aendern — Live-Verify
- [ ] **TT.V6** Developer Mode (TT9-TT16) nur fuer admin-Rolle erreichbar — Viewer/Trader sehen Dev-Tabs nicht — AC.V10-Pattern anwenden
- [ ] **TT.V7** ReactFlow Visual Editor (TT7 v2) — offen bis v2
- [ ] **TT.V8** Memory Paper Konzepte (episodic/semantic split) im Memory-Tab UI sichtbar — offen (TT4 design-phase)
