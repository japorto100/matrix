# exec-16: LLM Provider Gateway (LiteLLM + Multi-Provider Routing)

**Datum:** 10.04.2026
**Status:** In Progress
**Abhaengig von:** exec-10 (LangGraph Agent), exec-15 (control-ui ApiModelsTab)

> **Phase-B carried-forward debt (2026-04-20):** Siehe `exec-blocking.md §C11` für die vier offenen items: (a) `agent.user_llm_settings.preferred_runner` column als hook für Phase-C dispatcher user-override, (b) CredentialPool multi-key-per-(user, provider) jenseits von `SingleKeyCredentialPool`, (c) InsightsEngine event-driven rollup, (d) MemPalace/Hindsight concrete `on_pre_compress` impls.

**Referenzen:**
- OpenRouter API: https://openrouter.ai/docs (Models, Pricing, Provider Routing)
- LiteLLM Docs: https://docs.litellm.ai/docs/simple_proxy
- LiteLLM Config: https://docs.litellm.ai/docs/proxy/configs
- Vercel AI SDK Provider Registry: https://ai-sdk.dev/docs/reference/ai-sdk-core/provider-registry
- NIST PQC Standards: https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards

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
| `llm_helper.py` fuer Utility-Calls | ✅ Provider-agnostisch, LiteLLM endpoint |
| control-ui ApiModelsTab (7 Provider gelistet) | ✅ Rewritten mit EditApiKeyModal |
| Model-Routing per Trading-Rolle | ✅ `models.py` (alle auf Default) |
| OpenRouter als Provider | ✅ Via LiteLLM config.yaml (wildcard routing) |
| LiteLLM Proxy | ✅ Installiert (`litellm-gateway/`, Port 4000) |
| Dynamic Model Selection (UI → Backend) | 🔶 Model-Dropdown + User-Settings (teilweise) |
| User LLM Settings (DB + KeyVault) | ✅ Alembic 009, AES-256-GCM, CRUD API |
| Fallback/Retry | ❌ Kein Fallback |
| Cost Tracking | ❌ Nicht vorhanden |

---

## Kernprinzip: Eine Konfiguration, alle Pfade

Der User konfiguriert **einmal** in control-ui seine LLM-Praeferenzen (API Keys, Default-Model,
Per-Rolle Overrides). Danach gilt das **ueberall** — egal ob Matrix Mention oder Agent Chat UI.

```
control-ui: User setzt API Keys + Default Model + Per-Rolle Routing
                          ↓ (gespeichert in DB)
Matrix Mention:   sender → User-ID → DB → User-Settings → LiteLLM (User's Key + Model)
Agent Chat UI:    req.model oder User-Default → LiteLLM (User's Key + Model)
```

- Bridge schickt `sender` (Matrix User-ID) mit → Python Agent resolved zu User-Settings
- Python Agent holt User-Settings aus DB: API Keys, Default-Model, Per-Rolle Overrides
- LiteLLM bekommt den Virtual Key des Users → routet zum richtigen Provider
- Orchestrator antwortet mit dem Model das der User konfiguriert hat

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

- [x] **1.2:** `.env` Konfiguration fuer OpenRouter (via LiteLLM, not AGENT_PROVIDER=openai-compatible pattern)
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

- [x] **2.1.1:** Eigene Venv fuer LiteLLM Gateway
  ```
  python-backend/litellm-gateway/
    pyproject.toml          # litellm[proxy] dependency
    .venv/                  # eigene Venv (uv)
    config.yaml             # Model-Liste + Provider-Config
    start.ps1               # Startscript fuer devstack2
  ```

- [x] **2.1.2:** `pyproject.toml`
  ```toml
  [project]
  name = "litellm-gateway"
  requires-python = ">=3.11"
  dependencies = ["litellm[proxy]"]

  [tool.uv]
  managed = true
  ```

- [x] **2.1.3:** Installation
  ```bash
  cd python-backend/litellm-gateway
  uv sync
  ```

- [x] **2.1.4:** Start
  ```bash
  uv run litellm --config config.yaml --port 4000
  ```

### 2.2 config.yaml

- [x] **2.2.1:** Basis-Config mit allen Providern (wildcard routing)
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

- [x] **2.3.1:** Agent `.env` auf LiteLLM umstellen (LITELLM_BASE_URL=http://localhost:4000, llm_client.py is sole OpenAI client)
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

- [x] **2.3.2:** `llm_helper.py` auf LiteLLM Endpoint umstellen (uses shared llm_client)
  - Gleiche Logik, nur `OPENAI_BASE_URL` zeigt auf LiteLLM statt direkt Provider
  - Utility-Calls (Summarization, Skills) nutzen gleichen Endpoint

- [x] **2.3.3:** Hindsight Memory Engine (bridges to LiteLLM via ENV)
  - Hindsight nutzt eigene LLM-Config (`engine.py` setzt ENV vars)
  - Umstellen auf LiteLLM Endpoint fuer Retain/Recall LLM-Calls

### 2.4 DevStack Integration

- [x] **2.4.1:** `dev-stack2.ps1` — LiteLLM als Service (`-SkipLiteLLM` Flag, Port 4000)
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

- [x] **2.5.1:** Alle Provider-Keys in einer `.env` Datei (.env + .env.example updated)
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

## Stufe 2.5: User LLM Settings (DB + API Key Security)

> Kern-Baustein: Ohne DB-gespeicherte User-Settings gibt es kein Per-User Model-Routing.
> Muss VOR Stufe 3 implementiert werden.

### 2.6 Alembic Migration: `agent.user_llm_settings`

- [x] **2.6.1:** Migration erstellen (Alembic 009: user_llm_settings + user_credentials tables)
  ```sql
  CREATE TABLE agent.user_llm_settings (
    id            SERIAL PRIMARY KEY,
    user_id       TEXT NOT NULL UNIQUE,        -- Matrix User-ID oder App User-ID
    default_model TEXT DEFAULT 'claude-sonnet', -- Logischer Model-Name
    per_role_overrides JSONB DEFAULT '{}',     -- {"researcher": "claude-opus", "trader": "gpt-4o"}
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
  );

  CREATE TABLE agent.user_api_keys (
    id            SERIAL PRIMARY KEY,
    user_id       TEXT NOT NULL,
    provider_id   TEXT NOT NULL,              -- "anthropic", "openai", "openrouter", "gemini"
    api_key_enc   BYTEA NOT NULL,             -- Fernet-verschluesselt
    is_valid      BOOLEAN DEFAULT TRUE,       -- Letzte Validierung erfolgreich
    validated_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider_id)
  );
  ```

### 2.7 API Key Verschluesselung (Go + Python, cross-language)

> Im Hauptprojekt (tradeview-fusion) ist Go der zentrale Network-Layer mit DB-Zugriff.
> Go braucht Keys fuer Exchanges, Datenquellen, Storage. Python braucht Keys fuer LLM Provider.
> Beide muessen die gleiche DB-Tabelle lesen/schreiben → **identisches AES-256-GCM Format**.

- [x] **2.7.1:** Python KeyVault (`agent/security/key_vault.py`) — AES-256-GCM with 0x01 prefix
  - AES-256-GCM via `cryptography` Package (bereits in Dependencies)
  - Server-Secret aus ENV: `KEY_ENCRYPTION_SECRET` (32 Bytes, hex-encoded)
  - Modulares Backend-Interface fuer spaetere PQC-Erweiterung:
    ```python
    class KeyVault:
        def __init__(self, backend: str = "aesgcm"):
            # "aesgcm"     = AES-256-GCM (Standard, jetzt)
            # "hybrid-pqc" = AES-256-GCM + ML-KEM Key-Wrap (spaeter)
        def encrypt(self, plaintext: str) -> bytes: ...
        def decrypt(self, ciphertext: bytes) -> str: ...
    ```
  - Format: `[12-byte nonce][ciphertext][16-byte GCM tag]` — identisch in Go + Python

- [x] **2.7.2:** Go KeyVault (`internal/keyvault/keyvault.go`) — AES-256-GCM same format
  - AES-256-GCM via Go stdlib (`crypto/aes` + `crypto/cipher`)
  - Gleicher ENV: `KEY_ENCRYPTION_SECRET`
  - Gleiches Byte-Format wie Python (cross-language kompatibel)
  - Modulares Interface mit **beiden Backends von Anfang an**:
    ```go
    type KeyVault interface {
        Encrypt(plaintext string) ([]byte, error)
        Decrypt(ciphertext []byte) (string, error)
        Backend() string // "aesgcm" oder "hpke-mlkem"
    }

    // AESGCMVault — Standard, symmetric, shared secret aus ENV
    // crypto/aes + crypto/cipher (Go 1.0+)
    type AESGCMVault struct { key []byte }

    // HPKEVault — Post-Quantum ready, asymmetric, public/private key pair
    // crypto/hpke (Go 1.26+ stdlib, kein externer Import)
    // KEM: X25519MLKEM768 (hybrid classical + PQC)
    // Keypair in DB oder Filesystem, rotierbar
    type HPKEVault struct { publicKey, privateKey []byte }

    // NewKeyVault erstellt das richtige Backend basierend auf ENV
    func NewKeyVault(backend string) (KeyVault, error) {
        switch backend {
        case "hpke-mlkem":
            return NewHPKEVault()  // crypto/hpke + ML-KEM
        default:
            return NewAESGCMVault() // crypto/aes (Standard)
        }
    }
    ```
  - **Beide Backends implementiert**, `KEY_VAULT_BACKEND` ENV wählt aus
  - Default: `aesgcm` (kompatibel mit Python, symmetrisch, einfach)
  - `hpke-mlkem`: sofort nutzbar auf Go 1.26+, Post-Quantum
  - Auto-Detect beim Decrypt: erkennt Format am Prefix-Byte
    - `0x01` + Daten = AES-GCM
    - `0x02` + Daten = HPKE-MLKEM
    - → Decrypt funktioniert mit beiden Formaten, egal welches Backend aktiv
  - Go braucht das fuer: Exchange API Keys, Datenquellen-Credentials, Storage Secrets
  - Wird bei Portierung ins Hauptprojekt 1:1 uebernommen

- [x] **2.7.3:** Go HPKE (`internal/keyvault/hpke.go`) — crypto/hpke with 0x02 prefix, auto-detect
  - **Python:** `pqcrypto` oder `liboqs-python` fuer ML-KEM Key-Wrap
    - Hybrid = ML-KEM kapselt den AES-256 Key → AES-256-GCM verschluesselt Daten
    - `KEY_VAULT_BACKEND=hybrid-pqc` ENV aktiviert PQC
  - **Go:** `crypto/hpke` (stdlib seit Go 1.26) — **von Anfang an implementiert**
    - Go 1.24+ hat X25519MLKEM768 bereits default in TLS (in-transit)
    - Go 1.26 `crypto/hpke` fuer Keys at rest (HPKE mit ML-KEM KEM)
    - `KEY_VAULT_BACKEND=hpke-mlkem` ENV aktiviert PQC
    - HPKEVault ist Teil des Go Backends, nicht nachtraeglich
    - Keypair-Management: generiert bei erstem Start, persistiert in DB/Filesystem
  - **Migration:** Auto-Detect via Prefix-Byte:
    - `0x01` = AES-GCM (Python + Go kompatibel)
    - `0x02` = HPKE-MLKEM (Go-only, Python spaeter via pqcrypto)
    - Decrypt versteht beide Formate, Encrypt nutzt aktives Backend
    - Re-Encrypt Script: alle Keys auf neues Backend umschreiben
  - **Kein Breaking Change:** AES-GCM bleibt Default, HPKE-MLKEM ist opt-in
  - **Portierung:** Go KeyVault wird 1:1 ins Hauptprojekt uebernommen

- [x] **2.7.4:** Sicherheitsregeln (Go + Python) — masked preview, BYTEA, KEY_ENCRYPTION_SECRET required
  - API Keys nie in Logs (auch nicht teilweise)
  - API Keys nie in API Responses (nur `is_set: true/false` + masked Preview)
  - DB-Spalte ist BYTEA (verschluesselt), nicht TEXT
  - `KEY_ENCRYPTION_SECRET` muss in `.env` gesetzt sein, Fehler wenn fehlend
  - Secret-Rotation: Re-Encrypt aller Keys mit neuem Secret (Migration-Script)

### 2.7b Shared DB-Tabelle fuer alle Credentials

> Nicht nur LLM Keys — auch Exchange Keys, Datenquellen usw.
> Eine Tabelle, beide Sprachen (Go + Python) lesen/schreiben.

- [x] **2.7b.1:** Generische Credentials-Tabelle (user_credentials with category field)
  ```sql
  CREATE TABLE agent.user_credentials (
    id            SERIAL PRIMARY KEY,
    user_id       TEXT NOT NULL,
    category      TEXT NOT NULL,    -- "llm", "exchange", "datasource", "storage"
    provider_id   TEXT NOT NULL,    -- "anthropic", "binance", "alpha_vantage", etc.
    credential_enc BYTEA NOT NULL,  -- AES-256-GCM (oder Hybrid-PQC)
    metadata      JSONB DEFAULT '{}', -- Provider-spezifisch (endpoint, region, etc.)
    is_valid      BOOLEAN DEFAULT TRUE,
    validated_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, category, provider_id)
  );
  ```
  - `category` trennt LLM Keys von Exchange Keys etc.
  - Go liest Exchange/Datasource Keys, Python liest LLM Keys
  - Beide nutzen identisches AES-256-GCM Format

### 2.8 CRUD Endpoints fuer User-Settings

- [x] **2.8.1:** `agent/control/user_llm.py` — CRUD Router with all 6 endpoints
  ```
  GET    /api/v1/control/user/llm           → User-Settings + Provider-Status (masked keys)
  PUT    /api/v1/control/user/llm/model     → Default-Model setzen
  PUT    /api/v1/control/user/llm/roles     → Per-Rolle Overrides setzen
  PUT    /api/v1/control/user/llm/key/{provider}  → API Key setzen (verschluesselt in DB)
  DELETE /api/v1/control/user/llm/key/{provider}  → API Key loeschen
  POST   /api/v1/control/user/llm/key/{provider}/validate → Key testen (LLM-Call mit minimal Prompt)
  ```

- [x] **2.8.2:** Key Validation Endpoint (LLM call + model fetching)
  - Macht einen minimalen LLM-Call (`"Hi"` → pruefen ob Response kommt)
  - Speichert `is_valid` + `validated_at` in DB
  - Gibt `{ valid: true, model_list: [...] }` zurueck
  - Timeout: 10s, kein Retry

### 2.9 Python Agent: User-Settings Resolution

- [x] **2.9.1:** `agent/control/credentials.py` — Settings Loader (get_user_api_key, get_user_default_model, provider_from_model)
  ```python
  async def get_user_llm_settings(user_id: str) -> UserLLMSettings:
      # DB Lookup → Fallback auf ENV
      # Returns: default_model, per_role_overrides, decrypted api_keys
  ```

- [x] **2.9.2:** Integration in `app.py` + `runner.py` (user settings resolution)
  - Vor LangGraph-Start: `settings = await get_user_llm_settings(user_id)`
  - Model: `req.model or settings.default_model or ENV`
  - API Key: `settings.api_key_for(provider) or ENV`
  - Per-Rolle: `settings.model_for_role(role) or settings.default_model`

- [x] **2.9.3:** Integration in NATS Bridge (`nats_handler.py` → `get_user_default_model(sender)`)
  - `sender` → User-ID → `get_user_llm_settings(sender)` → Model
  - `model` Feld im Payload an Agent Service

---

## Stufe 3: Dynamic Model Selection (UI → Backend)

### 3.1 Agent Chat UI: Model-Dropdown

- [x] **3.1.1:** Model-Picker in AgentChatToolbar (dynamic, grouped cloud/local)
  - Dropdown/Popover mit verfuegbaren Models
  - Grouped: Cloud (Claude, GPT, Gemini) | Local (Ollama, vLLM) | Free (OpenRouter Free)
  - Selected Model wird im Request mitgeschickt: `{ model: "claude-sonnet" }`

- [x] **3.1.2:** `useAvailableModels()` Hook
  - Fetcht `GET /api/v1/control/user/llm` (User-Settings inkl. verfuegbare Models)
  - Zeigt nur Models wo User einen **gueltigen** API Key hat (`is_valid: true`)
  - Grouped: Cloud (Claude, GPT, Gemini) | Aggregator (OpenRouter) | Local (Ollama)
  - Cached via TanStack Query, invalidiert bei Key-Aenderung in control-ui

- ~~**3.1.3:** Model-Badge im Chat-Header~~ (entfernt — Toolbar-Dropdown zeigt Model bereits)
  - Bei Fallback: "claude-sonnet · via OpenRouter (fallback)"

### 3.2 Request-Body + User-Settings Resolution

- [x] **3.2.1:** `AgentChatRequest.model` — resolves model from user settings
  - Aktuell: `req.model or os.environ.get("AGENT_MODEL", default)`
  - Aenderung: `req.model or user_settings.default_model or ENV`
  - Model-Name wird 1:1 an LiteLLM durchgereicht

- [x] **3.2.2:** Go Gateway durchreichen
  - `agent_chat_handler.go` leitet `model` Feld bereits im Request-Body durch ✅
  - Keine Go-Aenderungen noetig

- [x] **3.2.3:** User-Settings Resolution im Python Agent
  - `sender` (Matrix User-ID) oder `X-Auth-User` Header → User-ID
  - `user_settings = get_user_llm_settings(user_id)` aus DB
  - Settings: `default_model`, `api_keys`, `per_role_overrides`
  - Fallback-Kette: `req.model` → `user_settings.default_model` → `ENV AGENT_MODEL`
  - Alembic Migration: `agent.user_llm_settings` Tabelle

- [x] **3.2.4:** NATS Bridge User-Settings (nats_handler.py → get_user_default_model → model param)

- [x] **3.2.5:** Per-Rolle Routing mit User-Settings (credentials.get_user_role_model + runner.py)
  - Orchestrator: `user_settings.per_role_overrides` oder System-Default
  - z.B. User will: Researcher → claude-opus, Rest → claude-haiku
  - In `models.py` bereits vorbereitet (routing per TradingRole)
  - Erweitern: User-Override hat Vorrang vor System-Default

### 3.3 control-ui: Provider Management (API Keys + Config via UI)

> control-ui ist die zentrale Oberflaeche fuer alles Agent-bezogene — fuer ALLE User,
> nicht nur Admin/Dev. API Keys setzen gehoert in **User Mode** (nicht Dev Mode).
> LiteLLM hat eine Admin API (`/config/update`, `/key/generate`) die Hot-Reload
> ohne Service-Restart unterstuetzt. Keys werden in LiteLLM DB (Postgres) gespeichert.
>
> **User Mode:** API Keys setzen, Model auswaehlen, Cost einsehen
> **Dev Mode:** Provider aktivieren/deaktivieren, Fallback-Config, System Health, Routing per Rolle

- [x] **3.3.1:** ApiModelsTab rewritten with EditApiKeyModal for setting/testing keys
  - "Set API Key" Button pro Provider → verschluesselt in LiteLLM DB
  - Flow: control-ui → Python Backend → LiteLLM Admin API → Hot-Reload
  - Kein .env-Neustart noetig
  - Initiales Setup weiterhin via .env (vor erstem Start)
  - **Per-User Keys:** Jeder User kann eigene API Keys setzen (User Settings)
    - User-Key hat Vorrang vor System-Default
    - LiteLLM Virtual Keys: pro User eigener Key → gebunden an seine Provider-Keys
    - Self-Hosted (1 User): User = Admin, kein Gate noetig
    - Multi-User: jeder nutzt eigenen OpenRouter/Anthropic Account

- [x] **3.3.2:** Provider aktiv/inaktiv = Key vorhanden/nicht vorhanden (Set Key / Remove Key Buttons)
  - Kein separater Toggle noetig — Key-Praesenz bestimmt Provider-Status
  - agent-chat zeigt nur Models von aktiven Providern (is_active = bool(key))

- [x] **3.3.3:** ApiModelsTab — Model-Routing per Rolle (Dropdown pro Rolle, PUT /user/llm/roles)
  - Researcher → claude-opus, Trader → gpt-4o, RiskManager → claude-sonnet
  - Gespeichert in DB (Alembic Migration), nicht .env

- [x] **3.3.4:** LiteLLM Health in SystemTab (ping /health, Dashboard unter :4000/ui)
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

- [x] **3.3b.1:** `GET /api/v1/control/user/llm` returns dynamic models from provider APIs
  - Wird von agent-chat Model-Dropdown und control-ui gemeinsam genutzt
  - Filtert auf: Provider aktiv + API Key gesetzt + Model in config.yaml

- [ ] **3.3b.2:** Model-Auswahl persistieren pro User (spaeter)
  - Default: `AGENT_MODEL` aus ENV
  - User-Override: localStorage oder DB

### 3.4 Cost Tracking

- [x] **3.4.1:** LiteLLM Spend-Tracking aktivieren (`LITELLM_DATABASE_URL` in .env gesetzt)
  - `LITELLM_DATABASE_URL` auf bestehende PostgreSQL Instanz
  - Dashboard: `/ui` auf LiteLLM Port 4000
  - API: `GET /spend/logs` → pro User/Model/Session

- ~~**3.4.2:** Cost-Badge im Agent Chat~~ (entfernt — nice-to-have, nicht im Scope)

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

### Gate 2.5: User LLM Settings + Key Security (Stufe 2.5)
- [x] Alembic Migration: `agent.user_llm_settings` + `agent.user_credentials` Tabellen
- [x] Python KeyVault: AES-256-GCM encrypt/decrypt via `cryptography`
- [x] Go KeyVault: AES-256-GCM encrypt/decrypt via stdlib `crypto/aes`
- [x] Cross-language: Python-verschluesselt → Go-entschluesselbar (gleiches Byte-Format)
- [x] `KEY_ENCRYPTION_SECRET` ENV gesetzt, Fehler wenn fehlend (Go + Python)
- [x] CRUD: PUT Key → AES-256-GCM verschluesselt → GET zeigt nur masked Preview
- [x] Key Validation: POST validate → minimaler LLM-Call → `is_valid` + `model_list`
- [x] User-Settings Resolution: `get_user_llm_settings(user_id)` in runner.py
- [x] Fallback-Kette: `req.model` → `user_settings.default_model` → `ENV`
- [x] Matrix Mention: `sender` → User-Settings → richtiges Model (nats_handler.py)
- [x] PQC-Readiness: `KEY_VAULT_BACKEND` ENV vorhanden, default `aesgcm`

### Gate 3: Dynamic Model Selection (Stufe 3)
- [x] Model-Dropdown in AgentChatToolbar (dynamic, grouped cloud/local)
- [ ] User waehlt "gpt-4o" → Backend nutzt OpenAI via LiteLLM (not verified)
- [ ] User waehlt "claude-sonnet" → Backend nutzt Anthropic via LiteLLM (not verified)
- [ ] User waehlt "local-llama" → Backend nutzt Ollama via LiteLLM (not verified)
- ~~Model-Badge~~ (entfernt — Toolbar zeigt Model)
- [x] control-ui: API Key Eingabe + Live-Validation + Model-Picker (User Mode)
- [x] control-ui: Per-Rolle Overrides (Dropdown pro Rolle in ApiModelsTab)
- [x] agent-chat ↔ control-ui: gleicher Endpoint, Aenderung sofort sichtbar

### Gate 4: Cost Tracking (Stufe 3)
- [x] LiteLLM Spend-Tracking in PostgreSQL (`LITELLM_DATABASE_URL` konfiguriert)
- ~~Cost pro Nachricht sichtbar im Agent Chat~~ (entfernt)
- ~~Session-Total im Footer~~ (entfernt)

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

---

## Phase 4.5 — Reasoning / Thinking Budget End-to-End (2026-04-18)

Ownership übernommen von archiviertem `exec-19 §5c` (DevStack-Consolidation).
Implementation ist pre-transfer bereits gelandet; offene Items sind
Live-Verify-Gates und eine Auto-Mode-Heuristik.

### Done (pre-transfer)

- LiteLLM `reasoning_effort` Pass-Through in `llm_node.py` (Anthropic thinking-
  block, OpenAI `reasoning_effort`, DeepSeek — provider-specific mapping
  auto-resolved durch LiteLLM v1.50+).
- Reasoning-delta → SSE `ReasoningDeltaPacket` Streaming in `streaming.py`.
- `state["reasoning_effort"]` in `llm_node.py:99` gelesen und durchgereicht.
- Audit: `prompt_tokens_details.cached_tokens` + `completion_tokens_details.reasoning_tokens` in Runtime-/Session-Metadata (exec-17 §Stufe 2).

### Open — Live-Verify-Gates (provider-access-gated)

- [ ] Live-Test `openrouter/anthropic/claude-sonnet-4-6` mit `reasoning_effort: "high"` → Thinking-Content im Stream, `reasoning_tokens > 0` in Usage.
- [ ] Live-Test `openrouter/openai/o3-mini` mit `reasoning_effort: "high"` → erfolgreich, `reasoning_tokens` in Usage.
- [ ] Langfuse-Dashboard zeigt `reasoning_tokens` als separates Cost-Item.

### Open — Auto-Mode-Heuristik (Phase 4.5.1)

Pure function `_compute_auto_effort(prompt, history, model_info) -> "low"|"medium"|"high"` — picks a reasoning-budget aus Prompt-Komplexität (Länge, Tool-Call-Count, Keyword-Signals). Heute user-controlled via control-ui; Auto-Mode ermöglicht Agent-Self-Selection bei Default-Model.

- [ ] Implementiere `_compute_auto_effort` in `agent/llm_client.py` oder neuem `agent/resilience/reasoning_budget.py`.
- [ ] Control-UI Filter **"Auto-Mode Capable"** (flagt Modelle die `reasoning_effort` akzeptieren) — ersetzt den exec-19 §5b.10-Followup.
- [ ] Sortierung nach `reasoning_quality_score` (Langfuse-basiert) — optional, post-Live-Gates.

### Ownership-Marker

- [x] Reasoning + Auto-Mode Ownership übernommen von archiviertem `exec-19 §5c` (2026-04-18).
- [x] Portierungs-Marker "exec-19 Stufe 5c → exec-16 Phase 4.5" aus exec-19 Spec-Map entfernt (archive erhält Historie).

---

## 2.10 Billing Ledger — CanonicalUsage + InsightsEngine (Phase-B P4 DONE)

**Status:** DONE — 2026-04-20.
**Cross-ref:** `exec-hermes.md §0` (usage_pricing + insights rows), `exec-harness.md §4f` (dual-path fitness).
**Implementation:** `agent/billing/usage_pricing.py` + `agent/billing/insights.py`. Hermes-port from `_ref/hermes-agent/agent/usage_pricing.py` (687 → 180 LOC) and `_ref/hermes-agent/agent/insights.py` (768 → 230 LOC).

**Pipeline:**

1. `llm_node.py` post-LLM-call: `usage_from_litellm(response.usage.model_dump())` → `CanonicalUsage` (normalises OpenAI/Anthropic/Google usage shapes including cache-read/cache-write/reasoning-tokens).
2. `estimate_usage_cost(model, usage) -> CostResult(amount_usd, status, source, notes)`:
   - **Primary**: `agent.llm.model_metadata.get_model_info(model)` (LiteLLM wrapper) → `input_cost_per_token` / `output_cost_per_token` / `cache_read_input_token_cost` / `cache_creation_input_token_cost`. Zero-token requests return `Decimal(0)` cleanly.
   - **Fallback**: minimal static snapshot (`claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`) — only for cases where LiteLLM has not yet shipped metadata for a new flagship. The moment the snapshot grows past ~20 entries, push changes upstream to LiteLLM instead.
3. Emits span-attributes on `agent.turn` span: `llm.input_tokens`, `llm.cache_read_tokens`, `llm.cache_write_tokens`, `llm.reasoning_tokens`, `llm.cost_status` ∈ {`estimated`, `included`, `unknown`}, `llm.cost_usd` (str-encoded Decimal), `llm.cost_source` ∈ {`litellm`, `snapshot`, `none`}.
4. `InsightsEngine(conn)` reads `agent.spans` JSONB (exec-18 Migration 017) — **never SQLite like hermes**. Aggregates per-user per-day via `generate(user_id, days=7)`.
5. **Dual-path** both consume the same aggregation:
   - REST endpoint (exec-16, TODO next phase): `GET /api/v1/billing/insights?user_id=X&days=7` → Control-UI
   - `agent/harness/scorer.py::_estimate_cost` delegates to `estimate_usage_cost` for meta-harness fitness (exec-harness §4f)
6. **Tier-1 redact** applied per-span inside `InsightsEngine._aggregate` BEFORE pulling billing fields — prevents leaking custom-pattern content via billing API if Tier-2 async consumer is lagging.

**InsightsReport shape:** `{user_id, since, until, total_sessions, total_turns, total_input_tokens, total_output_tokens, total_cache_read_tokens, total_cache_write_tokens, total_cost_usd, cost_status ∈ {known, partial, unknown}, per_model_cost, per_model_tokens}`. JSON-serialisable via `to_json()`.

**Slim-port philosophy:** `CanonicalUsage` kept 1:1 from hermes (excellent ergonomic), estimate-cost logic ~50 LOC, no OAuth-token-refresh (hermes-CLI-specific), no SQLite-state (spans are the source of truth).

## 3.1 model_metadata wrapper — LiteLLM-proxy (Phase-B P4 DONE)

**Status:** DONE — 2026-04-20.
**Cross-ref:** `exec-hermes.md §0` (model_metadata row), `exec-context.md §13`.
**Implementation:** `agent/llm/model_metadata.py`. Hermes-port from `_ref/hermes-agent/agent/model_metadata.py` (1116 LOC → 110 LOC wrapper).

Public API:

- `get_model_info(model) -> dict | None` — wrapper around `litellm.get_model_info(...)` with 1-hour TTL cache keyed by normalised model id. Returns LiteLLM's full ModelInfo dict (`max_input_tokens`, `max_tokens`, `input_cost_per_token`, `output_cost_per_token`, `cache_read_input_token_cost`, `cache_creation_input_token_cost`, etc.) or `None` if unknown.
- `normalize_model_id(raw) -> str` — `"openai:gpt-4o"` → `"openai/gpt-4o"`, strips whitespace, leaves provider/model forms intact.
- `get_model_context_window(model) -> int` — prefers `max_input_tokens`, falls back to `max_tokens`, finally `DEFAULT_CONTEXT_WINDOW = 200_000`.
- `reset_cache()` — test hook.

**No sync `requests.get()`** (hermes anti-pattern) — LiteLLM caches model-info internally; our TTL is a thin process-local layer on top so the same ID resolved twice in one minute doesn't re-run LiteLLM's dispatch.

Phase-B P4 replaced three hardcoded lookups:

1. `middleware/summarization.py` — `MODEL_MAX_TOKENS: dict[str, int]` removed → `get_model_context_window(model)` at call site in `should_summarize` + `apply_context_management`.
2. `harness/scorer.py` — `MODEL_COST_PER_MTOK: dict[str, float]` removed → `_estimate_cost` now delegates to `estimate_usage_cost` (60/40 input/output split as rough heuristic since audit events don't preserve the split; exact costs still available via `InsightsEngine.cost_for_session`).
3. `graph/runner.py` — `_FALLBACK_MODEL_MAX_TOKENS` dict + `_fallback_model_max_tokens()` helper (introduced in P1 as a transitional shim) deleted; runner now calls `get_model_context_window(ctx.model)` directly in `_prepare_messages` for the ContextEngine stage-lookup.

## 2.C CredentialPool call-site (Phase-B P1 DONE)

**Status:** DONE — commit `09988de`.
**Cross-ref:** `exec-hermes.md §0` (CredentialPool row), plan §P1.

`llm_node.py` now calls `get_credential_pool().acquire(user_id, provider)` before each LLM call + `apply_recovery(pool, credential, classify_error(exc))` on exception + `mark_success(credential)` post-response. Rate-limit bucket uses `credential.key_id` (opaque SHA-256 prefix) instead of `_provider_label(model)` — per-key isolation.

`CredentialExhaustedError` raised when `acquire()` returns None AND user != "anonymous" — propagates through runner's top-level `except Exception` → `build_error_packet_with_failover` for user-facing SSE error.

---

## 2.11 Changelog-append (Phase-B)

| Date | Change |
|---|---|
| 2026-04-20 | exec-hermes Phase-B P1 stubs §2.C (CredentialPool call-site DONE `09988de`). Phase-B P4 stubs §2.10 (Billing Ledger) + §3.1 (model_metadata wrapper) added. |
| 2026-04-20 | Phase-B P4 DONE. `agent/billing/usage_pricing.py` (CanonicalUsage + LiteLLM-primary estimate_usage_cost + snapshot fallback), `agent/billing/insights.py` (InsightsEngine reading agent.spans, dual-path REST + harness, Tier-1 redact in aggregation), `agent/llm/model_metadata.py` (LiteLLM wrapper + 1h TTL cache). Cost span-attributes now emitted on every agent.turn. Three hardcoded model-lookup sites replaced (summarization, scorer, runner). 24 new unit tests. |
