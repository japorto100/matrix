# Postgres-Architektur — matrix-Stack

**Datum**: 2026-04-17 (Bootstrap) · Revision 2026-04-17 (PgBouncer + Exporter + Backup aktiviert)
**Scope**: Postgres-Setup, Review ChatGPT-Postgres-Empfehlungen, Tuning, Extensions, Prod-Readiness
**Status**: ✅ Dev-tuning + Extensions + PgBouncer (`--profile pooler`) + postgres-exporter (`--profile observability`) + Backup-script aktiv

---

## 0. Context

Nach einem separaten Gespräch mit ChatGPT wurde die Frage aufgeworfen ob matrix-Stack auf den "2026 Postgres-Stack" (Postgres + PgBouncer + PostgREST + Meilisearch) umgestellt werden sollte. Dieses Dokument evaluiert jede Empfehlung gegen unsere **Matrix-AI-Agent-Platform-Domain**.

**TL;DR**: ChatGPT's Text ist **solide für generischen SaaS**, aber teilweise **nicht passend** für matrix-Repo. Einige gute Ideen übernommen, mehrere Empfehlungen wären **Security-Regression** oder **Duplikation**.

---

## 1. Was der ChatGPT-Text richtig findet ✅

### 1.1 pgvector als default für Embeddings
**Bei uns bereits drin**: `postgres` service nutzt `pgvector/pgvector:pg17` Image. Hindsight + memory_fusion nutzen produktiv.

### 1.2 PgBouncer als Default-Pooler (statt Pgpool-II) — ✅ **ADDED**
**Im docker-compose als `--profile pooler`**. Session-Pool-Mode als sicherer Default (zero breaking changes).

Research bestätigt: PgBouncer ist **ultra-leicht** (~2MB RAM per 1,000 Clients, ~128MB container-overhead, 0.05-0.1 CPU cores). Benefit auch im Dev spürbar, wenn mehrere services concurrent queries machen.

- **Image**: `edoburu/pgbouncer:1.24.1-p1` (Env-var-only config, Alpine-based)
- **Pool-Mode**: `session` default → alles funktioniert (LISTEN/NOTIFY, prepared statements, session vars)
- **Switch zu transaction-mode** später via `PGBOUNCER_POOL_MODE=transaction` env-var (benötigt `prepared_statements=false` in pgxpool/asyncpg)
- **Port**: :6432 (separate von Postgres :5433)

Siehe Sektion 4 für Aktivierungs-Commands + Benchmark-Zahlen.

### 1.3 `pg_stat_statements` von Tag 1
**Übernommen** ✅ — jetzt aktiv via `shared_preload_libraries=pg_stat_statements`.

### 1.4 SKIP LOCKED für Queues
**Bereits in matrix genutzt**: `alembic/versions/002_ingestion_jobs.py` hat Jobs-Tabelle. Ingestion-Worker sollte `FOR UPDATE SKIP LOCKED` im dequeue-pattern nutzen (zu verifizieren in Code).

### 1.5 Transaction-Pooling Quirks (prepared_statements=false)
**Dokumentarisch wertvoll** für falls wir PgBouncer adden. Dann: in `go-appservice/pgxpool` + Python-asyncpg entsprechend config'en.

---

## 2. Was der Text **NICHT** zu matrix passt ❌

### 2.1 PostgREST für **uns überflüssig**

ChatGPT's Use-Case: **CRUD-APIs direkt aus DB + RLS für multi-tenant User-Data**.

Unser Use-Case: **Matrix-Bot + AI-Agent + Memory-Engine**. Wir haben bereits:
- `go-appservice` als API-Gateway mit **capability-based security** (signed URLs)
- `python-backend/agent` mit LangGraph-based Agent-Control
- `control-ui` REST-routes für Admin-UI
- `frontend_merger` BFF-Routes

Wenn wir PostgREST einführen würden:
- 🔴 **Security-Regression**: PostgREST greift direkt auf DB zu, umgeht unser capability-based-pattern
- 🔴 **Duplikation**: wir haben bereits API-layer
- 🟡 Könnte für **future user-facing CRUD** sinnvoll sein (z.B. "My Documents" UI), aber **nicht** für Agent/Memory/Matrix-API

**Verdict**: **Nein** für jetzt. Falls später User-CRUD-heavy UI → evtl. für einzelnen sub-service.

### 2.2 Meilisearch **redundant zu Hindsight**

Hindsight macht bereits (im Code verifiziert):
- Semantic search (pgvector)
- BM25 keyword search
- Graph-traversal-search (link expansion)
- Temporal search
- **Reciprocal Rank Fusion** aller 4 Strategien
- Cross-encoder reranking

Meilisearch würde **nicht mithalten** im Memory-Search-Szenario.

**Mögliche Use-Cases für Meilisearch später**:
- File-Browser / Document-Library-UX (nicht Memory)
- Admin-Console search
- User-facing Search-Bar-UX

**Verdict**: **Nein jetzt**. Hindsight ist specialized. Für andere Search-UX evtl. später.

### 2.3 "Redis ersetzen" — unser NATS+Postgres Pattern ist moderner

ChatGPT empfiehlt Postgres als Redis-Queue-Ersatz via SKIP LOCKED.

**Bei uns**:
- **NATS** für async messaging (event-driven)
- **Postgres** für persistent job-state (ingestion_jobs Tabelle)
- **Valkey** als optional `--profile cache` (in-memory)

Das ist **moderner split** als "alles in Postgres". NATS hat Ordnungs-Garantien + Replay + Subjects die Postgres nicht natürlich bietet.

### 2.4 Compose-Default passt nicht

ChatGPT's Stack: `postgres + pgbouncer + postgrest + meilisearch`
Unser Stack: `postgres + tuwunel + nats + seaweedfs + go-appservice + python-backend + ...`

Völlig andere Domain — Chat-Platform mit AI-Agent.

---

## 3. Konkret übernommen — jetzt aktiv ✅

### 3.1 docker-compose.yml postgres service — Dev-Tuning

```yaml
postgres:
  image: pgvector/pgvector:pg17
  command:
    - postgres
    - -c
    - shared_preload_libraries=pg_stat_statements    # Query-transparency
    - -c
    - max_connections=200                             # 5+ services ok
    - -c
    - shared_buffers=512MB                            # bei 8GB RAM konservativ
    - -c
    - effective_cache_size=2GB                        # reflects host RAM
    - -c
    - work_mem=16MB                                   # per query
    - -c
    - maintenance_work_mem=128MB                      # VACUUM/REINDEX
    - -c
    - random_page_cost=1.1                            # SSD-optimal (vs default 4)
    - -c
    - track_io_timing=on                              # disk I/O stats
    - -c
    - pg_stat_statements.track=all                    # alle statements tracked
    - -c
    - wal_level=replica                               # minimum für pg_dump + future-replication
    - -c
    - max_wal_size=2GB                                # prevents frequent checkpoints
```

### 3.2 postgres-init/001_extensions.sql

Auto-applied on first container startup via `/docker-entrypoint-initdb.d/`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;            -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- Query-tracking
CREATE EXTENSION IF NOT EXISTS pg_trgm;           -- Fuzzy-similarity
```

### 3.3 RAM-Budget Erklärung für 8GB-Host

| Parameter | Value | Rationale |
|---|---|---|
| `shared_buffers` | 512MB | Konservativ für 8GB-Host mit vielen services (tuwunel, seaweedfs, nats, apps). Standard-Empfehlung wäre 25% RAM = 2GB, aber wir teilen mit vielem. |
| `effective_cache_size` | 2GB | Planner-hint: "wie viel RAM existiert für cache". Summe OS-cache + shared_buffers. Nicht tatsächlich allokiert. |
| `work_mem` | 16MB | Pro Query-Operation. 200 connections × 16MB = max 3.2GB falls alle concurrent sort/hash — realistisch <100MB |
| `maintenance_work_mem` | 128MB | Nur bei VACUUM/CREATE INDEX |

Total worst-case: 512MB shared_buffers + 128MB maintenance + realistisch ~200MB work_mem = **~850MB Postgres** bei load. Plus OS-cache (effective_cache). Bei 8GB OK, bleibt ~6GB für andere services.

---

## 4. PgBouncer — ✅ ADDED als `--profile pooler`

### 4.1 Aktivierung

```bash
# Starte PgBouncer + Postgres zusammen:
podman-compose --profile pooler up -d pgbouncer

# Oder alles (infra + pooler):
podman-compose --profile pooler up -d

# Check:
podman logs pgbouncer
psql -h localhost -p 6432 -U postgres -d hindsight_dev  # via pooler
psql -h localhost -p 5433 -U postgres -d hindsight_dev  # direkt (bypass)
```

### 4.2 Benchmark-Zahlen (verified 2026)

| Aspect | Without PgBouncer | With PgBouncer (Session-Mode) | With PgBouncer (Transaction-Mode) |
|---|---|---|---|
| **RAM-overhead** | — | ~50-150MB | ~50-150MB |
| **CPU-overhead** | — | 50-100m (negligible) | 50-100m |
| **Connection-multiplexing** | 1:1 | 1:1 (session-bound) | 10-20:1 |
| **Throughput ceiling** | ~25-30k tps above 75 conn | similar | **~44k tps** |
| **LISTEN/NOTIFY compatible?** | ✅ | ✅ | ❌ |
| **Prepared statements?** | ✅ | ✅ | ❌ (disable via `prepared_statements=false`) |

Source: [Tembo Benchmark 2026](https://www.tembo.io/blog/postgres-connection-poolers)

### 4.3 Dev-Setup: Apps switchen auf Pooler (optional)

Standardmäßig connecten Apps über :5433 (direkter Postgres). Um via Pooler zu gehen:

```bash
# In .env / go-appservice/.env.development / python-backend/.env.development:
HINDSIGHT_DB_URL=postgres://postgres:PASS@localhost:6432/hindsight_dev  # :6432 statt :5433
POSTGRES_DSN=postgres://postgres:PASS@localhost:6432/hindsight_dev
```

Alembic-Migrationen sollten **direkt auf :5433** bleiben (DDL ist session-scoped, mit transaction-pool inkompatibel).

### 4.4 Upgrade zu Transaction-Pool (später bei Scale-Trigger)

**Trigger**:
- >50 concurrent connections
- Multi-user-serving (10+ parallel users)
- Connection-exhaustion errors

**Aktivierung**:
```bash
# docker-compose.yml: PGBOUNCER_POOL_MODE env-var:
PGBOUNCER_POOL_MODE=transaction podman-compose --profile pooler up -d pgbouncer
```

**App-Code Impact** (muss man machen):
- `go-appservice/internal/*pgxpool`: `DefaultQueryExecMode` auf `pgx.QueryExecModeExec` (statt `CacheStatement`)
- `python asyncpg.create_pool(...)`: `statement_cache_size=0`
- Hindsight (external): config prüfen (wahrscheinlich asyncpg-based, braucht Umstellung)
- Code-places die `LISTEN/NOTIFY` nutzen: müssen direkte Postgres-Connection haben (Bypass Pooler)

### 4.5 PgCat als spätere Alternative

Wenn wir **Read/Write-Splitting** oder **Multi-Tenant-Sharding** brauchen:
- **PgCat** (Rust) — 59k tps vs PgBouncer 44k, skaliert besser auf Multi-Core
- Compatible mit PgBouncer-Config-Syntax
- Feature-set: query routing, replica-aware, connection-mirroring für canary-deploys

**Nicht für uns jetzt** — aber dokumentiert für "wenn Hindsight auf eigene DB + Read-Replica kommt" (siehe `exec-memory.md` Scale-Trigger).

---

## 5. Postgres-Observability — wie nutzen

### 5.1 pg_stat_statements queryen (nach Aktivierung)

```sql
-- Top 10 slowest queries:
SELECT
  substring(query, 1, 100) AS query_preview,
  calls,
  total_exec_time::int AS total_ms,
  mean_exec_time::int AS mean_ms,
  rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Top 10 by total rows affected:
SELECT
  substring(query, 1, 100) AS query_preview,
  calls,
  rows,
  shared_blks_hit,
  shared_blks_read
FROM pg_stat_statements
ORDER BY rows DESC
LIMIT 10;

-- Reset stats:
SELECT pg_stat_statements_reset();
```

### 5.2 Wann manuell queryen

- Nach Load-Test: welche queries sind Hotspots?
- Vor Index-Entscheidungen: was ist häufig + langsam?
- Debug Performance-Issues: welche query blockiert?

### 5.3 Integration mit OpenObserve

Aktuell nicht automatisiert. Future: pg_stat_statements → OTel-exporter → OpenObserve-Dashboard. Siehe `--profile observability`.

---

## 6. Schemas-Map (aus env-architecture-analysis.md)

Zur Erinnerung — Single DB + Multi-Schema pattern:

```
postgres :5433 (hindsight_dev DB)
  ├─ public         (Hindsight external package, pgvector-heavy)
  ├─ storage        (Go-appservice: artifact_metadata)
  ├─ matrix_crypto  (Go-appservice: Matrix E2EE)
  ├─ agent          (Python alembic: audit, skills, sessions, ...)
  └─ ingestion      (Python alembic: ingestion_jobs, chunk_hashes)
```

Pg_trgm + pg_stat_statements arbeiten **cross-schema** — keine per-schema-Aktivierung nötig.

---

## 7. Meine Ehrliche Meinung zum ChatGPT-Text

### ✅ Gut
- Technisch korrekt zu Postgres-Features
- PgBouncer vs Pgpool-II distinction ist präzise
- pg_stat_statements Empfehlung ist Standard-Best-Practice
- Transaction-Pooling-Quirks-Dokumentation wertvoll

### ❌ Schwach
- **Ohne Domain-Awareness**: CRUD-App mental-model, nicht AI-Agent-Platform
- Pauschale Empfehlungen: "Postgres + PostgREST ersetzt Middleware" gilt für SaaS-Basic, nicht für matrix-stack
- Meilisearch als generische Search-recommendation — übersieht dass wir Hindsight haben
- Redis-Replacement-Argumente: übersieht dass NATS+Postgres modernere Split ist

### 🟡 Ambivalent
- PostgREST: Gut für schema-driven CRUD, aber security-regression wenn man capability-based pattern bricht
- Schema-SQL-Beispiel (Jobs-Queue + RLS): lesenswert als Referenz, aber redundant zu unserem alembic-Setup

---

## 8. TODOs

### Erledigt ✅
- [x] `pg_stat_statements` + `pg_trgm` via init-sql + shared_preload_libraries
- [x] Dev-Tuning params in postgres-service (shared_buffers=512MB, work_mem=16MB, random_page_cost=1.1)
- [x] `postgres-init/001_extensions.sql` angelegt (auto-run bei first boot)
- [x] **PgBouncer** als `--profile pooler` (session-mode default, transaction-mode via env-var)
- [x] **postgres-exporter** in `--profile observability` (metrics auf :9187)
- [x] **`scripts/backup-postgres.sh`** — einfaches pg_dump + gzip nach HDD (`/mnt/cold-storage/backup/postgres/`)

### Low-priority (wenn mal Zeit)
- [ ] Verify ingestion-worker nutzt `FOR UPDATE SKIP LOCKED` für job-dequeue
- [ ] pg_stat_statements → OpenObserve-dashboard (via postgres-exporter + otel-collector)
- [ ] Query-top-10-report als dev-helper-script (`scripts/pg-top-queries.sh`)
- [ ] Cron-entry für `backup-postgres.sh` in `crontab -e` oder systemd-timer

### Future — Pre-Prod (Priority 2, wenn Deploy naht)
- [ ] **pgBackRest** statt pg_dump für PITR-capable backups (siehe Sektion 9)
- [ ] **SSL/TLS** für DB-connections (siehe Sektion 10)
- [ ] **Secrets-Management** (SOPS oder externer Vault — currently plain .env)
- [ ] **Backup-Retention-Policy** dokumentieren (aktuell 7 Tage Rolling)
- [ ] **WAL-Archive** nach S3/Garage (für PITR) — Teil von pgBackRest-Setup
- [ ] **Load-Test** vor Launch mit realistischen Traffic-Patterns

### Future — Scale-Trigger (Priority 3)
- [ ] **PgBouncer Transaction-Mode** (bei >50 concurrent connections)
- [ ] **Hindsight auf eigene DB** (siehe exec-memory.md Addendum) bei >10k conversations
- [ ] **Read-Replicas** für Memory-queries (separate load-balancing)
- [ ] **Patroni + etcd** für echtes HA (siehe Sektion 11)
- [ ] **PgCat** statt PgBouncer wenn Read/Write-Splitting gebraucht wird
- [ ] **Logical-Replication** für zero-downtime Major-Upgrades

### Explicit NICHT tun
- [ ] ~~PostgREST einführen~~ (Security-regression zu capability-based pattern)
- [ ] ~~Meilisearch als Memory-search~~ (Hindsight ist specialized)
- [ ] ~~Pgpool-II~~ (Failover-Verhalten problematisch, PgBouncer ist cleaner)
- [ ] ~~Supavisor (Elixir)~~ (overkill für non-serverless, komplexer Setup)

---

## 9. Future: pgBackRest (PITR-capable Backup)

**Trigger**: Prod-Deploy oder DB >10GB (wenn pg_dump zu langsam wird).

### Warum pgBackRest statt pg_dump

| Aspect | pg_dump (aktuell) | pgBackRest |
|---|---|---|
| **Incremental** | ❌ Full dump jede Nacht | ✅ Deltas (nur geänderte Blocks) |
| **Speed (10GB DB)** | ~5 min | ~30s incremental, 2 min full |
| **PITR** | ❌ (nur snapshot) | ✅ Restore zu any-minute via WAL-replay |
| **Compression** | gzip external | zstd built-in (besser, CPU-faster) |
| **Encryption** | ❌ | ✅ AES |
| **S3-offsite** | manuell | native support (AWS S3, MinIO, Garage) |
| **Retention** | manual scripting | configurable policies |
| **Complexity** | 1 script, 50 Zeilen | config-file + stanza-setup |

### Setup-Outline

```yaml
# docker-compose.yml — als --profile prod-backup
services:
  pgbackrest:
    image: pgbackrest/pgbackrest:2.54.2
    container_name: pgbackrest
    volumes:
      - postgres-data:/var/lib/postgresql/data:ro
      - pgbackrest-repo:/var/lib/pgbackrest
      - ./pgbackrest.conf:/etc/pgbackrest.conf:ro
    environment:
      PGBACKREST_STANZA: matrix
    profiles: [prod-backup]

# Plus im postgres service:
postgres:
  command:
    # ... existing ...
    - -c
    - archive_mode=on
    - -c
    - "archive_command=pgbackrest --stanza=matrix archive-push %p"
    - -c
    - wal_level=logical  # (war replica, logical erlaubt später logical-replication)

volumes:
  pgbackrest-repo:        # lokal oder S3-mount
```

### pgbackrest.conf Template

```ini
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=7
repo1-retention-diff=14
repo1-type=posix           # oder: s3 (für Garage-target)
compress-type=zst
compress-level=6

# For Garage/S3 offsite:
# repo1-type=s3
# repo1-s3-endpoint=garage:3900
# repo1-s3-bucket=matrix-pg-backups
# repo1-s3-key=GK...
# repo1-s3-key-secret=...
# repo1-s3-region=garage

[matrix]
pg1-host=postgres
pg1-port=5432
pg1-user=postgres
pg1-path=/var/lib/postgresql/data
```

### Workflow

```bash
# Setup initial
podman exec pgbackrest pgbackrest --stanza=matrix stanza-create
podman exec pgbackrest pgbackrest --stanza=matrix check

# Full backup (weekly):
podman exec pgbackrest pgbackrest --stanza=matrix --type=full backup

# Incremental (daily):
podman exec pgbackrest pgbackrest --stanza=matrix --type=incr backup

# PITR Restore (to timestamp):
podman exec pgbackrest pgbackrest --stanza=matrix \
  --type=time "--target=2026-04-15 14:30:00" restore
```

---

## 10. Future: SSL/TLS für DB-Connections

**Trigger**: Prod-Deploy oder multi-host (wenn Postgres-traffic durch Netz geht, nicht nur localhost).

### Für Single-Host (Dev/Staging)

SSL ist **nicht kritisch** — alle connections via localhost/service-names im internen podman-network.

Aber: Manche Compliance-Frameworks (SOC2, ISO27001) fordern **encryption-at-rest + in-transit** als hard requirement. Für die: SSL aktivieren.

### Für Multi-Host (echte Prod)

**Pflicht**: Apps connecten von anderen Hosts. Plain-TCP leakable.

### Setup-Schritte

1. **Certs generieren** (self-signed für internal, Let's Encrypt für public):
   ```bash
   mkdir -p postgres-tls
   openssl req -new -x509 -days 365 -nodes -text \
     -out postgres-tls/server.crt \
     -keyout postgres-tls/server.key \
     -subj "/CN=postgres"
   chmod 600 postgres-tls/server.key
   chown 999:999 postgres-tls/server.*   # postgres-container UID
   ```

2. **docker-compose.yml postgres service erweitern**:
   ```yaml
   postgres:
     command:
       # ... existing ...
       - -c
       - ssl=on
       - -c
       - ssl_cert_file=/var/lib/postgresql/server.crt
       - -c
       - ssl_key_file=/var/lib/postgresql/server.key
     volumes:
       - ./postgres-tls/server.crt:/var/lib/postgresql/server.crt:ro
       - ./postgres-tls/server.key:/var/lib/postgresql/server.key:ro
   ```

3. **Client-side** (alle env-vars):
   ```env
   # Enforce SSL via URL-param:
   HINDSIGHT_DB_URL=postgres://postgres:PASS@localhost:5433/hindsight_dev?sslmode=require
   # Varianten: disable, allow, prefer (default), require, verify-ca, verify-full
   ```

4. **pgbouncer** config für SSL:
   ```yaml
   pgbouncer:
     environment:
       SERVER_TLS_SSLMODE: require
       CLIENT_TLS_SSLMODE: require
       CLIENT_TLS_CERT_FILE: /etc/pgbouncer/client.crt
       CLIENT_TLS_KEY_FILE: /etc/pgbouncer/client.key
   ```

### For Public-Facing DB (z.B. Cloud-deploy mit Internet-Zugang)

- **Let's Encrypt**: certbot + DNS-challenge (weil Postgres nicht HTTP)
- **Automated renewal**: cron `certbot renew` + `pg_ctl reload`
- **Verify-full** auf Client-Side: checks hostname matches cert-CN

---

## 11. Future: Patroni für echte HA

**Trigger**: Mehrere Server zur Verfügung UND Downtime <1 min gefordert.

### Warum Patroni

- **Automatic Failover**: Bei Primary-crash wird Replica automatisch promoted
- **Leader-Election via DCS** (etcd/Consul/ZooKeeper)
- **REST-API** für Cluster-Management
- **Integration**: HAProxy sieht via Patroni-REST welcher Node Primary ist

### Minimal-HA-Setup (3 Nodes)

```
┌────────┐  ┌────────┐  ┌────────┐
│ etcd-1 │──│ etcd-2 │──│ etcd-3 │   (DCS-Quorum)
└───┬────┘  └───┬────┘  └───┬────┘
    │           │           │
┌───▼───────┐ ┌─▼────────┐ ┌▼────────┐
│ patroni-1 │ │patroni-2 │ │patroni-3│
│    +      │ │    +     │ │   +     │
│ postgres  │ │ postgres │ │postgres │
│ (PRIMARY) │ │(REPLICA) │ │(REPLICA)│
└───────────┘ └──────────┘ └─────────┘
       ↑            ↑            ↑
       └────────────┼────────────┘
                    │
               ┌────▼─────┐
               │ HAProxy  │  (routes writes to current Primary via patroni-API)
               └────┬─────┘
                    │
               ┌────▼─────┐
               │PgBouncer │  (connection-pooling)
               └────┬─────┘
                    │
                  Apps
```

### Patroni-Minimal-Config

```yaml
# patroni.yml
scope: matrix-cluster
namespace: /service/
name: patroni-1
restapi:
  listen: 0.0.0.0:8008
  connect_address: patroni-1:8008
etcd3:
  hosts: etcd-1:2379,etcd-2:2379,etcd-3:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    postgresql:
      use_pg_rewind: true
      parameters:
        max_connections: 200
        shared_buffers: 2GB
        wal_level: logical
        max_wal_senders: 10

postgresql:
  listen: 0.0.0.0:5432
  connect_address: patroni-1:5432
  data_dir: /var/lib/postgresql/data
  pgpass: /tmp/pgpass0
  authentication:
    superuser:
      username: postgres
      password: ${POSTGRES_PASSWORD}
    replication:
      username: replicator
      password: ${REPLICATION_PASSWORD}
```

### Alternative: Cloud-managed

Skipp Patroni komplett. Use:
- **AWS RDS Multi-AZ** (automatic failover)
- **Google Cloud SQL HA**
- **Supabase** (managed)
- **Neon** (serverless)

Trade-off: Cost (rec $100+/mo) vs. zero-ops.

---

## 12. Future: PgCat als PgBouncer-Replacement

**Trigger**: Read/Write-Splitting oder Multi-Tenant-Sharding gebraucht.

### Warum PgCat

- **Rust-based** — 59k tps vs PgBouncer 44k
- **Query-routing** (automatic read-to-replica, write-to-primary)
- **Sharding-support** (consistent hashing auf shard_key)
- **Config-as-Code** (toml statt pgbouncer.ini)
- **Compatible mit PgBouncer** (drop-in-replacement wenn kein query-routing genutzt)

### Nicht jetzt weil

- Wir haben nur **1 Postgres** (kein Read-Replica zu routen)
- PgBouncer reicht für unser scale
- PgCat jung (Rust, aktiv entwickelt) — PgBouncer battle-tested seit 2007

Wenn Hindsight-DB separiert wird (siehe `exec-memory.md` Addendum), evaluieren ob PgCat Read-Routing lohnt.

---

## 13. Future: Secrets-Management (aktuell plain .env)

**Trigger**: Team-Collaboration, CI/CD, Cloud-Deploy.

### Aktueller State

Plain `.env.development` + `.env.production` in gitignored dirs. Mode 600. Bootstrap-env.py generiert secrets.

### Option A: SOPS + age (bereits evaluiert)

- ✅ Committable `.enc.yaml` in repo (encrypted)
- ✅ Team-sharing via age-public-key
- ❌ Overkill für Solo-Dev (entfernt in früherer Session)
- 🟡 Re-activate wenn Team wächst

### Option B: HashiCorp Vault

- ✅ Secrets-API (dynamic credentials, rotation)
- ✅ Audit-log für jede Secret-Access
- ❌ Extra Service (+ its own HA)
- 🟡 Prod-Deploy-Candidate bei Enterprise

### Option C: Kubernetes External Secrets Operator

- ✅ Bridges K8s-Secrets zu AWS SM / GCP SM / Vault
- ✅ Declarative (kubectl apply)
- ❌ Braucht K8s-Deploy (nicht docker-compose)

### Option D: Cloud-native (AWS SM / GCP SM / Doppler)

- ✅ Zero-ops
- ❌ Vendor-lock + $

**Entscheidung für matrix**: Depends on Deploy-target. Für self-hosted: SOPS+age. Für Cloud: native provider.

---

## 14. Prod-Deploy Checkliste (sobald relevant)

Alle Todos aus Section 8 Priority 2:

- [ ] **Backups**: pgBackRest statt pg_dump + S3-offsite
- [ ] **TLS**: Server-certs + `sslmode=require` in allen Apps
- [ ] **Monitoring**: OpenObserve-profile aktiv + postgres-exporter scraped
- [ ] **Alerting**: Critical-metrics → PagerDuty/Telegram (disk-usage, replication-lag, query-latency)
- [ ] **Secrets**: SOPS+age oder Cloud-SM (nicht plain .env)
- [ ] **Load-Test**: k6/vegeta-scenarios durchlaufen
- [ ] **Failover-Test**: Primary kill + verify PgBouncer retry-behavior
- [ ] **Rollback-Plan**: Alembic-downgrade-scripts + pg_dump-restore-verify
- [ ] **PII/GDPR**: pg_anonymize für test-data-copies
- [ ] **Connection-Quota**: per-App-pool-size dokumentiert + enforced

Minimum-MVP für Prod:
- pgBackRest daily-full + hourly-incremental mit 7d retention
- SSL-enforced connections
- OpenObserve aktiv (zumindest logs + postgres-metrics)
- Plain .env → SOPS migrated (wenn Team-collaboration)

---

## 15. Appendix A: Tuning bei Veränderung der Hardware

### Bei mehr RAM (z.B. 32GB-Upgrade)

```yaml
- shared_buffers=4GB       # 25% RAM
- effective_cache_size=16GB # 50% RAM
- work_mem=32MB
- maintenance_work_mem=512MB
```

### Bei Prod (Bare Metal, >64GB)
- `shared_buffers=16GB` (25%)
- `wal_level=logical` (für logical replication)
- `max_wal_senders=10` (für read-replicas)
- Connection-Pooler **zwingend** (PgBouncer oder pgcat)

---

## 16. Appendix B: Referenzen

- `env-architecture-analysis.md` — Schemas-Map + DB-URLs
- `specs/execution/exec-memory.md` — Memory-Layer (Hindsight + Mempalace-Issue)
- `scripts/dev-stack.sh` — Native apps startup
- `postgres-init/001_extensions.sql` — Extension auto-loader
- ChatGPT-Original-Doc: `~/Schreibtisch/Postgres` (Referenz, nicht committed)

### External
- [PgBouncer Usage](https://www.pgbouncer.org/usage.html) — pool-modes
- [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)
- [pgvector README](https://github.com/pgvector/pgvector) — HNSW, IVFFlat
- [Postgres Feature Matrix](https://www.postgresql.org/about/featurematrix/)
