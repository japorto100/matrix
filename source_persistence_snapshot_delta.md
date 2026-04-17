# Source Persistence / Snapshot Delta

> **Stand:** 12. Maerz 2026
> **Zweck:** Aktiver Arbeitsvertrag fuer Cache-, Snapshot- und Raw-Persistenz
> externer Quellen nach abgeschlossener Source Selection und vor Retrieval bzw.
> Vector-Ingestion.

---

## 0. Execution Contract

### Scope In

- Persistenzklassen fuer externe Quellen (`api-hot`, `api-snapshot`,
  `file-snapshot`, `stream-only`)
- Rohsnapshot-Policy, Metadatenfelder, Cadence-Hinweise und Retention-Klassen
- Trennung zwischen Object Storage, relationalem Snapshot-Index und Hot Cache

### Scope Out

- Auswahl/Tiering neuer Quellen (Owner: `source_selection_delta.md`)
- Key-/Env-Onboarding (Owner: `source_onboarding_and_keys.md`)
- semantisches Retrieval / Embedding / Chroma/Falkor-Ingestion im Detail
  (Owner: `vector_ingestion_delta.md`)
- produktive Live-Verify einzelner Quellen

### Mandatory Upstream Sources

- `docs/storage_layer.md`
- `docs/MEMORY_ARCHITECTURE.md`
- `docs/CONTEXT_ENGINEERING.md`
- `docs/specs/ARCHITECTURE.md`
- `docs/specs/SYSTEM_STATE.md`
- `docs/specs/EXECUTION_PLAN.md`
- `docs/specs/execution/source_selection_delta.md`
- `docs/specs/execution/source_onboarding_and_keys.md`
- `docs/references/sources/README.md`
- `docs/references/status.md`

---

## 1. Leitregeln

1. **Selection vor Persistence:** keine Persistenzentscheidung ohne dokumentierte
   Quellenwahl.
2. **Persistence vor Vectorization:** raw/cache/snapshot kommt vor embedding.
3. **Cache ist nicht Audit:** Redis oder in-memory reduziert Latenz, ersetzt aber
   keinen Replay-faehigen Snapshot.
4. **Object-first fuer file-snapshot:** XML/CSV/ZIP/PDF/Parquet Downloads gehen
   zuerst in den Object Store.
5. **Metadata-first fuer Nachvollziehbarkeit:** Hash, Parser-Version und
   Snapshot-Status sind Pflichtfelder fuer persistierte Rohdaten.
6. **Backend-owned relationale Zielschicht:** fuer staging/prod gehoeren
   Go-owned Snapshot-/Provider-/Workflow-Metadaten mittelfristig in eine
   backend-owned relationale DB statt dauerhaft in frontend-/Prisma-nahe
   Pfade.

---

## 2. Persistenzklassen

| Klasse | Zweck | Raw Blob | Normalized Snapshot | Cache |
|:-------|:------|:---------|:--------------------|:------|
| `api-hot` | kleine read-mostly APIs, intraday reads | optional | optional | verpflichtend |
| `api-snapshot` | API-Antworten mit Replay-/Diff-Wert | optional oder `on-change` | ja | ja |
| `file-snapshot` | offizielle Downloads / Batch-Dateien | verpflichtend | ja | optional |
| `stream-only` | SSE/WebSocket/Push | nein | optional materialized window | verpflichtend |

---

## 3. Mindest-Metadaten

Jeder persistierte Snapshot braucht mindestens:

- `source_id`
- `source_class`
- `fetch_mode`
- `fetched_at`
- `source_url`
- `content_type`
- `content_length`
- `sha256`
- `etag` falls vorhanden
- `last_modified` falls vorhanden
- `parser_version`
- `snapshot_status`
- `retention_class`

Empfohlene Zusatzfelder:

- `cadence_hint`
- `dataset_name`
- `partition_key`
- `trace_id`
- `error_class`

---

## 4. Cadence- und Change-Regeln

### Fetch-Modi

- `poll`
- `conditional-poll`
- `on-demand`
- `stream`

### Change Detection

- `etag`
- `last-modified`
- `sha256`
- record diff

### Retention-Klassen

- `ephemeral`
- `snapshot`
- `audit`

Arbeitsregel:

- `file-snapshot` Quellen: raw persist `on-change` oder `always`
- `api-hot`: raw persist nur bei klarem Debug-/Audit-Nutzen
- `stream-only`: windowed materialization statt blindem Raw-Archiv

---

## 5. Offene Deltas

- [x] **SPS1** fuer jede aktive Quelle genau eine Persistenzklasse dokumentieren
- [~] **SPS2** file-snapshot Quellen auf Object Storage + relationalen Snapshot-Index abbilden
- [~] **SPS3** api-hot Quellen explizit als cache-first statt snapshot-first markieren
- [~] **SPS4** api-snapshot Quellen mit Hash-/Parser-/Status-Metadaten versehen
- [ ] **SPS5** stream-only Quellen auf materialized-window- oder cache-only-Modell begrenzen
- [x] **SPS6** Cadence-Hinweise pro aktiver Quellenfamilie dokumentieren
- [x] **SPS7** Retention-Klassen (`ephemeral` / `snapshot` / `audit`) in Owner-Dokumenten spiegeln
- [~] **SPS8** Raw Snapshot -> normalized snapshot -> retrieval/vector boundary explizit dokumentieren
- [ ] **SPS9** backend-owned relational metadata/index layer fuer staging/prod
  als Zielpfad dokumentieren und gegen lokalen SQLite-Bootstrap abgrenzen

---

## 6. Verify-Gates

- [ ] **SPS.V1** keine aktive `file-snapshot` Quelle ohne Raw-Blob- und
  Metadatenmodell
- [ ] **SPS.V2** keine Quelle gleichzeitig als Hot-Cache und Source-of-Truth
  dokumentiert
- [ ] **SPS.V3** Vectorization greift nur auf normalisierte Outputs oder bewusst
  freigegebene Textartefakte zu
- [x] **SPS.V4** Cadence-, change- und retention-Regeln sind pro Quellenfamilie
  sichtbar
- [ ] **SPS.V5** erster echter Object-Storage-Write/Read fuer Snapshot-Quellen
  (`OFAC`, `UN`, `SECO`, `CFTC`) gegen den laufenden SeaweedFS-Stack verifiziert
- [ ] **SPS.V6** Snapshot-Live-Run prueft `etag`/`last-modified`/hash- und
  Statuspfad gegen reale Upstream-Antworten; aktuell bewusst deferred bis zum
  naechsten Stack-/Live-Verify-Fenster

---

## 7. Naechster Todo-Batch

### A. Object-Storage / file-snapshot

- [ ] `OFAC`, `UN`, `SECO`, `CFTC` vom lokalen Raw-Bootstrap auf echten
  Seaweed/Object-Storage-Livepfad heben
- [ ] `OFAC`, `UN`, `SECO`, `CFTC` Snapshot-Error-/Recovery-Pfad gegen
  laufenden Object-Storage absichern
- [ ] `EU Sanctions` vom aktuellen `api-snapshot`-/OpenSanctions-Default auf
  offiziellen file-snapshot Runtime-Pfad umstellen

### B. api-snapshot / normalized snapshot

- [ ] ersten gezielten Downstream-Consumer fuer normalisierte Snapshots
  definieren
- [ ] Reader-/Query-Pfad fuer `ACLED`, `GDELT News` und `CrisisWatch`
  oberhalb von `source_snapshot_metadata` andocken
- [ ] normalisierte Snapshot-Reads gegen `dataset_name` / `partition_key` /
  `snapshot_status` weiter schaerfen

### C. api-hot / stream-only

- [ ] `ECB`, `BCB`, `BCRA`, `TCMB`, `RBI`, `IMF`, `OECD`, `World Bank`, `UN`
  bewusst auf `api-hot` ohne neuen Snapshot-Pfad belassen oder selektiv
  spaeteren Cache-/Snapshot-Bedarf markieren
- [ ] `stream-only` Quellen auf materialized-window- oder cache-only-Modell
  konkret begrenzen
- [ ] `Finnhub` Stream-Pfad bewusst getrennt vom Quote-Cache halten und diese
  Grenze im Runtime-/Owner-Pfad weiter spiegeln

### D. Architektur / Zielbild

- [ ] backend-owned relationale Ziel-DB fuer staging/prod konkret benennen
- [ ] Migrationspfad vom lokalen SQLite-Bootstrap in den spaeteren
  backend-owned Metadata-/Index-Layer festziehen
- [ ] Vector-Ingestion erst nach stabilem normalized-snapshot Consumer starten

---

## 8. Evidence (12. Maerz 2026)

- `docs/references/status.md` fuehrt jetzt Persistenzprofile fuer:
  - SDMX-/Macro-Provider
  - EM-/Central-Bank-Zeitreihen
  - Market / Realtime
  - Internal / Bridge / Geo Context
  - News / Headline Connectoren
  - BulkFetcher / DiffWatcher
- `docs/references/sources/macro-and-central-banks.md` spiegelt den
  `api-hot`-Default fuer Macro-/Central-Bank-Quellen.
- `docs/references/sources/market-data.md` spiegelt `api-hot`,
  `api-snapshot`, `file-snapshot` und den Vector-Grenzvertrag fuer
  market-nahe Quellen.
- `docs/references/sources/legal-and-regulatory.md` spiegelt den
  `file-snapshot`-Default fuer offizielle Sanctions-/Diff-Downloads.
- `docs/references/sources/financial-stability-and-nbfi.md` spiegelt
  `api-hot` vs. `api-snapshot` vs. `file-snapshot` fuer Stability-/NBFI-Quellen.
- `docs/references/sources/geopolitical-and-osint.md` spiegelt den
  `api-snapshot`-Charakter reproduzierbarer Geo-/OSINT-Windows.
- `docs/storage_layer.md`, `docs/specs/ARCHITECTURE.md` und
  `docs/specs/SYSTEM_STATE.md` halten explizit fest, dass Go-owned
  Snapshot-/Metadata-Layer mittelfristig aus frontend-/Prisma-nahen Pfaden in
  eine backend-owned relationale DB uebergehen sollen.
- `go-backend/internal/storage/metadata_store.go` besitzt jetzt eine erste
  konkrete `source_snapshot_metadata`-Migration als Bootstrap fuer den spaeteren
  backend-owned Metadata-/Index-Layer.
- `go-backend/internal/storage/metadata_store.go` bietet jetzt zusaetzlich
  listen-/latest-Queries fuer statusgefilterte Snapshot-Reads pro Quelle; damit
  steht die erste lesende Backend-Boundary fuer Downstream-Consumer.
- `go test ./internal/storage` ist mit dem neuen Snapshot-Metadata-Test gruen.
- `go-backend/internal/connectors/base/diff_watcher.go` kann jetzt ueber einen
  `OnFetched`-Hook Raw-Payload plus Hash/Header-Metadaten an einen
  Snapshot-Recorder weiterreichen.
- `go-backend/internal/connectors/base/bulk_fetcher.go` besitzt jetzt dieselbe
  Snapshot-Hook-Boundary fuer bulk-/download-basierte Quellen.
- `go-backend/internal/connectors/base/source_snapshot_recorder.go` kapselt den
  Bootstrap fuer Raw-Object + `source_snapshot_metadata` ueber denselben
  Storage-Env-Contract wie der Artefaktpfad; lokales Filesystem bleibt nur
  Fallback, wenn kein S3-/Seaweed-Provider konfiguriert ist.
- `go-backend/internal/connectors/seco/sanctions_watcher.go` nutzt diese
  Boundary jetzt fuer den ersten konkreten `file-snapshot` Bootstrap:
  offizieller SECO-XML-Fetch -> lokale Raw-Datei -> `source_snapshot_metadata`.
- `go-backend/internal/connectors/ofac/sdn_watcher.go`,
  `go-backend/internal/connectors/un/sanctions_watcher.go` und
  `go-backend/internal/connectors/cftc/cot_fetcher.go` haengen jetzt ebenfalls
  an derselben lokalen Snapshot-Boundary.
- `go-backend/internal/connectors/base/source_snapshot_recorder_test.go`
  verifiziert den Recorder gegen einen S3-kompatiblen Testserver mit
  `ARTIFACT_STORAGE_PROVIDER=seaweedfs`.
- `go test ./internal/connectors/base ./internal/connectors/ofac ./internal/connectors/un ./internal/connectors/seco ./internal/connectors/cftc ./internal/storage`
  ist fuer den ersten produktnahen Snapshot-Batch gruen.
- `go-backend/internal/connectors/news/gdelt_client.go` schreibt fuer
  `GDELT News` jetzt einen ersten `api-snapshot`-Bootstrap: Raw-JSON plus
  `source_snapshot_metadata` ueber denselben Recorder-/Storage-Vertrag.
- `go-backend/internal/connectors/news/gdelt_client.go` erzeugt jetzt
  zusaetzlich einen normalized snapshot fuer `GDELT News` und setzt den
  Snapshot-Status auf `normalized`.
- `go-backend/internal/connectors/news/gdelt_client_test.go` verifiziert
  Headline-Fetch, Raw-/normalized-Snapshot-Datei und Snapshot-Metadaten fuer
  `GDELT News`.
- `go-backend/internal/app/wiring.go` fuehrt `GDELT_NEWS_SNAPSHOT_STATE_PATH`
  als expliziten Runtime-Vertrag.
- `go test ./internal/connectors/news ./internal/connectors/base ./internal/storage ./internal/app`
  ist fuer den News-`api-snapshot`-Pfad mit normalized snapshot gruen.
- `go-backend/internal/connectors/acled/client.go` schreibt jetzt fuer reale
  ACLED-API-Antworten Raw-JSON plus `source_snapshot_metadata`.
- `go-backend/internal/connectors/acled/client.go` erzeugt jetzt zusaetzlich
  den ersten echten normalized snapshot fuer eine `api-snapshot`-Quelle und
  setzt den Snapshot-Status auf `normalized`.
- `go-backend/internal/connectors/crisiswatch/client.go` schreibt jetzt fuer
  echte CrisisWatch-RSS-Laeufe Raw-XML plus `source_snapshot_metadata`, ohne den
  bestehenden Persisted-Cache-Pfad zu ersetzen.
- `go-backend/internal/connectors/crisiswatch/client.go` erzeugt jetzt
  zusaetzlich einen normalized snapshot fuer `CrisisWatch` und setzt den
  Snapshot-Status auf `normalized`.
- `go-backend/internal/connectors/acled/client_test.go` und
  `go-backend/internal/connectors/crisiswatch/client_test.go` verifizieren
  Raw-/normalized-Snapshots plus Snapshot-Metadaten fuer beide
  `api-snapshot`-Quellen.
- `go-backend/internal/connectors/base/source_snapshot_recorder.go` kapselt
  jetzt auch den ersten lokalen Normalizer-Pfad fuer deterministische
  `source-snapshots/normalized/...` Objekte.
- `go test ./internal/connectors/news ./internal/connectors/crisiswatch ./internal/connectors/acled ./internal/connectors/base ./internal/storage ./internal/app`
  ist fuer den erweiterten `api-snapshot`-Batch gruen.
- `go-backend/internal/connectors/base/api_hot_cache.go` kapselt jetzt den
  ersten gemeinsamen `api-hot` JSON-TTL-Cache fuer read-mostly Connectoren.
- `go-backend/internal/connectors/fred/client.go`,
  `go-backend/internal/connectors/finnhub/client.go`,
  `go-backend/internal/connectors/banxico/client.go`,
  `go-backend/internal/connectors/bok/client.go`,
  `go-backend/internal/connectors/ofr/client.go` und
  `go-backend/internal/connectors/nyfed/client.go` nutzen jetzt denselben
  cache-first JSON-TTL-Pfad fuer read-mostly Quotes bzw. Serienreads, bevor ein
  Upstream-Fetch ausgefuehrt wird.
- `go-backend/internal/app/wiring.go` fuehrt jetzt explizite
  `*_CACHE_TTL_MS`-Vertraege fuer `Finnhub`, `FRED`, `Banxico`, `BoK`, `OFR`
  und `NYFed`.

---

## 9. Initiale Klassifizierung der aktiven Quellen

### `api-hot`

- `finnhub`
- `fred`
- `ecb`
- `banxico`
- `bok`
- `bcb`
- `bcra`
- `tcmb`
- `rbi`
- `imf`
- `oecd`
- `worldbank`
- `un macro`
- `ofr`
- `nyfed`

### `file-snapshot`

- `ofac sanctions`
- `un sanctions`
- `seco sanctions`
- `cftc cot`

### `api-snapshot`

- `finra ats`
- `gdelt news` fuer reproduzierbare dossier-/headline-batches mit erstem
  normalized snapshot
- `acled` mit erstem normalized snapshot
- `crisiswatch` mit erstem normalized snapshot

### `stream-only`

- gateway-nahe SSE/streaming surfaces
- tick/orderbook event windows, soweit kein expliziter capture path beschlossen

---

## 10. Propagation Targets

- `docs/storage_layer.md`
- `docs/MEMORY_ARCHITECTURE.md`
- `docs/CONTEXT_ENGINEERING.md`
- `docs/specs/ARCHITECTURE.md`
- `docs/specs/SYSTEM_STATE.md`
- `docs/specs/EXECUTION_PLAN.md`
- `docs/specs/execution/storage_layer_delta.md`
- `docs/specs/execution/source_onboarding_and_keys.md`
- `docs/specs/FRONTEND_ARCHITECTURE.md` (wenn BFF-/DB-Ownership explizit
  umgezogen wird)
- `docs/references/sources/README.md`
- `docs/references/status.md`

---

## 11. Exit Criteria

- `SPS1-SPS9` sind entschieden oder mit Owner/Datum deferred
- aktive Quellenfamilien haben dokumentierte Persistenzklasse, Cadence-Hinweis
  und Retention-Klasse
- Storage-, Memory- und Context-Dokumente benutzen dieselbe Pipeline
  `selection -> onboarding -> persistence -> retrieval/vector`
