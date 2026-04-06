# STORAGE AND PERSISTENCE

> **Stand:** 17. Maerz 2026  
> **Zweck:** Owner-Spec fuer Object Storage, Source-Snapshot-Klassen, Cache-Abgrenzung
> und Artefakt-Persistenz.
> **Source-of-Truth-Rolle:** Autoritativ fuer Storage-Architekturregeln; vollstaendiger
> Implementierungsleitfaden in `docs/storage_layer.md`.

---

## 1. Kernprinzipien (verbindlich)

1. **Object-first fuer grosse oder replay-relevante Artefakte** (PDF, Audio, Parquet, Snapshots).
2. **No direct browser root access** — signierte kurzlebige URLs via Go.
3. **Go-owned policy boundary** — ACL, retention, quota, tenancy, audit laufen ueber Go.
4. **Metadata split** — Objektinhalt im Store, Index/Lifecycle/Ownership relational.
5. **Integrity by default** — checksum/etag/last-modified bei Upload/Download erfassen.
6. **Replay-safe ingestion** — async Pfade mit idempotency key, dedup hash, parser version.
7. **Cache != Persistenz** — Hot cache und source snapshots sind getrennte Schichten.
8. **Vectorization ist Downstream** — Embeddings entstehen aus normalisierten Outputs, nie aus ungoverned Raw-Downloads.
9. **Parquet ist Baseline-Dateiformat fuer tabellarische Artefakte**; `Iceberg` wird nur bei echtem Tabellen-/Snapshot-Mehrwert eingezogen.

---

## 2. Technologie-Entscheidung

| System | Rolle | Status |
|:-------|:------|:-------|
| SeaweedFS | Primaerer dev-/staging-local Object Store (S3-kompatibel) | Aktiv, single-binary |
| S3-kompatibel | Productionpfad (Drop-in fuer SeaweedFS) | Vorbereitet |
| Garage | Alternative mit Cluster-Fokus | Offen fuer Evaluation |

**Arbeitsregel:** SeaweedFS bevorzugen, solange Single-Node und schneller Dev-Start im Vordergrund stehen.

---

## 3. Persistenzklassen

| Klasse | Typischer Input | Raw Snapshot | Normalized Snapshot | Hot Cache |
|:-------|:----------------|:-------------|:--------------------|:----------|
| `api-hot` | kleine REST-Reads, intraday Quotes | optional, nur bei Audit-Bedarf | optional | verpflichtend |
| `api-snapshot` | API-Serien mit diff-/replay-Wert | optional bei `on-change` | ja | ja |
| `file-snapshot` | XML/CSV/ZIP/PDF/Parquet Downloads | verpflichtend | ja | optional |
| `stream-only` | SSE/WebSocket/Ticks | nein, ausser gezielter Capture-Pfad | optional windowed/materialized | verpflichtend |

---

## 4. Snapshot-Metadaten (Mindestset)

Jeder persistierte Rohsnapshot fuehrt mindestens:

- `source_id`, `source_class`, `fetch_mode`
- `fetched_at`, `source_url`
- `content_type`, `content_length`, `sha256`
- `etag` (falls vorhanden), `last_modified` (falls vorhanden)
- `parser_version`, `snapshot_status`, `retention_class`

Optional je Quelle: `cadence_hint`, `dataset_name`, `partition_key`, `trace_id`, `error_class`

---

## 5. Retention-Klassen

| Klasse | Zweck | Beispiel |
|:-------|:------|:---------|
| `ephemeral` | kurzfristiger Cache ohne Langzeitaudit | intraday REST reads |
| `snapshot` | replay-faehige Roh- und Normalform | sanctions XML, CFTC, FINRA ATS |
| `audit` | regulatorisch oder produktkritisch nachvollziehbar | Promotion-/Review-nahe Artefakte |

---

## 6. Cache-Abgrenzung

| Schicht | Technologie | Charakteristik |
|:--------|:------------|:---------------|
| Hot Cache | Valkey (Redis-kompatibel) | Sekunden-Stunden, niedr. Latenz, kein SoT |
| Object Snapshot | SeaweedFS | Replay, Audit, Parser-Neulauf, unveraenderlich |
| Relat. Metadata | Postgres (Ziel), SQLite (Dev-Bootstrap) | Index, Lifecycle, Ownership, Parserstatus |

**Entscheidungsheuristik:** Latenzreduktion → Cache. Diff/Debug/Audit/Neu-Interpretation → Snapshot-Pfad.

---

## 7. IST-Status (16.03.2026)

- Go besitzt Artefakt-Frontdoor (`/api/v1/storage/artifacts/*`).
- Upload/Download via kurzlebige signierte Gateway-URLs.
- Metadaten in SQLite (`artifact_metadata`) — Bootstrap akzeptiert.
- Lokale Blob-Ablage filesystem-backed fuer saubere Boundary-/Fehlerpfad-Tests.
- SeaweedFS aktiver dev-default fuer S3-kompatible Objektpfade.

**Offen:**
- Source-Snapshot-Klassen und Cadence-Policy vollstaendig durchziehen.
- Rohsnapshot-Metadaten fuer `file-snapshot` und `api-snapshot` Quellen.
- Postgres-Migration fuer backend-owned metadata layer (mittelfristig).

---

## 8. Daten-Zonen fuer Vectorization-Chain

```
source selection
  -> fetch / cache / snapshot (Go)
  -> normalize (Go/Python)
  -> chunking + embedding + vector storage (Python)
```

Embeddings werden nicht direkt aus ungeprueften Rohdownloads produziert.
Raw blobs landen zuerst im Object Store; Parser erzeugen normalisierte Records/Textsegmente.

### Arbeitsdefault fuer tabellarische Artefakte

- grosse tabellarische Exporte, Replay-Outputs und Batch-Artefakte gehen
  bevorzugt als `Parquet` in den Object Store
- `DuckDB` liest diese Artefakte fuer Analyse, Replay und Worker-SQL

---

## 9. Querverweise

- `docs/storage_layer.md` (vollstaendiger Implementierungsleitfaden)
- `docs/specs/data/DATA_ARCHITECTURE.md`
- `docs/specs/architecture/MEMORY_AND_STORAGE_BOUNDARIES.md`
- `docs/specs/execution/storage_layer_delta.md`
- `docs/specs/execution/source_persistence_snapshot_delta.md`
- `docs/specs/execution/vector_ingestion_delta.md`
