# Env-Architecture & LLM-Routing Analysis — matrix-Stack

**Datum**: 2026-04-17
**Scope**: Deep-dive auf `python-backend/.env.development` + LLM-routing-Architecture + Hindsight-Integration
**Status**: Ist-Zustand dokumentiert, TODOs priorisiert

---

## 1. Executive Summary

Nach Refactor vom `claude/merge-frontend-chat-ui-2OqmH` Branch:

- **106 env-vars** in `python-backend/.env.development` (normal range für Agent-Platform)
- **LLM-Architecture ist SOTA**: per-user DB-keys + .env-Fallback + LiteLLM als central gateway
- **Voice umgeht LiteLLM bewusst** (Latency-Optimierung für LiveKit-Agents)
- **Hindsight bereits via LiteLLM konfiguriert** (BASE_URL=http://localhost:4000)
- **Nur 1 echter Dead-Weight**: `HUGGING_FACE_HUB_TOKEN` entfernt (duplicate zu `HF_TOKEN`)
- **Per-User-Key-Infrastructure EXISTIERT** im Code (`AESGCMVault`, `get_user_llm_settings`, `_temporary_env`), aber UI-Onboarding-Flow fehlt noch

---

## 2. Env-Var-Statistik

### Aufteilung der 106 Variablen in `.env.development`

| Kategorie | Count | Beispiele | Kann weg? |
|---|---|---|---|
| **LLM Provider Keys** | 6 | ANTHROPIC/OPENAI/OPENROUTER/GEMINI_API_KEY, HF_TOKEN, OPENAI_BASE_URL | Nein — LiteLLM-Config nutzt Wildcards |
| **Agent Behavior** | 11 | AGENT_MAX_ITERATIONS, AGENT_TOOL_TIMEOUT_SEC, AGENT_SUMMARIZE_*, AGENT_SKILL_* | Teilweise — einige Defaults matchen Code |
| **Memory/Hindsight** | 11 | HINDSIGHT_*_, MEMORY_FUSION_*_, MEMPALACE_PALACE_PATH | Meistens notwendig (Hindsight ist external package) |
| **Ingestion/Chunker/Embedder** | 12 | INGESTION_HOST/PORT, CHUNKER_*, EMBEDDER_* | Default-matching, teilweise redundant |
| **KG + Vector Store** | 7 | KG_PROVIDER, KG_KUZU_PATH, VECTOR_STORE_* | Defaults, aber dokumentarisch gut |
| **Voice/LiveKit** | 6 | AGENT_PROVIDER, AGENT_MODEL, AGENT_STT/TTS_PROVIDER, LIVEKIT_URL | Alle genutzt in voice/providers.py |
| **Matrix Bot** | 5 | MATRIX_BOT_USER_ID, _PASSWORD, _ACCESS_TOKEN, MATRIX_STORE_PATH, E2EE | Core-functionality |
| **Sandbox** | 6 | OPEN_SANDBOX_*, SANDBOX_CODE_IMAGE, CONTAINER_SOCK | Feature-abhängig |
| **Security (shared)** | 3 | KEY_ENCRYPTION_SECRET, INGESTION_WORKER_SHARED_SECRET, KEY_VAULT_BACKEND | **Shared mit go-appservice — identisch!** |
| **Telemetry** | 9 | OPENOBSERVE_*, OTEL_*, LANGFUSE_* | Feature-off default, aktivierbar |
| **Service-URLs** | 9 | NATS_URL, GO_GATEWAY, AGENT_SERVICE_URL, MATRIX_HOMESERVER_URL | Defaults, aber dev/prod-Unterschied dokumentarisch |
| **Runtime** | 7 | LOG_LEVEL, DEBUG, HOST, PORT, HF_HOME, SEAWEEDFS_HEALTH_URL | Teils system-level (bashrc) |
| **Skills** | 5 | AGENT_SKILLS_SOURCE, AGENT_SKILL_FINDER_*, SKILL_UPLOAD_DIR | Feature-spezifisch |
| **Storage Health** | 1 | SEAWEEDFS_HEALTH_URL | Nur /system/health endpoint |
| **Dev-specific Overrides** | 8 | VECTOR_STORE_MOCK, EMBEDDER_ALLOW_MODEL_DOWNLOAD, HINDSIGHT_API_SKIP_LLM_VERIFICATION | Critical für Dev-Mode |

**Industry-Vergleich**: 100±30 env-vars ist **normal** für Agent-Platforms (Kubernetes-typical apps haben 50-150 env-vars).

---

## 3. LLM-Routing-Architecture — 3-Level-Hierarchie

### Level 1 (Primär): Per-User DB-Keys
```
User-Login → control-ui "Model Settings" Tab
  ↓ User tippt Anthropic-API-Key
agent/control/user_llm.py::save_user_llm_settings
  ↓
AESGCMVault.encrypt(key, KEY_ENCRYPTION_SECRET)
  ↓
DB: user_llm_settings.encrypted_api_key

Runtime:
agent/control/user_llm.py::get_user_llm_settings(user_id)
  → AESGCMVault.decrypt → user's plaintext key
  → LiteLLM-request with user's key
```

### Level 2 (Fallback): .env System-Keys
Falls User **keine** DB-Settings hat:
```
.env: OPENROUTER_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY
  ↓
LiteLLM-Gateway (:4000) mit wildcards
  ↓
Provider API (Anthropic/OpenAI/etc.)
```

### Level 3 (Voice-Ausnahme): Direkt-Provider
```
voice/providers.py::get_llm
  → AGENT_PROVIDER (anthropic | openai | openai-compatible)
  → AGENT_MODEL
  → LiveKit-LLM-Plugin (direkt zu Provider-SDK, nicht LiteLLM)
```

**Warum Voice umgeht LiteLLM**: LiveKit-Agents-SDK braucht low-latency streaming (<500ms first-token). LiteLLM-Proxy addiert 100-300ms. Streaming-plugins reden direkt mit Provider-API.

### Hindsight-Integration (SOTA)
```env
HINDSIGHT_API_LLM_BASE_URL=http://localhost:4000   # ← LiteLLM
HINDSIGHT_API_LLM_API_KEY=sk-litellm               # ← virtual-key
HINDSIGHT_API_LLM_PROVIDER=openai                  # ← LiteLLM ist openai-compatible
```
→ Hindsight geht **bereits vollständig durch LiteLLM**. Runtime:
```python
# memory_fusion/providers.py
with _temporary_env(HINDSIGHT_API_LLM_API_KEY=user_specific_key):
    hindsight_engine.query(...)
```
`_temporary_env` ist ein Context-Manager der pro Request user-specific keys injecten kann.

---

## 4. Hindsight-Optionen (A/B/C) — Roadmap

### Option A — Shared System-Key (aktuell)
- Alle User's Hindsight-Calls nutzen **einen** LiteLLM-Virtual-Key (`sk-litellm`)
- Billing auf System-Account
- ✅ Simpel, keine Onboarding-Logik
- ❌ Kein per-user-budget / cost-tracking

### Option B — LiteLLM Virtual-Keys pro User (Mid-term)
- LiteLLM generiert `sk-alice-XXXX` mit `max_budget=$10` via `/key/generate` endpoint
- User kriegt Virtual-Key, spielt nicht direkt mit Provider-Keys
- ✅ Per-user budget enforced, cost-tracking built-in
- ✅ Keys rotierbar, LiteLLM-UI zeigt Usage
- 🟡 Braucht: LITELLM_DATABASE_URL + User-Onboarding

### Option C — User's eigene Provider-Keys direct (Long-term UI)
- User tippt **eigenen** Anthropic/OpenAI-Key in Control-UI
- AESGCMVault encrypted in DB
- `_temporary_env` injected user-key zur runtime via LiteLLM
- ✅ User zahlt selbst, keine System-Billing-Komplexität
- ❌ User braucht eigenen Provider-Account

### Empfehlung: Phasen-Ansatz
```
Phase 1 (jetzt, dev)     → Option A (sk-litellm shared, bootstrap-friendly)
Phase 2 (pre-launch)     → Option C (User-UI für own keys) + Fallback auf A
Phase 3 (scale/billing)  → Option B (LiteLLM Virtual Keys + Budget-Management)
```

**Code ist bereits vorbereitet für alle 3** — der Switch ist UI-Logik, nicht Backend-Refactor.

---

## 5. Dead-Weight-Analysis

### Entfernt (echtes Duplicate)
- ✅ `HUGGING_FACE_HUB_TOKEN` — redundant zu `HF_TOKEN` (transformers/datasets auto-detect)

### Behalten trotz "leerer" Werte (Code nutzt sie)
| Variable | Code-Referenz | Zweck |
|---|---|---|
| `ANTHROPIC_API_KEY` | `litellm-gateway/config.yaml` | Wildcard-routing `anthropic/*` |
| `OPENAI_API_KEY` | LiteLLM + `voice/providers.py` | Wildcard + direct voice |
| `GEMINI_API_KEY` | LiteLLM wildcard | Falls User Gemini aktiviert |
| `OPENAI_BASE_URL` | `voice/providers.py`, `agent/app.py` | Ollama/vLLM fallback |
| `AGENT_MODEL` | `voice/providers.py` | LiveKit-plugin selection |
| `AGENT_PROVIDER` | `voice/providers.py` | Plugin-switcher |
| `AGENT_TTS_VOICE` | `voice/providers.py` | TTS-voice-id |

### Gitnexus-verified (nichts im Code read-only ohne Grund)

---

## 6. Vendor-Lock-Assessment

| Component | Aktuelle Lösung | Risk | Mitigation |
|---|---|---|---|
| **LiveKit Server** | livekit/livekit-server (Apache 2.0) | 🟢 Low | OSS, self-hosted |
| **LiveKit Agents SDK** | Python package (Apache 2.0) | 🟢 Low | OSS |
| **LiteLLM** | BerriAI/litellm (MIT) | 🟢 Low | OSS, gateway-Architektur |
| **Hindsight** | External Python package | 🟡 Medium | Selbst-hostbar aber 1-Maintainer |
| **Kuzu** | MIT, Microsoft-backed | 🟢 Low | Embedded, OSS |
| **Tambo** | Client-lib MIT, Cloud für AI-features | 🟡 Medium | Optional — ohne API-key local-only-mode |
| **CopilotKit** | MIT | 🟢 Low | OSS, client-lib |
| **Voice STT (OpenAI-Whisper default)** | Cloud | 🔴 High | TODO: switch zu `whisper-local` als Default |
| **Voice TTS (piper)** | OSS neural TTS | 🟢 Low | Local |
| **Voice LLM (Anthropic/OpenAI direkt)** | Cloud | 🟡 Medium | TODO: `AGENT_PROVIDER=openai-compatible` + Ollama |

---

## 7. TODOs (prioritized)

### 🔴 Priority 1 — Stack-Functionality
- [ ] **OPENROUTER_API_KEY** in `python-backend/.env.development` eintragen (mindestens einer für LLM-flow)
- [ ] **Matrix-User Setup**: `./scripts/setup-users.sh` nach Tuwunel-Start ausführen
- [ ] **Integration-Test**: Full stack starten + 1 Message durchlaufen lassen
  ```bash
  podman-compose up -d tuwunel postgres nats seaweedfs
  ./scripts/dev-stack.sh
  # → Text-chat via frontend_merger :3003, Message an @agent-bot
  ```

### 🟡 Priority 2 — Dev-Quality-of-Life
- [ ] **`.env.development` vereinfachen**: Default-Werte die Code schon hat → entfernen (reduziert 106 → ~50 vars)
  - Risk: Ohne Integration-Tests bricht möglicherweise ein sub-service
  - Alternative: als Kommentar behalten (`# AGENT_MAX_ITERATIONS=10    # code default`)
- [ ] **Linux setup-users.sh testen** nach tuwunel-Start (Integration-test)
- [ ] **podman-compose config validation**: `podman-compose config --quiet` ohne errors
- [ ] **Voice stack testen**: `--profile calls` — LiveKit Room-Join mit whisper-local + piper

### 🟢 Priority 3 — Features & Polish
- [ ] **User LLM-Settings UI** in control-ui/frontend_merger implementieren (Option C)
- [ ] **LiteLLM Virtual-Keys** aktivieren (`LITELLM_DATABASE_URL` + `/key/generate` admin-flow)
- [ ] **Voice fully-local Default**: whisper-local + piper + Ollama (siehe `voice/README.md`)
- [ ] **Tambo optional**: wenn nicht genutzt, aus Provider-Stack entfernen (spart 100KB bundle)
- [ ] **OpenObserve aktivieren**: `--profile observability` + OTEL_ENABLED=true in Services

### ⚪ Priority 4 — Migration/Cloud
- [ ] **SOPS+age reaktivieren** wenn Multi-Machine oder Team (siehe exec-secrets)
- [ ] **Kubernetes-Deploy-Plan**: SealedSecrets statt .env
- [ ] **Garage als Default-Storage evaluieren**: falls 1-2GB RAM gespart werden soll (vs SeaweedFS 2-4GB)
- [ ] **NornicDB Re-evaluation Q3/Q4 2026**: wenn stabil + community wächst

---

## 8. Don't-Dos (explizite Nicht-Ziele)

### ❌ Nicht tun: SEAWEEDFS/GARAGE S3-Keys in python-backend/.env
**Grund**: Capability-based Architecture. Python-Agent darf **niemals** direkte S3-credentials haben — nur signed URLs von go-gateway. Wenn du die keys in Python-env hinzufügst, umgeht agent den Gateway → Security-Regression.

**Ausnahme**: `SEAWEEDFS_HEALTH_URL` für `/system/health` endpoint (nur URL-Ping, keine creds).

### ❌ Nicht tun: Voice durch LiteLLM routen
**Grund**: LiveKit-Agents-Plugins brauchen optimierte Streaming-connections direkt zu Provider. LiteLLM-Proxy adds 100-300ms latency → Voice-Konversation wirkt unnatürlich.

**Ausnahme später**: LiteLLM v1.50+ hat native-streaming, könnte evaluiert werden.

### ❌ Nicht tun: .env-Files committen
Alle `.env*` Files (außer `.env.example`) sind gitignored. Bei Commit: `git status` prüft, `.env`-matches sollten nicht aufs Remote.

### ❌ Nicht tun: FalkorDB aktivieren
License-Risk (RSALv2). Kuzu (MIT, embedded) ist Default und funktional gleichwertig.

### ❌ Nicht tun: HUGGING_FACE_HUB_TOKEN wieder reinnehmen
Redundant zu HF_TOKEN. transformers/datasets libs auto-detecten HF_TOKEN.

### ❌ Nicht tun: nohang-desktop aktivieren
(Separate Memory-Entry: war zu aggressiv, fror legitime Apps ein)

---

## 9. Decision-Log (diese Session)

| Entscheidung | Rationale |
|---|---|
| SOPS+age entfernt | Overkill für Solo-Dev. Plain `.env` + gitignore reicht. Tools bleiben installiert für "wenn later". |
| FinBERT: HF-API → lokal via transformers | Public model, kein Token nötig. Dependency auf `transformers` ist ok. |
| Seaweedfs vs Garage: Switch-option statt Garage-default | SeaweedFS ist production-validated (Kubeflow). Garage als opt-in für Dev. |
| NornicDB nur als `--profile kg-nornic` (opt-in) | Zu jung (v1.0.x), solo-dev projekt. Kuzu bleibt default. |
| Tuwunel v1.6.0-rc default | Ende April stable erwartet. v1.5.2 als Fallback via env-var verfügbar. |
| Tambo-key leer lassen | Local-mode funktioniert ohne, cloud-features optional. |
| 106 env-vars OK, nicht reducen jetzt | Self-documenting. Reduzierung später nach Integration-Tests. |

---

## 10. Related Files

### Dokumentation
- `docs/env-vars.md` — Vollständige Env-Var-Referenz
- `podman_lifehacks.md` — Podman-Workflow-Patterns
- `specs/execution/exec-secrets-bootstrap-2026-04-17.md` — SOPS+age-Setup (historisch, inactive)
- `specs/execution/exec-linux-setup-users-2026-04-17.md` — Matrix-User-Creation
- `python-backend/voice/README.md` — Voice-Stack + TODOs

### Scripts
- `scripts/bootstrap-env.py` — Initial `.env`-Generation + Secret-Creation (einmal)
- `scripts/sync-storage-creds.sh` — S3-Keys aus `.env` in tuwunel.toml + s3.json propagieren
- `scripts/setup-users.sh` — Matrix-User registrieren + Tokens in `.env` schreiben
- `scripts/harden-env.py` — Insecure defaults regenerieren
- `scripts/dev-stack.sh` — Native dev-apps starten

### Kritische Code-Funktionen (für LLM-Routing)
- `agent/control/user_llm.py::get_user_llm_settings` — Per-user DB key retrieval
- `agent/security/credentials.py::get_user_default_model` — Model + Key mit Fallback
- `agent/security/key_vault.py::AESGCMVault` — Encryption für stored keys
- `memory_fusion/providers.py::_temporary_env` — Context-Manager für per-request env-injection
- `memory_fusion/providers.py::create_hindsight_engine` — Hindsight-Factory
- `memory_fusion/runtime_env.py::bridge_hindsight_env` — Hindsight-env-bridging
- `agent/memory/engine.py::_bridge_env` + `get_memory_engine` — Memory-engine-factory
- `voice/providers.py::get_llm`, `get_stt`, `get_tts`, `get_vad` — Voice-plugin-factory

### Config Files
- `.env` + `.env.development` + `.env.production` (repo-root, docker-compose)
- `go-appservice/.env.development` (35 vars, 0 empty)
- `python-backend/.env.development` (106 vars, ~15 empty = API-keys)
- `frontend_merger/.env.local` (10 vars)
- `homeserver/tuwunel.v1.6.toml` (Matrix homeserver)
- `homeserver/registration.yaml` (Matrix appservice auth)
- `python-backend/litellm-gateway/config.yaml` (LiteLLM wildcard routing)

---

## 11. Final Architecture-Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  User (Browser/Element-X)                                        │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Frontend (frontend_merger :3003)                                │
│  - Matrix-client (UI)                                            │
│  - Agent-chat (Sheet overlay)                                    │
│  - Control-UI (Model-Settings → AESGCMVault → DB)                │
└──────┬────────────────────────────┬─────────────────────────────┘
       │ Matrix-Protocol             │ BFF-Routes
       ▼                             ▼
┌─────────────────┐           ┌────────────────────────────────────┐
│  Tuwunel :8448  │           │  Go-Appservice :8090                │
│  (Matrix HS)    │◄──────────┤  - Gateway (signed URLs)           │
│  + registration │ AS/HS-    │  - Storage (seaweedfs S3)           │
│  + seaweedfs    │ Tokens    │  - AESGCMVault (shared key)         │
│  (media store)  │           │  - PG artifact metadata             │
└─────────────────┘           └──┬─────────────────────────────────┘
                                 │
                                 ▼
                              ┌────────────────────────────────────┐
                              │  Python Backend                    │
                              │  ┌──────────────────────────────┐  │
                              │  │ Agent :8094 (LangGraph)      │  │
                              │  │  ├─ get_user_llm_settings    │──┼─► DB (encrypted keys)
                              │  │  └─ LiteLLM-call             │  │
                              │  └──────┬───────────────────────┘  │
                              │         │                          │
                              │         ▼                          │
                              │  ┌──────────────────────────────┐  │
                              │  │ LiteLLM :4000                │──┼─► Provider (Anthropic/OpenAI/OR/Gemini)
                              │  │ (wildcards + virtual-keys)   │  │
                              │  └──────────────────────────────┘  │
                              │                                    │
                              │  ┌──────────────────────────────┐  │
                              │  │ Hindsight (Memory)           │  │
                              │  │  └─ HINDSIGHT_API_LLM_       │──┼─► LiteLLM ↑ (same path)
                              │  │     BASE_URL=:4000           │  │
                              │  └──────────────────────────────┘  │
                              │                                    │
                              │  ┌──────────────────────────────┐  │
                              │  │ Voice Worker (LiveKit-join)  │  │
                              │  │  └─ AGENT_PROVIDER direkt    │──┼─► Provider (direct, umgeht LiteLLM)
                              │  └──────────────────────────────┘  │
                              └────────────────────────────────────┘
```

---

## 12. Zusammenfassung für Handover

**Wenn jemand diese Session liest und weiterarbeiten will**:

1. **Bootstrap**: Scripts in `scripts/` sind die Entry-Points. `bootstrap-env.py` nie wieder nötig (einmal-Setup).
2. **Daily**: `podman-compose up -d <services>` + `./scripts/dev-stack.sh` + `./scripts/setup-users.sh` (once)
3. **Secrets-Rotation**: `./scripts/harden-env.py` für insecure defaults, `./scripts/sync-storage-creds.sh` für S3-keys
4. **Voice ist optional**: `--profile calls` nur wenn gebraucht
5. **Observability ist optional**: `--profile observability` für OpenObserve
6. **106 env-vars ist normal**: nicht Panic, die meisten sind self-documenting defaults
7. **LLM-routing ist SOTA**: Code ist vorbereitet für per-user-keys, nur UI-Onboarding-Flow fehlt
