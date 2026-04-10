# exec-16: LLM Provider Gateway (LiteLLM + Multi-Provider Routing)

**Datum:** 10.04.2026
**Status:** Geplant
**Abhaengig von:** exec-10 (LangGraph Agent), exec-15 (control-ui ApiModelsTab)
**Referenzen:** LiteLLM Docs, OpenRouter API, Vercel AI SDK Provider Registry

---

## Warum

Aktuell wird der LLM-Provider via ENV-Vars (`AGENT_PROVIDER`, `AGENT_MODEL`) hart konfiguriert.
Ein Wechsel zwischen Anthropic, OpenAI, Gemini, Ollama oder OpenRouter erfordert `.env` Aenderungen
und Neustart. Kein Fallback, kein Cost-Tracking, keine User-Level Model-Auswahl.

### Ziel

1. **Ein Endpoint fuer alle Provider** — LiteLLM Proxy als Gateway
2. **Dynamic Model Selection** — User waehlt Model in UI, Backend routet automatisch
3. **Automatic Fallback** — Provider A down → Provider B uebernimmt transparent
4. **Cost Tracking** — pro User/Session/Model automatisch
5. **API-Key Isolation** — Frontend kennt keine echten Keys

### Ist-Zustand

| Feature | Status |
|---------|--------|
| `AGENT_PROVIDER` ENV Routing (anthropic/openai/openai-compatible/litellm) | ✅ In `llm_node.py` |
| `req.model` Override im Request-Body | ✅ In `app.py` (AC107) |
| `llm_helper.py` fuer Utility-Calls | ✅ Provider-agnostisch |
| control-ui ApiModelsTab (7 Provider gelistet) | ✅ Frontend + Backend |
| Model-Routing per Trading-Rolle | ✅ `models.py` (alle auf Default) |
| OpenRouter als Provider | ❌ Gelistet aber nicht verdrahtet |
| LiteLLM Proxy | ❌ Nicht installiert |
| Dynamic Model Selection (UI → Backend) | ❌ Nur ENV-basiert |
| Fallback/Retry | ❌ Kein Fallback |
| Cost Tracking | ❌ Nicht vorhanden |

---

## Architektur

```
┌──────────────────────┐     ┌─────────────────────┐
│  agent-chat UI       │     │  control-ui          │
│  Model-Dropdown      │     │  ApiModelsTab        │
│  "claude-sonnet"     │     │  Provider Config     │
└──────────┬───────────┘     └──────────┬──────────┘
           │ { model: "claude-sonnet" }  │
           ▼                             │
┌──────────────────────┐                 │
│  Go Gateway (:8090)  │ ← SSE Proxy    │
│  /api/v1/agent/chat  │                 │
└──────────┬───────────┘                 │
           │                             │
           ▼                             │
┌──────────────────────┐                 │
│  Python Agent (:8094)│                 │
│  llm_node.py         │                 │
│  model = req.model   │                 │
└──────────┬───────────┘                 │
           │ OpenAI-compatible API       │
           ▼                             │
┌──────────────────────────────────────────┐
│  LiteLLM Proxy (:4000)                   │
│  config.yaml → Provider Routing          │
│                                          │
│  "claude-sonnet" → Anthropic API         │
│  "gpt-4o"        → OpenAI API           │
│  "gemini-pro"    → Google Vertex         │
│  "local-llama"   → Ollama :11434        │
│  "free-*"        → OpenRouter (free)    │
│                                          │
│  Fallback: Anthropic down → OpenRouter   │
│  Cost Tracking: per user/session         │
└──────────────────────────────────────────┘
```

**Go bleibt reiner SSE-Proxy.** LLM-Routing passiert in LiteLLM, nicht in Go.

---

## Stufe 1: OpenRouter Quick-Start (0 Code, nur ENV)

Fuer sofortiges Verify-Testing ohne LiteLLM Setup.

- [x] **1.1:** OpenRouter Account + API Key ✅ (10.04.2026)

- [ ] **1.2:** `.env` Konfiguration fuer OpenRouter
  ```env
  AGENT_PROVIDER=openai-compatible
  OPENAI_API_KEY=sk-or-v1-<dein-key>
  OPENAI_BASE_URL=https://openrouter.ai/api/v1
  AGENT_MODEL=anthropic/claude-sonnet-4-6
  ```

- [ ] **1.3:** Verify: Agent Chat funktioniert ueber OpenRouter
  - SSE Streaming korrekt
  - Tool-Calls funktionieren
  - Token-Usage wird zurueckgegeben

### OpenRouter Free Models (fuer kostenlose Tests)
- `openrouter/auto` — Automatische Auswahl
- `qwen/qwen3-480b:free` — 480B Parameter, rate-limited
- `meta-llama/llama-3.3-70b-instruct:free`
- `nvidia/llama-3.1-nemotron-ultra-253b:free`
- `devstral/devstral-small:free`
- Rate Limits: ~20 req/min, ~200/Tag

---

## Stufe 2: LiteLLM Proxy im DevStack

### 2.1 LiteLLM Installation (uv, eigene Venv)

LiteLLM laeuft als reiner Python-Prozess — kein Docker noetig.

- [ ] **2.1.1:** Eigene Venv fuer LiteLLM Gateway
  ```
  python-backend/litellm-gateway/
    pyproject.toml          # litellm[proxy] dependency
    .venv/                  # eigene Venv (uv)
    config.yaml             # Model-Liste + Provider-Config
    start.ps1               # Startscript fuer devstack2
  ```

- [ ] **2.1.2:** `pyproject.toml`
  ```toml
  [project]
  name = "litellm-gateway"
  requires-python = ">=3.11"
  dependencies = ["litellm[proxy]"]

  [tool.uv]
  managed = true
  ```

- [ ] **2.1.3:** Installation
  ```bash
  cd python-backend/litellm-gateway
  uv sync
  ```

- [ ] **2.1.4:** Start
  ```bash
  uv run litellm --config config.yaml --port 4000
  ```

### 2.2 config.yaml

- [ ] **2.2.1:** Basis-Config mit allen Providern
  ```yaml
  model_list:
    # ── Anthropic (direkt) ──
    - model_name: "claude-sonnet"
      litellm_params:
        model: "anthropic/claude-sonnet-4-6"
        api_key: "os.environ/ANTHROPIC_API_KEY"
    - model_name: "claude-opus"
      litellm_params:
        model: "anthropic/claude-opus-4-6"
        api_key: "os.environ/ANTHROPIC_API_KEY"
    - model_name: "claude-haiku"
      litellm_params:
        model: "anthropic/claude-haiku-4-5-20251001"
        api_key: "os.environ/ANTHROPIC_API_KEY"

    # ── OpenAI (direkt) ──
    - model_name: "gpt-4o"
      litellm_params:
        model: "openai/gpt-4o"
        api_key: "os.environ/OPENAI_API_KEY"
    - model_name: "gpt-4o-mini"
      litellm_params:
        model: "openai/gpt-4o-mini"
        api_key: "os.environ/OPENAI_API_KEY"

    # ── Google Gemini ──
    - model_name: "gemini-pro"
      litellm_params:
        model: "gemini/gemini-2.5-pro"
        api_key: "os.environ/GEMINI_API_KEY"
    - model_name: "gemini-flash"
      litellm_params:
        model: "gemini/gemini-2.5-flash"
        api_key: "os.environ/GEMINI_API_KEY"

    # ── OpenRouter (Aggregator / Fallback) ──
    - model_name: "claude-sonnet"
      litellm_params:
        model: "openrouter/anthropic/claude-sonnet-4-6"
        api_key: "os.environ/OPENROUTER_API_KEY"
    # ↑ Gleicher model_name wie Anthropic direkt = automatischer Fallback

    - model_name: "openrouter-auto"
      litellm_params:
        model: "openrouter/openrouter/auto"
        api_key: "os.environ/OPENROUTER_API_KEY"

    # ── OpenRouter Free (kostenlose Tests) ──
    - model_name: "free-qwen"
      litellm_params:
        model: "openrouter/qwen/qwen3-480b:free"
        api_key: "os.environ/OPENROUTER_API_KEY"
    - model_name: "free-llama"
      litellm_params:
        model: "openrouter/meta-llama/llama-3.3-70b-instruct:free"
        api_key: "os.environ/OPENROUTER_API_KEY"

    # ── Ollama (lokal, kein API Key) ──
    - model_name: "local-llama"
      litellm_params:
        model: "ollama/llama3.3"
        api_base: "http://localhost:11434"
    - model_name: "local-mistral"
      litellm_params:
        model: "ollama/mistral"
        api_base: "http://localhost:11434"

    # ── vLLM / LM Studio (lokal, OpenAI-kompatibel) ──
    - model_name: "local-vllm"
      litellm_params:
        model: "openai/custom-model"
        api_base: "http://localhost:8000/v1"
        api_key: "dummy"

  # ── General Settings ──
  litellm_settings:
    drop_params: true            # Unbekannte Params ignorieren statt Fehler
    set_verbose: false
    request_timeout: 120         # 2 Minuten Timeout
    num_retries: 2               # 2 Retries bei Fehler
    allowed_fails: 3             # 3 Fehler bevor Provider aus Rotation

  # ── Router Settings (Fallback/Load-Balancing) ──
  router_settings:
    routing_strategy: "simple-shuffle"  # Failover bei gleichem model_name
    enable_pre_call_checks: true
  ```

### 2.3 Python Agent Umstellung

- [ ] **2.3.1:** Agent `.env` auf LiteLLM umstellen
  ```env
  # Vorher:
  # AGENT_PROVIDER=anthropic
  # ANTHROPIC_API_KEY=sk-ant-...

  # Nachher:
  AGENT_PROVIDER=openai-compatible
  OPENAI_API_KEY=sk-litellm-master-key  # Virtual Key von LiteLLM (optional)
  OPENAI_BASE_URL=http://localhost:4000
  AGENT_MODEL=claude-sonnet
  ```

- [ ] **2.3.2:** `llm_helper.py` auf LiteLLM Endpoint umstellen
  - Gleiche Logik, nur `OPENAI_BASE_URL` zeigt auf LiteLLM statt direkt Provider
  - Utility-Calls (Summarization, Skills) nutzen gleichen Endpoint

- [ ] **2.3.3:** Hindsight Memory Engine
  - Hindsight nutzt eigene LLM-Config (`engine.py` setzt ENV vars)
  - Umstellen auf LiteLLM Endpoint fuer Retain/Recall LLM-Calls

### 2.4 DevStack Integration

- [ ] **2.4.1:** `devstack2.ps1` — LiteLLM als Service hinzufuegen
  ```powershell
  # LiteLLM Gateway (Port 4000)
  if (-not $SkipLiteLLM) {
    Push-Location python-backend/litellm-gateway
    uv run litellm --config config.yaml --port 4000 &
    Pop-Location
  }
  ```
  - `-SkipLiteLLM` Flag fuer direkten Provider-Zugriff (Stufe 1 Modus)

- [ ] **2.4.2:** docker-compose Alternative
  ```yaml
  litellm:
    image: litellm/litellm:main-stable
    ports: ["4000:4000"]
    volumes: ["./python-backend/litellm-gateway/config.yaml:/config.yaml:ro"]
    env_file: ./python-backend/.env
    command: --config /config.yaml
    profiles: [litellm]
  ```

### 2.5 .env Master-Template

- [ ] **2.5.1:** Alle Provider-Keys in einer `.env` Datei
  ```env
  # ─── LLM Provider API Keys ───────────────────────────────────────
  # Setze nur die Keys fuer Provider die du nutzen willst.
  # LiteLLM routet automatisch zum richtigen Provider.

  ANTHROPIC_API_KEY=               # Anthropic Claude (direkt)
  OPENAI_API_KEY=                  # OpenAI GPT (direkt)
  GEMINI_API_KEY=                  # Google Gemini
  OPENROUTER_API_KEY=              # OpenRouter (Aggregator, Free Tier)
  # AZURE_API_KEY=                 # Azure OpenAI (optional)
  # AZURE_API_BASE=                # Azure Endpoint

  # ─── LiteLLM Gateway ─────────────────────────────────────────────
  LITELLM_MASTER_KEY=sk-litellm-dev-key  # Virtual Key fuer Agent Service
  LITELLM_PORT=4000

  # ─── Agent LLM Config ────────────────────────────────────────────
  # Bei LiteLLM: OPENAI_BASE_URL zeigt auf LiteLLM, nicht direkt
  AGENT_PROVIDER=openai-compatible
  OPENAI_BASE_URL=http://localhost:4000
  AGENT_MODEL=claude-sonnet           # Logical model name aus config.yaml
  AGENT_UTILITY_MODEL=claude-haiku    # Fuer Summarization, Skills, etc.
  ```

---

## Stufe 3: Dynamic Model Selection (UI → Backend)

### 3.1 Agent Chat UI: Model-Dropdown

- [ ] **3.1.1:** Model-Picker im AgentChatComposer
  - Dropdown/Popover mit verfuegbaren Models
  - Grouped: Cloud (Claude, GPT, Gemini) | Local (Ollama, vLLM) | Free (OpenRouter Free)
  - Selected Model wird im Request mitgeschickt: `{ model: "claude-sonnet" }`

- [ ] **3.1.2:** `useAvailableModels()` Hook
  - Fetcht `GET /api/v1/control/models/providers` (bestehender Endpoint)
  - Filtert auf `is_active` + `available_models`
  - Cached via TanStack Query

- [ ] **3.1.3:** Model-Badge im Chat-Header
  - Zeigt aktives Model an: "claude-sonnet · Anthropic"
  - Bei Fallback: "claude-sonnet · via OpenRouter (fallback)"

### 3.2 Request-Body Erweiterung

- [ ] **3.2.1:** `AgentChatRequest.model` (bereits vorhanden in `app.py:94`)
  - Aktuell: `req.model or os.environ.get("AGENT_MODEL", default)`
  - Aenderung: Model-Name wird 1:1 an LiteLLM durchgereicht
  - LiteLLM resolved den logischen Namen zum Provider

- [ ] **3.2.2:** Go Gateway durchreichen
  - `agent_chat_handler.go` leitet `model` Feld bereits im Request-Body durch ✅
  - Keine Go-Aenderungen noetig

### 3.3 control-ui: Provider Management (API Keys + Config via UI)

> control-ui ist die zentrale Oberflaeche fuer alles Agent-bezogene — fuer ALLE User,
> nicht nur Admin/Dev. API Keys setzen gehoert in **User Mode** (nicht Dev Mode).
> LiteLLM hat eine Admin API (`/config/update`, `/key/generate`) die Hot-Reload
> ohne Service-Restart unterstuetzt. Keys werden in LiteLLM DB (Postgres) gespeichert.
>
> **User Mode:** API Keys setzen, Model auswaehlen, Cost einsehen
> **Dev Mode:** Provider aktivieren/deaktivieren, Fallback-Config, System Health, Routing per Rolle

- [ ] **3.3.1:** ApiModelsTab erweitern — Provider Keys via UI (alle User, nicht nur Admin)
  - "Set API Key" Button pro Provider → verschluesselt in LiteLLM DB
  - Flow: control-ui → Python Backend → LiteLLM Admin API → Hot-Reload
  - Kein .env-Neustart noetig
  - Initiales Setup weiterhin via .env (vor erstem Start)
  - **Per-User Keys:** Jeder User kann eigene API Keys setzen (User Settings)
    - User-Key hat Vorrang vor System-Default
    - LiteLLM Virtual Keys: pro User eigener Key → gebunden an seine Provider-Keys
    - Self-Hosted (1 User): User = Admin, kein Gate noetig
    - Multi-User: jeder nutzt eigenen OpenRouter/Anthropic Account

- [ ] **3.3.2:** ApiModelsTab — Provider aktivieren/deaktivieren
  - PATCH Endpoint togglet Provider in LiteLLM config
  - Deaktivierte Provider erscheinen nicht im agent-chat Model-Dropdown

- [ ] **3.3.3:** ApiModelsTab — Model-Routing per Rolle
  - Researcher → claude-opus, Trader → gpt-4o, RiskManager → claude-sonnet
  - Gespeichert in DB (Alembic Migration), nicht .env

- [ ] **3.3.4:** LiteLLM Health + Dashboard in SystemTab
  - `GET http://localhost:4000/health` → LiteLLM Status
  - Active Models, Provider Status, Request-Count
  - Link zu LiteLLM Built-in Dashboard (`/ui` auf Port 4000)

### 3.3b Verbindung control-ui ↔ agent-chat

```
control-ui (Admin):                    agent-chat (User):
┌──────────────────────┐               ┌──────────────────────┐
│ Provider ein/aus     │               │ Model-Dropdown       │
│ API Keys setzen      │──────────────→│ zeigt nur aktive     │
│ Fallback-Reihenfolge │               │ Models               │
│ Per-Rolle Routing    │               │                      │
│ Cost Dashboard       │               │ "claude-sonnet" ▼    │
└──────────────────────┘               └──────────┬───────────┘
                                                  │
                                       { model: "claude-sonnet" }
                                                  ▼
                                       LiteLLM → richtiger Provider
```

- [ ] **3.3b.1:** `GET /api/v1/control/models/available` — liefert nur aktive Models
  - Wird von agent-chat Model-Dropdown und control-ui gemeinsam genutzt
  - Filtert auf: Provider aktiv + API Key gesetzt + Model in config.yaml

- [ ] **3.3b.2:** Model-Auswahl persistieren pro User (spaeter)
  - Default: `AGENT_MODEL` aus ENV
  - User-Override: localStorage oder DB

### 3.4 Cost Tracking

- [ ] **3.4.1:** LiteLLM Spend-Tracking aktivieren (braucht Postgres)
  - `LITELLM_DATABASE_URL` auf bestehende PostgreSQL Instanz
  - Dashboard: `/ui` auf LiteLLM Port 4000
  - API: `GET /spend/logs` → pro User/Model/Session

- [ ] **3.4.2:** Cost-Badge im Agent Chat
  - Token-Usage + geschaetzte Kosten pro Nachricht
  - Session-Total im Footer

---

## Verify-Gates

### Gate 1: OpenRouter Quick-Start (Stufe 1)
- [ ] `AGENT_PROVIDER=openai-compatible` + `OPENAI_BASE_URL=openrouter.ai` funktioniert
- [ ] SSE Streaming ueber OpenRouter korrekt
- [ ] Tool-Calls funktionieren ueber OpenRouter
- [ ] Free Models (`qwen3-480b:free`) antworten

### Gate 2: LiteLLM Proxy (Stufe 2)
- [ ] LiteLLM startet auf Port 4000 via `uv run litellm`
- [ ] `GET http://localhost:4000/health` → OK
- [ ] Agent Chat funktioniert ueber LiteLLM → Anthropic
- [ ] Agent Chat funktioniert ueber LiteLLM → OpenRouter
- [ ] Agent Chat funktioniert ueber LiteLLM → Ollama (lokal)
- [ ] Fallback: Anthropic Key fehlt → OpenRouter uebernimmt automatisch
- [ ] devstack2.ps1 startet LiteLLM als Service

### Gate 3: Dynamic Model Selection (Stufe 3)
- [ ] Model-Dropdown im AgentChatComposer
- [ ] User waehlt "gpt-4o" → Backend nutzt OpenAI via LiteLLM
- [ ] User waehlt "claude-sonnet" → Backend nutzt Anthropic via LiteLLM
- [ ] User waehlt "local-llama" → Backend nutzt Ollama via LiteLLM
- [ ] Model-Badge zeigt aktives Model + Provider
- [ ] ApiModelsTab zeigt aktive Provider + Routing

### Gate 4: Cost Tracking (Stufe 3)
- [ ] LiteLLM Spend-Tracking in PostgreSQL
- [ ] Cost pro Nachricht sichtbar im Agent Chat
- [ ] Session-Total im Footer

---

## Venv-Architektur (Stand mit LiteLLM)

```
python-backend/
  .venv/                    # Venv 1: Agent Service (Port 8094)
  ingestion/.venv/          # Venv 2: Ingestion Worker (Port 8098)
  extraction_layout/.venv/  # Venv 3: Layout Extraction (503 Skeleton)
  kg_pipeline/.venv/        # Venv 4: KG Pipeline (503 Skeleton)
  litellm-gateway/          # Venv 5: LiteLLM Proxy (Port 4000) ← NEU
    .venv/
    pyproject.toml
    config.yaml
```

---

## Risiken

| Risiko | Mitigation |
|---|---|
| LiteLLM Latenz (+8ms P95) | Vernachlaessigbar vs. LLM-Latenz (~2-30s) |
| LiteLLM Instabilitaet | Fallback: `AGENT_PROVIDER=anthropic` direkt (Stufe 1 Modus) |
| Config-Drift (config.yaml vs .env) | config.yaml liest Keys aus ENV (`os.environ/KEY`) |
| OpenRouter Rate Limits (Free) | Nur fuer Dev/Testing, Prod nutzt direkte Provider |
| Zu viele Venvs | LiteLLM Venv ist isoliert, kein Dependency-Conflict |

---

## Abhaengigkeiten

- exec-10: LangGraph Agent (llm_node.py Provider-Routing) ✅
- exec-15 Slice 5: control-ui ApiModelsTab ✅
- PostgreSQL (fuer Stufe 3 Cost Tracking) — bereits vorhanden (exec-11)
- Stufe 3 benoetigt exec-merge-chat (Agent Chat im Hauptprojekt)

---

## Abgrenzung: Was ist NICHT in diesem Slice

- **Embedding-Provider-Routing** — bleibt lokal (sentence-transformers), kein LiteLLM
- **STT/TTS Provider-Routing** — bleibt in voice/providers.py, kein LiteLLM
- **Go LLM-Proxy** — Go bleibt reiner SSE-Proxy, keine LLM-Logik
