# exec-19: DevStack Consolidation (Verify Gate Prep)

**Datum:** 10.04.2026
**Status:** Draft
**Abhaengig von:** exec-15 (Control UI), exec-16 (LiteLLM), exec-17 (Observability), exec-18 (Schema, optional)
**Referenzen:**
- Tradefusion Go Backend: `D:\tradingview-clones\tradeview-fusion\go-backend`
- Tradefusion Scripts: `D:\tradingview-clones\tradeview-fusion\scripts`
- Matrix Control Copy: `D:\matrix\control\storage\go-backend` (unvollstaendige Kopie ohne `cmd/`)
- Matrix Go Appservice: `D:\matrix\go-appservice`

---

## Warum

Beim Versuch Verify-Gates fuer exec-15/16/17 zu starten haben sich mehrere Probleme
im DevStack gezeigt die **vor** den Verify-Gates behoben werden muessen:

### DevStack Startup-Bugs

1. **LiteLLM crasht** — `config.yaml` hatte Non-ASCII Zeichen, Python liest als cp1252 auf Windows
2. **PowerShell Unicode-Bug** — `dev-stack2.ps1` hatte Em-Dashes, Pfeile, Section-Signs, Box-Drawing Zeichen die PowerShell 5 auf Windows nicht parsen konnte
3. **Go Appservice crasht** — `no such table: crypto_account` (leere SQLite DB, olm machine load failed)
4. **SeaweedFS Port-Conflict** — `listen tcp 192.168.1.34:8080: bind: Zugriff verweigert` (Apache httpd auf :8080, SeaweedFS Volume Server Default Port)
5. **Postgres Crash-Loop** — Stale `postmaster.pid` nach Force-Kill, Watcher startet permanent neu
6. **Matrix Crypto SQLite** — Appservice nutzt lokales SQLite fuer Olm Store, aber wir haben PG laufen. Inkonsistent.
7. **Duplicate Go Backend** — `control/storage/go-backend` wurde aus tradefusion kopiert, hat aber keinen `cmd/` / `go.mod` und laeuft nie. Verwirrender Tote-Code.

### Files API Gaps (kritisch fuer control-ui exec-15)

8. **Files API fehlt komplett im Backend** — control-ui ruft `/api/v1/files/*` auf, diese Routes existieren **nirgendwo** (weder go-appservice noch control/storage/go-backend noch tradefusion Hauptprojekt)
9. **control-ui BFF Bug** — 7 API Routes nutzen hardcoded `localhost:9060` statt `getGatewayBaseURL()` (`:8090`)
10. **Per-User Isolation fehlt** — Files API hat keine User-basierte Filterung. Jeder User wuerde alle Files sehen
11. **SeaweedFS Direct-Listing fehlt** — Das aktuelle Design zeigt nur Files die durch Ingestion Pipeline liefen. Direkt hochgeladene Media-Files (ohne RAG-Indexierung) sind unsichtbar
12. **Keine Pipeline fuer Audio/Video/Image Ingestion** — `PipelineKind` hat nur `document/note/link/batch`. Media-Files gehen nirgends durch die Pipeline und haben daher keine `ingestion.jobs` Eintraege
13. **Ingestion Worker hat keine /jobs List Route** — nur `/jobs/{id}` und `/status`

### Viewer-Packages fuer control-ui Files Tabs

14. **Missing UI Packages** — control-ui Files Tabs brauchen Viewer die in nextjs-chat schon existieren, aber im control-ui noch nicht alle:
    - PDF: `react-pdf` ✓ (schon in control-ui)
    - Spreadsheet: `xlsx` — fehlt
    - Audio Waveform: `wavesurfer.js` — fehlt
    - Video HLS: `hls.js` ✓ (schon in control-ui)
    - Image EXIF: `exifr` — fehlt
    - DOCX: `docx-preview` — fehlt

Ziel: DevStack laeuft **ohne Fehler**, alle Services kommen hoch, Files Tabs zeigen
echte Daten (per-user), Viewer funktionieren, Verify-Gates fuer exec-15/16/17 koennen starten.

### Nicht-Ziel

- Volle Migration aller control/storage Features nach go-appservice (nur was Verify braucht)
- Matrix E2EE Phase C Verify (das ist ein separates Thema)
- exec-18 Schema-Migration (exec-18 bleibt separat)

---

## Ist-Zustand (nach exec-17 Commit)

### DevStack Services Status (beim ersten Run)

| Service | Port | Status | Problem |
|---------|------|--------|---------|
| Postgres | 5433 | UP | Auto-recovery nach Crash erfolgreich |
| NATS | 4222 | UP | - |
| OpenObserve | 5080/5081 | UP | - |
| Homeserver (Zendrite) | 8448 | UP | - |
| Agent Service | 8094 | UP | - |
| py-bridge | 8097 | UP | - |
| Ingestion Worker | 8098 | UP | - |
| nextjs | 3000 | UP | - |
| control-ui | 3001 | UP | - |
| **LiteLLM** | **4000** | **DOWN** | Unicode decode error in config.yaml |
| **Go Appservice** | **8090** | **DOWN** | olm machine load: crypto_account table fehlt |
| **SeaweedFS** | **8333** | **DOWN** | Volume server bind error auf 192.168.1.34:8080 |

### Cross-Service Issues

- **PowerShell Script** — 12 Em-Dashes + weitere Unicode-Zeichen verursachten Parse-Errors (FIXED in exec-17 commit)
- **LiteLLM config.yaml** — 30+ Non-ASCII Zeichen (FIXED in exec-17 commit)
- **Files Routes** — Fehlen komplett im Go Backend
- **Control Backend Duplicate** — `control/storage/go-backend` ist 75% Tradefusion-Kopie ohne `cmd/`, Storage-Package schon in `go-appservice/internal/storage/` identisch vorhanden

---

## Architektur-Entscheidung: Ein Go Backend, nicht zwei

Matrix hat aktuell:
- `go-appservice/` — Haupt Go-Backend (Matrix Bridge, NATS, Artifact Storage)
- `control/storage/go-backend/` — Tote Tradefusion-Kopie ohne Entry Point

**Entscheidung:** `go-appservice` ist das **einzige** Go-Backend fuer Matrix.

- Alle Routes gehen ueber `:8090`
- Der `control/` Ordner bleibt als **Referenz-Material** (`control_surface`, `files_surface` sind Mockups/Prototypes)
- `control/storage/go-backend/` wird bei Bedarf geloescht oder mit einem README markiert dass es nicht laeuft
- Fehlende Features wie Files API Routes werden in `go-appservice` hinzugefuegt

**Vorteil:** Einheitlicher Build, einheitliches Env, einheitliches Deployment, einheitliches Logging/Tracing.

---

## Stufe 1: DevStack Startup-Fixes (kritisch)

Bereits in exec-17 Commit erledigt (dokumentiert hier fuer Nachvollziehbarkeit):

- [x] `scripts/dev-stack2.ps1` Unicode-Zeichen durch ASCII ersetzt
  - Em-dashes (12x), Pfeile, Section-Signs
- [x] `python-backend/litellm-gateway/config.yaml` Non-ASCII Zeichen ersetzt
  - 30+ Box-Drawing Chars, Em-dashes, Pfeile

Noch offen:

### 1.1 SeaweedFS Port-Binding Fix

Problem: `listen tcp 192.168.1.34:8080: bind: Zugriff verweigert` — weed bindet auf LAN IP.

Loesung: SeaweedFS mit `-ip=127.0.0.1 -port=8080` statt LAN IP. Oder `-publicUrl=http://localhost:8333`.

- [ ] `scripts/dev-stack2.ps1` SeaweedFS StartAction anpassen:
  ```powershell
  Start-LoggedProcess -Name "seaweedfs" -FilePath $seaweedExe `
      -ArgumentList @(
          "server",
          "-ip=127.0.0.1",
          "-ip.bind=127.0.0.1",
          "-dir=$seaweedDataDir",
          "-s3",
          "-s3.config=$($repoRoot)\tools\seaweedfs\s3.json"
      ) -WorkingDirectory $repoRoot
  ```

### 1.2 control-ui Files Routes — Gateway URL Fix

Problem: 7 Routes nutzen hardcoded `localhost:9060` statt `getGatewayBaseURL()` (`:8090`).

- [ ] `control-ui/src/app/api/files/route.ts` — nutze `getGatewayBaseURL()`
- [ ] `control-ui/src/app/api/files/[id]/route.ts`
- [ ] `control-ui/src/app/api/files/[id]/url/route.ts`
- [ ] `control-ui/src/app/api/files/[id]/reindex/route.ts`
- [ ] `control-ui/src/app/api/files/upload-intent/route.ts`
- [ ] `control-ui/src/app/api/files/search/route.ts`

Alle auf einheitliches `import { getGatewayBaseURL } from "@/lib/server/gateway"` umstellen.

---

## Stufe 2: Matrix Crypto Store auf Postgres

Problem 1: Go Appservice scheitert mit `olm machine load: SQL logic error: no such table: crypto_account (1)`.

Das liegt an einer **leeren SQLite DB** — mautrix-go's `SQLCryptoStore` sollte das Schema automatisch anlegen, tut es aber bei `Load()` vor dem Schema-Upgrade nicht.

**Problem 2 (geklaert 11.04.2026): libolm CGO Dependency — bereits geloest via `-tags goolm`.**

Bei `go build ./...` ohne Build-Tag schlaegt `mautrix@v0.22.0/crypto/libolm` mit fehlendem
C-Header `olm/olm.h` fehl. Das war zunaechst verwirrend, stellte sich aber als Non-Issue raus:

**Root Cause:**
mautrix-go hat **zwei parallele Crypto-Backends** mit Build-Tags:
- `crypto/libolm/*.go` mit `//go:build !goolm` — default, braucht libolm C-Library
- `crypto/goolm/*.go` mit `//go:build goolm` — pure Go, kein CGO

Unser `internal/crypto/machine.go` ist bereits fuer `goolm` geschrieben (Zeile 23 Kommentar:
"kapselt OlmMachine via goolm — Pure-Go, kein libolm"). Das Binary wird in
`scripts/dev-stack2.ps1:238` korrekt gebaut:

```powershell
& go build -tags goolm -o ".\tmp\appservice.exe" ./cmd/appservice
```

Der Fehler kam nur bei **manuellen** `go build ./...` / `go test ./...` Commands ohne Tag.
Das ist Dev-Ergonomie, kein Blocker.

**Verifikation (11.04.2026):**
```bash
$ cd go-appservice && go build -tags goolm ./...
EXIT=0
$ go test -tags goolm ./...
ok   matrix/go-appservice/internal/storage     3.666s
ok   matrix/go-appservice/internal/telemetry  20.393s
```

**Keine Code-Aenderung notwendig.** Dokumentations-Action:
- [ ] `go-appservice/README.md` erweitern: "Always build with `-tags goolm`"
- [ ] Optional: `//go:build goolm`-Dummy in `internal/crypto/assert_goolm.go` der einen
  klaren Compile-Error gibt wenn ohne Tag gebaut wird (besser als libolm.h Fehler)

### Entdeckte Probleme waehrend Stufe 3 Tests (11.04.2026)

- [x] Go Appservice Crypto `no such table: crypto_account` → Fixed via `cryptoStore.DB.Upgrade(ctx)` vor `Load()`
- [x] **libolm CGO dependency** → Non-Issue. Code ist bereits goolm-basiert, devstack2.ps1 baut korrekt mit `-tags goolm`. Nur manuelle `go build ./...` ohne Tag scheitern. README-Doc ausstehend.
- [x] **Postgres Crash** `WAL writer process terminated by exception 0xFFFFFFFF` → Windows Defender scannt WAL files, fsync blockiert (30s+ elapsed time im Log), WAL writer crashed im Timeout. **Geloest durch Defender-Exclusions** auf `tools/pgsql-data/` + `tools/pgsql/bin/` + `postgres.exe` Process (11.04.2026, User-bestaetigt).

---

**Wichtiger Kontext: Tuwunel hat EIGENE Datenbank**

```
Tuwunel Homeserver (extern, nicht unser Code)
  └─ RocksDB: ./homeserver/data/db
  └─ Managed by Tuwunel binary
  └─ Stores: Rooms, Events, Device Keys, State Resolution

Unser Postgres Cluster (tools/pgsql-data/)
  ├─ public schema       — Hindsight (banks, memory_units, entities)
  ├─ agent schema        — Unser (audit_events, skills_state, consent, ...)
  ├─ ingestion schema    — Unser (jobs, chunks)
  └─ matrix_crypto (NEU) — Olm Account + Keys fuer Appservice-Bot

Unser Go Appservice Olm Store
  VORHER:  SQLite (go-appservice/data/crypto.sqlite3)
  JETZT:   Postgres matrix_crypto schema (via cfg.PostgresDSN)
  FALLBACK: SQLite wenn PostgresDSN leer
```

Der Olm Crypto Store im Go Appservice ist NUR fuer den **Appservice Bot** der
Messages im Namen von `@agent-*:matrix.local` Users verschluesselt. Das hat
**nichts** mit Tuwunels Matrix Room State zu tun — das ist eine separate Concern.

### 2.1 Option A: SQLite Schema-Upgrade Fix ✅ DONE

- [x] `go-appservice` beim ersten Start: `cryptoStore.DB.Upgrade()` **vor** `OlmMachine.Load()`
- [x] Fix in `internal/crypto/machine.go` (vor dieser Session implementiert)

### 2.2 Option B: Migration auf Postgres ✅ DONE (13.04.2026)

**Implementierung:**

- [x] `internal/crypto/machine.go` — Dialect-Switch via `openCryptoDB()`:
  - `cfg.PostgresDSN` (= `HINDSIGHT_DB_URL`) starts with `postgres://` → `sql.Open("pgx", dsn)` + dialect `"postgres"`
  - `CREATE SCHEMA IF NOT EXISTS matrix_crypto` automatisch
  - `SET search_path TO matrix_crypto, public` damit mautrix-go Tables dort landen
  - Sonst → SQLite fallback (`MATRIX_CRYPTO_DB_PATH`)
  - mautrix-go **erzwingt** `*sql.DB` via `dbutil.NewWithDB()` — pgxpool NICHT moeglich (Library-Constraint)
  - Import: `_ "github.com/jackc/pgx/v5/stdlib"` (wrapper, nicht native)
- [x] `internal/config/config.go` — neues Feld `PostgresDSN` mit Fallback-Chain:
  `POSTGRES_URL` → `HINDSIGHT_DB_URL` → `DATABASE_URL` (forward-compatible fuer exec-18 Rename)
- [x] `internal/handler/server.go` — `crypto.New(ctx, client, cfg.PostgresDSN, cfg.CryptoDBPath, ...)`
- [x] `internal/app/storage_wiring.go` — `BuildArtifactService(host, port, cfg.PostgresDSN)` statt direkt env lesen
- [x] Key-Backup + Cross-Signing Seeds Pfad: bei PG in `./data/crypto/`, bei SQLite neben der DB-Datei
- [x] `golangci-lint` 0 issues, `go build -tags goolm ./...` EXIT=0

**Env-Var Konsolidierung:**

Kein neues `MATRIX_CRYPTO_DB_URL` noetig. Stattdessen nutzt Go dieselbe PG-Instanz
wie Python (`HINDSIGHT_DB_URL`), mit eigenem Schema `matrix_crypto`. Die Fallback-
Chain in `config.resolvePostgresDSN()` macht den Env-Var-Namen zukunftssicher:

```
POSTGRES_URL → HINDSIGHT_DB_URL → DATABASE_URL → "" (= SQLite fallback)
```

| Env-Var | Gesetzt in | Nutzer |
|---------|-----------|--------|
| `HINDSIGHT_DB_URL` | go-appservice/.env.development + python-backend/.env | Go (storage + crypto), Python (hindsight + agent + ingestion) |
| `MATRIX_CRYPTO_DB_PATH` | go-appservice/.env.development | Go (SQLite fallback, nur wenn PG DSN leer) |

**Nach Stufe 2B: `modernc.org/sqlite` Dependency im go.mod** bleibt als Fallback
fuer Dev-Setups ohne Postgres. In exec-18 Phase 0 wird der SQLite-Pfad in
`crypto/machine.go` entfernt und die Dependency kann weg.
- [ ] `go-appservice/internal/crypto/machine.go`:
  ```go
  db, err := dbutil.NewWithDB(rawDB, dialect)
  if err != nil { ... }
  // Mautrix-go nutzt default public schema, setze search_path
  if dialect == "pgx" {
      _, _ = rawDB.Exec("SET search_path TO matrix_crypto, public")
  }
  ```

### 2.3 Migration 019: matrix_crypto Schema

- [ ] Neue Alembic Migration `019_matrix_crypto_schema.py`:
  ```python
  def upgrade():
      op.execute("CREATE SCHEMA IF NOT EXISTS matrix_crypto")
      # mautrix-go erstellt seine Tables selbst beim ersten Connect
      # diese Migration stellt nur sicher dass das Schema existiert

  def downgrade():
      op.execute("DROP SCHEMA IF EXISTS matrix_crypto CASCADE")
  ```

### 2.4 Env-Files updaten

- [ ] `go-appservice/.env.development`:
  ```
  # Option A (SQLite, default)
  MATRIX_CRYPTO_DB_PATH=./data/crypto.sqlite3

  # Option B (Postgres, preferred)
  MATRIX_CRYPTO_DB_URL=postgres://postgres@localhost:5433/hindsight_dev?search_path=matrix_crypto
  ```

**Empfehlung:** Stufe 2 startet mit **Option A** (SQLite Upgrade Call) fuer schnellen Verify-Fix.
Option B (Postgres) wird Teil von exec-18 (Unified Schema).

---

## Stufe 3: Files API — Full-Stack Implementation

### 3.0 Vorarbeit: pgxpool native + Schema Separation (erledigt 11.04.2026)

**Vorher:** `metadata_store_postgres.go` nutzte `database/sql` + `github.com/jackc/pgx/v5/stdlib`
(Wrapper-Modus). Funktional OK, aber NICHT SOTA — kein native jsonb/uuid-Binding,
keine context-first Queries, kein COPY FROM, keine direkten OTel-Spans.

**Jetzt:** Rewrite auf `github.com/jackc/pgx/v5/pgxpool` + `pgx.RowToStructByName[T]`.
Das Interface `MetadataStore` blieb unveraendert, Service + Handler nicht angefasst.

**Warum jetzt und nicht spaeter:**

1. **Boilerplate in Stufe 3 direkt** — `pgx.RowToStructByName[artifactRow]` ersetzt
   ~30 Zeilen Scanner-Code pro Methode. Bei 6 Methoden = ~150 Zeilen gespart.
2. **exec-18 Unified Schema** — 8 neue Tabellen (sessions, evals, metrics, traces, spans,
   components, schedules, approvals) sind jsonb/uuid/timestamptz-heavy. Native pgx liest
   jsonb direkt in `map[string]any` oder structs, keine `json.Marshal`-Umwege.
   Geschaetzt ~3-5h Arbeit in exec-18 gespart.
3. **exec-17 Tracing** — `pgxotel` adapter fuer automatische Query-Spans, keine manuellen
   Timer/Span Wrapper pro Call.
4. **exec-15 Ingestion bulk insert** — `COPY FROM` nativ fuer 1000+ Chunk-Batches.

**Zusaetzlich: Schema Separation.** Die Tabelle wurde von `public.artifact_metadata`
nach `storage.artifact_metadata` verschoben via `ALTER TABLE ... SET SCHEMA` (one-shot
migration im `migrate()` Code, idempotent). Begruendung:

- `public` schema gehoert Python Hindsight (banks, memory_units, entities)
- `storage` gehoert Go Appservice (artifact_metadata jetzt, matrix_crypto_* spaeter)
- Visuelle Trennung: `\dt storage.*` zeigt alle Go-owned Tables, `\dt public.*` alle
  Hindsight-Tables, keine Vermischung
- Erfuellt "Schema per Bounded Context" Pattern (Chris Richardson, Microservices Patterns)
- Dokumentiert in `specs/17-schema-ownership.md`

**Defense-in-Depth (PG Permissions)** ist verschoben nach **exec-18 Phase 0** —
aktuell laeuft alles als `postgres` superuser, die Ownership-Regel ist Konvention.
PG-Level Enforcement (separate Users `matrix_go_user`, `matrix_py_user` mit
schema-level GRANTs) kommt sobald wir die exec-18 Tabellen anfassen.

**Verified:**
- [x] `go test ./internal/storage/...` — alle Tests gruen (6 Integration + 26 Unit cases)
- [x] `metadata_store_postgres_test.go` deckt Create/Get/MarkUploaded/ListByUser/CountByStatus/Delete ab
- [x] Cross-User Isolation Test (userA sieht nie userB files) — pass
- [x] `ErrArtifactNotFound` mapping via `pgx.ErrNoRows` — funktioniert
- [x] Schema-Rename von `public.artifact_metadata` → `storage.artifact_metadata` — funktioniert
- [x] `specs/17-schema-ownership.md` geschrieben

**Was NICHT umgestellt wurde (und warum):**
- `metadata_store.go` (SQLite) — pgx ist Postgres-only, kein Wechsel moeglich
- `crypto/machine.go` (Matrix Olm Store) — mautrix-go `dbutil.NewWithDB(rawDB, dialect)`
  zwingt `*sql.DB`. Wenn Stufe 2 Option B (PG-Migration) kommt, muss das ueber
  `pgx/v5/stdlib`-Wrapper laufen — **nicht** pgxpool native. Library-Constraint von
  mautrix-go, kein Workaround.

### 3.0.1 Test-Coverage Baseline (11.04.2026)

**Vor exec-19 Stufe 3:** 39 Source-Files, **1 Test-File** (`telemetry_test.go`, portiert aus tradefusion exec-17). Alles andere ungetestet. Go-appservice war praktisch untestet.

**Jetzt (nach Stufe 3, Phase 1+2+3 Progress, 11.04.2026):** 8 Test-Files + die Phase 3 FilesService Tests:

| Test-File | Was | Modus |
|-----------|-----|-------|
| `storage/media_type_test.go` | `ClassifyMediaType` 26 Edge-Cases + extension handling | pure unit |
| `storage/metadata_store_postgres_test.go` | Create/Get/MarkUploaded/ListByUser/CountByStatus/Delete + per-user isolation | integration gegen PG (:5433), skip wenn down |
| `storage/provider_s3_test.go` | Put/Get gegen mock HTTP + Config validation (missing bucket/endpoint/creds) | pure unit (httptest server) |
| `storage/s3_lister_test.go` | ListObjects/Delete + prefix isolation + maxKeys limit + idempotent delete | integration gegen SeaweedFS (:8333), skip wenn down |
| `storage/signer_test.go` | HMAC token roundtrip + tamper + expiry + wrong-secret + action roundtrip **+ UserID binding + tamper detection + 5 cases** | pure unit |
| `storage/files_service_test.go` | **Phase 3:** List (user-iso/media-filter/ingestion-join/ingestion-down), Overview, Get, Delete **+ write-flows: TriggerIngestion per media-type, Reindex, MarkReady auto-ingest, Delete cancels running job, forward-ready 404→ErrPipelineNotImplemented** — 17 Test-Funktionen | pure unit (httptest mock + fake store) |
| `connectors/ingestion/client_test.go` | ListJobs/GetJob/Health + 404→ErrJobNotFound + nil client | pure unit (httptest server) |
| `connectors/ingestion/errors.go` | Error const (`ErrJobNotFound`, `ErrPipelineNotImplemented`) | n/a |

**Alle Tests gruen:** `HINDSIGHT_DB_URL=... go test -tags goolm -count=1 ./internal/storage/... ./internal/connectors/ingestion/...`

**Full Build:** `go build -tags goolm ./...` → EXIT=0

### 3.0.2 Security Gap entdeckt: Signer Token ohne User-Binding

Beim Portieren von `provider_s3_test.go` + `signer_test.go` aus dem Dead-Code-Tree
(`control/storage/go-backend`) ist aufgefallen dass **`TokenClaims` keine UserID** hat:

```go
type TokenClaims struct {
    ArtifactID string
    Action     Action
    ExpiresAt  time.Time
    // UserID fehlt!
}
```

**Konsequenz:**
1. User A fragt `POST /api/v1/storage/artifacts/upload-url` → bekommt Token `T` fuer Artifact `X`
2. Token wandert durch Logs / Clipboard / Browser-Back / leaked-request
3. **User B kann mit `T` auch zu Artifact `X` uploaden** — der Signer prueft nur HMAC + Expiry, **nicht** Ownership

**Root Cause:** Die capability-based-access Architektur (exec-15 D12) war token-based, nicht identity-based. Tradefusion hatte das gleiche Loch — wir uebernehmen den Bug beim 1:1-Portieren.

**Fix Phase 2 (A):** `TokenClaims.UserID` hinzufuegen, Signer/Service/Handler erweitern, Handler prueft `X-Actor-User-Id` header gegen Token-UserID. Siehe Phase-Plan unten.

### 3.0.3 Test-Coverage Audit — Top P0 Files die noch ungetestet sind

(Via Subagent-Audit aller 34 Source-Files, 11.04.2026)

| Rang | File | Priorität | Warum |
|------|------|-----------|-------|
| 1 | `handlers/http/artifact_handler.go` | P0 | Signed URLs + User-ID Binding Gap (Phase 2) |
| 2 | `storage/service.go` | P0 | CreateArtifact/IssueUploadURL Orchestrierung, state mutations |
| 3 | `handler/server.go` | P0 | Matrix Transaction Receiver, Event-Routing |
| 4 | `keyvault/keyvault.go` | P0 | AES-256-GCM Vault fuer Secrets-at-Rest |
| 5 | `keyvault/hpke.go` | P0 | HPKE RFC 9180 (MLKEM768X25519 Post-Quantum) — gegen known vectors testen |
| 6 | `storage/provider_filesystem.go` | P1 | Path-Traversal moeglich, SHA256 silent-fail |
| 7 | `handlers/http/agent_chat_handler.go` | P1 | Request parsing Attachments + Streaming |
| 8 | `handlers/http/agent_audio_handler.go` | P1 | Audio input parsing |
| 9 | `handlers/http/agent_tool_proxy_handler.go` | P1 | Tool param forwarding |
| 10 | `handlers/http/memory_handler.go` | P1 | KG seed JSON parsing |
| 11 | `connectors/agentservice/client.go` | P1 | Agent HTTP client |
| 12 | `connectors/memory/client.go` | P1 | Memory service client |
| 13 | `natsbridge/bridge.go` | P1 | Inbound/Reply message serialization |
| 14 | `intent/agent.go` | P1 | Matrix event construction (virtual user-ids) |

**Hard-to-test (Homeserver-Mock noetig):**
- `crypto/machine.go` + `crypto/statestore.go` — E2EE wrapper, testbar nur mit echter Homeserver-Instance

### 3.0.4 Umsetzungsplan (A → B → C)

**Phase 2 (A) — User-ID Token Binding (security fix) ✅ DONE 11.04.2026:**
1. [x] `storage/types.go`: `TokenClaims.UserID string` + `ErrForbidden` hinzugefuegt
2. [x] `storage/signer.go`: Issue/Verify packt UserID in signed payload (`uid,omitempty`)
3. [x] `storage/service.go`: `IssueUploadURL`/`IssueDownloadURL`/`GetArtifact`/`UploadArtifact`/`OpenDownload` nehmen userID; neuer `assertOwnership()` helper; Legacy-Artifacts mit leerer UserID bleiben backward-kompatibel
4. [x] `handlers/http/artifact_handler.go`: `actorUserID(r)` liest `X-Actor-User-Id`, alle Handler reichen es durch, `ErrForbidden` → HTTP 403
5. [x] `signer_test.go`: 3 neue Tests (Roundtrip mit 5 UserID-Varianten, Hybrid-Attack tamper detection, Action roundtrip mit UserID)
6. [x] `go test -tags goolm ./internal/storage/...` grün

**Phase 3 (B) — Stufe 3 Core Files API** (in progress 11.04.2026):

*Erledigt:*
1. [x] `storage/files_service.go` — **READ flows:** List (mit Ingestion-Join, MediaType-Filter post-SQL, ingestion-down non-fatal), Overview (per-user counts), Get (owner-enforced), Delete (mit running-job cancel)
2. [x] `storage/files_service.go` — **WRITE flows:** `CreateUploadIntent` (delegiert an Service.CreateArtifact+IssueUploadURL), `MarkReady` (Direct-PUT flow counterpart zu Proxy-PUT, mit optional Auto-Ingest), `IssueDownloadURL`, `TriggerIngestion` (Media-Type routing), `Reindex`
3. [x] `connectors/ingestion/types.go` — `PipelineKind` const + Request-Structs fuer alle Pipelines (document/note/link/image/audio/video/batch), `IsImplemented()` flag
4. [x] `connectors/ingestion/client.go` — `TriggerDocument/Note/Link/Image/Audio/Video/Reindex/CancelJob` + `postJSON` helper, 404/501 auf `/ingest/*` → `ErrPipelineNotImplemented`
5. [x] `connectors/ingestion/errors.go` — `ErrPipelineNotImplemented` fuer forward-ready stubs
6. [x] `storage/files_service_test.go` — 17 Tests (Read + Write flows + Ownership + MediaType routing + Auto-Ingest + Cancel-on-Delete + forward-ready 404 handling)

*Offen:*
7. [ ] `handlers/http/files_handler.go` — HTTP handlers fuer `GET /api/v1/files`, `GET /{id}`, `DELETE /{id}`, `GET /{id}/url`, `POST /upload-intent`, `POST /{id}/mark-ready`, `POST /{id}/ingest`, `POST /{id}/reindex`, `GET /overview`
8. [ ] `handler/server.go` — FilesService-Wiring (Store + S3Lister + IngestionClient + Service injizieren), Route registration
9. [ ] `control-ui/src/app/api/files/**/route.ts` — BFF `X-Actor-User-Id` Header forward + die 9 neuen Endpoint-Proxies
10. [ ] `handlers/http/files_handler_test.go` — HTTP integration

### 3.0.5 Review-Fixes Status (complete 11.04.2026)

Nach Phase 3 Core code review wurden 11 Fixes identifiziert. **Alle 11 DONE:**

**Small (3/3 ✅):**
- [x] Fix #1: `pipelineForMediaType` — Data/Other skip silent statt document fallback
- [x] Fix #2: `triggerKind` — Note/Link/Batch → `ErrUnsupportedPipelineForArtifact`
- [x] Fix #3: `postJSON` 404 body-aware mapping (`isMissingRouteBody` helper, FastAPI default vs. resource-specific unterscheiden)

**Medium (3/3 ✅):**
- [x] Fix #4: Overview `CountByMediaType` via SQL — `media_type` als PG Spalte + Backfill (Option A, scales zu 10k+ files per user)
- [x] Fix #5: `MarkReadyResult` struct (`MarkedReady` / `IngestTriggered` / `IngestJobID` / `IngestError`) — Partial-Commit semantics, mark-ready success ist getrennt von ingestion success
- [x] Fix #6: Ownership consolidation — `FilesService.checkOwnership` als single gate, Service.assertOwnership bleibt als defense-in-depth fuer direct artifact_handler paths (dokumentierter Dual-Check)

**Large (3/3 ✅):**
- [x] Fix #7: `ObjectLister` join in `FilesService.List` — orphan S3 blobs (in S3 aber nicht in metadata) werden surfaced mit `Status="orphan"` + synthetic `ID="orphan:<key>"`, operators koennen reconcilen
- [x] Fix #8: Python worker shared-secret auth — `X-Service-Auth` header via `WithSharedSecret` option in Go client + Python middleware mit `hmac.compare_digest`, dev-mode fallback bei leerem secret, `INGESTION_WORKER_SHARED_SECRET` env var synced zwischen go-appservice + python-backend
- [x] Fix #9: `AllowLegacyOwnerless` feature flag in `FilesServiceConfig` — default false (production-safe), dev-mode optional true fuer pre-exec-19 rows mit leerer UserID, warning log bei jedem Legacy-Access

**Security (2/2 ✅):**
- [x] Fix #10: `X-Actor-User-Id` trust documentation in `specs/17-schema-ownership.md` — neuer "Trust boundary: BFF is the gatekeeper" Abschnitt plus "Inter-service authentication" Abschnitt mit production deployment rules (Go `:8090` darf nicht direkt exposed sein)
- [x] Fix #11: Warning-Logs via `slog.WarnContext` in hot paths: empty user_id in `List`, legacy owner-less rejected/allowed in `checkOwnership`, ingestion `ListJobs`/`ListObjects` failures

### 3.0.6 Neue Tests (Phase 3 Review-Fixes)

9 neue Test-Funktionen hinzugefuegt, alle gruen:

**`files_service_test.go`:**
- `TestFilesServiceMarkReadyIngestFails` — ingest failure darf mark-ready nicht hart failen lassen (Fix #5 semantics)
- `TestFilesServiceLegacyOwnerlessDefaultForbidden` — default: legacy artifact Get/Delete forbidden
- `TestFilesServiceLegacyOwnerlessAllowedWithFlag` — `AllowLegacyOwnerless=true` allows legacy access
- `TestFilesServiceLegacyEmptyRequestUserStillForbidden` — empty req user ist immer forbidden (auch mit flag)
- `TestFilesServiceListSurfacesOrphanS3Objects` — 1 known + 2 orphans = 3 records
- `TestFilesServiceListOrphanRespectsMediaTypeFilter` — MediaType-filter auch fuer orphans (3 blobs, filter audio → 1 result)
- `TestFilesServiceListSkipsOrphansIfNoLister` — ohne lister keine orphans (backward compat)

**`client_test.go` (ingestion):**
- `TestSharedSecretHeaderSent` — 5 methods (ListJobs/GetJob/Health/TriggerDocument/CancelJob) setzen den `X-Service-Auth` header
- `TestSharedSecretHeaderOmittedInDevMode` — ohne `WithSharedSecret` kein Header (dev mode)

**Verification:**
- `golangci-lint run --build-tags goolm ./...` → **0 issues**
- `HINDSIGHT_DB_URL=... go test -tags goolm -count=1 ./internal/storage/... ./internal/connectors/ingestion/...` → **alle gruen**
- `go build -tags goolm ./...` → **EXIT=0**

**SQLite Store Removal (exec-18 Phase 0 vorgezogen, DONE 11.04.2026):**
- [x] `internal/storage/metadata_store.go` geloescht (~700 Zeilen inkl. Tradefusion SourceSnapshot code)
- [x] `internal/storage/metadata_store_factory.go` geloescht
- [x] `types.go`: `SourceSnapshot`, `SourceSnapshotStatus` entfernt (toter tradefusion code)
- [x] `storage_wiring.go`: `NewArtifactMetadataStore` → direkt `NewPostgresMetadataStore`
- [x] `.env.example` + `.env.development`: `ARTIFACT_STORAGE_METADATA_PROVIDER`/`_DB_PATH` entfernt
- [x] Einziger metadata backend: `PostgresMetadataStore` (pgxpool native)
- [x] `modernc.org/sqlite` Dependency bleibt bis Stufe 2B (crypto store auf PG migriert)
- [x] Bringt **30 wrapcheck + modernize Issues** automatisch weg (Dead Code)

**Lint + Security Status (nach Review-Fixes + Handler, 13.04.2026):**
- `golangci-lint run --build-tags goolm ./...` — **0 issues** (von initial 50)
- `govulncheck -tags goolm ./...` — **0 code-reachable vulns** (Go toolchain auf 1.26.2)
- `go build -tags goolm ./...` — EXIT=0
- `go build -tags goolm -o ./tmp/appservice.exe ./cmd/appservice` — 51.9 MB binary

### 3.0.7 HTTP Handler Layer + Server Wiring (Phase 3 B final, 13.04.2026)

- [x] `handlers/http/files_handler.go` — 9 Endpoint-Funktionen:
  - `FilesListHandler` (GET /api/v1/files mit query params)
  - `FilesOverviewHandler` (GET /api/v1/files/overview)
  - `FilesUploadIntentHandler` (POST /api/v1/files/upload-intent)
  - `FilesItemHandler` (Multiplexer fuer /{id}, /{id}/url, /{id}/mark-ready, /{id}/ingest, /{id}/reindex)
  - `mapFilesError` error → HTTP status mapping (10 cases inkl. 207 Multi-Status)
  - `parseFileID` URL parser fuer sub-resource routing
- [x] `handler/server.go` — FilesService Wiring:
  - `IngestionClient` mit `WithSharedSecret` + `INGESTION_WORKER_URL` env var
  - `ObjectLister` via type-assert auf S3Provider
  - `AllowLegacyOwnerless` via `FILES_ALLOW_LEGACY_OWNERLESS` env var
  - Route registration: `/api/v1/files` + `/api/v1/files/` (catch-all)
- [x] `handlers/http/files_handler_test.go` — 18 Test-Funktionen:
  - Query param parsing, limit clamping, forbidden/error mapping (10 cases)
  - Dispatch tests fuer alle Sub-routes (Get/Delete/URL/MarkReady/Ingest/Reindex)
  - MarkReady partial-success → 207 Multi-Status
  - UploadIntent validation + success
  - `parseFileID` unit tests (8 cases)

### 3.0.8 control-ui BFF + Proxy Layer (Phase 3 B, 13.04.2026)

**Neue Datei: `control-ui/src/proxy.ts`** (Next.js 16 Proxy, Nachfolger von `middleware.ts`)
- Injiziert `X-Actor-User-Id: default-dev-user` auf jeden `/api/*` Request
- Injiziert `X-Request-ID` UUID wenn nicht vorhanden
- **MUSS UMGESTELLT WERDEN** bei Portierung zu tradefusion oder Produktions-Auth:
  - Ersetze hardcoded `DEV_DEFAULT_USER` durch `getToken()` aus `next-auth/jwt`
  - Pattern identisch zu `tradeview-fusion/src/proxy.ts` (Zeile 286: `token.sub` → `X-Auth-User`)
  - Keine BFF-Route muss sich aendern — nur proxy.ts austauschen
- Env-Vars: keine neuen noetig fuer Dev-Mode. In Production kommt NextAuth config dazu.

**BFF Route Updates:**
- [x] `app/api/files/route.ts` — GET: Query-Param forwarding + `X-Actor-User-Id` header fix
- [x] `app/api/files/[id]/route.ts` — GET handler NEU (Einzelfile-Detail) + DELETE existiert
- [x] `app/api/files/[id]/url/route.ts` — `X-Actor-User-Id` header forwarding fix
- [x] `app/api/files/upload-intent/route.ts` — `X-Actor-User-Id` header forwarding fix
- [x] `app/api/files/overview/route.ts` — NEU
- [x] `app/api/files/[id]/mark-ready/route.ts` — NEU
- [x] `app/api/files/[id]/ingest/route.ts` — NEU
- [x] `app/api/files/[id]/reindex/route.ts` — existiert, `X-Actor-User-Id` war korrekt
- [x] `app/api/files/search/route.ts` — existiert, unveraendert

**Env-Var Status:**

| Env-Var | Wo | Wert (Dev) |
|---------|-----|-----------|
| `HINDSIGHT_DB_URL` | go-appservice/.env.development | `postgres://postgres@localhost:5433/hindsight_dev` |
| `INGESTION_WORKER_URL` | go-appservice/.env.development | `http://127.0.0.1:8098` |
| `INGESTION_WORKER_SHARED_SECRET` | go-appservice/.env.development + python-backend/.env | `bc7800...` (synced) |
| `FILES_ALLOW_LEGACY_OWNERLESS` | go-appservice/.env.development | `true` |
| `GO_GATEWAY_BASE_URL` | control-ui/.env.local | `http://127.0.0.1:8090` |

**⚠️ MUSS BEI PORTIERUNG UMGESTELLT WERDEN:**
1. `control-ui/src/proxy.ts` — `DEV_DEFAULT_USER` → NextAuth JWT `token.sub` (gleich wie tradeview-fusion `proxy.ts`)
2. `go-appservice/.env.development` — `FILES_ALLOW_LEGACY_OWNERLESS=true` → `false` in Production
3. `INGESTION_WORKER_SHARED_SECRET` — neues Secret generieren pro Deployment
4. Go Header `X-Actor-User-Id` → evtl. umbenennen zu `X-Auth-User` fuer Konsistenz mit Tradefusion (aktuell zwei verschiedene Header-Namen — tradefusion nutzt `X-Auth-User`, matrix nutzt `X-Actor-User-Id`)

**Phase 3.5 — Python Worker Forward-Compatible Pipelines (folgt nach Phase 3):**

Der Go Ingestion Client ruft bereits `/ingest/image`, `/ingest/audio`, `/ingest/video`, `/ingest/batch` auf (forward-ready). Aktuell gibt der Python Worker 404 zurueck → `ErrPipelineNotImplemented` → HTTP 501 nach oben. Damit Auto-Ingest fuer Media funktioniert, muss Python diese implementieren:

- [ ] `python-backend/ingestion/pipelines/image.py` — OCR (Tesseract / Florence-2) + Vision Captioning (OpenAI / local qwen-vl)
- [ ] `python-backend/ingestion/pipelines/audio.py` — Whisper Transcription → text chunks
- [ ] `python-backend/ingestion/pipelines/video.py` — Key-frame extraction (ffmpeg) + Whisper (audio track) + scene description
- [ ] `python-backend/ingestion/pipelines/batch.py` — ZIP/TAR fan-out zu per-file pipelines
- [ ] `python-backend/ingestion/worker.py` — `POST /ingest/image`, `/audio`, `/video`, `/batch` routes
- [ ] `python-backend/ingestion/worker.py` — `POST /jobs/{job_id}/cancel` route (best-effort, markiert job als "cancelled" in DB, versucht running task zu stoppen)
- [ ] `python-backend/ingestion/core/types.py` — `PipelineKind` enum um `image/audio/video/batch` erweitern

**Phase 4 (C) — Test-Expansion der P0/P1 Files ✅ DONE 13.04.2026:**

Commit `45f12e1` — 13 neue Test-Files, ~150 Tests, 3 Code-Fixes.

| # | Test-File | Tests | Modus |
|---|-----------|-------|-------|
| 1 | `keyvault/keyvault_test.go` | 15 (AES roundtrip/tamper/cross-vault/nonce + HPKE roundtrip/cross/key + factory) | pure unit |
| 2 | `storage/provider_filesystem_test.go` | 6 (roundtrip, not-found, path-traversal 5 vectors, SHA256, subdirs) | pure unit |
| 3 | `storage/service_test.go` | 6 (create, upload-url, get, wrong-user, delete) | pure unit (fake store+provider) |
| 4 | `handlers/http/artifact_handler_test.go` | 6 (upload-url, metadata, not-found, forbidden, invalid-token, download) | httptest |
| 5 | `handlers/http/agent_chat_handler_test.go` | 5 (method, SSE stream, invalid-json, upstream-error, body-forward) | httptest |
| 6 | `handlers/http/agent_audio_handler_test.go` | 4 (transcribe, synthesize, method, invalid-json, body-too-large) | httptest |
| 7 | `handlers/http/agent_tool_proxy_handler_test.go` | 6 (GET/POST proxy, method, nil-client) | httptest (fake interface) |
| 8 | `handlers/http/memory_handler_test.go` | 5 (seed, query, nodes, search, method) | httptest |
| 9 | `connectors/agentservice/client_test.go` | 5 (post, get, default-url, nil, normalization) | httptest |
| 10 | `connectors/memory/client_test.go` | 6 (seed, query, nodes, default-url, slash, error) | httptest |
| 11 | `natsbridge/bridge_test.go` | 3 (inbound serialization, reply serialization, omitempty) | pure unit |
| 12 | `intent/agent_test.go` | 2 (user-id generation, server-name) | pure unit |

**Code-Fixes entdeckt durch Tests (Phase 4):**

- [x] **Fix A:** `agent_chat_handler.go` — SSE Status-Forwarding. Upstream non-2xx wird jetzt
  als JSON-Error zurueckgegeben statt als maskierter 200+SSE-Stream. Clients sehen echte
  Fehler (500/502/etc.) statt eines "broken stream".
- [x] **Fix C:** `agent_chat_handler.go` — `AgentChatHandler(url, httpClient...)` nimmt optionalen
  `*http.Client` Parameter fuer Testability. Default bleibt 5-Minuten-Timeout Client.
  `agentChatHTTPClient` → `defaultChatHTTPClient` umbenannt.
- [x] **Fix D:** `artifact_handler.go` — `parseArtifactPath` Kommentar dokumentiert die invertierte
  Upload-URL-Struktur (`/upload/{id}` statt `/{id}/upload`) als historisches Tradefusion-Artefakt.
- [x] `keyvault.go` — gosec G602 `//nolint` fuer bounds-checked slice access (false positive)

**Design-Entscheidung dokumentiert (nicht gefixt):**
- **Fix B (uebersprungen):** `memory/client.go` + `agentservice/client.go` geben (status, body, nil)
  bei non-2xx zurueck — kein error. Das ist ein bewusstes **Proxy-Pattern**: Handler forwarden den
  upstream Status 1:1. Ingestion-Client hingegen ist ein **Business-Client** der errors interpretiert.
  Zwei verschiedene Patterns, beide korrekt fuer ihren Use-Case.

**Gesamte go-appservice Test-Coverage nach Phase 4:**
- 17 Test-Files, ~150+ Test-Funktionen
- 9/9 Pakete mit Tests PASS
- Pakete ohne Tests: `cmd/appservice`, `app`, `config`, `contracts`, `crypto`, `handler`, `registration`, `requestctx`
  (Glue-Code, Config-Loading, Struct-only, oder hard-to-test ohne Homeserver)

---

Die Files API ist **nicht** trivial. Sie muss drei Datenquellen vereinigen und per-User isoliert sein:

1. **SeaweedFS S3** (`:8333`) — Source of Truth fuer alle Blobs (Upload/Download/Listing)
2. **Artifact Metadata Store** (`agent.artifact_metadata` PG table) — Namen, Content-Type, Size, Upload-Tokens
3. **Ingestion Jobs** (`ingestion.jobs` PG table) — Pipeline-State fuer Files die durch RAG-Pipeline liefen

### 3.1 Datenquellen-Architektur

```
SeaweedFS S3 (:8333)
  ├── bucket: user-{user_id}-files
  │   ├── object: {artifact_id}/{filename}
  │   └── ...
  │
ArtifactMetadataStore (Postgres: agent.artifact_metadata)
  ├── artifact_id, user_id, filename, content_type, size_bytes, sha256
  ├── retention_class, status (pending/uploaded/ready/failed)
  └── created_at, updated_at
  
IngestionJobs (Postgres: ingestion.jobs)
  ├── id, file_id, pipeline, user_id, status, progress
  ├── chunks_total, chunks_done, error_message
  └── started_at, completed_at
```

**Die Files API joined ALLE drei Quellen** damit der User sieht:
- Files die nur in S3 sind (direkt upload, kein Ingestion) → Audio, Video, Images
- Files die in S3 + ArtifactMetadata sind (upload via BFF)
- Files die in allen drei Quellen sind (Document mit RAG-Index)

### 3.2 Per-User Isolation

**Kritisch fuer exec-19**: Der aktuelle Entwurf hat KEINE User-Filterung.
Jeder Request muss einen `user_id` Context haben (aus Session oder Matrix ID).

- [ ] `go-appservice/internal/handlers/http/files_handler.go` — alle Handlers
  extrahieren `user_id` aus Header `X-Actor-User-Id` (aus control-ui BFF gesetzt)
- [ ] `ListFiles` filtert nach `user_id`
- [ ] `GetFile` / `DeleteFile` / `UploadIntent` pruefen `user_id` Ownership
- [ ] SeaweedFS Bucket-Strategie: ein Bucket pro User (`user-{user_id}-files`)
  oder ein Prefix pro User (`user-{user_id}/artifact-id/filename`)
  → **Empfehlung: Prefix** (einfacher, kein Bucket-Management)
- [ ] Artifact Metadata Store braucht `user_id` Filter in allen Queries
- [ ] Ingestion Jobs haben schon `user_id`, aber `list_recent()` muss filtern

### 3.3 Route-Spezifikation (erweitert)

| Route | Methode | Zweck | Datenquelle |
|-------|---------|-------|------------|
| `GET /api/v1/files` | List | Aggregierte Overview + Files pro User | Jobs + Metadata + S3 |
| `GET /api/v1/files?type=audio` | List | Nach Media-Type filtern | Jobs + Metadata + S3 |
| `GET /api/v1/files?status=pending` | List | Nach Ingestion-Status filtern | Jobs |
| `GET /api/v1/files/{id}` | Detail | File Details + Metadata | Metadata + Jobs |
| `DELETE /api/v1/files/{id}` | Delete | S3 Object + Metadata + Jobs cleanup | Alle drei |
| `GET /api/v1/files/{id}/url` | Sign | Presigned Download URL (TTL 15 min) | Metadata + S3 signing |
| `POST /api/v1/files/{id}/reindex` | Reindex | Trigger Re-Ingestion | Ingestion Worker |
| `POST /api/v1/files/upload-intent` | Upload | Presigned Upload URL erstellen | Metadata + S3 signing |
| `GET /api/v1/files/search?q=...` | Search | Full-Text Suche in indexed files | Ingestion Worker search |

### 3.4 Response-Struktur (voll ausgestattet)

Matches `control-ui/src/features/files/components/*` FileRecord + FilesOverviewData.

```go
type FileRecord struct {
    ID          string    `json:"id"`
    Name        string    `json:"name"`
    Type        MediaType `json:"type"`                    // document|image|audio|video|data|other
    Extension   string    `json:"extension,omitempty"`     // pdf, mp3, png, ...
    ContentType string    `json:"content_type,omitempty"`  // MIME type
    Status      string    `json:"status"`                  // uploaded|pending|indexing|done|failed
    SizeBytes   int64     `json:"size_bytes,omitempty"`
    SHA256      string    `json:"sha256,omitempty"`
    CreatedAt   string    `json:"created_at"`
    UpdatedAt   string    `json:"updated_at,omitempty"`
    UserID      string    `json:"user_id,omitempty"`

    // Ingestion-specific (nil if not ingested)
    Pipeline    string    `json:"pipeline,omitempty"`     // document|note|link|batch
    Progress    float64   `json:"progress,omitempty"`     // 0.0 - 1.0
    ChunksTotal int       `json:"chunks_total,omitempty"`
    ChunksDone  int       `json:"chunks_done,omitempty"`
    Error       string    `json:"error,omitempty"`

    // Media-specific (extracted from content when available)
    // Audio
    DurationSec float64   `json:"duration_sec,omitempty"`
    // Video
    Width       int       `json:"width,omitempty"`
    Height      int       `json:"height,omitempty"`
    // Image EXIF
    TakenAt     string    `json:"taken_at,omitempty"`
    GPS         *GPSCoord `json:"gps,omitempty"`
}

type FilesOverviewResponse struct {
    TotalDocuments  int                `json:"total_documents"`
    IndexingPending int                `json:"indexing_pending"`
    IndexingFailed  int                `json:"indexing_failed"`
    RecentUploads   []FileRecord       `json:"recent_uploads"`
    ByType          map[MediaType]int  `json:"by_type"`         // {document: 12, image: 34, ...}
    TotalBytes      int64              `json:"total_bytes"`
}
```

### 3.5 Media-Type Classification

Zentrale Funktion in Go die aus `content_type` oder `filename` extension den
`MediaType` ableitet. Wird bei jeder File-Listing-Operation verwendet.

```go
const (
    MediaTypeDocument MediaType = "document"  // pdf, md, txt, html, docx, doc, odt
    MediaTypeImage    MediaType = "image"     // png, jpg, svg, webp, avif, gif
    MediaTypeAudio    MediaType = "audio"     // mp3, wav, opus, m4a, flac, ogg
    MediaTypeVideo    MediaType = "video"     // mp4, webm, mkv, mov, hls
    MediaTypeData     MediaType = "data"      // csv, tsv, json, xlsx, xls, parquet
    MediaTypeOther    MediaType = "other"     // fallback
)

func ClassifyMediaType(contentType, filename string) MediaType {
    // 1. Check content-type prefix
    // 2. Check known content-types exactly
    // 3. Fallback: filename extension
}
```

### 3.6 SeaweedFS S3 ListObjects Integration

**Neue Komponente** in `go-appservice/internal/storage/`:

- [ ] `s3_lister.go` — wraps SeaweedFS S3 API fuer Listing
  - Nutzt bestehenden `provider_s3.go` Client
  - `ListObjects(bucket, prefix, maxKeys)` -> `[]S3Object{Key, Size, LastModified, ETag}`
  - Per-User Filter via prefix `user-{user_id}/`
- [ ] `FilesService` integriert S3 Listing + Metadata-Join:
  ```go
  func (s *FilesService) List(userID string, filters FileFilters) ([]FileRecord, error) {
      // 1. Query ArtifactMetadataStore fuer User
      // 2. Query IngestionJobs fuer User
      // 3. List S3 Objects fuer User-Prefix
      // 4. Merge/Join by artifact_id
      // 5. Classify media type
      // 6. Apply filters (type, status, limit)
      // 7. Return sorted by created_at DESC
  }
  ```

### 3.7 Ingestion Worker Extensions (Python)

- [x] `python-backend/ingestion/tracking/jobs.py` — neue `list_recent()` Method
- [x] `python-backend/ingestion/worker.py` — neue `GET /jobs` Route mit Filtern
- [ ] Pipeline-Support fuer Media-Files (optional, spaetere Stufe):
  - `PipelineKind.AUDIO` — Whisper Transcription → Hindsight
  - `PipelineKind.IMAGE` — Vision Model Description → Hindsight
  - `PipelineKind.VIDEO` — Key-Frame Extraction + Whisper
  - **Fuer exec-19 nicht kritisch** — Media-Files koennen als "uploaded only" markiert werden

### 3.8 Implementation Files

**Go (go-appservice):**

- [ ] `internal/handlers/http/files_handler.go` — HTTP handlers (ListFiles, GetFile, DeleteFile, UploadIntent, FileURL, Reindex, Search)
- [ ] `internal/handlers/http/files_media_types.go` — `ClassifyMediaType` helper
- [ ] `internal/connectors/ingestion/client.go` — HTTP client fuer Python ingestion worker
- [ ] `internal/storage/s3_lister.go` — SeaweedFS ListObjects wrapper
- [ ] `internal/storage/files_service.go` — Join Logic (Metadata + Jobs + S3)
- [ ] `internal/storage/metadata_store.go` — erweitern um `ListByUser(userID, filters)`
- [ ] `internal/handler/server.go` — Route Registrierung

**Python (ingestion worker):**

- [x] `ingestion/tracking/jobs.py` — `list_recent()` Method
- [x] `ingestion/worker.py` — `GET /jobs` Route
- [ ] `ingestion/worker.py` — `GET /search?q=...&user_id=...` Route

**control-ui BFF:**

- [x] `src/lib/server/gateway.ts` — zentraler `getGatewayBaseURL()`
- [x] 7 Files Routes auf `getGatewayBaseURL()` umgestellt
- [ ] BFF Routes forwarden `X-Actor-User-Id` Header aus Session
- [ ] BFF Routes forwarden `type`, `status`, `limit` Query-Params

### 3.9 control-ui Viewer Packages

Die Viewer sind in **nextjs-chat** schon vorhanden (exec-07 Matrix Media).
Wir portieren sie nach **control-ui**:

| Viewer | nextjs-chat Package | control-ui Status |
|--------|--------------------|--------------------|
| PDF | `react-pdf` ✓ | ✓ vorhanden |
| DOCX | `docx-preview` ✓ | **fehlt — installieren** |
| Markdown | `react-markdown` + `rehype-*` ✓ | pruefen |
| Spreadsheet | `xlsx` ✓ | **fehlt — installieren** |
| HLS Video | `hls.js` | ✓ vorhanden |
| Audio Waveform | — (matrix chat hat nur HTML5 audio) | **`wavesurfer.js` neu** |
| Image + EXIF | — (matrix chat nutzt Native IMG) | **`exifr` neu** |

Packages zu installieren in `control-ui`:
- [ ] `bun add wavesurfer.js @wavesurfer/react`
- [ ] `bun add exifr`
- [ ] `bun add xlsx`
- [ ] `bun add docx-preview`
- [ ] `bun add react-markdown rehype-raw rehype-sanitize remark-gfm`

**Oder** — Viewer-Komponenten aus `nextjs-chat/src/components/matrix/message/content/`
als `shared/` copy-paste und anpassen.

---

## Stufe 4: control/ ist tote Kopie — ignorieren

`control/storage/go-backend/` ist eine 1:1-Kopie aus dem Hauptprojekt (tradefusion)
ohne `cmd/main.go`, ohne eigenes `go.mod`, **wird nie ausgefuehrt**. Selbst im
Hauptprojekt ist dieser Teil laut User kaputt. Wir fixen es hier richtig in `go-appservice`.

**Regel:** Single Go backend = `go-appservice/`. Alles was Files/Storage/Artifacts betrifft,
gehoert dorthin. `control/` wird bei exec-19 **nicht angefasst** — kein Cleanup, kein Umzug,
kein Delete. Irrelevant fuer Verify Gates.

Stufe 4 Aufgaben wurden in **Stufe 3** integriert (Files API Full-Stack in `go-appservice`).

---

## Stufe 5: LiteLLM Encoding + Restart

Bereits in exec-17 Commit gefixt (config.yaml ASCII-clean), plus weitere Fixes in exec-19.

### 5.1 Config Cleanup

- [x] `config.yaml` Non-ASCII Zeichen ersetzt (30+)
- [x] Lokale Provider (Ollama, vLLM, LM Studio) auskommentiert — laufen in DevStack nicht per default, sonst spammt `pre_call_checks` Connection-Refused Errors
- [x] `enable_pre_call_checks: true` beibehalten — wichtig fuer spaetere Provider-Aktivierung via control-ui

### 5.2 Default Model Update

- [x] `python-backend/.env`:
  `AGENT_DEFAULT_UTILITY_MODEL=openrouter/qwen/qwen3-235b-a22b:free`
  **→ veraltetes Model, existiert nicht mehr bei OpenRouter**
  `AGENT_DEFAULT_UTILITY_MODEL=openrouter/google/gemma-4-26b-a4b-it:free`
  **→ aktuelles free model (Stand 10.04.2026)**

### 5.3 Verify Tests

- [x] DevStack restart → LiteLLM kommt auf `:4000` hoch (verifiziert)
- [x] `GET /v1/models` → LiteLLM listet 19 Model-Wildcards + expanded models (verifiziert)
- [x] Test request: `POST /v1/chat/completions` mit `openrouter/google/gemma-4-26b-a4b-it:free`
  - Response: `"Hi!"` in 2 completion_tokens, cost=0, provider=Google AI Studio
  - Das beweist: API Key OK, Routing OK, Response Format OK

---

## Stufe 5b: Dynamic Model Discovery + Filtering

**Kontext:** Das ist eigentlich **exec-16 Stufe 4** (LLM Provider Gateway). Wir tracken es
hier in exec-19 weil der DevStack Verify ohne eine funktionierende Model-Liste nicht
sinnvoll testbar ist. Nach Implementierung **portieren wir diese Section zurueck nach
exec-16** und verlinken nur noch darauf.

**Problem:** control-ui ApiModelsTab zeigt aktuell Provider-Cards mit `available_models.length`
aber **keine Filter**. OpenRouter hat 350 Models von 56 Providern — ohne Filter unbenutzbar.

**Zielzustand:** User kann in control-ui nach Models suchen/filtern mit denselben Dimensionen
die OpenRouter selbst anbietet, plus free/paid Badge, plus Cost-Range Slider.

### 5b.1 Ist-Zustand Analyse

Bereits vorhanden (exec-16):
- [x] `agent/control/user_llm.py` `_fetch_provider_models(provider_id, api_key?)` — fetcht live von Provider `/v1/models` API
- [x] `GET /api/v1/control/user/llm` liefert `providers[].available_models[]`
- [x] 1h Cache pro Provider in `_model_cache`
- [x] OpenRouter, Anthropic, OpenAI, Gemini, Cohere, Mistral, Groq unterstuetzt
- [x] control-ui ApiModelsTab nutzt die Liste als Dropdown

Was fehlt (exec-19 Stufe 5b):
- [ ] `_fetch_provider_models()` gibt nur `id` Strings zurueck, nicht die vollen Metadaten
- [ ] Kein `is_free` Flag (Pricing-Prompt == 0)
- [ ] Keine `supports_tools` / `supports_vision` / `supports_reasoning` Flags
- [ ] Keine `context_length` / `max_output_tokens` Info
- [ ] Keine Filter-API im Backend
- [ ] Keine Filter-UI in control-ui

### 5b.2 OpenRouter Model Schema (Reference)

```json
{
  "id": "anthropic/claude-opus-4.6",
  "canonical_slug": "anthropic/claude-4.6-opus",
  "name": "Anthropic: Claude Opus 4.6",
  "created": 1775592472,
  "description": "...",
  "context_length": 1000000,
  "architecture": {
    "modality": "text+image->text",
    "input_modalities": ["text", "image"],
    "output_modalities": ["text"]
  },
  "pricing": {
    "prompt": "0.00003",           // USD per token ($30/Mtok)
    "completion": "0.00015",        // USD per token ($150/Mtok)
    "input_cache_read": "0.00000375",
    "input_cache_write": "0.00003750",
    "web_search": "0.01",
    "image": "0.0048"
  },
  "top_provider": {
    "context_length": 1000000,
    "max_completion_tokens": 128000,
    "is_moderated": true
  },
  "supported_parameters": [
    "tools", "tool_choice", "reasoning", "reasoning_effort",
    "structured_outputs", "response_format", "temperature",
    "top_p", "top_k", "max_tokens", "stop", "seed", ...
  ],
  "default_parameters": { "temperature": null, "top_p": null, ... },
  "knowledge_cutoff": null,
  "expiration_date": null
}
```

### 5b.3 Filter-Dimensionen (voll)

| Filter | Typ | Werte | UI-Element | Priority |
|--------|-----|-------|-----------|----------|
| **Provider** | multi-select | 56 (anthropic, openai, google, qwen, meta-llama, ...) | Checkboxes / Combobox | Ja |
| **Free/Paid** | enum | free / paid / any | Toggle | **HIGH** |
| **Modality** | multi-select | text-only, vision, audio-in, audio-out, video-in, multimodal | Checkboxes | Ja |
| **Context Length** | range | 2k / 8k / 32k / 128k / 200k / 1M / 2M | Slider mit Presets | Ja |
| **Max Output Tokens** | range | 1k / 4k / 16k / 64k / 128k | Slider | Optional |
| **Supports Tools** | bool | `tools` in supported_parameters | Toggle | Ja |
| **Supports Structured Outputs** | bool | `structured_outputs` in supported_parameters | Toggle | Ja |
| **Supports Reasoning** | bool | `reasoning` in supported_parameters | Toggle | Ja |
| **Supports Vision** | bool | `image` in input_modalities | Toggle | Ja |
| **Supports Audio Input** | bool | `audio` in input_modalities | Toggle | Optional |
| **Supports Audio Output** | bool | `audio` in output_modalities | Toggle | Optional |
| **Web Search** | bool | `web_search_options` in supported_parameters | Toggle | Optional |
| **Prompt Price (USD/Mtok)** | range | 0 - 100+ | Slider | Ja |
| **Completion Price (USD/Mtok)** | range | 0 - 100+ | Slider | Ja |
| **Cache Supported** | bool | `input_cache_read` in pricing | Toggle | Optional |

### 5b.4 Sortierung

- name (alphabetical)
- provider (alphabetical, dann name)
- context_length (desc — largest first)
- prompt_price (asc — cheapest first)
- completion_price (asc)
- created (desc — newest first)
- is_free (free first, dann cheapest)

### 5b.5 Backend Aenderungen

**Datei:** `python-backend/agent/control/user_llm.py`

- [ ] `_fetch_provider_models()` erweitern um **vollständige Metadata** zu returnen:
  ```python
  async def _fetch_provider_models(
      provider_id: str,
      api_key: str | None = None,
  ) -> list[ModelInfo]:
      """Returns ModelInfo dicts instead of plain ID strings."""
  ```

- [ ] Neues TypedDict `ModelInfo`:
  ```python
  class ModelInfo(TypedDict):
      id: str
      name: str
      provider: str
      is_free: bool
      modality: str
      supports_tools: bool
      supports_structured_outputs: bool
      supports_reasoning: bool
      supports_vision: bool
      supports_audio_in: bool
      supports_audio_out: bool
      supports_cache: bool
      supports_web_search: bool
      context_length: int
      max_output_tokens: int
      prompt_price_per_mtok: float  # USD
      completion_price_per_mtok: float
      cached_prompt_price_per_mtok: float | None
      description: str
      knowledge_cutoff: str | None
      created: int  # unix timestamp
  ```

- [ ] Provider-spezifische Parser:
  - OpenRouter → voller Support (Schema oben)
  - Anthropic → statische Liste + manuelle Flags (kein /models Endpoint)
  - OpenAI → `/v1/models` API, aber weniger Metadata — anreichern mit known defaults
  - Gemini → `/v1/models` via google-genai SDK
  - Cohere → `/v1/models`
  - Mistral, Groq → OpenAI-kompatibel

- [ ] Neue Route:
  ```
  GET /api/v1/control/user/llm/models
    ?provider=openrouter,anthropic     # multi-value
    &free_only=true
    &supports_tools=true
    &supports_vision=true
    &min_context=32000
    &max_prompt_price=5.0              # USD/Mtok
    &modality=text,vision
    &sort=prompt_price_asc
    &limit=50
    &offset=0

  Response:
  {
    "models": [ModelInfo, ...],
    "total": 128,
    "filters_applied": { ... },
    "facets": {                       # available values for each filter
      "providers": { "openrouter": 128, "anthropic": 8, ... },
      "modalities": { "text": 300, "vision": 48, ... },
      "by_is_free": { "true": 27, "false": 323 }
    }
  }
  ```

- [ ] Filter-Logik im Backend:
  ```python
  def _filter_models(models: list[ModelInfo], query: ModelFilterQuery) -> list[ModelInfo]:
      # Apply all filters from query
      # Return matching models

  def _compute_facets(models: list[ModelInfo]) -> dict:
      # Compute counts for each filter dimension
      # Used by UI to show "X models match" beside each filter
  ```

### 5b.6 Frontend Aenderungen

**Dateien:** `control-ui/src/features/control/components/ApiModelsTab.tsx`

- [ ] Neue Komponente `ModelFilterSidebar`:
  - Provider Checkboxes mit Counts (`"anthropic (8)"`)
  - Free/Paid Toggle
  - Modality Checkboxes
  - Context Length Slider mit Presets (2k/8k/32k/128k/1M)
  - Feature Toggles (Tools, Vision, Reasoning, Structured Output)
  - Price Range Sliders (Prompt + Completion)

- [ ] Neue Komponente `ModelCard`:
  - Model Name + Provider Badge
  - Free Badge (green) wenn `is_free`
  - Feature Badges (Vision, Tools, Reasoning, 1M ctx)
  - Pricing Display ($X/$Y per Mtok)
  - "Use for [role]" Button pro Rolle

- [ ] Neuer Hook `useModelList(filters)` in `lib/queries/hooks.ts`:
  ```typescript
  export function useModelList(filters: ModelFilters) {
    return useQuery({
      queryKey: ['llm-models', filters],
      queryFn: () => api.get(`/control/user/llm/models?${buildQueryString(filters)}`),
      staleTime: 60 * 60 * 1000, // 1h cache
    });
  }
  ```

- [ ] Types in `features/control/types.ts`:
  ```typescript
  export interface ModelInfo { ... }
  export interface ModelFilters {
    providers?: string[];
    free_only?: boolean;
    supports_tools?: boolean;
    // ... alle anderen
  }
  ```

- [ ] URL-State mit `nuqs` — Filter in Query-Params persistieren damit man
  sharebare Links hat (`/control/models?free_only=true&supports_vision=true`)

### 5b.7 Cache-Strategie

LiteLLM cached 1h im Backend — reicht fuer die meisten User-Flows.

Zusaetzlich:
- [ ] Persistenter Cache in Postgres: `agent.llm_models_cache` Tabelle
  - Damit Cold-Starts nicht auf OpenRouter API Rate-Limits laufen
  - Refresh on-demand via `POST /api/v1/control/user/llm/models/refresh`
- [ ] Stale-While-Revalidate: alte Daten zeigen waehrend im Background neu geholt wird

### 5b.8 Verify-Gates

- [ ] `GET /api/v1/control/user/llm/models` liefert Full-ModelInfo JSON
- [ ] Filter `?free_only=true` gibt nur free Models zurueck (27 bei OpenRouter)
- [ ] Filter `?supports_tools=true&supports_vision=true` gibt Claude/GPT-4 Modelle
- [ ] control-ui ApiModelsTab zeigt Filter-Sidebar funktional
- [ ] "128 models matching" Counter aktualisiert sich live
- [ ] Model-Cards zeigen alle Badges
- [ ] Price-Filter schliesst 100 USD/Mtok Models aus wenn max=10

### 5b.9 Implementation Status (13.04.2026)

**DONE (Commit c74e798):**
- [x] Backend: `ModelInfo` TypedDict, OpenRouter detailed fetch, static normalization
- [x] Backend: `GET /user/llm/models` mit 11 Filtern + Facets + Pagination
- [x] Backend: `PUT/GET /user/llm/selected-models` (User Model Selection)
- [x] Alembic 011: `selected_models` jsonb column
- [x] Frontend: `ModelExplorer.tsx` mit shadcn (Card/Badge/Checkbox/Select)
- [x] Frontend: 11 Filter (Free/Tools/Vision/Reasoning/Structured Output/Provider/Context/Price/Modality/Max Output/Search + Sort)
- [x] Frontend: Select-for-Use Buttons + Save + Load on mount
- [x] `useModelList` hook + `ModelInfo`/`ModelListResponse` types
- [x] `control-proxy.ts` forwarded `x-actor-user-id` + `x-request-id`
- [x] `exec-merge-chat.md`: Model Picker Integration fuer agent-chat

**OFFEN (naechste Session):**
- [ ] **Filter-Extraction**: `ModelFilterSidebar.tsx` + `ModelCard.tsx` als eigene Components extrahieren (Wiederverwendung im agent-chat Merge)
- [ ] **Provider Account-Level Info** in Provider Cards:
  - OpenRouter: `GET /api/v1/auth/key` → credits_remaining, usage, rate limits
  - OpenAI: Usage API
  - Anthropic: Usage Dashboard (kein API, nur Web)
  - Darstellung: direkt in den bestehenden Provider-Cards (ApiModelsTab) neben dem API Key — Budget, Usage, Rate Limit, Tier
- [ ] **Budget-Filter im ModelExplorer**: "zeig nur Models die ich mir mit verbleibendem Budget leisten kann" (berechnet aus credits_remaining / prompt_price)
- [ ] `useSelectedModels` eigener Hook (statt inline useEffect fetch)
- [ ] Portierung zurueck zu exec-16 Stufe 4

---

## Stufe 5c: Reasoning / Thinking Budget — End-to-End Pipeline

> **Hinweis:** Gehoert eigentlich zu **exec-16 Stufe 4.5**. Bleibt hier bis implementiert,
> dann Portierung analog zu 5b. Wichtig weil `llm_node.py` den Reasoning-Param blind
> verliert und daher kein Extended Thinking zustande kommt — selbst wenn Frontend + BFF
> ihn korrekt setzen.

### 5c.1 Ist-Zustand Analyse

**Wired (halb):**
- `agent-chat/src/components/AgentChatToolbar.tsx:46` — `ReasoningEffort` type low|medium|high, BrainCircuit cycle button
- `agent-chat/src/hooks/useChatSession.ts:119` — `reasoningEffort` state, forwarded to BFF body
- `go-appservice/internal/handlers/http/agent_chat_handler.go:36` — `ReasoningEffort string`
- `python-backend/agent/app.py:114` — `AgentChatRequest.reasoning_effort: str | None`
- `python-backend/agent/context.py:30` — `AgentContext.reasoning_effort`
- `python-backend/agent/graph/state.py:69` — `AgentGraphState.reasoning_effort`
- `python-backend/agent/graph/runner.py:169` — weitergereicht an State
- `python-backend/agent/graph/nodes/tool_node.py:55` — state.get("reasoning_effort")

**BROKEN:**
- **`python-backend/agent/graph/nodes/llm_node.py`** — `kwargs` enthaelt nur `model/messages/tools/extra_body.api_key`. `reasoning_effort` wird **nie** an `client.chat.completions.create()` uebergeben. Die im `agent_chat_ui_delta.md` AC108 erwaehnte `_REASONING_BUDGET` map existiert nicht im Code.
- `control-ui` — keine Reasoning-UI
- `nextjs-chat` — keine Reasoning-UI
- `ApiModelsTab` — kein Filter fuer `supports_reasoning`, kein Thinking-Budget Slider
- Kein Auto-Mode (weder fuer Modell-Routing noch fuer Reasoning-Level)

### 5c.2 OpenRouter Reasoning API (Referenz)

OpenRouter normalisiert Reasoning ueber alle Provider via `reasoning` Param im Request Body:

```json
{
  "model": "anthropic/claude-sonnet-4-6",
  "messages": [...],
  "reasoning": {
    "effort": "high",         // "low" | "medium" | "high"
    "max_tokens": 32000,      // alternative zu effort (Anthropic-Style Budget)
    "exclude": false          // true = Reasoning nicht in Response
  }
}
```

Mapping pro Provider (automatisch durch OpenRouter):

| Provider        | Wie OpenRouter es mapped                           |
|-----------------|----------------------------------------------------|
| Anthropic       | `thinking: {type: "enabled", budget_tokens: N}`    |
| OpenAI (o-Serie)| `reasoning_effort: "low"/"medium"/"high"`          |
| DeepSeek R1     | `reasoning: true` / `thinking_tokens: N`            |
| Gemini 2.5 Pro  | `thinking_budget: N`                                |
| xAI Grok        | `reasoning_effort: "low"/"high"`                    |
| Qwen QwQ        | native reasoning, immer aktiv                       |

**effort → max_tokens Heuristik (OpenRouter default):**
- `low` ≈ 1k tokens
- `medium` ≈ 4k tokens
- `high` ≈ 16k tokens
- Wer manuell budgetieren will: `max_tokens` direkt setzen (ueberschreibt effort)

Via LiteLLM funktioniert das 1:1 — LiteLLM reicht den `reasoning` Block als `extra_body` oder als Top-Level Param durch (je nach Provider).

### 5c.3 LiteLLM Pass-Through

LiteLLM unterstuetzt `reasoning_effort` als First-Class Param ab v1.50+ (siehe [LiteLLM docs](https://docs.litellm.ai/docs/reasoning_content)). Fuer OpenRouter muss der Param in `extra_body.reasoning` eingebettet werden, fuer Anthropic direkt als `thinking`, fuer OpenAI o-series als `reasoning_effort`.

**Strategie fuer uns:** Einheitliches Interface — immer `reasoning: {effort, max_tokens, exclude}` im Request. LiteLLM macht den Rest. Bei OpenRouter als Provider (`openrouter/*` models) geht der Block in `extra_body`.

### 5c.4 Auto-Modi

**Auto-Model (OpenRouter):**
- Model-String: `openrouter/openrouter/auto`
- OpenRouter waehlt automatisch das geeignete Modell basierend auf Prompt
- Kostenoptimiert (vermeidet Overkill)
- **Status:** NICHT in unserer `litellm-gateway/config.yaml`, nicht in `_PROVIDER_META` registriert

**Auto-Reasoning (eigene Heuristik):**
Kein Provider hat "auto" Reasoning nativ — muessen wir selbst bauen. Heuristik-Optionen:

1. **Rolle-basiert:** `AgentRole.TRADING` → high, `AgentRole.CHAT` → low, `AgentRole.RESEARCH` → medium
2. **Prompt-Length:** > 2000 chars → high, > 500 → medium, sonst low
3. **Tool-Complexity:** wenn Tools wie `code_execution`, `deep_research` aktiv → high
4. **Cost-Aware:** `budget_remaining < threshold` → downgrade
5. **User-Override wins:** wenn User `reasoning_effort` explizit setzt, Heuristik ueberspringen

**Empfehlung:** Auto-Mode als 4. Option neben low/medium/high in der UI (`auto` = Heuristik). Default = auto.

### 5c.5 Backend Changes

**Datei:** `python-backend/agent/graph/nodes/llm_node.py`

Neue Funktion + Integration:

```python
from typing import Literal

ReasoningLevel = Literal["low", "medium", "high", "auto"] | None

_EFFORT_TO_BUDGET: dict[str, int] = {
    "low": 1024,
    "medium": 4096,
    "high": 16384,
}


def _compute_auto_effort(
    model: str,
    messages: list[dict],
    role: str | None,
    tools: list[dict] | None,
) -> str:
    """Heuristik fuer Auto-Reasoning (exec-19 Stufe 5c)."""
    if role in ("trading", "research"):
        return "high"
    prompt_chars = sum(len(m.get("content", "")) for m in messages if isinstance(m.get("content"), str))
    if prompt_chars > 2000:
        return "high"
    if prompt_chars > 500:
        return "medium"
    if tools and any(t.get("function", {}).get("name") in ("code_execution", "deep_research") for t in tools):
        return "high"
    return "low"


def _build_reasoning_block(
    model: str,
    effort: ReasoningLevel,
    messages: list[dict],
    role: str | None,
    tools: list[dict] | None,
) -> dict | None:
    """Baut den reasoning-Block fuer LiteLLM basierend auf effort + model."""
    if not effort:
        return None
    if effort == "auto":
        effort = _compute_auto_effort(model, messages, role, tools)
    if effort not in _EFFORT_TO_BUDGET:
        return None

    # OpenRouter: reasoning block in extra_body
    if model.startswith("openrouter/"):
        return {"extra_body_key": "reasoning", "value": {"effort": effort, "exclude": False}}

    # Anthropic direkt: thinking block
    if "anthropic" in model.lower() or "claude" in model.lower():
        return {
            "top_level_key": "thinking",
            "value": {"type": "enabled", "budget_tokens": _EFFORT_TO_BUDGET[effort]},
        }

    # OpenAI o-series: reasoning_effort
    if any(m in model for m in ("o1", "o3", "o4", "gpt-5")):
        return {"top_level_key": "reasoning_effort", "value": effort}

    # DeepSeek R1: thinking_tokens
    if "deepseek" in model.lower() and ("r1" in model.lower() or "reasoner" in model.lower()):
        return {"top_level_key": "thinking_tokens", "value": _EFFORT_TO_BUDGET[effort]}

    # Gemini 2.5: thinking_budget
    if "gemini" in model.lower() and "2.5" in model:
        return {"top_level_key": "thinking_budget", "value": _EFFORT_TO_BUDGET[effort]}

    # Default: kein Reasoning-Support oder unbekannt → skip
    return None
```

Integration in `llm_node()`:

```python
reasoning_effort = state.get("reasoning_effort")
reasoning_block = _build_reasoning_block(
    model=model,
    effort=reasoning_effort,
    messages=oai_messages,
    role=state.get("role"),
    tools=openai_tools,
)

kwargs: dict[str, Any] = {"model": model, "messages": oai_messages}
if openai_tools:
    kwargs["tools"] = openai_tools
if api_key:
    kwargs["extra_body"] = {"api_key": api_key}
if reasoning_block:
    if reasoning_block.get("extra_body_key"):
        kwargs.setdefault("extra_body", {})[reasoning_block["extra_body_key"]] = reasoning_block["value"]
    else:
        kwargs[reasoning_block["top_level_key"]] = reasoning_block["value"]

# Audit + Tracing
span.set_attribute("reasoning.effort", reasoning_effort or "none")
if reasoning_block:
    span.set_attribute("reasoning.enabled", True)
    span.set_attribute("reasoning.method", reasoning_block.get("top_level_key") or "extra_body.reasoning")
```

**Datei:** `python-backend/agent/control/user_llm.py`

Erweitere `ModelInfo` um:
```python
class ModelInfo(TypedDict):
    ...
    supports_reasoning: bool       # True wenn Provider/Model Reasoning unterstuetzt
    reasoning_type: str | None     # "thinking" | "effort" | "thinking_tokens" | "thinking_budget"
    max_reasoning_tokens: int | None
```

Quelle: OpenRouter `/models` API hat `supported_parameters: ["reasoning", "include_reasoning", ...]`, daraus ableiten. Fuer statische Listen (Anthropic, Gemini): manuell gepflegt.

### 5c.6 Frontend Changes

**Datei:** `control-ui/src/features/control/components/ApiModelsTab.tsx`

Filter-Sidebar erweitern:
- [ ] Neuer Filter `Reasoning Support` (checkbox) — zeigt nur Models mit `supports_reasoning: true`
- [ ] Neuer Filter `Auto-Mode Capable` (wenn Heuristik ein Auto-Budget setzen kann)
- [ ] Sortierung nach `reasoning_quality_score` (optional, Langfuse-basiert spaeter)

**Datei:** `control-ui/src/features/control/components/DefaultReasoningSelect.tsx` (neu)

Analog zu Model-Select: Default Reasoning Level fuer Agent-Sessions.
- Options: `low | medium | high | auto`
- Save to `control.user.llm.default_reasoning_effort`
- Icon: BrainCircuit (konsistent zu agent-chat)

**Datei:** `control-ui/src/features/control/components/ModelCard.tsx` (Teil von 5b)

Badges erweitern:
- [ ] `Reasoning` Badge mit Icon BrainCircuit wenn `supports_reasoning: true`
- [ ] Hover-Tooltip zeigt `reasoning_type` + `max_reasoning_tokens`

**Datei:** `agent-chat/src/components/AgentChatToolbar.tsx`

Cycle-Button erweitern:
- [ ] Option `auto` als 4. State (default)
- [ ] Cycle: `auto → low → medium → high → auto`
- [ ] Label im Button: `L/M/H/A`
- [ ] Tooltip: "Auto: heuristic based on role, prompt length, tools"

**Datei:** `nextjs-chat/src/components/matrix/ChatComposer.tsx`

- [ ] Reasoning Cycle Button im Composer hinzufuegen (analog agent-chat)
- [ ] State in Room-Timeline, persistent per Room (wie Model-Selection)
- [ ] Body-Forward im `/api/agent/chat` Route

**Datei:** `nextjs-chat/src/app/api/agent/chat/route.ts`

- [ ] `reasoningEffort` aus Request Body uebernehmen
- [ ] Forward zu Agent Service unter `reasoningEffort`

### 5c.7 Audit + Observability Integration (exec-17)

Tracing Attrs in `llm_node.py` setzen:

| Attribut                  | Wert                                         |
|---------------------------|----------------------------------------------|
| `reasoning.requested`     | user-provided level (inkl. "auto")           |
| `reasoning.resolved`      | nach Heuristik aufgeloest                    |
| `reasoning.method`        | `thinking` / `effort` / `thinking_budget` / `extra_body.reasoning` |
| `reasoning.budget_tokens` | ermittelter Token-Budget                     |
| `reasoning.tokens_used`   | aus `usage.completion_tokens_details.reasoning_tokens` (wenn verfuegbar) |

Langfuse Integration: `span.track_generation()` erhaelt `reasoning_tokens` als separates Usage-Feld (fuer Cost-Tracking wichtig — Reasoning-Tokens werden bei Anthropic/OpenAI separat und teurer abgerechnet).

### 5c.8 Verify Gates

- [ ] `llm_node.py` uebergibt Reasoning-Param an LiteLLM (verified via Langfuse/OpenObserve)
- [ ] `openrouter/anthropic/claude-sonnet-4-6` mit `reasoning: {effort: "high"}` gibt Thinking-Content zurueck
- [ ] `openrouter/openai/o3-mini` mit `reasoning_effort: "high"` laeuft erfolgreich
- [ ] Auto-Mode resolver erzeugt `high` bei Prompt > 2000 chars
- [ ] Trace in OpenObserve zeigt `reasoning.method` + `reasoning.tokens_used`
- [ ] Control-UI ApiModelsTab Filter "Reasoning Support" funktioniert
- [ ] Agent-Chat Cycle Button durchlaeuft alle 4 States (auto/low/medium/high)
- [ ] Langfuse Dashboard zeigt `reasoning_tokens` als separates Cost-Item
- [ ] Bei Provider ohne Reasoning-Support (z.B. Mistral Small) wird der Block silently dropped

### 5c.9 Portierung zurueck zu exec-16

Nach Implementierung:
- [ ] exec-19 Stufe 5c Markierung als "portiert zu exec-16 Stufe 4.5"
- [ ] exec-16 Stufe 4.5 mit vollstaendiger Spec ergaenzt
- [ ] Querverweis von exec-19 → exec-16

### 5c.10 Offene Entscheidungen

1. **Auto-Mode Heuristik — wo gepflegt?** Options:
   - Im Code hartkodiert (einfach, nicht konfigurierbar)
   - In DB (`agent.reasoning_heuristics` Tabelle, konfigurierbar per User/Role)
   - **Empfehlung:** Code-First, spaeter in DB wenn Nutzer es wirklich tunen wollen
2. **`openrouter/auto` Model-Router in Registry aufnehmen?** — vermutlich ja, aber als separates Model-Entry mit eigenem Label "Auto (OpenRouter)"
3. **Combined Auto: Model + Reasoning Auto?** — Wenn User `auto` wahlt, koennte System BEIDES auto machen (Model via openrouter/auto, Reasoning via Heuristik). Separater Toggle oder kombiniert?

---

## Stufe 6: Pre-Flight Validierung

Nach allen Fixes: DevStack **komplett sauber** starten, alle Services pruefen.

### 6.1 Cold-Start Test

- [ ] DevStack stoppen (alle Windows schliessen, `tasklist` fuer Stragglers)
- [ ] `.\scripts\dev-stack2.ps1` starten (ohne Flags, Full Stack)
- [ ] **Alle** Services MUESSEN hochkommen:
  - Postgres :5433
  - NATS :4222
  - OpenObserve :5080
  - Homeserver :8448
  - Go Appservice :8090 (mit Crypto Fix)
  - Agent Service :8094
  - py-bridge :8097
  - Ingestion Worker :8098
  - LiteLLM :4000 (mit ASCII config)
  - SeaweedFS :8333 (mit localhost binding)
  - nextjs :3000
  - control-ui :3001

### 6.2 Smoke Tests

- [ ] `curl http://localhost:3001/` → control-ui laedt
- [ ] `curl http://localhost:3000/matrix` → nextjs matrix chat laedt
- [ ] `curl http://localhost:4000/v1/models` → LiteLLM listet OpenRouter models
- [ ] `curl http://localhost:5080/` → OpenObserve UI
- [ ] `curl http://localhost:8090/health` → go-appservice health
- [ ] `curl http://localhost:8094/health` → agent-service health

### 6.3 Integration Tests

- [ ] control-ui Memory Tab laedt Sessions aus PG
- [ ] control-ui Files Tab zeigt leere Liste (ohne Fehler)
- [ ] control-ui Tools Tab zeigt MCP Tools
- [ ] Agent Chat sendet Message → SSE Response via LiteLLM → OpenRouter
- [ ] OpenObserve Dashboard zeigt Spans der Agent-Session

---

## Offene Fragen

1. **control/storage/go-backend Cleanup — welche Option?**
   - A: Delete
   - B: Umbenennen + README
   - C: Nach `_ref/` verschieben (empfohlen)

2. **Matrix Crypto — Sofort Option A oder erst Option B?**
   - A: SQLite Upgrade Fix (10 min, funktioniert sofort)
   - B: Postgres Migration (1-2h, Teil von exec-18, sauberer)
   - Empfehlung: **Erst A**, dann B als Teil von exec-18

3. **Files API Scope — minimal oder voll?**
   - Minimal: Nur `/api/v1/files` GET + `/api/v1/files/upload-intent` (fuer Verify reichen)
   - Voll: Alle 7 Routes (Search, Reindex, Delete, URL)
   - Empfehlung: **Minimal fuer Verify-Gates**, voll spaeter

4. **control_surface und files_surface Ordner** — behalten oder aufraeumen?
   - Aktuell keine Referenzen von Matrix Code zu diesen Ordnern
   - Referenz-Material fuer UI Design

---

## Backend-Wiring Status (Audit 10.04.2026)

**Memory + Control (alle 14 Tabs) — KORREKT gewired:**

```
control-ui Browser
  ↓ fetch('/api/control/...' | '/api/memory/...')
control-ui BFF (Next.js :3001)
  ↓ controlProxy() → getGatewayBaseURL() → :8090
Go Appservice (:8090)
  ↓ ControlProxyHandler → :8094
Python Agent Service (:8094)
  ↓ agent.control.router → agent.control.{memory,episodes,kg,agents,...}.py
  ↓ get_memory_engine() → hindsight_api.MemoryEngine
Hindsight (Postgres public schema)
```

Alle 14 Tabs laufen ueber denselben catch-all Proxy:
- Memory Tab → `/api/v1/control/memory/*`
- Episodes Tab → `/api/v1/control/episodes/*`
- KG Tab → `/api/v1/control/kg/*`
- Agents, Permissions, Skills, Tools, Sandbox, System, Audit,
  Sessions, MCP, A2A, Models, Overview → alle `/api/v1/control/*`

**Files Tab — NICHT gewired** (Ausnahme von der Regel):

Files nutzt eine eigene Route-Struktur `/api/v1/files/*` (nicht `/api/v1/control/files/*`)
weil es NICHT nur Control-API ist, sondern multiple Quellen vereint:
- SeaweedFS (S3 blob storage) - Source of Truth fuer Files
- ArtifactMetadataStore - Metadaten
- Ingestion Jobs - Pipeline-State
- Per-User Isolation

Diese Route-Struktur existiert NICHT im Backend. Das ist Stufe 3 dieser Spec.

**Andere Control-UI Tabs die bereits funktionieren sollten:**

| Tab | Status | Quelle |
|-----|--------|--------|
| Memory | ✓ wired | Python `agent.control.memory` → Hindsight |
| Episodes | ✓ wired | Python `agent.control.episodes` → Hindsight |
| KG (Knowledge Graph) | ✓ wired | Python `agent.control.kg_crud` → Hindsight |
| Highlights | ✓ wired | Python `agent.control.highlights` |
| Agents | ✓ wired | Python `agent.control.agents` (role overrides) |
| Permissions | ✓ wired | Python `agent.control.permissions` (consent) |
| Skills | ✓ wired | Python `agent.control.skills` (exec-10) |
| Tools | ✓ wired | Python `agent.control.tools` (exec-09 MCP) |
| Sandbox | ✓ wired | Python `agent.control.sandbox` (exec-12) |
| System | ✓ wired | Python `agent.control.system` |
| Audit | ✓ wired | Python `agent.control.audit` (exec-12 audit events) |
| Sessions | ✓ wired | Python `agent.control.sessions` |
| MCP | ✓ wired | Python `agent.control.mcp` |
| A2A | ✓ wired | Python `agent.control.a2a` (exec-10) |
| Models | ✓ wired | Python `agent.control.user_llm` (exec-16) |
| Overview | ✓ wired | Python `agent.control.overview` (aggregate) |
| **Files** | **✗ NICHT wired** | Stufe 3 — erfordert neue `files_handler.go` + SeaweedFS Integration |

Verify-Gates fuer exec-15 koennen **alle Tabs ausser Files** direkt testen sobald
DevStack laeuft. Files Tab kommt nach Stufe 3 Implementation.

---

## Verify-Gates (nach exec-19)

### Infra Gates

- [ ] DevStack Cold-Start: alle 12 Services UP
- [ ] Keine Unicode-Fehler in PowerShell oder Python logs
- [ ] Postgres: keine Crash-Loops nach 5 min Uptime
- [ ] Go Appservice: `crypto_account` Tabelle erstellt (schema upgrade call wirkt)
- [ ] SeaweedFS: Volume Server auf :8180, S3 API auf :8333
- [ ] LiteLLM: `/v1/models` listet OpenRouter free models
- [ ] OpenObserve: :5080 erreichbar, Traces aus Agent Service sichtbar

### Control-UI Gates (Stufen 1+4 komplett)

- [ ] Memory Tab: Banks werden geladen (Hindsight)
- [ ] Episodes Tab: Empty State oder Episoden werden angezeigt
- [ ] KG Tab: Nodes/Edges werden geladen
- [ ] Agents Tab: Role overrides sichtbar
- [ ] Tools Tab: MCP Tool List aus Agent Service
- [ ] Skills Tab: Skills aus agent.skills_state
- [ ] Sandbox Tab: Sandbox Runs aus audit_events
- [ ] Models Tab: LLM Provider + User Settings (exec-16)
- [ ] Audit Tab: Events aus agent.audit_events

### Files Gates (nach Stufe 3)

- [ ] Files Overview Tab: Ingestion Counts + leere recent_uploads (keine 503)
- [ ] Files Documents Tab: Leere Liste oder Test-PDF
- [ ] Files Images Tab: Leere Liste oder Test-Image
- [ ] Files Audio Tab: Leere Liste oder Test-MP3
- [ ] Files Video Tab: Leere Liste oder Test-MP4
- [ ] Files Data Tab: Placeholder (v1.5)
- [ ] Files Upload Tab: Upload Dropzone funktional, generiert presigned URL
- [ ] Upload → Download roundtrip: PDF hochgeladen, wiederheruntergeladen
- [ ] Per-User Isolation: User A sieht nicht Files von User B

### Agent Chat Gates

- [ ] Agent Chat mit `google/gemma-2-9b-it:free` funktioniert E2E
- [ ] SSE Streaming sichtbar in browser
- [ ] Response wird persistiert (audit_events + Hindsight)
- [ ] Tool-Calls funktionieren

### Keine Duplicate/Konflikt Gates

- [ ] `control/storage/go-backend` deaktiviert oder geloescht (keine Verwirrung)
- [ ] LiteLLM config.yaml ASCII only
- [ ] DevStack2.ps1 ASCII only
- [ ] Keine Port-Konflikte

Danach sind wir bereit fuer **exec-15/16/17 Verify Phase A**.
