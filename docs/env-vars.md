# Environment Variables — Reference

Zentrale Übersicht aller Environment Variables im matrix-Stack.

**Stand**: 2026-04-17 (post-frontend_merger-merge)

## Quick-Overview: Wo welche `.env` gehört

| Datei | Scope | Generator |
|---|---|---|
| `.env` (repo-root) | docker-compose interpolation (TUWUNEL_IMAGE, POSTGRES_*, LIVEKIT_*, CLOUDFLARED_*) | Manuell + `harden-env.py` |
| `go-appservice/.env.development` | Go Appservice Runtime (Matrix-Tokens, Secrets, Storage) | Manuell + `harden-env.py` |
| `python-backend/.env` | Python Backend Runtime (API-Keys, Agent-Config, KG, Memory) | Manuell + `harden-env.py` |
| `frontend_merger/.env.local` | Next.js frontend_merger (client+server vars) | Manuell |
| `control-ui/.env.local` | Next.js control-ui standalone | Manuell |
| `nextjs-chat/.env.local` | Next.js nextjs-chat standalone | Manuell |
| `agent-chat/.env` | Next.js agent-chat standalone | Manuell |
| `python-backend/ingestion/.env` | Ingestion-Pipeline Subservice | Manuell |

Alle `.env*` Files sind in `.gitignore`, **niemals committen**.

---

## Variable-Kategorien

### 🔐 Secrets (müssen generiert/bereitgestellt werden)

| Variable | Datei | Generator | Notes |
|---|---|---|---|
| `MATRIX_AS_TOKEN` | go-appservice/.env.development | `openssl rand -hex 32` | Matrix Appservice Registration |
| `MATRIX_HS_TOKEN` | go-appservice/.env.development | `openssl rand -hex 32` | Matrix Homeserver Token |
| `MATRIX_CRYPTO_PICKLE_KEY` | go-appservice/.env.development | `openssl rand -hex 32` | E2EE SQLite Encryption |
| `MATRIX_KEY_BACKUP_PASSWORD` | go-appservice/.env.development | alphanum | Megolm Backup |
| `MATRIX_BOT_PASSWORD` | python-backend/.env | harden-env.py (alphanum) | Matrix Bot Login |
| `MATRIX_BOT_ACCESS_TOKEN` | python-backend/.env | Matrix-server generated | Provides via bot login |
| `KEY_ENCRYPTION_SECRET` | go + python (identisch!) | `python -c "import secrets; print(secrets.token_hex(32))"` | AES-GCM Vault |
| `ARTIFACT_STORAGE_SIGNING_SECRET` | go-appservice | `openssl rand -hex 32` | Signed-URL HMAC |
| `INGESTION_WORKER_SHARED_SECRET` | go + python | `openssl rand -hex 32` | Anti-SSRF Auth |
| `AUTH_JWT_SECRET` | go-appservice | `openssl rand -hex 32` | JWT-Token Signing |
| `LIVEKIT_API_KEY` | .env (root) | harden-env.py (alphanum) | LiveKit Server API |
| `LIVEKIT_API_SECRET` | .env (root) | harden-env.py (alphanum_long) | LiveKit Server API |
| `POSTGRES_PASSWORD` | .env (root) | harden-env.py (alphanum) | Postgres |
| `OPENOBSERVE_PASSWORD` | go + python | harden-env.py (alphanum) | Telemetry |
| `OPEN_SANDBOX_API_KEY` | .env (root) | `openssl rand -hex 32` | Sandbox API |
| `CLOUDFLARED_TUNNEL_TOKEN` | .env (root) | Cloudflare Dashboard | CF Tunnel |
| `ARTIFACT_STORAGE_S3_ACCESS_KEY_ID` / `_SECRET_ACCESS_KEY` | go-appservice | SeaweedFS tools/seaweedfs/s3.json | S3-compat access |

### 🔑 API-Keys (User muss providen)

| Variable | Datei | Provider |
|---|---|---|
| `ANTHROPIC_API_KEY` | python-backend/.env | console.anthropic.com |
| `OPENAI_API_KEY` | python-backend/.env | platform.openai.com |
| `OPENROUTER_API_KEY` | python-backend/.env | openrouter.ai |
| `GEMINI_API_KEY` | python-backend/.env | aistudio.google.com |
| `LANGFUSE_PUBLIC_KEY` / `_SECRET_KEY` | python-backend/.env | cloud.langfuse.com |
| `NEXT_PUBLIC_TAMBO_API_KEY` | frontend_merger/.env.local | tambo.ai |

### 🌐 Service-URLs (Defaults via `getenv(X, "http://localhost:…")`)

**Dev-Fallbacks im Code** — müssen in prod per env überschrieben werden:

| Variable | Default | Used by |
|---|---|---|
| `GO_GATEWAY_BASE_URL` | `http://127.0.0.1:8090` | python-backend, frontend_merger, control-ui |
| `AGENT_SERVICE_URL` | `http://127.0.0.1:8094` | go-appservice, python-backend |
| `MCP_SERVICE_URL` | `http://127.0.0.1:8094` | go-appservice |
| `MEMORY_SERVICE_URL` | `http://127.0.0.1:8093` | go-appservice |
| `LITELLM_BASE_URL` | `http://localhost:4000` | python-backend (bypass: direct API-keys) |
| `OPENAI_BASE_URL` | `http://localhost:8095/v1` | python-backend (Ollama fallback: `http://localhost:11434/v1`) |
| `KG_PIPELINE_URL` | `http://127.0.0.1:8099` | python-backend/ingestion |
| `EXTRACTION_LAYOUT_URL` | `http://127.0.0.1:8101` | python-backend/ingestion |
| `INGESTION_WORKER_URL` | `http://127.0.0.1:8098` | go-appservice, python-backend |
| `ARTIFACT_GATEWAY_BASE_URL` | `http://127.0.0.1:8090` | python-backend |
| `MATRIX_HOMESERVER_URL` | `http://localhost:8448` | alle (Matrix clients) |
| `MATRIX_APPSERVICE_URL` | `http://localhost:29318` | go-appservice |
| `OPENSANDBOX_SERVER_URL` | `http://127.0.0.1:8100` | python-backend |
| `NEXT_PUBLIC_MCP_URL` | `http://localhost:8090/api/v1/mcp` | frontend_merger (client-side) |
| `NEXT_PUBLIC_LK_JWT_SERVICE_URL` | `http://localhost:8080` | frontend_merger (LiveKit JWT) |

### ⚙️ Agent-Config (LangGraph / Skills / Memory)

~30 `AGENT_*` Variablen steuern LangGraph-Flow, Skill-Coverage, Memory-Engine, Summarization. Siehe `python-backend/.env.example` Zeilen 40-90 für vollständige Liste. **Alle optional** — Defaults in Code.

### 📥 Ingestion / Chunking / Embedding

| Variable | Default | Notes |
|---|---|---|
| `CHUNKER_NAME` | `sliding-window` | sliding-window / paragraph / sentence |
| `CHUNKER_SIZE` | `512` | Tokens per chunk |
| `CHUNKER_OVERLAP` | `64` | Overlap tokens |
| `EMBEDDER_PROVIDER` | `local` | local / openai / anthropic |
| `EMBEDDER_ALLOW_MODEL_DOWNLOAD` | `false` | HF model auto-download |
| `PDF_EXTRACTOR` | `pypdf` | pypdf / pdfminer |

### 🧠 KG / Vector / Memory

| Variable | Default | Notes |
|---|---|---|
| `KG_PROVIDER` | `kuzu` | kuzu / falkordb / sqlite |
| `KG_KUZU_PATH` | `./data/kg/kuzu` | Kuzu DB path |
| `KG_FALKORDB_URL` | `redis://localhost:6379` | FalkorDB (bei redis/valkey) |
| `VECTOR_STORE_PROVIDER` | — | pgvector / lance / chroma |
| `VECTOR_STORE_PATH` | `./data/vector` | Local vector DB path |
| `AGENT_MEMORY_ENGINE` | `auto` | auto / mempalace / hindsight |
| `MEMPALACE_PALACE_PATH` | `./data/memory/palace` | MemPalace storage |

### 📊 Telemetry (OpenObserve + Langfuse)

| Variable | Default | Notes |
|---|---|---|
| `OTEL_ENABLED` | `false` | Enable OTel export |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://127.0.0.1:5080/api/default` | OpenObserve endpoint |
| `OPENOBSERVE_USER` | `admin@example.com` | OpenObserve login |
| `OPENOBSERVE_ORG` | `default` | OpenObserve org |
| `LANGFUSE_ENABLED` | — | Enable Langfuse tracing |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse endpoint |

### 📋 Flags & Misc

| Variable | Default | Notes |
|---|---|---|
| `GO_ENV` | `development` | development / production |
| `APP_ENV` / `ENVIRONMENT` | — | Alternative Dev/Prod flags |
| `LOG_LEVEL` | `info` / `INFO` | go: lowercase, python: uppercase |
| `MATRIX_E2EE_ENABLED` | `false` | E2EE in Bot |
| `MATRIX_DELETE_KEYS_AFTER_DECRYPT` | `false` | Forward Secrecy |
| `MATRIX_AGENT_CAPABILITIES` | `gateway` | gateway / native |
| `FILES_ALLOW_LEGACY_OWNERLESS` | `false` | Dev-only legacy compat |
| `MENTION_ONLY_IN_GROUPS` | `false` | @-mentions policy |
| `NATS_SUBJECT_ROUTING_ENABLED` | `false` | Per-Agent NATS subjects |
| `NODE_ENV` | — | Next.js auto-set |

---

## Workflows

### 1. Initial Setup (erstmalig)

```bash
# 1. Copy examples
cp .env.example .env
cp go-appservice/.env.example go-appservice/.env.development
cp python-backend/.env.example python-backend/.env
cp frontend_merger/.env.example frontend_merger/.env.local
cp control-ui/.env.example control-ui/.env.local

# 2. Generate secrets (erweitert harden-env.py)
uv run python scripts/harden-env.py                               # python-backend/.env
uv run python scripts/harden-env.py --env-file go-appservice/.env.development
uv run python scripts/harden-env.py --env-file .env               # root

# 3. Manuelle API-Keys eintragen (ANTHROPIC/OPENAI/etc.)
nano python-backend/.env
```

### 2. Post-Merge / Neue Vars hinzugekommen

```bash
# Diff neuen .env.example mit existing .env
diff <(grep -E "^[A-Z_]+=" python-backend/.env.example | cut -d= -f1 | sort) \
     <(grep -E "^[A-Z_]+=" python-backend/.env        | cut -d= -f1 | sort)
# Fehlt was? Manuell ergänzen.
```

### 3. Validate (optional script, noch nicht implementiert)

Idee für `scripts/validate-env.py`: scannt Code für alle env-reads, prüft ob in `.env` definiert.

---

## Scheduler (exec-scheduler Phase-1)

| Variable | Datei | Default | Notes |
|---|---|---|---|
| `SCHEDULER_SERVICE_USER_ID` | python-backend/.env + go-appservice/.env.development | `scheduler-service` | Pseudo-User-ID für system-owned infra-tasks (health-ping, memory-prune, metric-rollup, etc.). Wird als `scheduler.scheduled_tasks.user_id` persistiert wenn ein Dev/Admin / System-Task eine Row anlegt (nicht via agent-chat). Keine Credentials — Infra-Tasks rufen kein LLM auf. |
| `SCHEDULER_SERVICE_API_KEY` | python-backend/.env | *optional* | Nur nötig wenn ein zukünftiger Infra-Task doch einen LLM braucht (z.B. digest-summary). Phase-1 läuft ohne. Liegt dann als Eintrag in `agent.user_credentials` mit `user_id=$SCHEDULER_SERVICE_USER_ID`, manuell via admin-tool oder bootstrap-script. |
| `SCHEDULER_JETSTREAM_STREAM` | go-appservice/.env.development + python-backend/.env | `SCHEDULER` | Name des JetStream-Streams der `matrix.scheduler.>`-Subjects persistiert. Durable-Consumer wird gegen diesen Stream in Lane C angelegt. |
| `SCHEDULER_QUEUE_GROUP` | python-backend/.env | `scheduler-exec` | NATS-JetStream Durable-Consumer Name für die Python-subscribers. Identische Namen → Queue-Group-Semantik (nur ein Worker zieht jede Message). |

---

## Security Best Practices

1. **Niemals `.env` committen** — alle in `.gitignore` (verified 2026-04-17)
2. **Secrets via `harden-env.py`** generieren, nicht manuell
3. **Secrets zwischen go + python müssen IDENTISCH sein** wo shared (z.B. `KEY_ENCRYPTION_SECRET`, `INGESTION_WORKER_SHARED_SECRET`)
4. **Rotation-Plan**: Secrets jährlich rotieren (manuell, via harden-env.py regenerate)
5. **In Prod**: Secrets via Kubernetes-Secret / Vault / SOPS-encrypted, nicht plain `.env`
6. **Keine hardcoded fallbacks** in Prod — `MATRIX_CRYPTO_PICKLE_KEY=changeme-*` muss überschrieben sein

---

## Related Tools (installed, siehe MINT-SETUP-OVERVIEW.md)

- **age** 1.1.1 — File-level encryption (für SOPS)
- **SOPS** 3.12.2 — Mozilla SOPS für encrypted `.env.enc` files (Git-safe)
- **direnv** 2.32 — Auto-load `.envrc` per-project-dir
- **pass** — Terminal password manager für secret storage
- **KeePassXC** — GUI für secret database

Für production-grade secret-management: **SOPS + age** ist der aktuelle SOTA-Weg (encrypted-in-repo, decryption via private-key, integriert in CI).
