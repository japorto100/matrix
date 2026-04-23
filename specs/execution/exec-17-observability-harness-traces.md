# exec-17: Observability & Agent Harness Traces

**Datum:** 10.04.2026
**Status:** Draft — infrastructure (Stufen 1–5) **LANDED** (`otel-collector.yaml`, `docker-compose.otel.yml`, Python + Go OTel integrated, span taxonomy defined). **Verify-gates pending live `dev-stack.sh --observability` run** to fire end-to-end traces; §4g A/B fitness backfill is live (see changelog 2026-04-20 + 2026-04-23 eval_id wiring). No open design decisions.
**Abhaengig von:** exec-10 (LangGraph Agent), exec-16 (LLM Provider Gateway)

> **ADR-002 (2026-04-23):** Tracing (`agent.spans`) + Audit (`agent.audit_events`) bleiben bewusst parallel. Formeller ADR + `LLM_REQUEST` cross-write-removal in [`docs/superpowers/findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md`](../../docs/superpowers/findings/2026-04-23-adr-002-tracing-audit-parallel-stores.md). `LLM_RESPONSE`/`TOOL_CALL`/`TOOL_RESULT` bleiben (content für 1y compliance). Future-cleanup: per-tool `audit_required: bool` Flag zusammen mit `exec-security` sensitive-tool-Klassifikation.

**Referenzen:**
- Meta-Harness Paper: https://arxiv.org/html/2603.28052v1 (Stanford/KRAFTON/MIT)
- Meta-Harness Artifact: https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact
- tradefusion OTel Setup: `tradeview-fusion/python-backend/shared/app_factory.py`, `go-backend/internal/telemetry/`
- tradefusion DevStack: `tradeview-fusion/scripts/dev-stack2.ps1` (OpenObserve Section)
- OpenObserve: https://openobserve.ai/docs
- Langfuse: https://langfuse.com/docs (LLM-spezifische Observability)
- PentAGI Observability: `_ref/pentagi/backend/pkg/observability/` (Langfuse + OTel Go-Client)
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/

---

## Warum

Unser Agent-System (LangGraph Multi-Agent, Memory Engine, MCP Tools, NATS Bridge) laeuft,
aber wir haben **keine strukturierte Sicht** auf was passiert:
- Welche Prompts gehen raus, welche Responses kommen zurueck?
- Welche Tools werden aufgerufen, wie lange dauern sie, schlagen sie fehl?
- Welche Memory-Retrievals passieren, wie relevant sind die Ergebnisse?
- Was kostet ein Agent-Turn? Welcher Provider/Model performt besser?

### Meta-Harness Insight

Die Stanford-Studie "Meta-Harness: End-to-End Optimization of Model Harnesses" zeigt:

> **Voller Zugang zu Execution Traces** (nicht nur Scores) ermoeglicht dramatisch bessere
> Harness-Optimierung. Der Proposer liest median 82 Files pro Iteration — 41% Source Code,
> 40% Execution Traces, 6% Scores. Traces sind genauso wichtig wie der Code selbst.

Fuer uns heisst das: Wenn wir strukturierte Agent-Traces sammeln, koennen wir spaeter
(manuell oder automatisiert) unseren gesamten Agent-Harness systematisch verbessern —
Prompts, Tool-Configs, Retrieval-Strategien, Routing.

### Ziel

1. **Infra-Observability** — OTel Traces/Metrics/Logs fuer alle Services (Go + Python)
2. **Agent-Traces** — Strukturierte Execution Traces pro Agent-Session (Turns, Tools, Memory, LLM)
3. **LLM Observability** — Langfuse fuer Prompt/Response Tracking, Cost, Latency per Model
4. **MCP Exposition** — Traces als MCP-Tool exponieren fuer Live-Analyse via Claude Code
5. **Harness Feedback Loop** — Grundlage fuer Meta-Harness-artigen Optimierer

### Ist-Zustand

| Feature | Status |
|---------|--------|
| tradefusion Go OTel (Traces + Metrics) | Vorhanden in `go-backend/internal/telemetry/` |
| tradefusion Python OTel (`app_factory.py`) | Vorhanden — Traces + Metrics + Logs Bridge |
| tradefusion OpenObserve + devstack2 | Vorhanden in `tools/openobserve/`, `scripts/dev-stack2.ps1` |
| tradefusion `otel-collector.yaml` | Vorhanden — mit Langfuse Fan-Out vorbereitet |
| tradefusion `flight_recorder.go` | Vorhanden in `go-backend/internal/observability/` |
| matrix python-backend OTel | ✅ Stufe 1.4 — `shared/app_factory.py` zentral |
| matrix go-appservice OTel | ✅ Stufe 1.5 — `internal/telemetry/` + main.go init |
| matrix devstack2 OpenObserve | ✅ Stufe 1.3 — Port 5080, `$SkipObservability` |
| matrix otel-collector.yaml | ✅ Stufe 1.2 — mit Langfuse Fan-Out vorbereitet |
| matrix docker-compose.otel.yml | ✅ Stufe 1.2 — OpenObserve + Collector |
| matrix .env OTel Vars | ✅ Stufe 1.6 — Python + Go Env-Dateien |
| Agent Execution Traces (strukturiert) | ❌ Nicht vorhanden (Stufe 2) |
| Langfuse Integration | ❌ Nicht vorhanden (Stufe 3) |
| MCP Trace Tool | ❌ Nicht vorhanden (Stufe 4) |
| Trace2Skill (exec-10) | Angelegt in `agent/skills/evolver.py` |

---

## Architektur

```
┌────────────────────────────────────────────────────────────────┐
│                        Agent Session                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ LLM Call  │  │ Tool Call│  │ Memory   │  │ NATS Bridge  │  │
│  │ Span      │  │ Span     │  │ Retrieval│  │ Span         │  │
│  │           │  │          │  │ Span     │  │              │  │
│  └─────┬─────┘  └─────┬────┘  └────┬─────┘  └──────┬───────┘  │
│        └───────────────┴───────────┴────────────────┘          │
│                         │ OTel Spans                           │
└─────────────────────────┼──────────────────────────────────────┘
                          ▼
              ┌───────────────────────┐
              │  OTel Collector       │
              │  (otel-collector.yaml)│
              └───────┬───────┬───────┘
                      │       │
           ┌──────────┘       └──────────┐
           ▼                             ▼
┌────────────────────┐       ┌────────────────────┐
│  OpenObserve       │       │  Langfuse          │
│  :5080             │       │  (Cloud/Self-Host) │
│                    │       │                    │
│  Infra Traces      │       │  LLM Traces        │
│  Metrics           │       │  Prompt/Response    │
│  Logs              │       │  Cost/Latency       │
└────────────────────┘       └─────────┬──────────┘
                                       │
                             ┌─────────▼──────────┐
                             │  MCP Trace Tool     │
                             │  (fuer Claude Code) │
                             │                     │
                             │  trace_list()       │
                             │  trace_detail()     │
                             │  trace_search()     │
                             │  trace_compare()    │
                             └─────────────────────┘
```

---

## Stufe 1: OTel Infra aus tradefusion portieren

Portiert die bestehende OTel-Infrastruktur aus tradefusion nach matrix.
Kein neuer Code — nur kopieren, anpassen, devstack integrieren.

### 1.1 OpenObserve Tool kopieren

- [x] `tradeview-fusion/tools/openobserve/openobserve.exe` → `matrix/tools/openobserve/openobserve.exe`
- [x] `matrix/tools/openobserve/data/` Verzeichnis erstellt
- [x] `.gitignore` updated: `tools/openobserve/data/` (binary via `*.exe` bereits ignoriert)

### 1.2 OTel Collector Config + Docker Compose

- [x] `matrix/otel-collector.yaml` erstellt (aus tradefusion portiert)
  - Receivers: OTLP gRPC (4317) + HTTP (4318)
  - Exporters: OpenObserve (5080) + Langfuse (auskommentiert, Stufe 3)
  - Processors: batch (1s/1024) + memory_limiter (512MiB)
- [x] `matrix/docker-compose.otel.yml` erstellt
  - OpenObserve (5080/5081) + OTel Collector (4317/4318)

### 1.3 devstack2.ps1 updaten

- [x] `$SkipObservability` Parameter hinzugefuegt
- [x] OpenObserve Service-Registration (Port 5080, Tier infra)
  - `Ensure-ToolAvailable` fuer Auto-Download v0.14.7
  - Env-Vars: `ZO_ROOT_USER_EMAIL`, `ZO_ROOT_USER_PASSWORD`, `ZO_DATA_DIR`, `ZO_GRPC_PORT=5081`
  - OTel Env-Vars fuer downstream Services: `OTEL_ENABLED=true`, `OTEL_EXPORTER_OTLP_ENDPOINT`
- [x] Dashboard-Link in Startup-Ausgabe: `OpenObserve: http://localhost:5080`

### 1.4 Python-Backend OTel integrieren

- [x] `shared/app_factory.py` — zentraler OTel-Block portiert (aus tradefusion)
  - Traces: `TracerProvider` + `BatchSpanProcessor` + `OTLPSpanExporter` (gRPC)
  - Auto-Instrumentation: `FastAPIInstrumentor` + `HTTPXClientInstrumentor`
  - Metrics: `MeterProvider` + `PeriodicExportingMetricReader`
  - Logs Bridge: `LoggerProvider` + `LoggingHandler`
  - OpenObserve Basic Auth via `OPENOBSERVE_USER`/`PASSWORD`
  - Alles in try/except fuer graceful degradation
  - Jeder Service der `create_service_app()` nutzt bekommt OTel automatisch
- [x] OTel Dependencies in `pyproject.toml` + `uv sync` ausgefuehrt:
  ```
  opentelemetry-api>=1.25.0, opentelemetry-sdk>=1.25.0,
  opentelemetry-exporter-otlp-proto-grpc>=1.25.0,
  opentelemetry-instrumentation-fastapi>=0.46b0,
  opentelemetry-instrumentation-httpx>=0.46b0
  ```
- [x] Ruff check + format sauber

### 1.5 Go-Backend OTel

- [x] `go-appservice/internal/telemetry/` Package erstellt (aus tradefusion portiert):
  - `auth.go` (37 Zeilen) — `stripScheme()` + `otelHeaders()` Basic Auth
  - `tracer.go` (52 Zeilen) — `InitTracerProvider` OTLP gRPC
  - `metrics.go` (43 Zeilen) — `InitMeterProvider` OTLP gRPC
  - `logger.go` (113 Zeilen) — `InitLogProvider` + fanout handler (stdout JSON + OTel)
  - `telemetry_test.go` (195 Zeilen) — alle Tests bestanden
- [x] `go-appservice/cmd/appservice/main.go` — OTel Init hinzugefuegt
  - Guarded: `if os.Getenv("OTEL_ENABLED") == "true"`
  - TracerProvider + MeterProvider + LogProvider mit defer Shutdown
- [x] `go mod tidy` — OTel Go Dependencies installiert
- [x] `golangci-lint run` — 0 Issues
- [x] `go build -tags goolm ./cmd/appservice/...` — erfolgreich

### 1.6 ENV Variablen

- [x] `python-backend/.env.example` — OTel Section hinzugefuegt
- [x] `python-backend/.env` — OTel Vars hinzugefuegt (OTEL_ENABLED=false default)
- [x] `go-appservice/.env.development` — OTel Vars hinzugefuegt

### 1.7 Verify (ausstehend — erfordert DevStack-Run)

- [ ] DevStack starten → OpenObserve auf `:5080` erreichbar
- [ ] `OTEL_ENABLED=true` setzen → Agent-Chat Message senden → Traces in OpenObserve
- [ ] `OTEL_ENABLED=false` → keine Traces, kein Overhead

---

## Stufe 2: Agent Execution Traces (Custom Spans)

Strukturierte Spans fuer Agent-spezifische Operationen. Das ist der Meta-Harness-relevante
Layer — nicht nur Infra-Latency sondern **was der Agent tut und warum**.

### 2.1 Agent Turn Span

Pro LangGraph-Knoten ein Span mit:
```
span.name = "agent.turn"
span.attributes = {
  "agent.session_id":    "uuid",
  "agent.role":          "technical_analyst",
  "agent.turn_number":   3,
  "agent.node":          "llm_node",
  "llm.model":           "claude-sonnet-4-6",
  "llm.provider":        "anthropic",
  "llm.prompt_tokens":   1240,
  "llm.response_tokens": 380,
  "llm.cost_usd":        0.0048,
  "llm.latency_ms":      1850,
  "llm.system_prompt":   "<hash oder erste 200 chars>",
}
span.events = [
  { "name": "prompt",  "body": "<full system + user prompt>" },
  { "name": "response", "body": "<full LLM response>" },
]
```

### 2.2 Tool Call Span

Pro Tool-Aufruf ein Child-Span:
```
span.name = "agent.tool_call"
span.attributes = {
  "tool.name":        "market_data_fetch",
  "tool.type":        "mcp" | "builtin" | "skill",
  "tool.input_size":  456,
  "tool.output_size": 1200,
  "tool.duration_ms": 320,
  "tool.success":     true,
  "tool.error":       null,
}
```

### 2.3 Memory Retrieval Span

Pro Memory-Zugriff:
```
span.name = "agent.memory_retrieval"
span.attributes = {
  "memory.type":        "episodic" | "kg" | "vector" | "hindsight",
  "memory.query":       "BTE divergence pattern",
  "memory.results":     5,
  "memory.top_score":   0.87,
  "memory.latency_ms":  45,
  "memory.tokens_used": 800,
}
```

### 2.4 Session Summary Span

Pro kompletter Agent-Session (Root-Span):
```
span.name = "agent.session"
span.attributes = {
  "session.id":          "uuid",
  "session.user_id":     "@user:matrix.local",
  "session.source":      "matrix_mention" | "agent_chat" | "api",
  "session.total_turns": 5,
  "session.total_tools": 3,
  "session.total_tokens": 4200,
  "session.total_cost":  0.015,
  "session.duration_ms": 8500,
  "session.outcome":     "completed" | "error" | "timeout",
}
```

### 2.5 Implementierung

- [x] `python-backend/agent/tracing.py` — Neues Modul mit Context-Manager Helpers
  - `session_span(session_id, user_id, source, role)` — Root-Span
  - `turn_span(node_name, model, turn_number)` — LangGraph-Knoten
  - `tool_span(tool_name, tool_type)` — Einzelner Tool-Call
  - `memory_span(memory_type, query)` — Memory Recall/Retain
  - `set_session_summary(span, total_turns, total_tokens, outcome)` — Post-Session
  - NoopTracer wenn OTEL_ENABLED=false (zero overhead)
- [x] `agent/graph/runner.py` (`_run_graph`): `agent.session` Root-Span
  - Attributes: thread_id, user_id, total_turns, total_tokens, outcome
- [x] `agent/graph/runner.py` (`_prepare_system_prompt`): `agent.turn` Span
  - Trackt Prompt-Construction: Skills, Temporal Context, Pre-Memory Recall
  - Attributes: prompt.length
- [x] `agent/graph/nodes/llm_node.py`: `agent.turn` Span um LLM-Call
  - Attributes: model, iteration, prompt_tokens, completion_tokens, token_usage, tool_calls_count
- [x] `agent/graph/nodes/approval_node.py`: `agent.turn` Span um Consent Gate
  - Attributes: approval.total, approval.approved, approval.denied
  - Trackt ob/warum Tools geblockt wurden (kritisch fuer Harness-Analyse)
- [x] `agent/graph/nodes/tool_node.py` (`_execute_single`): `agent.tool_call` Span
  - Attributes: tool_name, tool_type (mcp/builtin), duration_ms, success, error
- [x] `agent/graph/nodes/memory_node.py` (recall): `agent.memory` Span
  - Attributes: type=hindsight_recall, query, results, entities, tokens_used
- [x] `agent/graph/nodes/memory_node.py` (retain): `agent.memory` Span
  - Attributes: type=hindsight_retain, content_length, conflict
- [x] Ruff check + format: sauber

### 2.6 Span-Abdeckung (Graph Flow)

```
START
  └── prepare_system_prompt [agent.turn]  ← Skills, Temporal, Pre-Memory
       └── memory_recall [agent.memory]   ← Hindsight Recall
            └── llm_call [agent.turn]     ← LLM Request/Response
                 └── approval_gate [agent.turn]  ← Consent Check
                      └── tool_execute            (Wrapper-Node)
                           ├── tool_1 [agent.tool_call]
                           └── tool_2 [agent.tool_call]
                      └── increment               (kein Span, trivial)
                           └── llm_call → ... (Loop)
            └── memory_retain [agent.memory]  ← Hindsight Retain
END

Alles gewrappt in: agent.session [Root-Span]
```

### 2.7 Verify (ausstehend — erfordert DevStack-Run)

- [ ] Agent-Session → OpenObserve zeigt verschachtelte Spans:
  ```
  agent.session (8.5s)
    ├── agent.turn [prepare_system_prompt] (200ms)
    ├── agent.memory [hindsight_recall] (45ms)
    ├── agent.turn [llm_call] (2.1s)
    │   model=claude-sonnet, tokens=1620
    ├── agent.turn [approval_gate] (5ms)
    │   approved=2, denied=0
    ├── agent.tool_call [market_data_fetch] (320ms)
    │   success=true
    ├── agent.tool_call [chart_analysis] (180ms)
    │   success=true
    ├── agent.turn [llm_call] (1.8s)
    │   model=claude-sonnet, tokens=980
    └── agent.memory [hindsight_retain] (30ms)
  ```

---

## Stufe 3: Langfuse LLM Observability

Langfuse ist spezialisiert auf LLM-Traces — Prompt/Response Paare, Cost-Tracking,
Evaluations. Ergaenzt OpenObserve (Infra) um den AI-spezifischen Layer.

### 3.1 Architektur-Entscheidungen

- [x] **PentAGI Langfuse Client evaluiert** (`_ref/pentagi/backend/pkg/observability/langfuse/`)
  - Massiver auto-generated Go SDK (20+ Files) — zu heavyweight fuer uns
  - PentAGI nutzt Dual-Strategy: OTel SDK (infra) + Langfuse Direct API (LLM)
  - Entscheidung: Wir nutzen **nicht** den PentAGI Go-Client
- [x] **Strategie festgelegt:**
  - Primaer: OTel Collector Fan-Out zu Langfuse (alle Spans automatisch, nur Config)
  - Sekundaer: Langfuse Python SDK nur fuer LLM-spezifische Enrichments (`track_generation`)
  - `track_generation()` ist in `agent/tracing.py` (`AgentSpan`) zentralisiert
  - Nur `llm_node.py` ruft `span.track_generation()` auf — Langfuse ist LLM-spezifisch,
    Tool/Memory Spans gehen automatisch via OTel Fan-Out zu Langfuse

### 3.2 Langfuse Account (TODO — manueller Schritt)

- [ ] **Langfuse Cloud Account erstellen** auf https://cloud.langfuse.com (Free Tier: 50k Observations/Monat)
  - Kein Self-Host: Langfuse hat kein natives Windows Binary, braucht Docker (PG + ClickHouse + Redis + MinIO)
  - Cloud Free Tier genuegt fuer Entwicklung
  - Self-Hosted spaeter moeglich wenn Docker im Stack
- [ ] API Keys generieren: Settings → API Keys → Public Key + Secret Key
- [ ] Keys in `python-backend/.env` eintragen:
  ```
  LANGFUSE_ENABLED=true
  LANGFUSE_PUBLIC_KEY=pk-lf-...
  LANGFUSE_SECRET_KEY=sk-lf-...
  LANGFUSE_HOST=https://cloud.langfuse.com
  ```

### 3.3 OTel Collector Fan-Out (aktivieren nach Account)

- [ ] `otel-collector.yaml`: Langfuse Exporter Block uncommentieren + Keys eintragen
- [ ] Traces Pipeline: `exporters: [otlphttp/openobserve, otlphttp/langfuse]`
- [ ] Damit fliessen ALLE OTel Spans (Sessions, Tools, Memory) automatisch zu Langfuse

### 3.4 Implementierung

- [x] `agent/tracing.py` — `AgentSpan` Wrapper vereint OTel + Langfuse
  - `track_generation()` setzt OTel Attributes UND ruft Langfuse SDK auf
  - Nodes nutzen nur `span.track_generation(...)` — wissen nicht ob Langfuse aktiv
- [x] `agent/langfuse_tracker.py` — Thin Python SDK Wrapper
  - Lazy singleton via `@lru_cache`
  - No-Op wenn `LANGFUSE_ENABLED != true`
  - `track_generation(name, model, input, output, usage, metadata)`
  - `flush()` fuer Shutdown
- [x] `agent/graph/nodes/llm_node.py` — nutzt `span.track_generation()`
  - Kein direkter Langfuse-Import, alles ueber AgentSpan
- [x] `pyproject.toml` — `langfuse>=2.40.0` + `uv sync` ausgefuehrt
- [x] `.env.example` + `.env` — Langfuse Env-Vars hinzugefuegt
- [x] Ruff check + format: sauber

### 3.5 Verify (ausstehend — erfordert Langfuse Account + DevStack)

- [ ] `LANGFUSE_ENABLED=true` + Keys gesetzt → Agent-Chat senden
- [ ] Langfuse Dashboard zeigt:
  - Prompt/Response pro LLM-Call
  - Token-Counts + Cost pro Model
  - Session-Trace mit verschachtelten Spans (via OTel Fan-Out)

---

## Stufe 4: MCP Trace Exposition + Audit Vervollstaendigung

Traces als MCP-Tool exponieren — damit Claude Code (und spaeter ein Meta-Harness Proposer)
die Traces live inspizieren kann. Plus: Audit Store vervollstaendigen damit alle Agent-Events
aufgezeichnet werden (Memory-Events fehlten, LLM Prompt/Response Text fehlte).

### 4.1 Audit Store Vervollstaendigung

Audit und OTel bleiben **getrennte Systeme** (Audit = persistent + immer aktiv,
OTel = optional + live-observability). Beide tracken dieselben Events, aber fuer
unterschiedliche Zwecke.

- [x] Alembic Migration `010_audit_exec17_fields.py`:
  - `iteration` Spalte (Integer, nullable) fuer Graph-Loop Tracking
  - Composite Index `ix_audit_thread_timestamp` fuer schnelle Session-Abfragen
- [x] `agent/audit/store.py` PostgresAuditStore: `iteration` Feld im INSERT
- [x] `agent/graph/nodes/llm_node.py`: Prompt/Response Text in Audit Store
  - `input_data`: letzter User-Message Content (truncated 2000)
  - `output_data`: LLM Response Content (truncated 2000)
- [x] `agent/graph/nodes/memory_node.py`: Memory Audit-Events hinzugefuegt
  - `MEMORY_RECALL`: output=memory_text, metadata={facts_recalled, entities, tokens_used}
  - `MEMORY_RETAIN`: input=content, metadata={content_length, conflict, bank_id, role}

**Audit-Abdeckung aller Graph-Nodes (komplett):**

| Node | Audit Actions | Input/Output | Metadata |
|------|--------------|-------------|----------|
| `llm_node` | `LLM_REQUEST` + `LLM_RESPONSE` | Prompt + Response Text | model, tokens, done |
| `tool_node` | `TOOL_CALL` + `TOOL_RESULT` | Tool Input + Output | duration, success |
| `approval_node` | `CONSENT_DECISION` (3 Pfade) | — | decision, policy_id, reason |
| `memory_node` (recall) | `MEMORY_RECALL` | — + Memory Text | facts, entities, tokens |
| `memory_node` (retain) | `MEMORY_RETAIN` | Content | length, conflict, role |

### 4.2 MCP Trace Server

- [x] `agent/mcp_traces.py` erstellt — FastMCP Server mit 6 Tools:
  - `trace_list(last_n=20)` — Sessions auflisten mit Summary-Stats
  - `trace_detail(thread_id)` — Kompletter Trace: alle Events mit Timestamps, Inputs, Outputs
  - `trace_search(query, last_n=50)` — Freitext-Suche ueber alle Audit-Events
  - `trace_compare(session_a, session_b)` — Zwei Sessions nebeneinander vergleichen
  - `trace_score(thread_id)` — Abgeleitete Quality-Scores (Effizienz, Tool-Success, Cost)
  - `harness_config(role?)` — Aktuelle Agent-Config (Prompts, Tools, Memory, Consent, Graph)
- [x] Datenquelle: Audit Store (JSONL/PostgreSQL) — direkt, kein OpenObserve API
- [x] Standalone-Modus: `uv run python -m agent.mcp_traces` (Port 8096)

### 4.3 Integration

- [x] `agent/app.py`: Gemountet unter `/mcp-traces` (Port 8094, kein eigener Port)
- [x] `.mcp.json`: `"matrix-traces"` Eintrag mit URL Transport
  - `http://127.0.0.1:8094/mcp-traces/mcp`
- [x] Kein devstack2.ps1 Eintrag noetig — Teil des Agent Service
- [x] Ruff check + format: sauber

### 4.4 Verify (ausstehend — erfordert DevStack-Run)

- [ ] Agent Service starten → `/mcp-traces` erreichbar
- [ ] Claude Code: `trace_list()` → Sessions sehen
- [ ] Claude Code: `trace_detail(thread_id)` → Prompts/Responses/Tools inspizieren
- [ ] Claude Code: `trace_search("error")` → Probleme finden
- [ ] Claude Code: `trace_score(thread_id)` → Session-Qualitaet bewerten
- [ ] Claude Code: `harness_config()` → Agent-Setup inspizieren
- [ ] Standalone: `uv run python -m agent.mcp_traces` auf :8096

---

## Stufe 5: Harness Feedback Loop (Meta-Harness Light)

LLM-basierter Proposer der Execution Traces analysiert und Harness-Verbesserungen
vorschlaegt. Funktioniert mit Claude Code (manuell) ODER automatisch via API LLM.

### 5.1 Architektur

```
┌──────────────────────────────────────────────────────┐
│  Harness Proposer (agent/harness/proposer.py)        │
│                                                      │
│  1. Liest: Harness Config + Traces + Scores          │
│  2. Sendet an LLM: "Was laeuft schlecht?"            │
│  3. LLM analysiert Muster und schlaegt Aenderungen   │
│  4. Speichert Proposal in data/harness/candidates/   │
│                                                      │
│  Aufrufe:                                            │
│  - MCP Tool: harness_propose() via Claude Code       │
│  - Standalone: uv run python -m agent.harness.proposer│
│  - API: jedes LLM via LiteLLM                        │
└──────────────────────────────────────────────────────┘
```

Meta-Harness Drei-Saeulen Mapping:
- **Source Code** (41% der Reads) → `harness_config()` MCP Tool + `harness/config.py`
- **Execution Traces** (40% der Reads) → `trace_detail/search()` + Audit Store
- **Scores** (6% der Reads) → `trace_score()` + `harness/scorer.py`

### 5.2 Implementierung

- [x] `agent/harness/__init__.py` — Package mit Docstring + Modul-Uebersicht
- [x] `agent/harness/config.py` — `HarnessConfig` Dataclass
  - `capture_current_config()` → Snapshot von roles, tools, memory, consent, graph
  - `to_json()` / `from_json()` / `save()` / `load()` fuer Serialisierung
- [x] `agent/harness/scorer.py` — Session-Scoring aus Audit-Daten
  - `score_session(thread_id)` → turn_efficiency, tool_success_rate, token_efficiency,
    memory_utilization, cost_estimate_usd, completion_rate
  - `score_sessions(thread_ids)` → Batch-Scoring
  - Model-basierte Cost-Estimation (claude-sonnet $6/Mtok, haiku $1/Mtok, etc.)
- [x] `agent/harness/proposer.py` — LLM-basierter Proposer
  - `propose(model?, last_n_sessions=10)` → Analyse + Vorschlaege
  - Nutzt `get_litellm_client()` → funktioniert mit jedem Provider (Anthropic, OpenAI, etc.)
  - Sammelt Context: Config + Traces + Scores (truncated fuer LLM Context Window)
  - System-Prompt instruiert LLM: analysiere Patterns, schlage spezifische Aenderungen vor
  - Speichert Proposals in `data/harness/candidates/v{NNN}/`
  - Standalone: `uv run python -m agent.harness.proposer`

### 5.3 MCP Tools (in mcp_traces.py hinzugefuegt)

- [x] `harness_propose(last_n_sessions=10, model="")` — Proposer ausfuehren via MCP
  - Claude Code oder jeder MCP Client kann den Loop triggern
  - Ergebnis: JSON mit analysis, proposed_changes, expected_improvement
- [x] `harness_history()` — Alle bisherigen Proposals auflisten
  - Zeigt Versionen, Timestamps, Model, Anzahl vorgeschlagener Aenderungen

### 5.4 Harness Filesystem (Meta-Harness Pattern)

- [x] `data/harness/candidates/` — Versionierte Harness-Varianten
  - Pro Variante: `config.json` (Snapshot) + `proposal.json` (LLM-Analyse)
- [x] `data/harness/search_set/queries.json` — Representative Evaluation-Queries
  - 5 Starter-Queries (simple_query, multi_tool, memory_recall, analysis, simple_chat)
  - Erweiterbar — Meta-Harness nutzt ~250 Search-Set Queries

### 5.5 Workflow

**Manuell (Claude Code):**
```
1. Claude Code: harness_propose(last_n_sessions=20)
2. LLM analysiert 20 Sessions, findet: "Agent ruft market_data_fetch auf
   obwohl Info im Memory — in 7/20 Sessions"
3. Vorschlag: "System-Prompt ergaenzen: 'Check memory before using tools'"
4. Proposal gespeichert in data/harness/candidates/v001/
5. Wir reviewen, implementieren die Aenderung in roles.py
6. Naechste harness_propose() zeigt ob es besser wurde
```

**Automatisch (API LLM):**
```
uv run python -m agent.harness.proposer
→ Nutzt AGENT_DEFAULT_UTILITY_MODEL (oder cli --model arg)
→ Proposal in data/harness/candidates/v{NNN}/
→ Kann per Cron/Schedule laufen
```

### 5.6 Verify (ausstehend — erfordert DevStack + Agent-Sessions)

- [ ] Agent laeuft, sammelt Traces in Audit Store
- [ ] `harness_propose()` via MCP → LLM analysiert und schlaegt Aenderungen vor
- [ ] `harness_history()` zeigt gespeicherte Proposals
- [ ] Standalone: `uv run python -m agent.harness.proposer` funktioniert
- [ ] Proposal JSON hat: analysis, proposed_changes (mit target + change + rationale)
- [x] Ruff check + format: sauber

### 5.7 Trace2Skill Verbindung (Future Work)

`agent/skills/evolver.py` und `consolidation_graph.py` (exec-10) nutzen bereits
Trace-Analyse fuer Skill-Generation. Die strukturierten Audit-Events (Phase 4)
liefern die Datenbasis die Trace2Skill braucht.

---

## Zusammenfassung

---

## Stufe 6: Meta-Harness Insights (Studie-Abgleich)

Verbesserungen basierend auf Abgleich mit der Studie (arxiv:2603.28052v1) und dem
TerminalBench-2 Artifact (github.com/stanford-iris-lab/meta-harness-tbench2-artifact).

### 6.1 Evaluator — automatische Search-Set Evaluation

- [x] `agent/harness/evaluator.py` erstellt
  - `evaluate_single(query, system_prompt_override?)` — Agent auf einer Query ausfuehren
  - `evaluate_search_set(max_queries?)` — Alle Search-Set Queries durchlaufen + aggregieren
  - Nutzt isolierte thread_ids pro Evaluation (`eval-{uuid}`)
  - Aggregiert: completion_rate, avg_turns, total_tokens, avg_tool_success_rate, total_cost
- [x] `harness_evaluate` MCP Tool — Evaluation via Claude Code triggerbar

### 6.2 Pareto-Frontier Ranking

Meta-Harness: "maintains a Pareto frontier over evaluated harnesses."
Ein Kandidat ist Pareto-optimal wenn kein anderer in ALLEN Dimensionen besser ist.

- [x] `agent/harness/pareto.py` erstellt
  - `compute_pareto_frontier(candidates)` — Non-dominated Sorting
  - `load_all_candidates()` — Alle scored Candidates aus data/harness/candidates/
  - `get_frontier_summary()` — Frontier mit Stats
  - Dimensionen: completion_rate, turn_efficiency, tool_success_rate, token_efficiency
- [x] `harness_pareto` MCP Tool — Frontier via Claude Code inspizierbar

### 6.3 Anthropic Ephemeral Caching

Direkt aus dem Meta-Harness TerminalBench Artifact (`anthropic_caching.py`).
Spart 60-90% Prompt-Tokens bei Multi-Turn Conversations mit Claude Models.

- [x] `agent/graph/nodes/llm_node.py` — `_apply_anthropic_caching()`
  - Setzt `cache_control: {"type": "ephemeral"}` auf letzten 3 Messages
  - Nur wenn Model "claude" oder "anthropic" im Namen hat
  - Keine Aenderung fuer andere Provider (OpenAI, Gemini, etc.)

### 6.4 Proposer Loop-Modus

Meta-Harness: "~60 harnesses over ~20 iterations"

- [x] `agent/harness/proposer.py` — `propose_loop(iterations, candidates_per_iter)`
  - Mehrere Iterationen automatisch durchlaufen
  - CLI: `uv run python -m agent.harness.proposer --iterations 20 --candidates 2`
- [x] `harness_loop` MCP Tool — Loop via Claude Code triggerbar

### 6.5 Search-Set erweitert

- [x] `data/harness/search_set/queries.json` — 5 Starter-Queries
  - Kategorien: simple_query, multi_tool, memory_recall, analysis, simple_chat
  - Meta-Harness nutzt ~250 — erweiterbar ueber Zeit

### 6.6 Vollstaendige MCP Tool-Liste (11 Tools)

| Tool | Phase | Zweck |
|------|-------|-------|
| `trace_list` | 4 | Sessions auflisten |
| `trace_detail` | 4 | Kompletter Session-Trace |
| `trace_search` | 4 | Freitext-Suche |
| `trace_compare` | 4 | Sessions vergleichen |
| `trace_score` | 4 | Abgeleitete Scores |
| `harness_config` | 4 | Aktuelle Agent-Config |
| `harness_propose` | 5 | LLM-Proposer ausfuehren |
| `harness_history` | 5 | Proposals auflisten |
| `harness_evaluate` | 6 | Search-Set Evaluation |
| `harness_pareto` | 6 | Pareto-Frontier anzeigen |
| `harness_loop` | 6 | Multi-Iteration Loop |

### 6.7 Verify (ausstehend)

- [ ] `harness_evaluate(max_queries=3)` → Agent laeuft gegen Search-Set, Scores zurueck
- [ ] `harness_pareto()` → Frontier nach mehreren Proposals sichtbar
- [ ] `harness_loop(iterations=3)` → 3 Proposals automatisch generiert
- [ ] Anthropic Caching: Token-Savings sichtbar in Audit/OTel Traces
- [x] Ruff check + format: sauber

---

## Zusammenfassung

| Stufe | Was | Status |
|-------|-----|--------|
| **1** | OTel Infra portieren (tools, devstack, Go/Python) | ✅ Komplett |
| **2** | Agent Custom Spans (Turn, Tool, Memory, Session, Approval, Prompt) | ✅ Komplett |
| **3** | Langfuse LLM Observability (SDK + Fan-Out vorbereitet) | ✅ Code komplett, Account TODO |
| **4** | MCP Trace Tools (6 Tools) + Audit Vervollstaendigung | ✅ Komplett |
| **5** | Harness Feedback Loop (Proposer + Scorer + Config + MCP) | ✅ Komplett |
| **6** | Meta-Harness Insights (Evaluator + Pareto + Caching + Loop) | ✅ Komplett |

---

## 2.5 Span-Redaction Hooks (Phase-B P3 stub)

**Status:** STUB — filled in exec-hermes Phase-B P3.
**Owner of redact.py port:** `exec-security.md §1`.
**This spec owns:** the hook-point in `PostgresSpanProcessor.on_end` + `trajectory/exporter.py`.

**Contrarian BLOCKER-1 design:** `PostgresSpanProcessor.on_end` (current `agent/tracing.py:255`) is sync-blocking (`with psycopg.connect(...)` sync). Async DB-backed pattern-lookup cannot run in this hook. Solution is **two-tier redact**:

- **Tier 1 (sync regex)** applied in `on_end` before DB INSERT — pure-CPU, 48+ static patterns snapshot-at-import. API: `redact_span_event(event: dict) -> dict`. Emits `audit.redaction_count` span-attribute.
- **Tier 2 (async DB-patterns)** runs in separate background consumer AFTER INSERT — UPDATEs spans in-place. NOT in the sync `on_end` hook. Enabled via `MATRIX_REDACT_CONSUMER_ENABLED=true`.

**Trajectory export hook:** `trajectory/exporter.py::export_to_jsonl` applies Tier-1 redact to every span-row before writing ShareGPT JSONL. Prevents fine-tuning-dataset leakage.

**Admin-bypass:** `GET /api/v1/audit/spans/{id}?raw=true&reason=<string>` returns un-redacted span. Admin-role-gated, reason required, audit-logged as `action=AUDIT_RAW_ACCESS`.

Full pattern-list + migration 023_agent_redaction_patterns filled during P3 implementation.

## Changelog-append (Phase-B)

| Date | Change |
|---|---|
| 2026-04-20 | exec-hermes Phase-B P2 stub added: §2.5 (span-redaction hooks, filled P3). Hook-point owned here, pattern-library owned by exec-security.md. |

Alle 6 Stufen implementiert. 11 MCP Tools. Ausstehend: DevStack Verify-Runs + Langfuse Account.
