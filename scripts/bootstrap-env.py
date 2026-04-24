#!/usr/bin/env python3
"""Bootstrap all .env files for matrix stack — run once.

Creates:
- .env + .env.development + .env.production        (repo root, docker-compose)
- go-appservice/.env.development + .env.production
- python-backend/.env + .env.development + .env.production
- frontend_merger/.env.development + .env.local + .env.production
- control-ui/.env.development + .env.local + .env.production
- homeserver/registration.yaml                     (Matrix AS config)
- secrets/stack.yaml                               (SOPS master, plain yet)

Reads existing generated secrets from /tmp/secrets.json.
Preserves existing API-Keys (never overwrites).

Usage:
    python3 scripts/bootstrap-env.py [--dry-run]
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SECRETS_JSON = Path("/tmp/secrets.json")
DRY = "--dry-run" in sys.argv

if not SECRETS_JSON.exists():
    print("ERROR: /tmp/secrets.json not found. Run secrets-gen.py first.")
    sys.exit(1)

S = json.loads(SECRETS_JSON.read_text())

# ─── Existing API-Keys preservation ────────────────────────────────────────
# Try to extract existing API keys from old .env (so we don't lose them).
def read_env(path: Path) -> dict:
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result

existing_py = read_env(REPO / "python-backend" / ".env")
existing_go = read_env(REPO / "go-appservice" / ".env.development")

# Pull user-provided API keys (keep them if set)
api_keys = {
    "ANTHROPIC_API_KEY":   existing_py.get("ANTHROPIC_API_KEY", ""),
    "OPENAI_API_KEY":      existing_py.get("OPENAI_API_KEY", ""),
    "OPENROUTER_API_KEY":  existing_py.get("OPENROUTER_API_KEY", ""),
    "GEMINI_API_KEY":      existing_py.get("GEMINI_API_KEY", ""),
    # Generic HuggingFace token (used by transformers, datasets libs)
    "HF_TOKEN": existing_py.get("HF_TOKEN", ""),
    "LANGFUSE_PUBLIC_KEY": existing_py.get("LANGFUSE_PUBLIC_KEY", ""),
    "LANGFUSE_SECRET_KEY": existing_py.get("LANGFUSE_SECRET_KEY", ""),
    "NEXT_PUBLIC_TAMBO_API_KEY": "",
    "CLOUDFLARED_TUNNEL_TOKEN": "",
}

# ─── File templates ────────────────────────────────────────────────────────
# Ports in dev-mode (native):
#   tuwunel :8448 | nats :4222 | postgres :5433 | seaweedfs :8333 (S3)
#   go-appservice :8090 (gateway) / :29318 (matrix AS endpoint)
#   python agent :8094 | ingestion :8098 | memory :8093 | extraction :8101 | kg :8099
#   litellm :4000 | opensandbox :8100 | livekit :7880 | lk-jwt :8080
#   frontend_merger :3003 | nextjs-chat :3000 | agent-chat :3001 | control-ui :3002

def write(path: Path, content: str, mode: int = 0o600):
    if DRY:
        print(f"[DRY] would write {path} ({len(content)} chars)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)
    print(f"[OK] {path} ({len(content.splitlines())} lines, mode {oct(mode)[2:]})")

# ════════════════════════════════════════════════════════════════════════════
# FILE 1: go-appservice/.env.development  (NATIVE DEV — localhost)
# ════════════════════════════════════════════════════════════════════════════
go_dev = f"""# go-appservice — Native Development Mode (localhost)
# Used by: scripts/dev-stack.sh when starting go-appservice native (not container)
# For container-mode: use .env.production (service-names)

GO_ENV=development
LOG_LEVEL=info

# ─── Matrix Homeserver ─────────────────────────────────────────────────────
MATRIX_HOMESERVER_URL=http://localhost:8448
MATRIX_SERVER_NAME=matrix.local

# Appservice endpoint (wie Tuwunel den go-appservice erreicht)
MATRIX_APPSERVICE_URL=http://localhost:29318
MATRIX_APPSERVICE_PORT=29318

# ─── Matrix AS Tokens (Appservice Auth) ────────────────────────────────────
# MÜSSEN identisch in homeserver/registration.yaml sein!
MATRIX_AS_TOKEN={S['MATRIX_AS_TOKEN']}
MATRIX_HS_TOKEN={S['MATRIX_HS_TOKEN']}

# ─── Matrix Bot Identity ───────────────────────────────────────────────────
MATRIX_BOT_USER_ID=@appservice-bot:matrix.local
MATRIX_AGENT_PREFIX=agent-
MATRIX_AGENT_CAPABILITIES=gateway

# ─── E2EE Configuration ────────────────────────────────────────────────────
MATRIX_E2EE_ENABLED=false
MATRIX_CRYPTO_DB_PATH=./data/crypto.sqlite3
MATRIX_CRYPTO_PICKLE_KEY={S['MATRIX_CRYPTO_PICKLE_KEY']}
MATRIX_KEY_BACKUP_PASSWORD={S['MATRIX_KEY_BACKUP_PASSWORD']}
MATRIX_DELETE_KEYS_AFTER_DECRYPT=false

# ─── Mentions & Routing ─────────────────────────────────────────────────────
MENTION_ONLY_IN_GROUPS=false
NATS_SUBJECT_ROUTING_ENABLED=false

# ─── Service URLs (native-dev all localhost) ───────────────────────────────
NATS_URL=nats://localhost:4222
AGENT_SERVICE_URL=http://127.0.0.1:8094
MEMORY_SERVICE_URL=http://127.0.0.1:8093
MCP_SERVICE_URL=http://127.0.0.1:8094
INGESTION_WORKER_URL=http://127.0.0.1:8098

# ─── Database (Postgres via container on :5433) ────────────────────────────
HINDSIGHT_DB_URL=postgres://postgres:{S['POSTGRES_PASSWORD']}@localhost:5433/hindsight_dev
POSTGRES_DSN=postgres://postgres:{S['POSTGRES_PASSWORD']}@localhost:5433/hindsight_dev

# ─── Security Secrets (shared with python-backend!) ────────────────────────
KEY_ENCRYPTION_SECRET={S['KEY_ENCRYPTION_SECRET']}
KEY_VAULT_BACKEND=aesgcm
INGESTION_WORKER_SHARED_SECRET={S['INGESTION_WORKER_SHARED_SECRET']}
AUTH_JWT_SECRET={S['AUTH_JWT_SECRET']}

# ─── Artifact Storage (SeaweedFS via container on :8333) ───────────────────
ARTIFACT_STORAGE_PROVIDER=seaweedfs
ARTIFACT_STORAGE_BASE_DIR=./data/storage/objects
ARTIFACT_STORAGE_S3_ENDPOINT=http://localhost:8333
ARTIFACT_STORAGE_S3_REGION=us-east-1
ARTIFACT_STORAGE_S3_BUCKET=matrix-artifacts
ARTIFACT_STORAGE_S3_ACCESS_KEY_ID=seaweedfs
ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY=seaweedfs-secret
ARTIFACT_STORAGE_S3_USE_PATH_STYLE=true
ARTIFACT_STORAGE_S3_CREATE_BUCKET=true
ARTIFACT_STORAGE_SIGNING_SECRET={S['ARTIFACT_STORAGE_SIGNING_SECRET']}
ARTIFACT_STORAGE_SIGNED_URL_TTL_MS=900000

# ─── Files Access (Dev-only Legacy) ────────────────────────────────────────
FILES_ALLOW_LEGACY_OWNERLESS=true

# ─── Registration Path (Matrix Appservice) ─────────────────────────────────
REGISTRATION_PATH=./homeserver/registration.yaml

# ─── Telemetry (disabled in dev) ───────────────────────────────────────────
OTEL_ENABLED=false
# OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:5080/api/default
# OPENOBSERVE_USER=admin@example.com
# OPENOBSERVE_PASSWORD={S['OPENOBSERVE_PASSWORD']}
# OPENOBSERVE_ORG=default
"""
write(REPO / "go-appservice" / ".env.development", go_dev)

# ════════════════════════════════════════════════════════════════════════════
# FILE 2: go-appservice/.env.production  (CONTAINER MODE — service-names)
# ════════════════════════════════════════════════════════════════════════════
go_prod = go_dev.replace(
    "http://localhost:8448", "http://tuwunel:8448"
).replace(
    "http://localhost:29318", "http://go-appservice:29318"
).replace(
    "nats://localhost:4222", "nats://nats:4222"
).replace(
    "http://127.0.0.1:8094", "http://agent-service:8094"
).replace(
    "http://127.0.0.1:8093", "http://memory-service:8093"
).replace(
    "http://127.0.0.1:8098", "http://ingestion:8098"
).replace(
    "@localhost:5433", "@postgres:5432"
).replace(
    "http://localhost:8333", "http://seaweedfs:8333"
).replace(
    "GO_ENV=development", "GO_ENV=production"
).replace(
    "# go-appservice — Native Development Mode (localhost)",
    "# go-appservice — Container Production Mode (service-names)"
).replace(
    "FILES_ALLOW_LEGACY_OWNERLESS=true",
    "FILES_ALLOW_LEGACY_OWNERLESS=false"
).replace(
    "MATRIX_E2EE_ENABLED=false",
    "MATRIX_E2EE_ENABLED=true"
)
write(REPO / "go-appservice" / ".env.production", go_prod)

# ════════════════════════════════════════════════════════════════════════════
# FILE 3: python-backend/.env  (default, kept for backwards compat)
# FILE 4: python-backend/.env.development  (NATIVE DEV)
# FILE 5: python-backend/.env.production   (CONTAINER PROD)
# ════════════════════════════════════════════════════════════════════════════
py_dev = f"""# python-backend — Native Development Mode
# Service runs locally via `scripts/dev-stack.sh` (not in container)

# ─── LLM Provider Keys (USER MUST PROVIDE — leave empty if unused) ─────────
ANTHROPIC_API_KEY={api_keys['ANTHROPIC_API_KEY']}
OPENAI_API_KEY={api_keys['OPENAI_API_KEY']}
OPENROUTER_API_KEY={api_keys['OPENROUTER_API_KEY']}
GEMINI_API_KEY={api_keys['GEMINI_API_KEY']}
# Generic HuggingFace token (transformers/datasets libs auto-detect)
HF_TOKEN={api_keys['HF_TOKEN']}
OPENAI_BASE_URL=

# ─── LiteLLM Gateway (wenn via --profile litellm gestartet) ────────────────
LITELLM_BASE_URL=http://localhost:4000
LITELLM_PORT=4000
AGENT_DEFAULT_UTILITY_MODEL=claude-3-haiku-20240307

# ─── Agent Core (LangGraph exec-10) ────────────────────────────────────────
AGENT_USE_LANGGRAPH=true
AGENT_MODEL=
AGENT_PROVIDER=
AGENT_MAX_ITERATIONS=10
AGENT_TOOL_TIMEOUT_SEC=30
AGENT_TIMEOUT_SEC=120
AGENT_SKILL_EVOLUTION=false
AGENT_PRM_ENABLED=false
AGENT_AUTO_MIGRATE=true
AGENT_PROMPT_GUARD_ENABLED=false

# ─── Summarization ─────────────────────────────────────────────────────────
AGENT_SUMMARIZE_THRESHOLD=0.7
AGENT_SUMMARIZE_KEEP_MESSAGES=20
AGENT_SUMMARIZE_MODEL=claude-3-haiku-20240307
AGENT_TOOL_RESULT_MAX_CHARS=2000

# ─── Skills ─────────────────────────────────────────────────────────────────
AGENT_SKILLS_SOURCE=filesystem
AGENT_SKILL_FINDER_TOP_K=3
AGENT_SKILL_FINDER_MAX_TOKENS=2000
AGENT_SKILL_REFINE_MODE=compose
SKILL_UPLOAD_DIR=/tmp/skill-uploads

# ─── Memory Engine (exec-11 Hindsight) ─────────────────────────────────────
HINDSIGHT_DB_URL=postgresql://postgres:{S['POSTGRES_PASSWORD']}@localhost:5433/hindsight_dev
HINDSIGHT_SYNC_TASKS=false
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_BASE_URL=http://localhost:4000
HINDSIGHT_API_LLM_API_KEY=sk-litellm
HINDSIGHT_API_EMBEDDINGS_PROVIDER=local
HINDSIGHT_API_RERANKER_PROVIDER=local
HINDSIGHT_API_SKIP_LLM_VERIFICATION=true
HINDSIGHT_API_LAZY_RERANKER=true

# ─── Memory Fusion (exec-15) ───────────────────────────────────────────────
AGENT_MEMORY_ENGINE=auto
MEMORY_FUSION_SUMMARY_LLM_PROVIDER=inherit
MEMORY_FUSION_VERBATIM_LLM_PROVIDER=inherit
MEMORY_FUSION_SUMMARY_EXTRACTION_MODE=concise
MEMORY_FUSION_VERBATIM_EXTRACTION_MODE=detailed
MEMPALACE_PALACE_PATH=./data/memory/palace

# ─── Vector Store & KG ─────────────────────────────────────────────────────
KG_PROVIDER=kuzu
KG_KUZU_PATH=./data/kg/kuzu
KG_SQLITE_PATH=./data/kg/kg.sqlite3
VECTOR_STORE_PROVIDER=chroma
VECTOR_STORE_PATH=./data/chroma
VECTOR_STORE_MOCK=true
MEMORY_CACHE_PROVIDER=local

# ─── Ingestion Pipeline ────────────────────────────────────────────────────
INGESTION_HOST=127.0.0.1
INGESTION_PORT=8098
INGESTION_WORKER_URL=http://localhost:8098
INGESTION_WORKER_SHARED_SECRET={S['INGESTION_WORKER_SHARED_SECRET']}
ARTIFACT_GATEWAY_BASE_URL=http://localhost:8090
PDF_EXTRACTOR=pymupdf4llm
CHUNKER_NAME=token
CHUNKER_SIZE=500
CHUNKER_OVERLAP=50
EMBEDDER_PROVIDER=local
EMBEDDER_ALLOW_MODEL_DOWNLOAD=true
ALLOW_MODEL_DOWNLOADS=true
EXTRACTION_LAYOUT_URL=http://localhost:8101
EXTRACTION_LAYOUT_ENABLED=false
EXTRACTION_LAYOUT_TIMEOUT_S=30
KG_PIPELINE_URL=http://localhost:8099
KG_PIPELINE_ENABLED=false

# ─── Sandbox (exec-12) ─────────────────────────────────────────────────────
OPENSANDBOX_SERVER_URL=http://localhost:8100
OPEN_SANDBOX_URL=http://localhost:8100
OPEN_SANDBOX_API_KEY={S['OPEN_SANDBOX_API_KEY']}
SANDBOX_CODE_IMAGE=opensandbox/code-interpreter:v1.0.2
SANDBOX_BROWSER_IMAGE=tradeview/sandbox-browser:v1
SANDBOX_TOOL_TIMEOUT_SEC=1800
CONTAINER_SOCK=/run/user/1002/podman/podman.sock

# ─── Networking & Service Discovery ────────────────────────────────────────
NATS_URL=nats://localhost:4222
MATRIX_HOMESERVER_URL=http://localhost:8448
GO_GATEWAY_BASE_URL=http://localhost:8090
AGENT_SERVICE_URL=http://localhost:8094
ALLOWED_HOMESERVERS=matrix.local

# ─── Matrix Bot Identity ───────────────────────────────────────────────────
MATRIX_BOT_USER_ID=@agent-bot:matrix.local
MATRIX_BOT_PASSWORD={S['MATRIX_BOT_PASSWORD']}
MATRIX_BOT_ACCESS_TOKEN=
MATRIX_STORE_PATH=./data/matrix_store
MATRIX_E2EE_ENABLED=false

# ─── Voice & Audio ─────────────────────────────────────────────────────────
AGENT_STT_PROVIDER=off
AGENT_TTS_PROVIDER=piper
AGENT_TTS_VOICE=
WHISPER_MODEL=base
LIVEKIT_URL=ws://localhost:7880

# ─── Security (identical to go-appservice KEY_ENCRYPTION_SECRET!) ──────────
KEY_ENCRYPTION_SECRET={S['KEY_ENCRYPTION_SECRET']}
KEY_VAULT_BACKEND=aesgcm

# ─── Observability ─────────────────────────────────────────────────────────
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:5081
OPENOBSERVE_USER=admin@example.com
OPENOBSERVE_PASSWORD={S['OPENOBSERVE_PASSWORD']}
OPENOBSERVE_ORG=default

LANGFUSE_ENABLED=false
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY={api_keys['LANGFUSE_PUBLIC_KEY']}
LANGFUSE_SECRET_KEY={api_keys['LANGFUSE_SECRET_KEY']}

# ─── Logging & Runtime ─────────────────────────────────────────────────────
LOG_LEVEL=INFO
DEBUG=false
GRPC_ENABLED=0
HOST=0.0.0.0
PORT=8000

# ─── HuggingFace cache (HDD-route via user bashrc env, fallback) ───────────
HF_HOME=/mnt/cold-storage/models/huggingface
"""
write(REPO / "python-backend" / ".env.development", py_dev)

# python-backend/.env — alias of .env.development (for legacy/default load)
write(REPO / "python-backend" / ".env", py_dev)

# python-backend/.env.production — container-mode
py_prod = py_dev.replace(
    "http://localhost:4000", "http://litellm:4000"
).replace(
    "@localhost:5433", "@postgres:5432"
).replace(
    "http://localhost:8098", "http://ingestion:8098"
).replace(
    "http://localhost:8090", "http://go-appservice:8090"
).replace(
    "http://localhost:8101", "http://extraction-layout:8101"
).replace(
    "http://localhost:8099", "http://kg-pipeline:8099"
).replace(
    "http://localhost:8100", "http://opensandbox:8100"
).replace(
    "nats://localhost:4222", "nats://nats:4222"
).replace(
    "http://localhost:8448", "http://tuwunel:8448"
).replace(
    "http://localhost:8094", "http://agent-service:8094"
).replace(
    "ws://localhost:7880", "ws://livekit-server:7880"
).replace(
    "http://localhost:5081", "http://openobserve:5081"
).replace(
    "INGESTION_HOST=127.0.0.1", "INGESTION_HOST=0.0.0.0"
).replace(
    "DEBUG=false\nGRPC_ENABLED=0", "DEBUG=false\nGRPC_ENABLED=1"
).replace(
    "# python-backend — Native Development Mode",
    "# python-backend — Container Production Mode (service-names)"
)
write(REPO / "python-backend" / ".env.production", py_prod)

# ════════════════════════════════════════════════════════════════════════════
# FILE 6: frontend_merger/.env.development  + .env.local + .env.production
# ════════════════════════════════════════════════════════════════════════════
fe_merger_dev = f"""# frontend_merger — Development (localhost)
# Next.js loads: .env.development + .env.local (overrides)

# ─── Matrix Credentials (server-side SSR on /matrix route) ─────────────────
# Leer lassen → /matrix zeigt Config-Hinweis statt Chat
MATRIX_HOMESERVER_URL=http://localhost:8448
MATRIX_USER_ID=@alice:matrix.local
MATRIX_ACCESS_TOKEN=
MATRIX_DEVICE_ID=

# ─── Go Gateway (BFF-Routes proxy target) ──────────────────────────────────
GO_GATEWAY_BASE_URL=http://127.0.0.1:8090

# ─── MCP Endpoint (client-side) ────────────────────────────────────────────
NEXT_PUBLIC_MCP_URL=http://localhost:8090/api/v1/mcp

# ─── LiveKit JWT Service (for Voice/Video Calls) ───────────────────────────
NEXT_PUBLIC_LK_JWT_SERVICE_URL=http://localhost:8082

# ─── Agent Namespace Prefix ────────────────────────────────────────────────
NEXT_PUBLIC_MATRIX_AGENT_PREFIX=agent-

# ─── E2EE Verification Policy ──────────────────────────────────────────────
NEXT_PUBLIC_E2EE_BLACKLIST_UNVERIFIED=false

# ─── Tambo Generative UI ───────────────────────────────────────────────────
NEXT_PUBLIC_TAMBO_API_KEY={api_keys['NEXT_PUBLIC_TAMBO_API_KEY']}

# ─── Agent Completion Model Override ───────────────────────────────────────
AGENT_COMPLETION_MODEL=
"""
write(REPO / "frontend_merger" / ".env.development", fe_merger_dev)
write(REPO / "frontend_merger" / ".env.local", fe_merger_dev)  # developer-override

fe_merger_prod = fe_merger_dev.replace(
    "http://localhost:8448", "http://tuwunel:8448"
).replace(
    "http://127.0.0.1:8090", "http://go-appservice:8090"
).replace(
    "http://localhost:8090", "http://go-appservice:8090"
).replace(
    "http://localhost:8082", "http://lk-jwt:8080"
).replace(
    "# frontend_merger — Development (localhost)",
    "# frontend_merger — Production (container service-names)"
)
write(REPO / "frontend_merger" / ".env.production", fe_merger_prod)

# ════════════════════════════════════════════════════════════════════════════
# FILE 7: control-ui/.env.development + .env.local + .env.production
# ════════════════════════════════════════════════════════════════════════════
ctrl_dev = """# control-ui — Development (localhost)
# Kept for standalone usage; in merger-mode frontend_merger has its own env.

GO_GATEWAY_BASE_URL=http://127.0.0.1:8090
# DEV_DEFAULT_USER=alice
"""
write(REPO / "control-ui" / ".env.development", ctrl_dev)
write(REPO / "control-ui" / ".env.local", ctrl_dev)

write(REPO / "control-ui" / ".env.production",
      "# control-ui — Production (container)\nGO_GATEWAY_BASE_URL=http://go-appservice:8090\n")

# ════════════════════════════════════════════════════════════════════════════
# FILE 8: Repo root .env, .env.development, .env.production (docker-compose)
# ════════════════════════════════════════════════════════════════════════════
root_env = f"""# Matrix Stack — Root .env (docker-compose interpolation)
# Default loaded by podman-compose when in repo-root.
# Symlink/copy of .env.development for dev-mode.

# Tuwunel Matrix Homeserver — default v1.6.0-rc
TUWUNEL_IMAGE=ghcr.io/matrix-construct/tuwunel:v1.6.0-rc
# TUWUNEL_IMAGE=ghcr.io/matrix-construct/tuwunel:v1.5.2    # stable fallback

# Postgres (pgvector:pg17 on :5433)
POSTGRES_USER=postgres
POSTGRES_PASSWORD={S['POSTGRES_PASSWORD']}
POSTGRES_DB=hindsight_dev

# OpenSandbox Code Execution
OPEN_SANDBOX_API_KEY={S['OPEN_SANDBOX_API_KEY']}
# Podman rootless socket path (check `podman info | grep remoteSocket`):
CONTAINER_SOCK=/run/user/1002/podman/podman.sock

# LiveKit (Video/Voice Calls — profile=calls)
LIVEKIT_API_KEY={S['LIVEKIT_API_KEY']}
LIVEKIT_API_SECRET={S['LIVEKIT_API_SECRET']}

# Cloudflare Tunnel (profile=tunnel) — needs user-provided token
CLOUDFLARED_TUNNEL_TOKEN={api_keys['CLOUDFLARED_TUNNEL_TOKEN']}
"""
write(REPO / ".env", root_env)
write(REPO / ".env.development", root_env)

# Production root env
root_prod = root_env.replace(
    "v1.6.0-rc", "v1.5.2"  # prefer stable in prod
)
write(REPO / ".env.production", root_prod)

# ════════════════════════════════════════════════════════════════════════════
# FILE 9: homeserver/registration.yaml (Matrix AS config for tuwunel)
# ════════════════════════════════════════════════════════════════════════════
registration = f"""# Matrix Appservice Registration — generated by bootstrap-env.py
# Referenced by homeserver/tuwunel.*.toml as appservices source.
# AS_TOKEN/HS_TOKEN MUST match go-appservice/.env.* exactly!

id: matrix-appservice
url: http://localhost:29318  # dev-mode; prod uses http://go-appservice:29318
as_token: {S['MATRIX_AS_TOKEN']}
hs_token: {S['MATRIX_HS_TOKEN']}
sender_localpart: appservice-bot
namespaces:
  users:
    - exclusive: true
      regex: "@agent-.*:matrix\\\\.local"
    - exclusive: true
      regex: "@appservice-bot:matrix\\\\.local"
  aliases: []
  rooms: []
rate_limited: false
protocols: []
"""
write(REPO / "homeserver" / "registration.yaml", registration, mode=0o644)

# ════════════════════════════════════════════════════════════════════════════
# FILE 10: secrets/stack.yaml (SOPS master — plain; encrypted in next step)
# ════════════════════════════════════════════════════════════════════════════
import yaml  # noqa

master = {
    "shared": {
        "KEY_ENCRYPTION_SECRET":           S["KEY_ENCRYPTION_SECRET"],
        "INGESTION_WORKER_SHARED_SECRET":  S["INGESTION_WORKER_SHARED_SECRET"],
    },
    "go_appservice": {
        "MATRIX_AS_TOKEN":                 S["MATRIX_AS_TOKEN"],
        "MATRIX_HS_TOKEN":                 S["MATRIX_HS_TOKEN"],
        "MATRIX_CRYPTO_PICKLE_KEY":        S["MATRIX_CRYPTO_PICKLE_KEY"],
        "MATRIX_KEY_BACKUP_PASSWORD":      S["MATRIX_KEY_BACKUP_PASSWORD"],
        "ARTIFACT_STORAGE_SIGNING_SECRET": S["ARTIFACT_STORAGE_SIGNING_SECRET"],
        "AUTH_JWT_SECRET":                 S["AUTH_JWT_SECRET"],
    },
    "python_backend": {
        "MATRIX_BOT_PASSWORD":             S["MATRIX_BOT_PASSWORD"],
        "OPEN_SANDBOX_API_KEY":            S["OPEN_SANDBOX_API_KEY"],
        # API keys kept here too (even if empty) so they're centrally managed
        "ANTHROPIC_API_KEY":               api_keys["ANTHROPIC_API_KEY"],
        "OPENAI_API_KEY":                  api_keys["OPENAI_API_KEY"],
        "OPENROUTER_API_KEY":              api_keys["OPENROUTER_API_KEY"],
        "GEMINI_API_KEY":                  api_keys["GEMINI_API_KEY"],
        "LANGFUSE_PUBLIC_KEY":             api_keys["LANGFUSE_PUBLIC_KEY"],
        "LANGFUSE_SECRET_KEY":             api_keys["LANGFUSE_SECRET_KEY"],
    },
    "root": {
        "POSTGRES_PASSWORD":               S["POSTGRES_PASSWORD"],
        "OPENOBSERVE_PASSWORD":            S["OPENOBSERVE_PASSWORD"],
        "LIVEKIT_API_KEY":                 S["LIVEKIT_API_KEY"],
        "LIVEKIT_API_SECRET":              S["LIVEKIT_API_SECRET"],
        "CLOUDFLARED_TUNNEL_TOKEN":        api_keys["CLOUDFLARED_TUNNEL_TOKEN"],
    },
}
master_yaml = yaml.safe_dump(master, default_flow_style=False, sort_keys=False)
write(REPO / "secrets" / "stack.yaml", master_yaml, mode=0o600)

print()
print("═" * 60)
print("  Bootstrap komplett.")
print("═" * 60)
print(f"  Files erstellt/updated in: {REPO}")
print(f"  Master secrets (pre-SOPS): {REPO/'secrets'/'stack.yaml'}")
print()
print("  Next steps:")
print("    1. .gitignore: add 'secrets/stack.yaml' (UNENCRYPTED)")
print("    2. age-keygen, .sops.yaml setup")
print("    3. sops -e secrets/stack.yaml > secrets/stack.enc.yaml")
print("    4. rm secrets/stack.yaml (plain)")
