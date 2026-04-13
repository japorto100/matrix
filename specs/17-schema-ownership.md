# Schema Ownership

> Established: exec-19 Stufe 3 (11.04.2026)

Matrix runs a single PostgreSQL cluster (`hindsight_dev` on `:5433`) but is a
**modular monolith** composed of Go and Python services. Each service owns one
or more schemas and accesses the others **only via HTTP API**, never by direct
cross-schema SQL reads or writes.

This is the "Schema per Bounded Context" pattern (Chris Richardson,
_Microservices Patterns_ — the pragmatic variant of Database-per-Service when
you share one cluster).

## Ownership map

| Schema              | Owner                           | Owned by                                       | What it stores                                               |
|---------------------|---------------------------------|------------------------------------------------|--------------------------------------------------------------|
| `public` (Hindsight)| **Python Hindsight lib**        | external Hindsight crate migrations            | banks, memory_units, entities, embeddings                    |
| `agent`             | **Python Agent Service (:8094)**| `python-backend/alembic/versions/*.py`         | audit_events, skills_state, consent, a2a, user_credentials, user_llm_settings |
| `ingestion`         | **Python Ingestion Worker (:8098)** | Alembic (002_ingestion_jobs, 003_chunk_hashes) | jobs, chunk_hashes                                           |
| `storage`           | **Go Appservice (:8090)**       | `go-appservice/internal/storage/metadata_store_postgres.go migrate()` | artifact_metadata + matrix_crypto_* (after Stufe 2B)        |
| `matrix_crypto` (future) | Go Appservice (mautrix-go) | mautrix-go SQLCryptoStore internal schema upgrade | Olm account, device keys, megolm sessions                |

## Trust boundary: BFF is the gatekeeper

> Added exec-19 Stufe 3 Review Fix #10 (11.04.2026)

Go Appservice enforces per-user access via the `X-Actor-User-Id` request
header. **This header is trusted, not verified cryptographically.** The
guarantee that it reflects the authenticated user comes from the layer
in front of Go:

```
Browser → control-ui Next.js BFF → (X-Actor-User-Id header set) → go-appservice
                                                                      ↓
                                                              Python agent / worker
```

The BFF authenticates the user (session cookie / NextAuth / matrix-js-sdk
token), then sets `X-Actor-User-Id` on the outgoing request to Go. Go
treats this header as truth and binds it into HMAC tokens + enforces
ownership on every artifact operation.

**Consequence — production deployment rules:**

1. **Go Appservice `:8090` MUST NOT be exposed to the public internet.**
   It must only be reachable from the BFF (same host, private network,
   or reverse-proxy with mTLS). Anyone who can reach `:8090` directly
   can set `X-Actor-User-Id` to any value and impersonate any user.
2. **No client-side code should ever talk to Go directly** — always via
   the BFF. This is why `control-ui/src/app/api/files/**/route.ts`
   exists as proxy routes; the browser never calls Go.
3. **Dev mode is OK** because BFF runs on localhost and Go is only
   bound to localhost (`ADDR=127.0.0.1:8090`). In Docker/prod, the
   equivalent is network-level isolation (Docker network, K8s
   NetworkPolicy, or at minimum a reverse-proxy that strips the
   header from external requests).

Python services (agent, ingestion) also trust `X-Actor-User-Id` when
called **by the BFF via Go**. They do not accept direct browser calls.

## Inter-service authentication (exec-19 Stufe 3 Review Fix #8)

Go Appservice calls the Python ingestion worker (`:8098`) for trigger /
reindex / cancel operations. Aktuell unauthenticated — any process with
network access to `:8098` can POST to `/ingest/*`.

**Planned:** Shared-secret header for service-to-service calls.

```
Env: INGESTION_WORKER_SHARED_SECRET=<32-byte hex>  (same value in both
                                                     go-appservice and
                                                     python-backend envs)

Go client sends: X-Service-Auth: <secret>
Python worker rejects if header missing or mismatch in non-dev mode.
```

Dev mode: `INGESTION_WORKER_SHARED_SECRET=""` → worker accepts unauth
calls (so the current dev flow continues working). Production requires
the var to be set.

See `go-appservice/internal/connectors/ingestion/client.go` + `python-backend/ingestion/worker.py` for current state.

## Blob storage (SeaweedFS)

- **Owner:** Go Appservice. Go holds the S3 credentials
  (`ARTIFACT_STORAGE_S3_*` in `go-appservice/.env.development`).
- **Python never has direct S3 credentials.** Python services access blobs
  only via the Go Gateway's signed URL flow:
  1. `POST /api/v1/storage/artifacts/upload-url` → signed PUT URL
  2. `PUT` bytes directly to SeaweedFS using the signed URL
  3. `POST /api/v1/storage/artifacts/{id}/mark-ready`
  4. `GET /api/v1/storage/artifacts/{id}` → signed download URL
- TTL on signed URLs: 15 min (configured by `ARTIFACT_STORAGE_SIGNED_URL_TTL_MS`).
- This is capability-based access (exec-15 D12): Python has no standing
  credential for blob storage — every access requires a fresh signed URL from
  Go, limiting blast radius of a compromised Python service.

## Cross-schema rules

1. **Writes**: only the owning service writes to its own schema. Never write
   across bounded contexts.
2. **Reads**: when Service A needs data from Service B's schema, A calls B's
   HTTP API, never `SELECT` from B's tables.
3. **Foreign keys across schemas**: avoided. If a Go artifact_metadata row
   references a Python agent.user row, the reference is stored as a plain
   `user_id TEXT` column, not a `FOREIGN KEY` — cross-schema FKs would couple
   the two services at the DB level and break the bounded-context invariant.

## Why this matters

Without the split, a Python bug could `UPDATE storage.artifact_metadata` or a
Go bug could `DELETE FROM agent.audit_events`. Both would be silent
catastrophes — no runtime error, no type-checker warning, just data in the
wrong place.

Keeping the split lets us:
- **Scale services independently** if we ever split to separate DBs.
- **Audit cross-service access** — any direct query outside the owned schema
  is a review red flag.
- **Enforce at the DB level later** via per-service PG users + `GRANT` — this
  is planned for exec-18 (Unified Schema) but not yet implemented.

## Planned: PG-level permission enforcement (exec-18)

Currently, all services connect as the `postgres` superuser, so the ownership
map above is a *convention*, not enforced. The defense-in-depth step is:

```sql
CREATE ROLE matrix_go_user LOGIN PASSWORD '...';
CREATE ROLE matrix_py_user LOGIN PASSWORD '...';

GRANT USAGE, CREATE ON SCHEMA storage TO matrix_go_user;
GRANT ALL ON ALL TABLES IN SCHEMA storage TO matrix_go_user;

GRANT USAGE, CREATE ON SCHEMA agent, ingestion, public TO matrix_py_user;
GRANT ALL ON ALL TABLES IN SCHEMA agent, ingestion, public TO matrix_py_user;

-- Cross-schema reads are not granted, so accidental queries fail at PG level.
```

**Status:** Not implemented. Tracked as exec-18 Phase 0 task: "PG Permission
Split (defense in depth)".

## What this document doesn't cover

- Matrix homeserver DB (`tuwunel` binary) — separate RocksDB, not in our PG
- SQLite fallbacks (dev-only filesystem store) — exec-18 removes these
- Redis / cache layers — none currently
