# Storage Layer (SeaweedFS / Garage / Source Snapshots)

> Stand: 12. Maerz 2026  
> Zweck: Root-Entscheidungsdokument fuer Object Storage, Source Snapshots,
> Cache-Abgrenzung und Rohartefakt-Persistenz in `tradeview-fusion`.

---

## 1) Zielbild

`tradeview-fusion` nutzt einen object-first Storage-Layer fuer grosse oder
replay-relevante Artefakte:

- PDF
- Audio
- Video
- Parquet
- regulatorische XML/CSV/ZIP-Downloads
- Roh-Snapshots batch- oder diff-basierter Quellen

Kernprinzip:

- Binaerdaten und Rohsnapshots liegen im Object Store.
- Domain-, Lifecycle-, Hash- und Parser-Metadaten liegen in relationalen
  Tabellen.
- Zugriffspfade werden ueber Go signiert, auditiert und policy-seitig
  kontrolliert.

### 1.1 Mittelfristige DB-Richtung

Der aktuelle lokale Zustand mit SQLite an mehreren Stellen ist als
Bootstrap-/Dev-Setup akzeptiert. Mittelfristig gilt aber:

- **Go-owned Domain- und Metadata-Layer** gehoeren in eine
  **backend-owned relationale DB**.
- Das betrifft insbesondere:
  - source snapshot metadata
  - provider metadata
  - workflow-/idempotency-/retry-state
  - review-/promotion-/audit-nahe Betriebsdaten
- Der frontend-/Prisma-nahe DB-Pfad bleibt nicht die Zielheimat fuer Daten, bei
  denen Go bereits Write-Owner oder Policy-Owner ist.

Arbeitsregel:

- lokal/dev darf SQLite weiter als pragmatischer Zwischenschritt laufen
- fuer staging/prod wird ein backend-owned relational metadata/index layer
  evaluiert und spaeter gehoben, voraussichtlich Postgres

---

## 2) Kandidaten fuer lokale und produktive Pfade

| System | Rolle in unserem Kontext | Reife fuer schnellen Host-Test |
|:------|:--------------------------|:-------------------------------|
| SeaweedFS | primaerer Kandidat fuer schnellen Start (single binary, S3 gateway) | sehr hoch |
| Garage | Alternative mit staerkerem Cluster-/Config-Fokus | mittel |

---

## 3) Architekturregeln (verbindlich)

1. **No direct browser root access:** Browser bekommt nur kurzlebige signierte Upload-/Download-Pfade.
2. **Go-owned policy boundary:** ACL, retention, quota, tenancy und audit laufen ueber Go.
3. **Object-first for large or replay-relevant artifacts:** grosse Dateien und Rohsnapshots nie als DB-Blob normalisieren.
4. **Metadata split:** Objektinhalt im Store, Index/Lifecycle/Ownership in relationalen Tabellen.
5. **Integrity by default:** checksum/etag/last-modified bei Upload oder Download erfassen, wenn verfuegbar.
6. **Replay-safe ingestion:** asynchrone Importpfade mit idempotency key, dedup hash und parser version.
7. **Cache ist nicht Persistenz:** Hot cache und source snapshots sind getrennte Schichten.
8. **Vectorization ist Downstream:** Embeddings entstehen aus normalisierten Outputs, nicht aus ungoverned Raw-Downloads.

---

## 4) Source-Persistence-Modell

Fuer Quellen gilt eine eigene Betriebslogik. Nicht jede Quelle braucht denselben
Persistenzgrad.

### 4.1 Persistenzklassen

| Klasse | Typischer Input | Raw Snapshot | Normalized Snapshot | Hot Cache |
|:-------|:----------------|:-------------|:--------------------|:----------|
| `api-hot` | kleine REST-Reads, intraday Quotes, leichte Macro-Reads | optional, nur bei Audit-Bedarf | optional | verpflichtend |
| `api-snapshot` | API-Serien mit diff-/replay-Wert | optional bei `on-change` | ja | ja |
| `file-snapshot` | XML/CSV/ZIP/PDF/Parquet Downloads | verpflichtend | ja | optional |
| `stream-only` | SSE/WebSocket/Ticks | nein, ausser gezielter Capture-Pfad | optional windowed/materialized | verpflichtend bzw. ring-buffered |

### 4.2 Typische Zuordnung

- `FRED`, `Banxico`, `BoK`, `ECB`, `OFR`, `NYFed`: primaer `api-hot`, bei
  wichtigen Serien optional `api-snapshot`
- `OFAC`, `UN Sanctions`, `SECO`, spaeter evtl. `EU Sanctions`: `file-snapshot`
- `FINRA ATS`: `api-snapshot` mit optionalem Download-Zweig
- SSE-/Streaming-Pfade: `stream-only`

---

## 5) Snapshot-Metadaten (Mindestset)

Jeder persistierte Rohsnapshot braucht mindestens:

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

Zusaetzlich sinnvoll je Quelle:

- `cadence_hint`
- `dataset_name`
- `partition_key`
- `trace_id` / `request_id`
- `error_class` bei fehlgeschlagenem Fetch

---

## 6) Cadence-, Change- und Retention-Regeln

### 6.1 Fetch-Modi

- `poll`
- `conditional-poll`
- `on-demand`
- `stream`

### 6.2 Change Detection

- `etag`
- `last-modified`
- `sha256`
- record-level diff

### 6.3 Retention-Klassen

| Klasse | Zweck | Beispiel |
|:-------|:------|:---------|
| `ephemeral` | kurzfristiger Cache ohne Langzeitaudit | intraday REST reads |
| `snapshot` | replay-faehige Roh- und Normalform | sanctions XML, CFTC, FINRA ATS responses |
| `audit` | regulatorisch oder produktkritisch nachvollziehbar | Promotion-/Review-nahe oder sicherheitsrelevante Artefakte |

Arbeitsregel:

- `file-snapshot` Quellen persistieren Rohdateien standardmaessig `on-change`
  oder `always`
- `api-hot` Quellen persistieren raw responses nur bei klarem Audit-/Replay-Nutzen
- `stream-only` bleibt standardmaessig im Cache-/materialized-window-Layer

---

## 7) Cache-Abgrenzung

Storage und Cache duerfen nicht vermischt werden:

- **Redis/Valkey / in-memory cache**
  - Sekunden bis Stunden
  - niedrige Latenz
  - kein Source of Truth
- **Object Storage / Snapshot Store**
  - Rohdateien, Replay, Parser-Neulauf, Audit
  - unveraenderliche oder append-only Artefakte
- **Relationaler Metadatenstore**
  - Index, Lifecycle, Ownership, Parserstatus

Wenn ein API-Response nur zur Latenzreduktion gebraucht wird, ist Cache der
richtige Ort. Wenn der Response fuer Diff, Debug, Audit oder spaetere
Neu-Interpretation gebraucht wird, braucht er einen Snapshot-Pfad.

---

## 8) Vector- und Retrieval-Abgrenzung

Vectorization gehoert **nicht** in den Storage- oder Fetch-Grundvertrag.

Saubere Kette:

`source selection -> source onboarding -> fetch/cache/snapshot -> normalize -> retrieval/vector ingestion`

Das bedeutet:

- Raw blobs landen zuerst im Object Store.
- Parser erzeugen normalisierte Records oder Textsegmente.
- Erst dann duerfen chunking, embedding und vector storage greifen.
- Embeddings werden nicht direkt aus ungeprueften Rohdownloads produziert.

---

## 9) Aktueller Implementierungsstand

Stand heute ist die erste produktnahe Gateway-Baseline bereits im Code:

- Go besitzt die Artefakt-Frontdoor (`/api/v1/storage/artifacts/*`).
- Upload und Download laufen ueber kurzlebige signierte Gateway-URLs.
- Metadaten liegen in einer relationalen SQLite-Tabelle (`artifact_metadata`).
- Die lokale Blob-Ablage ist vorerst filesystem-backed, damit die Boundary und
  Fehlerpfade ohne S3-Mock sauber testbar bleiben.
- SeaweedFS ist der aktuelle host-native Dev-Default fuer S3-kompatible
  Objektpfade.

Was noch als Architekturvertrag nachgezogen wird:

- Source-Snapshot-Klassen und Cadence-Policy
- Rohsnapshot-Metadaten fuer `file-snapshot` und `api-snapshot` Quellen
- Trennung zwischen Raw Snapshot, Normalized Snapshot, Cache und Vector-Ingestion

---

## 10) Entscheidungsheuristik SeaweedFS vs Garage

- **SeaweedFS bevorzugen**, wenn:
  - wir in 30-60 Minuten einen lokalen End-to-End-Test fahren wollen
  - ein einfacher Single-Node Start fuer Developer wichtig ist
  - S3 + Filesystem/Filer-Szenarien kurzfristig zusammen gedacht werden

- **Garage bevorzugen**, wenn:
  - Cluster-/Replikationsmodell frueh explizit im Mittelpunkt steht
  - wir bewusst mehr initiale Konfigurationsdisziplin akzeptieren

---

## 11) Minimales Acceptance Set

Ein Kandidat gilt als "baseline usable", wenn alle Punkte gruen sind:

- Bucket erstellen, listen, loeschen
- Upload/Download fuer PDF, Audio, Video, Parquet
- Signed URL / short-lived access flow ueber Go
- Metadatenpersistenz (owner, content_type, size, hash, retention_class)
- Fehlerpfade (timeout, broken upload, duplicate upload) sauber auditiert
- Source-Snapshot-Objekte koennen mit Hash, Parser-Version und Status persistiert
  werden

---

## 12) Verknuepfte Spezifikationen

- Architektur: `docs/specs/ARCHITECTURE.md`
- Aktiver Umsetzungsplan Artefakte: `docs/specs/execution/storage_layer_delta.md`
- Aktiver Umsetzungsplan Quellenpersistenz: `docs/specs/execution/source_persistence_snapshot_delta.md`
- Aktiver Umsetzungsplan Vector-Ingestion: `docs/specs/execution/vector_ingestion_delta.md`
- Gesamtplan: `docs/specs/EXECUTION_PLAN.md`
