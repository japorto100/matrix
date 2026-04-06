# Storage Layer Delta (SeaweedFS / Garage / Snapshot Boundary)

> **Stand:** 12. Maerz 2026
> **Zweck:** Aktiver Ausfuehrungsplan fuer Auswahl, lokalen Test und
> Architektur-Integration der Object-Storage-Schicht inkl. verbindlicher
> Boundary fuer Artefakte und Rohsnapshots.

---

## 0. Execution Contract (verbindlich fuer CLI-Agents)

### Scope In

- objektiver Kandidatenvergleich SeaweedFS vs. Garage
- signed-upload/download Integrationspfad ueber Go-Boundary
- Artefakt- und Fehlerpfad-Validierung fuer produktnahe Dateitypen
- Objektpfad fuer Raw Snapshots aus source-/batch-basierten Downloads

### Scope Out

- finaler produktiver HA-Rollout
- cloud-spezifische Vendor-Optimierung
- fachfremde Provider-Rollouts
- source-spezifische Cadence-/Vector-Policy im Detail

### Mandatory Upstream Sources (vor Abarbeitung lesen)

- `docs/storage_layer.md`
- `docs/specs/ARCHITECTURE.md`
- `docs/specs/EXECUTION_PLAN.md`
- `docs/specs/execution/source_persistence_snapshot_delta.md`
- `docs/specs/execution/infra_provider_delta.md`
- `docs/GO_GATEWAY.md`

### Arbeitsprinzip

- Entscheidungen werden ueber reproduzierbare lokale Nachweise getroffen, nicht
  ueber Theorie.
- Jede Storage-Entscheidung braucht Folgeeintrag in Runtime-/Plan-Dokumente.
- Object Storage ist fuer Rohartefakte und Rohsnapshots zustaendig, nicht fuer
  Hot Cache oder Embedding-Logik.

---

## 1. Leitentscheidung

- Wir evaluieren SeaweedFS und Garage host-nativ (ohne Docker) als S3-kompatiblen Object Layer.
- Fokus zuerst auf verifizierbare Produktpfade (Upload, Retrieval, signed URLs, audit), nicht auf Perfektion der Cluster-Topologie.
- Die aktuelle Gateway-Baseline ist bereits geliefert: Go-owned signed artifact flows + relationaler Metadaten-Store + filesystem-backed lokaler Blob-Provider als Vorstufe zur S3-kompatiblen Provider-Evaluation.
- Dieselbe Boundary wird auch fuer `file-snapshot` und spaeter `api-snapshot`
  Quellen genutzt: raw blob im object store, Metadaten im relationalen Index.

---

## 2. Scope fuer diese Delta-Spec

| In Scope | Out of Scope |
|:---------|:-------------|
| lokaler Binary-Betrieb, Single-Node, API-Schnitt, Integrationspfade | vollstaendige Multi-Region-HA-Architektur |
| Artefaktklassen PDF/Audio/Video/Parquet | exotische Object-Lock/S3-Edge-Features |
| retention-/metadata-Modell und Go-boundary | finaler produktiver Infra-Rollout |

---

## 3. Arbeits-Checkliste

### A. Candidate Bring-up

- [x] **SL1** SeaweedFS lokal starten (`weed server -dir=./data -s3`) und Baseline dokumentieren
- [~] **SL2** Garage lokal starten (Config + `garage server`) und Baseline dokumentieren
- [~] **SL3** Smoke-Test je Kandidat (`aws s3 ls`, bucket create/list/delete)

### B. API- und Boundary-Verifikation

- [x] **SL4** Signed upload/download flow ueber Go-Policy-Layer skizzieren und testen
- [x] **SL5** Kein direkter browserseitiger Root-Credential-Pfad
- [x] **SL6** Metadatenmodell fuer Objektindex (owner, hash, type, retention, created_at)

### C. Artefakt- und Fehlerpfade

- [x] **SL7** Upload/Download testen: PDF, Audio, Video, Parquet
- [x] **SL8** Fehlerpfade pruefen: unterbrochener Upload, Timeout, doppelter Upload
- [x] **SL9** Audit-/Trace-Ereignisse fuer Success + Failure in Go erfassen

### D. Entscheidungsabschluss

- [x] **SL10** Kandidatenvergleich dokumentieren (Betrieb, Komplexitaet, Entwicklungsfluss)
- [x] **SL11** "Default local stack" festlegen (voraussichtlich SeaweedFS)
- [x] **SL12** Follow-up fuer produktionsnahe HA-/Replication-Anforderungen in `infra_provider_delta.md` verankern

### E. Snapshot-/Source-Boundary

- [ ] **SL13** Raw-Snapshot-Objektmodell fuer `file-snapshot` Quellen an
  dieselbe Go-owned Storage-Boundary haengen
- [ ] **SL14** Mindest-Metadaten fuer Rohsnapshots (`sha256`, `etag`,
  `last_modified`, `parser_version`, `snapshot_status`) verbindlich machen
- [ ] **SL15** Trennung `object storage` vs. `hot cache` vs. `vector ingestion`
  in Runtime- und Owner-Dokumenten geschlossen halten
- [ ] **SL16** Signed Access nur fuer Artefakte, nicht fuer interne Raw-Snapshot-
  Betriebsobjekte
- [ ] **SL16a** erster echter SeaweedFS-Write/Read fuer `OFAC`, `UN`, `SECO`,
  `CFTC` gegen den laufenden Stack verifiziert; lokaler Raw-Bootstrap bleibt bis
  dahin nur Vorstufe

> **Zustand 02.04.2026 — `ofac_sdn.json`**: Die OFAC SDN-Liste liegt aktuell als
> statische 93k-Zeilen JSON-Datei in `go-backend/data/sanctions/ofac_sdn.json`
> direkt im Git-Repository. Das verursacht Probleme:
> 1. **Repo-Bloat** — 93k Zeilen Binaer-aehnliche Daten im Git-Index
> 2. **Stale Data** — OFAC-Liste wird regelmaessig aktualisiert, statische Kopie veraltet
> 3. **Tooling-Probleme** — tree-sitter (GitNexus) crasht beim Parsen der riesigen JSON
>
> **Optionen:**
> - **(a)** Download-Script im CI/CD — `ofac_sdn.json` bei jedem Deploy von
>   `https://www.treasury.gov/ofac/downloads/sdn_xml.zip` holen, nach JSON konvertieren
> - **(b)** SeaweedFS Object-Storage (SL16a) — JSON in Object-Storage, Go-Backend
>   liest von dort statt aus Dateisystem
> - **(c)** XML-Diff-Watcher (bereits in `sdn_watcher.go`) konsequent nutzen —
>   nur Deltas speichern statt Full-Dump
> - **(d)** `.gitignore` + Download-Script als Zwischenloesung bis SL16a fertig
>
> Empfehlung: **(d)** sofort (Datei aus Git entfernen), **(b)** mittelfristig mit SL16a.
- [ ] **SL16b** Snapshot-Error-/Recovery-Pfad gegen laufenden Object-Storage
  pruefen (`timeout`, fehlender Bucket, unterbrochener Write, doppelter
  Snapshot-Key)

### F. Backend-owned Metadata DB Direction

- [ ] **SL17** festhalten, welche heute frontend-/Prisma-nahen oder lokalen
  SQLite-Pfade mittelfristig in einen backend-owned relational metadata/index
  layer wandern muessen
- [ ] **SL18** Ziel-DB fuer staging/prod evaluieren und als Storage-/Source-
  Metadata-Zielpfad dokumentieren
- [ ] **SL19** schrittweise Trennung zwischen frontend-/BFF-naher App-DB und
  Go-owned Betriebs-/Metadata-DB planen
- [~] **SL20** lesende Query-Boundary fuer `source_snapshot_metadata`
  bereitstellen, damit normalized snapshots spaeter ohne direkten
  Dateipfad-Scan konsumiert werden koennen

### G. Naechster Todo-Batch

- [ ] `SL13-SL16a` als echter Seaweed/Object-Storage-Livepfad fuer
  `OFAC`, `UN`, `SECO`, `CFTC` schliessen
- [ ] `SL16b` mit expliziten Snapshot-Error-/Recovery-Faellen gegen laufenden
  Object-Storage schliessen
- [ ] `SL20` vom reinen Storage-Store auf den ersten echten Downstream-Consumer
  fuer normalized snapshots erweitern
- [ ] `SL17-SL19` gegen einen konkreten staging/prod Zielpfad
  backend-owned relational metadata/index layer praezisieren
- [ ] falls noetig separaten Read-Service / Query-Layer fuer
  `source_snapshot_metadata` ueber dem reinen SQLite-Bootstrap definieren

### Aktueller Baseline-Status

- Gateway-Routen aktiv: `POST /api/v1/storage/artifacts/upload-url`, `PUT /api/v1/storage/artifacts/upload/{id}`, `GET /api/v1/storage/artifacts/{id}`, `GET /api/v1/storage/artifacts/{id}/download`
- Signed URL Tokens: HMAC-basiert, kurzlebig, action-scoped (`upload` / `download`)
- Metadaten: SQLite (`artifact_metadata`) mit object key, filename, content type, retention class, status, size, sha256, timestamps
- Source-Snapshot-Metadaten-Basis ist jetzt ebenfalls im Go-Storage-Layer angelegt:
  `source_snapshot_metadata` mit `source_id`, `source_class`, `fetch_mode`,
  `source_url`, `object_key`, `sha256`, `etag`, `last_modified`,
  `parser_version`, `snapshot_status`, `retention_class`, `cadence_hint`
- Lokaler Blob-Provider: SeaweedFS host-nativ ist jetzt der aktuelle Dev-Default; filesystem-backed bleibt als fallback-faehige Boundary-Vorstufe erhalten
- Verifizierte Nachweise im Code: Go-Tests fuer Signer, Metadaten-Store, S3-Provider, HTTP Artifact Flow und Gateway-Wiring
- Tooling-Pfade angelegt: `tools/seaweedfs/weed.exe`, `tools/seaweedfs/s3.json`, `scripts/start-seaweedfs.sh`, `docker-compose.seaweedfs.yml`, `tools/seaweedfs/Dockerfile`

### Snapshot Metadata Foundation Evidence (2026-03-12)

- `go-backend/internal/storage/types.go` erweitert um `SourceSnapshot` und
  `SourceSnapshotStatus`
- `go-backend/internal/storage/metadata_store.go` migriert jetzt zusaetzlich
  `source_snapshot_metadata` und bietet:
  - `CreateSourceSnapshot`
  - `GetSourceSnapshot`
  - `MarkSourceSnapshotStatus`
  - `ListSourceSnapshots`
  - `GetLatestSourceSnapshot`
- `go-backend/internal/storage/metadata_store_test.go` deckt Create/Get/Status-
  Update fuer Snapshot-Metadaten ab
- fokussierter Testlauf gruen:
  - `go test ./internal/storage`

### First Source Snapshot Integration Evidence (2026-03-12)

- `go-backend/internal/connectors/base/diff_watcher.go` besitzt jetzt einen
  optionalen `OnFetched`-Hook, der Payload, Hash und Fetch-Metadaten an einen
  Snapshot-Recorder durchreichen kann
- `go-backend/internal/connectors/base/bulk_fetcher.go` besitzt jetzt einen
  analogen `OnFetched`-Hook fuer bulk-/download-basierte Rohdateien
- `go-backend/internal/connectors/base/source_snapshot_recorder.go` kapselt den
  Recorder fuer Raw-Object plus `source_snapshot_metadata` ueber denselben
  Storage-Env-Contract wie Artefakte; lokales Filesystem bleibt nur Fallback
- `go-backend/internal/connectors/base/diff_watcher_test.go` verifiziert den
  Hook fuer Payload-, Header- und Zeit-Metadaten
- `go-backend/internal/connectors/base/source_snapshot_recorder_test.go`
  verifiziert den Recorder gegen einen S3-kompatiblen Testserver mit
  `ARTIFACT_STORAGE_PROVIDER=seaweedfs`
- `go-backend/internal/connectors/ofac/sdn_watcher.go`,
  `go-backend/internal/connectors/un/sanctions_watcher.go` und
  `go-backend/internal/connectors/seco/sanctions_watcher.go` schreiben fuer
  offizielle XML-Diff-Feeds jetzt lokale Raw-Snapshots plus
  `source_snapshot_metadata`-Eintraege
- `go-backend/internal/connectors/cftc/cot_fetcher.go` schreibt fuer den
  offiziellen ZIP-Download jetzt ebenfalls einen lokalen Raw-Snapshot plus
  `source_snapshot_metadata`-Eintrag
- `go-backend/internal/connectors/news/gdelt_client.go` nutzt dieselbe
  Recorder-/Storage-Boundary jetzt auch fuer den ersten `api-snapshot`-Pfad
  auf JSON-Basis (`GDELT News`)
- `go-backend/internal/connectors/news/gdelt_client_test.go` verifiziert den
  `GDELT News`-Pfad auf Raw-Payload plus SQLite-Metadaten
- `go-backend/internal/connectors/acled/client.go` und
  `go-backend/internal/connectors/crisiswatch/client.go` nutzen dieselbe
  Recorder-/Storage-Boundary jetzt ebenfalls fuer `api-snapshot`-Quellen
- `go-backend/internal/connectors/base/source_snapshot_recorder.go` besitzt
  jetzt zusaetzlich einen lokalen Normalizer-Pfad fuer deterministische
  `source-snapshots/normalized/...` Objekte
- `go-backend/internal/connectors/acled/client_test.go` und
  `go-backend/internal/connectors/crisiswatch/client_test.go` verifizieren
  beide Pfade auf Raw-Payload plus SQLite-Metadaten
- `ACLED` setzt dabei als erster `api-snapshot`-Connector den
  Metadaten-Status von `fetched` auf `normalized`
- die zugehoerigen Paket-Tests verifizieren Raw-Datei plus SQLite-Metadata-
  Eintrag fuer echte Fetch-/Watcher-Laeufe
- fokussierter Testlauf gruen:
  - `go test ./internal/connectors/base ./internal/connectors/ofac ./internal/connectors/un ./internal/connectors/seco ./internal/connectors/cftc ./internal/storage`
  - `go test ./internal/connectors/news ./internal/connectors/base ./internal/storage ./internal/app`
  - `go test ./internal/connectors/news ./internal/connectors/crisiswatch ./internal/connectors/acled ./internal/connectors/base ./internal/storage ./internal/app`
  - `cd go-backend && go test ./internal/connectors/acled ./internal/connectors/base ./internal/storage ./internal/app`

### SeaweedFS Evidence (2026-03-09)

- Binary erfolgreich bereitgestellt und verifiziert: `tools/seaweedfs/weed.exe version` -> `4.15`
- Host-native Start erfolgreich mit lokalem Tool-Pfad und angepasstem Volume-Port `18080`:
  - Master UI `http://127.0.0.1:9333`
  - Filer `http://127.0.0.1:8888`
  - S3 `http://127.0.0.1:8333`
- Reale Gateway-E2E erfolgreich:
  - Upload-URL erzeugt
  - Artefakt via signiertem Go-Pfad hochgeladen
  - Metadatenstatus `ready`
  - Download ueber signierten Go-Pfad erfolgreich
- OSS-S3-CLI-Smoke erfolgreich ueber den laufenden SeaweedFS-Endpunkt:
  - `aws --endpoint-url http://127.0.0.1:8333 s3 ls`
  - `aws --endpoint-url http://127.0.0.1:8333 s3 mb s3://tradeview-artifacts-cli-smoke`
  - `aws --endpoint-url http://127.0.0.1:8333 s3 rb s3://tradeview-artifacts-cli-smoke`
- Re-Verify auf dem aktuellen Host erfolgreich ueber den DevCache-AWS-CLI-Pfad:
  - `AWS_ACCESS_KEY_ID=seaweedfs AWS_SECRET_ACCESS_KEY=seaweedfs-secret /d/DevCache/bin/aws --endpoint-url http://127.0.0.1:8333 s3 ls`
  - `AWS_ACCESS_KEY_ID=seaweedfs AWS_SECRET_ACCESS_KEY=seaweedfs-secret /d/DevCache/bin/aws --endpoint-url http://127.0.0.1:8333 s3 mb s3://tradeview-artifacts-cli-smoke-2`
  - `AWS_ACCESS_KEY_ID=seaweedfs AWS_SECRET_ACCESS_KEY=seaweedfs-secret /d/DevCache/bin/aws --endpoint-url http://127.0.0.1:8333 s3 rb s3://tradeview-artifacts-cli-smoke-2`
- Dev-Env auf SeaweedFS umgeschaltet: `go-backend/.env.development` nutzt `ARTIFACT_STORAGE_PROVIDER=seaweedfs`
- `scripts/dev-stack.ps1` startet SeaweedFS jetzt als lokalen Infra-Dienst neben NATS/OpenObserve

### Garage Candidate Staging (2026-03-09)

- Tooling-Pfade vorbereitet:
  - `tools/garage/garage.toml` fuer host-native Windows-Konfiguration
  - `tools/garage/garage.docker.toml` fuer Container-Pfad
  - `tools/garage/Dockerfile`
  - `docker-compose.garage.yml`
  - `scripts/start-garage.sh`
- Source-Kandidat lokal bereitgestellt: `tools/garage/src-v2.2.0`
- Rust/Cargo-Home fuer den User dauerhaft auf `D:\DevCache` verankert:
  - `CARGO_HOME=D:\DevCache\cargo\.cargo`
  - `RUSTUP_HOME=D:\DevCache\rustup`
- Host-native Windows-Build aktuell **upstream-blockiert**:
  - `cargo build --release` scheitert in `src/rpc/system.rs`, `src/api/common/generic_server.rs` und `src/web/web_server.rs`
  - Ursache: unguarded Unix-spezifische Imports/Listener/Permissions (`std::os::unix::*`, `nix::sys::statvfs`, `UnixListener`)
- Der aktuelle Arbeitsauftrag zieht deshalb **kein weiteres Garage-Debugging** mehr:
  - auf diesem Windows-Host wird Garage vorerst bewusst uebersprungen
  - Docker/Compose ist in der aktiven Git-Bash-Umgebung ebenfalls nicht verfuegbar, daher gibt es keinen belastbaren Container-Gegenbeweis in diesem Slice
- Konsequenz fuer diese Delta-Spec:
  - `SL2` ist auf diesem Host **deferred/blockiert**, bis entweder ein kleiner tragfaehiger Windows-Fork belegt ist oder Garage spaeter ueber einen verfuegbaren Containerpfad gegengeprueft wird
  - `SL3` ist fuer SeaweedFS verifiziert; der Garage-Teil bleibt deferred

### Kandidatenvergleich (2026-03-10)

| Kriterium | SeaweedFS | Garage |
|:----------|:----------|:-------|
| Host-nativer Windows-Start | verifiziert (`weed.exe`, lokaler S3/Filer/Master-Stack laeuft) | auf diesem Host upstream-blockiert durch Unix-only Code |
| S3-CLI-Smoke | verifiziert (`ls`, `mb`, `rb`) | nicht verifiziert auf diesem Host |
| Go-Integrationspfad | verifiziert ueber signed upload/download + S3-Provider-Tests | keine belastbare lokale Gegenprobe |
| Developer UX lokal | schnellster Weg zum laufenden Single-Node-Stack | aktuell hoher Reibungsgrad, weil Windows-Build nicht tragfaehig |
| Operative Klarheit im Dev-Setup | hoch, da Start-/Port-Modell bereits in `dev-stack.ps1` integriert | mittel bis niedrig, solange nur vorbereitete Configs/Docker-Artefakte existieren |

**Entscheidung:** SeaweedFS bleibt der begruendete `default local stack`.

**Warum:** SeaweedFS liefert auf dem aktuellen Windows-Host den einzigen voll verifizierten End-to-End-Pfad fuer lokalen Objekt-Storage. Garage bleibt ein optionaler Folgekandidat fuer spaetere Gegenpruefung, aber nicht mehr Gate fuer den laufenden Delivery-Plan.

### Storage Verify Evidence (2026-03-09, Go Tests)

- Fokus-Testlauf gruen: `go test ./internal/handlers/http ./internal/storage ./internal/app`
- `SL7` ueber HTTP-Artifact-Tests verifiziert:
  - Upload/Metadata fuer `application/pdf`
  - Upload/Metadata fuer `audio/mpeg`
  - Upload/Metadata fuer `video/mp4`
  - Upload/Metadata fuer `application/vnd.apache.parquet`
- `SL8` ueber gezielte Handler-Fehlerpfade verifiziert:
  - unterbrochener Upload -> `502` + Artefakt bleibt `pending_upload`
  - Timeout (`context.DeadlineExceeded`) -> `504` + Fehlerklasse `timeout`
  - doppelter Upload -> `409`
- `SL9` ueber strukturierte Audit-Logs verifiziert:
  - `artifact_action` fuer Upload/Download
  - `outcome=success` und `outcome=failure`
  - `requestId` wird in den Audit-Log geschrieben
  - Fehlerklassen fuer `invalid_token`, `not_ready`, `timeout`, `storage_error`

### Noch offen trotz Baseline

- `SL3`: SeaweedFS-Teil ist verifiziert; der Garage-Teil bleibt deferred, bis ein spaeterer Container- oder Windows-Fork-Pfad real verfuegbar ist
- `SL2`: Garage host-nativ ist auf diesem Windows-Host aktuell durch Upstream-Unix-Code blockiert; Vergleichspfad braucht entweder kompakten Windows-Patch oder Container-Gegenprobe
- `SL13-SL16`: Source-Persistence-Slice ist jetzt definiert, aber die
  Storage-Boundary fuer Raw Snapshots muss noch explizit an die produktive
  Storage-Implementierung gehaengt werden
- `SL17-SL19`: SQLite im Go-Backend bleibt lokaler Bootstrap-Pfad; mittelfristig
  ist ein backend-owned relational metadata/index layer fuer staging/prod zu
  entscheiden und zu planen

---

## 4. Entscheidungskriterien

1. **Developer UX:** setup time bis erster erfolgreicher Upload/Download
2. **Go-Integration:** sauberer signed-url und metadata-flow
3. **Operational clarity:** Logs, Fehlerbilder, einfache Recovery im lokalen Setup
4. **S3-Kompatibilitaet im praktischen Pfad:** keine blocker bei typischen SDK-Aufrufen
5. **Skalierungspfad:** glaubwuerdiger Weg von lokal -> staging -> prod

---

## 5. Querverweise

| Frage | Dokument |
|:------|:---------|
| Normative Architektur inkl. Storage-Knoten | [`../ARCHITECTURE.md`](../ARCHITECTURE.md) |
| Root-Entscheidung und Heuristik | [`../../../storage_layer.md`](../../../storage_layer.md) |
| Source-Snapshot-Persistenz | [`source_persistence_snapshot_delta.md`](./source_persistence_snapshot_delta.md) |
| Infra-/Provider-Rollout | [`infra_provider_delta.md`](./infra_provider_delta.md) |
| Master-Roadmap | [`../EXECUTION_PLAN.md`](../EXECUTION_PLAN.md) |

---

## 6. Evidence Requirements

Fuer jede geschlossene SL-Aufgabe (`SL1-SL12`) mindestens:

- Umgebung und Startkommando
- erfolgreicher Smoke-Nachweis (bucket/list/upload/download)
- Fehlerpfad-Nachweis (timeout/broken upload/duplicate)
- signed URL und audit-pfad dokumentiert
- begruendeter Kandidatenvergleich (UX, Integration, Ops, Skalierung)
- bei Source-Snapshot-Nutzung: Raw-Snapshot-Metadaten und Lifecycle-Regel
  dokumentiert

---

## 7. Propagation Targets

- `docs/storage_layer.md`
- `docs/specs/ARCHITECTURE.md`
- `docs/specs/SYSTEM_STATE.md`
- `docs/specs/EXECUTION_PLAN.md`
- `docs/MEMORY_ARCHITECTURE.md`
- `docs/CONTEXT_ENGINEERING.md`
- `docs/specs/execution/source_persistence_snapshot_delta.md`
- `docs/specs/execution/infra_provider_delta.md` (HA/Replication-Follow-up)
- `docs/specs/FRONTEND_ARCHITECTURE.md` (falls DB-/Ownership-Grenzen zwischen
  BFF und Go geaendert werden)

---

## 8. Exit Criteria

- `SL1-SL12` entschieden oder deferred mit Owner/Datum
- `SL13-SL16` entschieden oder an `source_persistence_snapshot_delta.md`
  uebergeben
- `SL17-SL19` mindestens als dokumentierte Zielrichtung fuer staging/prod
  festgehalten
- ein klarer Default-Local-Stack festgelegt
- objektiver Evidence-Satz fuer beide Kandidaten liegt vor
