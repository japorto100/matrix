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

- [ ] **2.1:** Structured Audit Logs
  - Jede Agent-Action (Tool-Call, LLM-Request, Sandbox-Execution) wird geloggt
  - Format: `{ timestamp, agentId, action, input, output, duration, success }`
  - Storage: Append-only Log (File oder DB)
- [ ] **2.2:** Consent Flows
  - Sensitive Tools (File Write, Network Access, Payment) brauchen User-Consent
  - Consent-Request als UI-Element im Chat (wie Tool-Approval, aber expliziter)
  - Configurable: welche Tools brauchen Consent (YAML Config)
- [ ] **2.3:** Rate-Limiting pro Tool/Agent/Session
  - Max N Calls pro Tool pro Session (deer-flow/Tambo `maxCalls` Pattern)
  - Max Token-Budget pro Session (Cost-Cap)
  - Configurable per Agent-Rolle
- [ ] **2.4:** Input/Output Sanitization
  - Agent-Outputs auf Injection-Versuche pruefen
  - Tool-Inputs validieren bevor Execution
  - Prompt-Injection Detection (regelbasiert + LLM-basiert)

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
