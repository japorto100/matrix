# exec-postgres-tuning — Postgres Dev-Tuning + PgBouncer + Exporter + Backup

**Datum**: 2026-04-17 (Bootstrap) · Revision 2026-04-17 (PgBouncer + Exporter + Backup aktiviert)
**Status**: ✅ Implementiert
**Scope**: Postgres-Container-Config + Extensions + Connection-Pooler + Metrics-Exporter + Backup-Script

## Motivation

Nach Analyse eines ChatGPT-Gesprächs zu "Postgres-Stack 2026" (siehe [`postgres.md`](../../postgres.md) im repo-root für Full-Review) wurden folgende Punkte als **übernehmenswert** identifiziert:

1. **`pg_stat_statements`** als Query-Observability-Standard ab Dev-Tag-1
2. **Dev-Performance-Tuning-Params** für 8GB-RAM-Host
3. **Extensions-Auto-Init** bei erstem Container-Start

Alle anderen Empfehlungen (PgBouncer, PostgREST, Meilisearch) sind **als Future-Option** in `postgres.md` dokumentiert und **NICHT** übernommen — Rationale siehe dort.

## Änderungen

### 1. `docker-compose.yml` — postgres Service erweitert

**Vorher** (8 Zeilen command-config):
```yaml
postgres:
  image: pgvector/pgvector:pg17
  environment:
    POSTGRES_USER: ...
  ports:
    - "5433:5432"
  volumes:
    - postgres-data:/var/lib/postgresql/data
```

**Nachher** (+ command-tuning + init-volume):
```yaml
postgres:
  image: pgvector/pgvector:pg17
  command:
    - postgres
    - -c
    - shared_preload_libraries=pg_stat_statements
    - -c
    - max_connections=200
    - -c
    - shared_buffers=512MB
    - -c
    - effective_cache_size=2GB
    - -c
    - work_mem=16MB
    - -c
    - maintenance_work_mem=128MB
    - -c
    - random_page_cost=1.1
    - -c
    - track_io_timing=on
    - -c
    - pg_stat_statements.track=all
    - -c
    - wal_level=replica
    - -c
    - max_wal_size=2GB
  volumes:
    - postgres-data:/var/lib/postgresql/data
    - ./postgres-init:/docker-entrypoint-initdb.d:ro   # NEW
```

### 2. `postgres-init/001_extensions.sql` — Neu angelegt

Auto-applied on first container startup (Postgres-docker-entrypoint reads `/docker-entrypoint-initdb.d/*.sql`).

```sql
CREATE EXTENSION IF NOT EXISTS vector;            -- pgvector (Hindsight)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- Query-tracking
CREATE EXTENSION IF NOT EXISTS pg_trgm;           -- Fuzzy-similarity
```

**Hinweis**: Extensions idempotent (IF NOT EXISTS) → re-runs harmless.

## Rationale pro Parameter

| Parameter | Value | Warum |
|---|---|---|
| `shared_preload_libraries=pg_stat_statements` | — | Library-loading beim Start, MUSS bevor `CREATE EXTENSION` |
| `max_connections=200` | — | 5+ Services × Pool-Size — realistisch 50-80 total |
| `shared_buffers=512MB` | — | Konservativ für 8GB-Host mit vielen services. Default-rec wäre 25% RAM = 2GB, aber wir teilen mit tuwunel/seaweedfs/apps. |
| `effective_cache_size=2GB` | — | Planner-hint: OS-cache + shared_buffers kombiniert. NICHT allokiert. |
| `work_mem=16MB` | — | Pro query-op (sort/hash). Worst-case 200 conn × 16MB = 3.2GB, realistisch <100MB. |
| `maintenance_work_mem=128MB` | — | Nur VACUUM/CREATE INDEX. |
| `random_page_cost=1.1` | — | SSD-optimal. Default 4 ist für HDD. |
| `track_io_timing=on` | — | Per-query I/O stats in pg_stat_statements. |
| `pg_stat_statements.track=all` | — | Tracked top-level + nested queries. Default `top` verpasst function-internal calls. |
| `wal_level=replica` | — | Minimum für `pg_basebackup`. Future: logical-replication braucht `logical`. |
| `max_wal_size=2GB` | — | Reduziert Checkpoint-Frequency. Default 1GB forciert öfter Checkpoints → I/O-spikes. |

## Extensions — Rationale

### `vector` (pgvector)
- **Nutzer**: Hindsight (`public` schema), memory_fusion
- **Funktion**: Embedding-storage + HNSW/IVFFlat similarity search
- **War schon da**: Image `pgvector/pgvector:pg17` hat es gebündelt, aber `CREATE EXTENSION` nötig für Availability im DB

### `pg_stat_statements`
- **Nutzer**: Observability (manuelle queries, später OTel-export)
- **Funktion**: Tracked planning + execution stats aller SQL-statements
- **Kritisch**: MUSS in `shared_preload_libraries` geladen sein BEVOR `CREATE EXTENSION`, sonst 0-rows-output

### `pg_trgm`
- **Nutzer**: Potenziell für agent-audit/skills-search (fuzzy match on names)
- **Funktion**: Trigram-similarity, GIN/GiST indexes für `LIKE`/`ILIKE` mit wildcards
- **Jetzt**: Aktiviert als "available" — Code-usage optional

## RAM-Budget für 8GB Host

Worst-case Postgres-consumption:
```
shared_buffers:     512MB  (alloziert, immer)
maintenance:        128MB  (peak during VACUUM)
work_mem (peak):   ~200MB  (realistisch bei load)
connections:       ~100MB  (50 × 2MB)
─────────────────────────
Total Postgres:    ~940MB  peak
```

Bei 8GB-Host + tuwunel + seaweedfs + apps: bleiben ~5-6GB für OS-cache + apps. OK.

**Bei Upgrade auf 32GB**:
```
shared_buffers=4GB          (25%)
effective_cache_size=16GB   (50%)
work_mem=32MB
maintenance_work_mem=512MB
```

## Impact-Analyse (was könnte brechen)

### Keine Breaking Changes
- `CREATE EXTENSION IF NOT EXISTS` ist idempotent
- Neue Tuning-Params beeinflussen nur Performance, nicht Schema/Data
- Restart von postgres: config-params werden angewendet

### Service-Kompatibilität
Alle konsumierenden Services (go-appservice, python-agent, Hindsight, Alembic, ingestion-worker) nutzen `HINDSIGHT_DB_URL` / `POSTGRES_DSN` — **keine Änderung** an Connection-Strings. Nur tiefer unter der Haube optimierter.

### Connection-Limit von 100 → 200
Alte Services evtl. für 100-max konfiguriert (Pool-Size). Jetzt 200-max ermöglicht mehr parallel. Keine Breaking-change, nur Headroom.

## Verify Gates

### Pre-Deploy
- [x] `docker-compose.yml` YAML valid: `python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"` → ok
- [x] `postgres-init/001_extensions.sql` existiert + syntax-clean
- [x] Existing `postgres-data` volume NICHT gelöscht (init-scripts laufen nur bei leerer DB)

### Post-Deploy (nach Restart)
- [ ] `podman-compose restart postgres` → ok
- [ ] `podman exec postgres psql -U postgres -d hindsight_dev -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;"`
  - erwartet: `pg_stat_statements`, `pg_trgm`, `vector`, plus plpgsql (default)
- [ ] `podman exec postgres psql -U postgres -d hindsight_dev -c "SELECT name, setting FROM pg_settings WHERE name IN ('shared_buffers','work_mem','random_page_cost','track_io_timing','pg_stat_statements.track');"`
  - erwartet: alle values wie konfiguriert
- [ ] `podman exec postgres psql -U postgres -d hindsight_dev -c "SELECT count(*) FROM pg_stat_statements;"` → sollte NICHT fehlerhaft sein (extension aktiv)
- [ ] nach ein paar app-queries: `SELECT query, calls FROM pg_stat_statements LIMIT 5` → zeigt queries

### Post-Deploy Sanity (services starten weiterhin)
- [ ] `go-appservice` startet (HINDSIGHT_DB_URL erreichbar)
- [ ] `python-agent` startet (DB-Connection ok)
- [ ] `alembic upgrade head` läuft durch (DDL-Operations)

## Troubleshooting

### Extensions nicht aktiv nach Restart
**Problem**: `CREATE EXTENSION IF NOT EXISTS pg_stat_statements;` gibt Fehler.
**Ursache**: `shared_preload_libraries` nicht geladen.
**Fix**: `podman exec postgres cat /proc/1/cmdline | tr '\0' ' '` — sollte `-c shared_preload_libraries=pg_stat_statements` enthalten. Falls nicht: docker-compose command-array syntax checken.

### Init-script lief nicht
**Problem**: `CREATE EXTENSION` nicht executed.
**Ursache**: `postgres-data` volume war schon initialisiert → init-scripts werden **nur beim ersten start** gerunt.
**Fix**:
```bash
# Option A (data-loss): volume wipen + neu start
podman-compose down
podman volume rm matrix_postgres-data
podman-compose up -d postgres

# Option B (data-preserved): manuell executen
podman exec -it postgres psql -U postgres -d hindsight_dev \
  -f /docker-entrypoint-initdb.d/001_extensions.sql
```

### Query-Performance schlechter nach Tuning
**Problem**: Nach Änderung ist queries langsamer.
**Ursache**: `shared_buffers` zu hoch für Host-RAM → swapping.
**Fix**: Reduziere `shared_buffers` (z.B. auf 256MB) wenn andere Services RAM brauchen.

## Not-In-Scope (bewusst nicht gemacht)

Aus `postgres.md` Review-Ergebnis **NICHT** übernommen:
- ❌ ~~PgBouncer~~ → **REVISED** in Rev 2 — ist jetzt drin (`--profile pooler`)
- ❌ PostgREST (würde capability-based security umgehen)
- ❌ Meilisearch (redundant zu Hindsight-search)
- ❌ Patroni (overkill für Single-Host-Dev — dokumentiert in `postgres.md` Section 11 für Scale)
- ❌ Replication (nicht relevant bis echtes Multi-Region)
- ❌ pgBackRest (Future für Prod-Deploy — siehe `postgres.md` Section 9)
- ❌ SSL/TLS (Future — siehe `postgres.md` Section 10)
- ❌ Supavisor (Elixir, overkill für non-serverless)

## Revision 2026-04-17 — PgBouncer + Exporter + Backup

Nach initial bootstrap wurde entschieden, **Prod-relevante Low-Hanging-Fruits jetzt bereits zu adden** (statt als Future-Option zu belassen). Rationale: siehe `postgres.md` Section 4 (Benchmarks + Research).

### Hinzugefügt: PgBouncer als `--profile pooler`

**docker-compose.yml**:
```yaml
pgbouncer:
  image: edoburu/pgbouncer:1.24.1-p1
  environment:
    POOL_MODE: ${PGBOUNCER_POOL_MODE:-session}   # session = zero breaking changes
    MAX_CLIENT_CONN: 200
    DEFAULT_POOL_SIZE: 20
    # ... siehe docker-compose.yml für full config
  ports:
    - "6432:5432"
  profiles: [pooler]
```

**Rationale**:
- Research bestätigte: PgBouncer ist **ultra-leicht** (~2MB/1000 Clients, ~128MB container RAM, 0.05-0.1 CPU cores)
- Session-Pool-Mode als Default = zero breaking changes (LISTEN/NOTIFY, prepared statements funktionieren)
- Transaction-Pool-Mode via env-var für späteren Scale-Trigger (5-10× Throughput-Gain, aber App-Code-Anpassung nötig)

**Usage**:
```bash
podman-compose --profile pooler up -d pgbouncer
# Apps auf Pooler: HINDSIGHT_DB_URL=postgres://...@localhost:6432/...
```

### Hinzugefügt: postgres-exporter in `--profile observability`

**docker-compose.yml**:
```yaml
postgres-exporter:
  image: prometheuscommunity/postgres-exporter:v0.17.0
  environment:
    DATA_SOURCE_NAME: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}?sslmode=disable"
    PG_EXPORTER_AUTO_DISCOVER_DATABASES: "true"
  ports:
    - "9187:9187"   # /metrics für Prometheus-scrape
  profiles: [observability]
```

**Rationale**:
- Exposed Postgres-metrics auf `:9187/metrics` im Prometheus-Format
- Feed via OTel-collector → OpenObserve (wenn `--profile observability` aktiv)
- Metriken: connections, cache-hit-ratio, lock-waits, replica-lag, pg_stat_statements summaries

### Hinzugefügt: `scripts/backup-postgres.sh`

Einfaches pg_dump-Backup zu HDD (`/mnt/cold-storage/backup/postgres/`):

- **Format**: gzip-komprimierter plain-SQL-dump
- **Retention**: 7 Tage rolling (via `--keep N` configurable)
- **Integrity-Check**: `gzip -t` nach Dump
- **Restore**: dokumentiert im Script-Output

**Usage**:
```bash
./scripts/backup-postgres.sh                # default target + 7-day retention
./scripts/backup-postgres.sh --keep 14      # 14-day retention
./scripts/backup-postgres.sh /custom/path   # custom target
```

**Cron-entry empfohlen** (daily 3am):
```bash
crontab -e
# Füge hinzu:
0 3 * * *  /home/lipfi2/code/matrix/scripts/backup-postgres.sh >> /tmp/pg-backup.log 2>&1
```

**Future**: pgBackRest statt pg_dump (siehe `postgres.md` Section 9) für PITR-capability bei Prod-scale.

## Files Changed

```
docker-compose.yml                         (postgres: +tuning, +pgbouncer, +postgres-exporter)
postgres-init/001_extensions.sql          (NEW, 11 lines)
postgres.md                                (NEW + revised — full review + Future-Roadmap)
scripts/backup-postgres.sh                 (NEW, executable)
specs/execution/exec-postgres-tuning-2026-04-17.md  (NEW — this file)
```

## Related Files

- [`postgres.md`](../../postgres.md) — Full ChatGPT-Review + Architecture-Meinung
- [`env-architecture-analysis.md`](../../env-architecture-analysis.md) — Schema-Map
- [`docker-compose.yml`](../../docker-compose.yml) — postgres service config
- [`postgres-init/001_extensions.sql`](../../postgres-init/001_extensions.sql) — extensions auto-init

## Next Steps (für später)

### Post-Revision Verification (nach nächstem Start)
1. **Restart postgres** → verify Tuning + Extensions aktiv (siehe "Post-Deploy" Gates oben)
2. **PgBouncer-Test**: `podman-compose --profile pooler up -d pgbouncer` → `psql -h localhost -p 6432 -U postgres` → verify connection
3. **Exporter-Test**: `podman-compose --profile observability up -d postgres-exporter` → `curl localhost:9187/metrics` zeigt pg-metrics
4. **Backup-Test**: `./scripts/backup-postgres.sh` → verify gzip-file in `/mnt/cold-storage/backup/postgres/`

### Prod-Preparation (Priority 2 — wenn Deploy naht)
- **pgBackRest**-Setup (siehe `postgres.md` Section 9)
- **SSL/TLS**-Certs generieren (siehe `postgres.md` Section 10)
- **cron-entry** für backup-postgres.sh
- **OpenObserve-Dashboards** für postgres-exporter-metrics
- **Alerting-rules** (disk-usage, replica-lag, slow-queries)

### Scale-Trigger (Priority 3 — wenn Multi-User)
- **PgBouncer Transaction-Mode** + App-Code-Änderungen (prepared_statements=false)
- **Hindsight auf eigene DB** (siehe exec-memory.md)
- **Read-Replica** Setup
- **Patroni + etcd** für HA (siehe `postgres.md` Section 11)

### Best Practices für dev-stack
- **PgBouncer nur bei `--profile pooler`**: sonst bypass (direct :5433)
- **Backup-cron**: einmal täglich 3am — 7-day retention
- **OpenObserve nur bei observability-needs**: spart 500MB RAM im dev-mode
