# exec-02: Env-Files + Linux Devstack + Compose-Update

**Datum:** 17.04.2026
**Status:** ✓ done (Code), ✗ nicht in VM getestet (siehe "Verify")

## Warum

- `frontend_merger/` braucht eine `.env.local.example`, existiert nicht.
- `go-appservice/.env.example` und `python-backend/.env.example` haben
  Env-Vars die im Source-Code referenziert werden, aber nicht dokumentiert
  sind — Full-Scan + Nachtrag.
- `scripts/dev-stack3.ps1` ist Windows-only. Linux-Port fehlt.
- `docker-compose.yml` nutzt `tuwunel:latest` — User will v1.6.0-rc pinnen.
- Default-Compose-Profile hat `go-appservice` und `python-bridge` als
  Container-Builds — fuer Dev nicht sinnvoll (Hot-Reload fehlt). Die sollen
  als lokale Prozesse ueber `dev-stack.sh` laufen.

## Env-Scan Ergebnis

Vollstaendiger Scan mit:

```bash
# Frontend
grep -rhoE 'process\.env\.[A-Z_][A-Z0-9_]*' src/

# Go
grep -rhoE 'os\.Getenv\("[A-Z_]+"\)|os\.LookupEnv\(...\)|"[A-Z_]{4,}"' .

# Python (excl. .venv + experiments)
find . ... | xargs grep -hoE '(getenv|environ\.get|environ\.setdefault|environ\[)\s*\(?\s*"[A-Z_]+"'
```

### `frontend_merger/env.example.merger` (NEW, 38 keys)

Union aus Matrix-Credentials, Gateway-Base-URL, MCP, LiveKit, Tambo,
Agent-Model, E2EE-Policy, Agent-Prefix.

### `go-appservice/.env.example` (erweitert, +24 keys)

Fehlte (jetzt dokumentiert): `APP_ENV`, `ARTIFACT_STORAGE_PUBLIC_BASE_URL`,
`AUTH_JWT_SECRET`, `AUTH_SECRET`, `DATABASE_URL`, `ENVIRONMENT`,
`FILES_ALLOW_LEGACY_OWNERLESS`, `GO_ENV`, `HINDSIGHT_DB_URL`,
`INGESTION_WORKER_SHARED_SECRET`, `INGESTION_WORKER_URL`,
`MATRIX_DELETE_KEYS_AFTER_HOURS`, `MCP_SERVICE_URL`,
`MENTION_ONLY_IN_GROUPS`, `NEXTAUTH_SECRET`, `OPENOBSERVE_{ORG,PASSWORD,USER}`,
`OTEL_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`,
`POSTGRES_DSN`, `POSTGRES_URL`, `REGISTRATION_PATH`.

### `python-backend/.env.example` (erweitert, +60 keys)

Addendum-Sektion mit:
- LLM Provider Keys (ANTHROPIC, OPENAI, OPENAI_BASE_URL, FinBERT)
- Agent Skills/LangGraph/Memory (AGENT_SKILL_*, AGENT_MEMORY_ENGINE, etc.)
- Ingestion (CHUNKER_*, EMBEDDER_*, PDF_EXTRACTOR)
- KG Backends (Kuzu, SQLite, FalkorDB)
- Vector Store (PGVector, Lance)
- Hindsight API config
- MemoryFusion Engine
- Sandbox (OpenSandbox URL + Images)
- Redis, Mock-Host, OpenObserve Org

## `scripts/dev-stack.sh` — Linux Port von dev-stack3.ps1

Feature-Parity-Mapping:

| PS1 `-Flag` | SH `--flag` |
|---|---|
| `-SkipHomeserver` | `--skip-homeserver` |
| `-SkipNats` | `--skip-nats` |
| `-SkipPostgres` | `--skip-postgres` |
| `-SkipGoAppservice` | `--skip-go` |
| `-SkipPython` | `--skip-python` |
| `-SkipAgentService` | `--skip-agent` |
| `-UseMock` | `--mock` |
| `-SkipNextjs` | `--skip-nextjs` |
| `-SkipControlUi` | `--skip-control-ui` |
| `-SkipAgentChat` | `--skip-agent-chat` |
| (NEU) `-SkipMerger` | `--skip-merger` |
| `-Tuwunel16` | `--tuwunel16` (default on, wie vom User gewuenscht) |
| `-FrontendOnly` | `--frontend-only` |
| `-AgentOnly` | `--agent-only` |
| (NEU) `-MergerOnly` | `--merger-only` |
| `-Kill` | `--kill` |

Architektur:
- **Container via `podman-compose`/`docker-compose`**: tuwunel, nats, postgres
  (+ optional litellm/sandbox/seaweedfs/openobserve via Profile).
- **Lokale Prozesse**: go-appservice, python agent-service (:8094),
  python-bridge (:8097), python-ingestion (:8098), alle vier Frontends
  (3000/3001/3002/3003). Grund: Hot-Reload, Debugger, schnelles Iterieren.

Logs in `logs/devstack/<service>.log`, PIDs in `logs/devstack/pids/`.

## `docker-compose.yml` — Update

**Tuwunel:** `ghcr.io/matrix-construct/tuwunel:v1.6.0-rc` (via
`${TUWUNEL_IMAGE:-...}` Env ueberridbar auf `:latest` fallback).

**Profiles eingefuehrt (default = nichts):**
- (default) → `tuwunel`, `nats`, `postgres` (infra fuer `dev-stack.sh`)
- `--profile litellm` → `litellm` (:4000)
- `--profile sandbox` → `opensandbox-server` + `opensandbox`
- `--profile mock` → `llm-mock` (:8094 in place of Python agent)
- `--profile merger` → `frontend-merger` (fuer Container-Build Test)
- `--profile prod` → `go-appservice`, `python-bridge`, `nextjs-chat`,
  `frontend-merger`, `coturn` (containerized alles)

**Postgres uncommented:** `pgvector/pgvector:pg17` auf Port 5433.

## Verify

| Check | Status |
|---|---|
| `.env.example` diff zwischen Source-Scan + Example — alle Scanned Keys abgedeckt | ✓ |
| `scripts/dev-stack.sh` syntax-check (`bash -n`) | ✓ |
| `docker-compose.yml` YAML parse | ✓ 12 services, 5 profiles |
| Full Stack-Start | ✗ docker.io/ghcr.io 503 in VM (podman ist installiert, Registry-Egress blockiert) |

**→ Live-Verify bei User lokal auf Linux+Podman:**

```bash
cp frontend_merger/env.example.merger frontend_merger/.env.local
cp go-appservice/.env.example go-appservice/.env.development
cp python-backend/.env.example python-backend/.env

podman-compose up -d                 # tuwunel v1.6 + nats + postgres
./scripts/dev-stack.sh               # alles andere lokal
# oder: ./scripts/dev-stack.sh --merger-only
```

## Pre-existing Syntax-Bug gefixt (Bonus)

`python-backend/memory_fusion/fusion_engine.py` (commit `f14e9b81`, 16.04.2026):
der FUSION-Route Zweig in `list_documents()` war ausserhalb des `try:` Blocks
UND Lines 1451-1473 waren faelschlich innerhalb des outer `for route_name,
result in (...)` Loops (fuehrte zu `return` auf erstem Iteration-Durchgang).

Fix: Lines 1402-1449 um +4 Spaces eingeruckt (in try: gezogen), Lines 1451-1473
dedentet (aus outer for herausgezogen). `py_compile` + `ruff` clean danach.
