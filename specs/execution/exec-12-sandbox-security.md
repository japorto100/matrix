# exec-12: Sandbox + Security (OpenSandbox + pentagi Patterns + Computer Use)

**Datum:** 30.03.2026
**Status:** Geplant
**Abhaengig von:** exec-10 (Multi-Agent), exec-08 (Python Backend)
**Spec:** `specs/agent-ui/06-protocols-roadmap.md`

---

## Phase 1: OpenSandbox (Alibaba)

**Repo:** github.com/alibaba/OpenSandbox | **Lizenz:** Apache 2.0 | **Status:** Aktiv (925 commits, CNCF Landscape)
**Docs:** open-sandbox.ai | **PyPI:** `opensandbox`, `opensandbox-code-interpreter`

### Grundregel: Wann Sandbox, wann nicht?

| Code-Quelle | Wo ausfuehren | Beispiel |
|:---|:---|:---|
| **Eigener Code** (Rust/Go/Python Backend) | Direkt im Backend | Indikatoren, Portfolio-API, Memory |
| **LLM-generierter Code** | Immer Sandbox | Data Analysis, Backtesting, Plots |
| **User-eingegebener Code** | Immer Sandbox | Custom Indicators, Scripts |
| **Tool-Ergebnisse** (API-Calls) | Backend (kein Code) | get_chart_state, get_portfolio |

Sandbox ist fuer **untrusted Code Execution**, nicht fuer interne API-Calls.
Deterministische Analyse (Rust-Indikatoren, Go-Gateway) braucht keine Sandbox.
Sandbox = Escape-Hatch fuer alles was die deterministische Pipeline nicht abdeckt.

### Konkrete Use-Cases (Bezug Hauptprojekt tradeview-fusion)

1. **Custom Data Analysis** — User: "Analysiere BTC/USD Sharpe Ratio ueber 90 Tage"
   Agent generiert pandas/numpy Code → Sandbox fuehrt aus → Chart + Zahlen zurueck
2. **Custom Indicators** — User will eigenen Indikator der nicht in Rust existiert
   Agent schreibt pandas-ta Code → Sandbox → Result als Artifact im Chat
3. **Backtesting** — User: "Teste meine Strategie auf historischen Daten"
   Lang laufender Code → Sandbox mit erhoehtem Timeout (30min)
4. **File Upload Analyse** — User laedt CSV/Excel hoch
   Flow: Backend empfaengt File → Kopie in Sandbox → Agent analysiert → Result zurueck → Sandbox destroyed
   Original-File beruehrt nie den Agent-Prozess. Backend speichert Result, nicht Sandbox.
5. **Browser Research** — Agent scrapt News/Research von JS-heavy Seiten
   Playwright in Sandbox-Container, isoliert vom Host-Browser
6. **Beliebiger LLM-generierter Code** — Python, JS, Shell, SQL
   Alles was das LLM generiert und ausfuehren will → Sandbox

### Windows Dev-Setup

OpenSandbox benoetigt Docker (Linux-Container). Optionen:
- **Docker Desktop + WSL2** — empfohlen, OpenSandbox Server laeuft in WSL2 oder als Container
- **Docker in WSL2 ohne Desktop** — leichtgewichtiger, gleiche Funktionalitaet
- **Natives Windows** — nicht moeglich (OpenSandbox Server ist Python/Linux, execd ist Go/Linux)
- **WSL1** — nicht moeglich (kein echter Linux-Kernel, Docker braucht WSL2)

Fuer Dev: docker-compose Service `opensandbox-server` (siehe unten).

### Architektur (4 Layer)

```
SDK (Python) → Specs (OpenAPI) → Runtime (FastAPI Server) → Sandbox Instances
                                  Docker Runtime (dev)        Container + execd + Jupyter
                                  K8s Runtime (prod)          + Egress Sidecar
```

**execd** = Go-Daemon in jedem Container: Code via Jupyter Kernels, Shell via SSE, Filesystem CRUD.
**Defaults pro Sandbox:** 1 CPU, 2 GB RAM, 10 Min TTL (alles konfigurierbar).
**System-Requirements (Server):** 4 CPU, 8 GB RAM, 50 GB Disk.

### Implementation Steps

- [ ] **1.1:** OpenSandbox Server + SDK
  - `uv pip install opensandbox opensandbox-code-interpreter` in python-backend
  - `opensandbox-server` als docker-compose Service (siehe unten)
  - Docker Image: `opensandbox/code-interpreter:v1.0.2`
  - Custom Image mit Trading-Packages: pandas, numpy, matplotlib, pandas-ta, httpx
- [ ] **1.2:** Sandbox-Manager in `python-backend/agent/sandbox/`
  - Lifecycle: Create → Execute → Collect Result → Destroy
  - Timeout: 10min default, 30min fuer Backtesting
  - Resource Limits: `{"cpu": "1", "memory": "2Gi"}` default
  - Egress Policy: nur erlaubte Domains (Exchange-APIs, keine beliebigen URLs)
- [ ] **1.3:** `code_execute` LangGraph Tool
  - Agent generiert Code → Tool schickt an Sandbox → Result zurueck
  - Unterstuetzte Sprachen: Python, JavaScript, Bash
  - Consent: `level: confirm` in consent_policy.yaml (User muss Code-Execution bestaetigen)
  - Result: stdout, stderr, files (Charts als Base64), execution_time
- [ ] **1.4:** File Upload Pipeline
  - Backend empfaengt File → `sandbox.files.write_files()` kopiert rein
  - Agent analysiert in Sandbox → Result zurueck ans Backend
  - Backend speichert Result im Hauptprojekt-Filesystem
  - Sandbox wird destroyed → File-Kopie ist weg
- [ ] **1.5:** Playwright Browser Sandbox (→ exec-13 Phase 5 nutzt das)
  - Custom Image mit Chromium + Playwright
  - Isoliert vom Host-Browser und Host-Netzwerk
  - Fuer JS-heavy Seiten, Research Reports, News Scraping

### docker-compose Service

```yaml
  # ── OpenSandbox Server (Code Execution, exec-12) ─────────────────────────
  opensandbox:
    image: opensandbox/server:latest
    container_name: opensandbox
    ports:
      - "8100:8100"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./sandbox-config.toml:/etc/opensandbox/config.toml:ro
    environment:
      - OPEN_SANDBOX_API_KEY=dev-sandbox-key
    restart: unless-stopped
    profiles:
      - sandbox
```

Starten: `docker-compose --profile sandbox up opensandbox`
Braucht Docker Socket Mount fuer Container-in-Container Lifecycle.

## Phase 2: Security Hardening (pentagi Patterns)

- [x] **2.1:** Structured Audit Logs ✅ (31.03.2026, Alembic-Update 31.03.2026, Wiring 31.03.2026)
  - `agent/audit/` Package: `logger.py` (structured events), `store.py` (PG + JSON Lines)
  - AuditAction Enum: LLM_REQUEST/RESPONSE, TOOL_CALL/RESULT, CONSENT_REQUEST/DECISION, RATE_LIMIT_HIT
  - Legacy `APPROVAL_REQUEST`/`APPROVAL_DECISION` Enum-Werte entfernt (AL-5)
  - `llm_node.py` extrahiert Token-Counts aus Provider-Response und loggt sie (AL-1)
  - `approval_node.py` loggt CONSENT_DECISION fuer alle Pfade: auto_allow, hard_deny, inform_allow, confirm
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
  - Legacy-Loop (`loop.py`) geloescht — `agent/graph/runner.py` ist einziger Entry-Point
  - `AGENT_USE_LANGGRAPH` ENV entfernt (immer LangGraph)
  - Audit-Integration: CONSENT_REQUEST + CONSENT_DECISION Events fuer alle Pfade
- [x] **2.3:** Rate-Limiting pro Tool/Agent/Session ✅ (31.03.2026)
  - `consent_policy.yaml` erweitert um `rate_limits` Section — Single Source of Truth
  - `consent/rate_limiter.py` — `SessionRateLimiter` mit per-tool counter + session token budget
  - Per-Tool Call Limits: `per_tool: { sandbox_execute: { max_calls: 5 } }`
  - Per-Session Total: `max_tool_calls_total: 50`, `max_tokens_per_session: 100000`
  - Grace Termination (pentagi): Warnung N Iterationen vor Hard-Stop
  - Rate Limiter in `check_consent()` eingehaengt (vor Provider-Check)
  - `tool_node.py` records Tool-Calls im Rate Limiter nach Execution
  - **Wiring-Fixes (31.03.2026):**
    - `llm_node.py` → `record_tokens()` nach jedem LLM-Call (RL-2)
    - `_increment_iteration()` → `record_iteration()` pro Graph-Iteration (RL-3)
    - Grace Warning propagiert durch `ConsentDecision.metadata` → System-Message an LLM (RL-4/CS-5)
  - **Konsolidierung bestehender Config:**
    - `MAX_ITERATIONS` (agent_graph.py) → YAML mit ENV-Fallback
    - `TOOL_TIMEOUT_SEC` (tool_node.py) → YAML mit ENV-Fallback
    - Loop Detection Thresholds (loop_detection.py) → YAML mit hardcoded Fallback
    - `middleware/guardrails.py` geloescht (redundant mit consent/)
- [x] **2.4:** Input/Output Sanitization ✅ (31.03.2026)
  - `agent/middleware/sanitizer.py` — Zentrales Modul mit 4-Layer Defense Stack
  - **P0: XML Content Tagging** (structural isolation, zero compute)
    - Tool-Outputs in `<tool_output source="..." trusted="false">` gewrappt
    - System-Prompt-Instruktion injiziert: untrusted Blocks = Daten, nicht Instruktionen
    - `runner.py` → `_prepare_system_prompt()` haengt `SYSTEM_PROMPT_INJECTION` an
  - **P1: Regex Pre-Filter** (~20 Pattern-Gruppen, case-insensitive)
    - Erkennt: instruction override, role manipulation, system prompt extraction,
      delimiter manipulation, tool/action manipulation, data exfiltration, encoding evasion
    - Multi-lingual: DE/FR/IT Patterns
    - Nur fuer high-risk Tools (web_search, browser, email etc.)
    - Warning-Prefix in LLM-Content bei Detection
  - **P2: ProtectAI DeBERTa-v3 Prompt Injection v2** (ML Classifier, CPU-only, ~180MB)
    - `protectai/deberta-v3-base-prompt-injection-v2` (nicht gated, kein HF Login)
    - Ersetzt meta-llama/Prompt-Guard-86M (gated, Login erforderlich)
    - 2 Labels: SAFE/INJECTION, DeBERTa-v3-base fine-tuned
    - Lazy-loaded, optional — graceful degradation wenn nicht installiert
    - Nur fuer high-risk Tools, threshold 0.85, hard-block bei 0.95+
    - `scripts/download-promptguard.py` — Download-Script mit skip-if-exists + Quick Test
    - Installiert + getestet: 100% Detection auf Standard-Injection-Proben
  - **P3: Output Anomaly Scan** (Exfiltration Detection)
    - Agent-Response auf suspicious URLs (ngrok, webhook.site etc.), IP-URLs,
      Base64-Blobs, API-Key Patterns, Bearer Tokens, Markdown Image Exfiltration gescannt
    - `runner.py` → vor SSE-Streaming der finalen Antwort
  - **Verdrahtung:**
    - `tool_node.py` → `sanitize_input()` Pipeline nach `tool.execute()`, vor LLM-Message
    - `runner.py` → `scan_output_anomalies()` auf finale Agent-Antwort
    - `runner.py` → Security-Instruktion im System-Prompt
  - **Tool Risk Classification:**
    - HIGH_RISK: web_search, http_request, browser_*, email_read, rss_feed, scrape_url
    - LOW_RISK: memory_*, list_tools, get_portfolio (trusted internal, P1/P2 skipped)
  - OWASP LLM01:2025 konform: Privilege Min ✅, HITL ✅, Structural Separation ✅, Content Tagging ✅, Filtering ✅
- [x] **2.5:** Prompt Template Validation ✅ (01.04.2026)
  - `agent/middleware/template_validator.py` — AST-basierte Validation (pentagi Pattern)
  - Allowlist erlaubter Variablen nach Kategorie: session, market, agent, memory, custom
  - Dangerous Pattern Detection: password/secret/key Zugriffe, Jinja2 Code-Blocks, Function Calls
  - `validate_template()` → `ValidationResult` mit errors/warnings/unauthorized_variables
  - `render_template()` → validiert + rendert in einem Schritt (returns None bei Fehler)
  - Vorbereitet fuer Frontend: User-definierte Prompt-Templates/Agent-Personas
  - Max Template Length: 10.000 Zeichen (DoS-Schutz)
- [x] **2.6:** Role Forwarding (Gateway-RBAC Durchreichung) ✅ (01.04.2026)
  - Kein eigenes RBAC — nutzt tradeview-fusion Rollen (viewer/analyst/trader/admin)
  - `X-User-Role` + `X-Auth-User` Headers aus Go Gateway → `AgentExecutionContext.user_role`
  - `app.py` liest Header aus FastAPI `Request` Objekt
  - Durchgereicht: Context → runner.py → AgentGraphState → approval_node → check_consent
  - `ConsentRequest.user_role` Feld hinzugefuegt
  - `ToolConsentConfig.min_role` in consent_policy.yaml — minimale User-Rolle pro Tool
  - `ROLE_HIERARCHY` in config.py — hierarchischer Level-Vergleich (1=viewer → 4=admin)
  - `role_meets_minimum()` Check im YamlPolicyProvider vor Consent-Evaluation
  - Bei unzureichender Rolle: `ConsentLevel.DENY` mit Grund-Message
- [x] **2.7:** Installer Hardening ✅ (01.04.2026)
  - `scripts/harden-env.py` — ersetzt Default-Credentials in .env (pentagi Pattern)
  - Idempotent: nur bekannte Default-Werte werden ersetzt (devkey, changeme etc.)
  - Backup: .env → .env.bak vor Aenderungen
  - `--dry-run` Flag zeigt Aenderungen ohne zu schreiben
  - Generiert: alphanumeric (24/36 chars), hex (32/64 chars), URL-safe tokens
  - Betrifft: LIVEKIT_API_KEY/SECRET, MATRIX_BOT_PASSWORD
  - Ueberspringt: API Keys die User selbst setzen muss (ANTHROPIC_API_KEY etc.)
  - **TODO:** Integration in Setup-Docs/Scripts spaeter spezifizieren (eigener Spec, nicht hier)

## Phase 3 + 4: → verschoben nach exec-13

Playwright MCP, WebMCP, Anthropic Computer Use und Artifacts UI wurden nach
[exec-13-ui-kg-extensions.md](exec-13-ui-kg-extensions.md) verschoben (01.04.2026).
Diese Features gehoeren thematisch zu UI/Extensions, nicht zu Sandbox/Security.

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

### Phase 1: OpenSandbox
- [ ] OpenSandbox Server laeuft als docker-compose Service
- [ ] `code_execute` Tool: Agent generiert Python-Code → Sandbox fuehrt aus → Result zurueck
- [ ] Consent: User muss Code-Execution bestaetigen (level: confirm)
- [ ] Timeout: Sandbox wird nach TTL automatisch destroyed
- [ ] Resource Limits: CPU/Memory pro Sandbox enforced
- [ ] Filesystem-Isolation: Agent kann nur innerhalb Sandbox-Container Dateien erstellen
- [ ] Egress Policy: nur erlaubte Domains erreichbar
- [ ] File Upload: Backend kopiert File in Sandbox, holt Result, Sandbox destroyed
- [ ] Custom Docker Image: Trading-Packages (pandas, numpy, matplotlib, pandas-ta) vorinstalliert

### Phase 2: Security Hardening
- [x] Audit Log: Jede Agent-Action ist nachvollziehbar geloggt (2.1) ✅
- [x] Audit Coverage: CONSENT_DECISION fuer alle Pfade (auto_allow, hard_deny, inform_allow, confirm) ✅
- [x] Audit Token-Tracking: LLM Token-Usage wird extrahiert und geloggt ✅
- [x] Consent Flow: Sensitive Tool-Call zeigt Consent-Dialog, wartet auf User-Bestaetigung (2.2) ✅
- [x] Consent Levels: none/inform/confirm/deny funktionieren korrekt ✅
- [x] Session Cache: allow_session/deny_session werden pro Thread gecacht ✅
- [x] Rate Limit: Agent wird nach N Tool-Calls pro Session gestoppt (2.3) ✅
- [x] Token Budget: Session wird nach N Tokens gestoppt ✅
- [x] Grace Warning: LLM bekommt System-Message N Iterationen vor Hard-Stop ✅
- [x] Iteration Tracking: record_iteration() wird pro Graph-Iteration aufgerufen ✅
- [x] Sanitization P0: Tool-Outputs in XML-Tags mit trust-Level gewrappt (2.4) ✅
- [x] Sanitization P0: System-Prompt enthaelt Security-Instruktion gegen Injection ✅
- [x] Sanitization P1: Regex erkennt bekannte Injection-Patterns in high-risk Tool-Outputs ✅
- [x] Sanitization P2: ML-Classifier (DeBERTa) erkennt Injection in high-risk Tool-Outputs ✅
- [x] Sanitization P2: Hard-Block bei Score >= 0.95, Warning bei >= 0.85 ✅
- [x] Sanitization P3: Agent-Output wird auf Exfiltration gescannt (URLs, Base64, Credentials) ✅
- [x] Legacy Cleanup: loop.py geloescht, runner.py ist einziger Entry-Point ✅
- [x] Template Validation 2.5: Prompt-Templates auf erlaubte Variablen geprueft (AST-Parse) ✅
- [x] Template Validation 2.5: Dangerous Patterns (password, secret, code exec) werden geblockt ✅
- [x] Role Forwarding 2.6: X-User-Role Header aus Gateway in Agent Context ✅
- [x] Role Forwarding 2.6: min_role Check im Consent-System blockiert unzureichende Rollen ✅
- [x] Role Forwarding 2.6: ROLE_HIERARCHY konsistent mit tradeview-fusion proxy.ts ✅
- [x] Installer 2.7: harden-env.py ersetzt Default-Credentials idempotent ✅
- [x] Installer 2.7: --dry-run zeigt Aenderungen ohne zu schreiben ✅

### Phase 3 + 4: → exec-13
- Playwright, WebMCP, Anthropic Computer Use, Artifacts → siehe exec-13-ui-kg-extensions.md

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
