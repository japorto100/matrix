# exec-12: Sandbox + Security (OpenSandbox + pentagi Patterns + Computer Use)

**Datum:** 30.03.2026
**Status:** Geplant
**Abhaengig von:** exec-10 (Multi-Agent), exec-08 (Python Backend)
**Spec:** `specs/agent-ui/06-protocols-roadmap.md`

---

## Phase 1: OpenSandbox (Alibaba)

- [ ] **1.1:** OpenSandbox SDK installieren
  - `pip install opensandbox-sdk` in `python-backend/pyproject.toml`
  - Docker muss auf dem Host verfuegbar sein
- [ ] **1.2:** Sandbox-Manager in `python-backend/agent/sandbox/`
  - Container pro Code-Execution erstellen
  - Lifecycle: Create → Execute → Collect Result → Destroy
  - Timeout-Enforcement (Default: 30s)
- [ ] **1.3:** Code Interpreter Integration
  - Agent generiert Python/JS Code → OpenSandbox fuehrt aus
  - Result (stdout, files, plots) zurueck an Agent
  - Fehler werden strukturiert zurueckgemeldet
- [ ] **1.4:** Browser Automation via Sandbox
  - Chrome/Playwright in Sandbox-Container
  - Agent kann Websites bedienen (Screenshot, Click, Extract)
  - Isoliert vom Host-Netzwerk
- [ ] **1.5:** Filesystem-Isolation
  - Jeder Sandbox-Container bekommt eigenes Temp-Filesystem
  - Agent kann Dateien erstellen/lesen innerhalb der Sandbox
  - Kein Zugriff auf Host-Filesystem

## Phase 2: Security Hardening (pentagi Patterns)

- [x] **2.1:** Structured Audit Logs ✅ (31.03.2026, Alembic-Update 31.03.2026)
  - `agent/audit/` Package: `logger.py` (structured events), `store.py` (PG + JSON Lines)
  - AuditAction Enum: LLM_REQUEST/RESPONSE, TOOL_CALL/RESULT, APPROVAL_REQUEST/DECISION, etc.
  - LangGraph Nodes instrumentiert: `llm_node.py`, `tool_node.py`, `approval_node.py`
  - **Alembic-managed** (exec-11): `agent.audit_events` Tabelle im `agent` Schema
    - Columns: user_id, thread_id, agent_class, agent_role, tool_name, input/output JSON
    - Indices: user_id, thread_id, action, timestamp
    - Raw DDL (`CREATE TABLE IF NOT EXISTS`) entfernt → `uv run alembic upgrade head`
  - Multi-User + Multi-Agent: user_id + agent_role Columns
  - Fallback: JSON Lines in `data/audit/` (kein PG konfiguriert)
  - Grafana-ready: PG als Datasource
- [x] **2.2:** Consent Flows ✅ (31.03.2026)
  - `agent/consent/` Package: Plugin-based Consent System (deer-flow GuardrailProvider Pattern)
  - 4 Levels: `none` (auto-allow), `inform` (log), `confirm` (interrupt), `deny` (hard block)
  - `consent_policy.yaml` — Single Source of Truth fuer Tool-Authorization
  - `ConsentProvider` Protocol (`@runtime_checkable`) mit Dynamic Class Import (`module:ClassName`)
  - Built-in Providers: `YamlPolicyProvider` (default), `AllowlistProvider`
  - `SessionConsentCache` — per thread_id + tool_name (ahead of SOTA, kein Framework hat das)
  - User-Decisions: `allow_once`, `allow_session`, `deny`, `deny_session`
  - Role-based Policies: `roles: [advisory]` beschraenkt Rules auf bestimmte Agent-Rollen
  - Domain Hardblocks (place_order, cancel_order, modify_position) aus `validators/trading.py`
    nach `consent_policy.yaml` migriert (level: deny, roles: [advisory])
  - `validators/trading.py` + `validators/` Package geloescht (komplett durch Consent-System ersetzt)
  - `approval_node.py` refactored auf Consent-System
  - `agent_class` zu `AgentGraphState` hinzugefuegt
  - Legacy-Loop (`loop.py`) auf Consent-System umgestellt
  - Audit-Integration: CONSENT_REQUEST + CONSENT_DECISION Events
- [x] **2.3:** Rate-Limiting pro Tool/Agent/Session ✅ (31.03.2026)
  - `consent_policy.yaml` erweitert um `rate_limits` Section — Single Source of Truth
  - `consent/rate_limiter.py` — `SessionRateLimiter` mit per-tool counter + session token budget
  - Per-Tool Call Limits: `per_tool: { sandbox_execute: { max_calls: 5 } }`
  - Per-Session Total: `max_tool_calls_total: 50`, `max_tokens_per_session: 100000`
  - Grace Termination (pentagi): Warnung N Iterationen vor Hard-Stop
  - Rate Limiter in `check_consent()` eingehaengt (vor Provider-Check)
  - `tool_node.py` recorded Tool-Calls im Rate Limiter nach Execution
  - **Konsolidierung bestehender Config:**
    - `MAX_ITERATIONS` (agent_graph.py) → YAML mit ENV-Fallback
    - `TOOL_TIMEOUT_SEC` (tool_node.py) → YAML mit ENV-Fallback
    - Loop Detection Thresholds (loop_detection.py) → YAML mit hardcoded Fallback
    - `middleware/guardrails.py` geloescht (redundant mit consent/)
- [ ] **2.4:** Input/Output Sanitization
  - Agent-Outputs auf Injection-Versuche pruefen
  - Tool-Inputs validieren bevor Execution
  - Prompt-Injection Detection (regelbasiert + LLM-basiert)
- [ ] **2.5:** Prompt Template Validation (pentagi Pattern)
  - Agent-generierte Prompts auf erlaubte Variablen pruefen (AST-Parse)
  - Verhindert Template Injection via nicht-deklarierte Variablen
  - Ref: `_ref/pentagi/backend/pkg/templates/validator/validator.go`
- [ ] **2.6:** RBAC Privilege System (pentagi Pattern)
  - User-basierte Berechtigungen: wer darf welchen Agent/Flow/Tool nutzen
  - Privilege Namespace: `flows.view`, `tools.admin`, `agents.create` etc.
  - Fuer Multi-User Szenarien (1000+ User mit eigenen Agents)
  - Admin-Rolle bypassed Ownership-Filter
  - Ref: `_ref/pentagi/backend/pkg/server/services/flows.go`
- [ ] **2.7:** Installer Hardening (pentagi Pattern)
  - Default-Credentials beim ersten Start durch kryptographisch sichere Werte ersetzen
  - `.env` Secrets auto-generieren wenn noch Default-Werte
  - Ref: `_ref/pentagi/backend/cmd/installer/hardening/hardening.go`

## Phase 3: Computer Use

### 3.1 Playwright MCP (Browser Automation)

- [ ] **3.1.1:** Playwright MCP Server im Agent-Stack
  - 33+ Tools (Navigate, Click, Type, Screenshot, Accessibility Tree)
  - Agent kann Websites bedienen
- [ ] **3.1.2:** Playwright CLI als Alternative (4x weniger Tokens)
  - Fuer wiederholbare Flows (CI/CD, Testing)
  - MCP fuer explorative Tasks
- [ ] **3.1.3:** Integration in Sandbox
  - Playwright laeuft innerhalb OpenSandbox Container
  - Isoliert vom Host-Browser

### 3.2 WebMCP (Zukunft)

- [ ] **3.2.1:** WebMCP Spec beobachten
- [ ] **3.2.2:** Trading-Pages exposen Capabilities via `navigator.modelContext`
  - Chart-State, Portfolio-Daten, Indikator-Werte als Tools
  - Agent ruft sie nativ auf (kein DOM-Scraping)

### 3.3 Anthropic Computer Use (Evaluation)

- [ ] **3.3.1:** Evaluieren fuer Desktop-Agent Use-Cases
  - Claude sieht Screen + klickt (Cloud-side)
  - Aktuell nicht prioritaer

## Phase 4: Artifacts UI (Code-Execution im Chat)

- [ ] **4.1:** E2B Fragments als UI-Inspiration
  - Artifacts-Style: Agent generiert Code → Preview im Chat
  - Split-View: Code links, Output rechts
- [ ] **4.2:** Sandpack fuer leichtgewichtige Browser-Previews
  - Kein Server noetig, laeuft komplett im Browser
  - React/JS Code-Previews direkt im Chat
- [ ] **4.3:** OpenSandbox fuer schwere Execution
  - Python Data-Analysis, File-Processing, API Calls
  - Results als Artifacts im Chat (Charts, Tables, Files)

## Phase 5: PDDL Formale Plan-Validierung (Optional)

Ref: `pddl_phase22b_delta.md` (aus Hauptprojekt)

- [ ] **5.1:** PDDL/ADL als optionale Validierungsschicht fuer Agent-Workflows
  - Pattern: `Plan → Validate → Execute/Replan`
  - Fuer komplexe Multi-Step Workflows mit harten Constraints
  - Ergaenzt LangGraph (Ausfuehrung), ersetzt es nicht
- [ ] **5.2:** Pilot: "Morning Research Run" Workflow
  - PDDL Domain + Problem Definition
  - Solver-gestuetzte Validierung vor Ausfuehrung
- [ ] **5.3:** Integration mit LangGraph
  - Validation-Node der PDDL-Solver aufruft bevor Graph weiterlaeuft
  - Bei Constraint-Verletzung: Replan statt Execute

---

## Verify-Gates

- [ ] OpenSandbox: Agent fuehrt Python-Code in isoliertem Container aus
- [ ] Timeout: Code-Execution wird nach 30s abgebrochen
- [ ] Filesystem-Isolation: Agent kann nur innerhalb Sandbox-Container Dateien erstellen
- [ ] Audit Log: Jede Agent-Action ist nachvollziehbar geloggt
- [ ] Consent Flow: Sensitive Tool-Call zeigt Consent-Dialog, wartet auf User-Bestaetigung
- [ ] Rate Limit: Agent wird nach N Tool-Calls pro Session gestoppt
- [ ] Playwright: Agent navigiert Website, extrahiert Daten, alles in Sandbox
- [ ] Artifacts: Agent-generierter Code rendert als Preview im Chat

---

## Code Review Fixes (aus exec-10 uebertragen)

Offene Security-Issues aus dem Python Backend Code Review (31.03.2026):

- [x] **#1 Low (downgraded):** Credentials in `.env` — nur lokale Dev-Tokens
  - Kein Security-Issue: `.env` in `.gitignore`, Tokens nur fuer lokalen Synapse Dev-Server
- [x] **#5/#11 Medium:** Dead Code in `agent/app.py` entfernen
  - `_stream_anthropic()`, `_stream_openai()`, `_REASONING_BUDGET`, `_sse()` entfernt (~130 LOC)
  - Unbenutzter `json` Import entfernt
- [x] **#16 Medium:** Working Memory Race Condition
  - Option C implementiert: Per-Entry Keys statt monolithisches Dict
  - Jeder Entry bekommt eigenen Cache Key (`tradeview:m5:session:{sid}:entry:{eid}`)
  - Neuer Index-Key trackt Entry-IDs fuer Enumeration
  - `working_memory_get_entry()` fuer O(1) Einzelzugriff (LoadMemoryTool nutzt es)
  - Kein Read-Modify-Write mehr bei `working_memory_set` — Multi-Agent safe
- [x] **#19 Low:** Mutable Default auf Pydantic Model
  - `BrowserToolDef.input_schema: dict = {}` → `Field(default_factory=dict)`
- [x] **#20 Low:** `bridge/config.py` .env Pfad relativ zum CWD
  - Fix: `Path(__file__).resolve().parents[1] / ".env"`
