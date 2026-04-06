# DATA ARCHITECTURE

> **Stand:** 17. Maerz 2026  
> **Zweck:** Verbindliche Data-/Aggregation-Spec fuer IST-Zustand, Datenzonen,
> Contract-Drifts und Zielzustand. Kanonischer Owner.
> Root-Datei `docs/specs/DATA_ARCHITECTURE.md` verweist hierher.
> **Source-of-Truth-Rolle:** Autoritativ fuer Datenform, Datenfluss und Aggregations-Ownership.

---

## 1. Executive Snapshot

Die Aggregation ist technisch bereits weit umgesetzt und laeuft klar ueber eine
Go-zentrierte Router- und Connector-Architektur.

Hauptblocker ist nicht die Grundarchitektur, sondern:

- einzelne Route-/Contract-Drifts schliessen
- strikterem Capability-Enforcement
- Live-/Rollout-Verify bei Quellenpfaden abschliessen

---

## 2. IST-Topologie (Datenfluss)

```
Quelle
  -> Go Connector/Router
  -> Hot cache ODER Snapshot (je Quellenklasse)
  -> Optional: raw -> normalized snapshot + source_snapshot_metadata
  -> Serving via Go API/SSE
  -> Next.js konsumiert via /api/* BFF-Proxys
  -> Python-Compute/Memory/Agent als interne Downstreams hinter Go
  -> Rust beschleunigt Teilpfade innerhalb Python
```

### Systemebenen (IST)

| Ebene | Technologie | Status |
|:------|:------------|:-------|
| Frontend / BFF | Next.js App Router, /api/* | produktiv; Agent-Chat-Route teils nicht voll geschlossen |
| Control Plane | Go Gateway (Port 9060); GCT lokal via go module replace | produktiv; Capability-Enforcement teils fail-open |
| Compute / ML | Python FastAPI Services | produktiv; agent-service WS-Endpunkt scaffold |
| Rust Layer | PyO3 cdylib in python-backend/rust_core | produktiv fuer Indicator-Batch-Compute und redb |
| Snapshot/Metadata | SQLite-Bootstrap (source_snapshot_metadata), SeaweedFS lokal | Baseline vorhanden; Object-Storage-Live-Verify offen |

---

## 3. Bekannte Contract-Drifts (IST)

| Drift | Beschreibung |
|:------|:-------------|
| Agent-Chat | Next erwartet /api/v1/agent/chat; Go-Route nicht vollstaendig registriert |
| Portfolio Order | Policy/Middleware referenziert /api/v1/portfolio/order; Mux-Route fehlt |
| Capability Enforcement | Teile sind noch fail-open oder per Feature-Flag gated |
| Agent-Service WS | WebSocket-Endpunkt in agent-service ist explizites Scaffold/Echo |

---

## 4. Verbindliche Datenzonen

- `raw` -- append-only, object-first; kein direktes Consumer-Access
- `normalized` -- kanonisch, versioniert, provenance-markiert
- `derived/serving` -- Features/Signals/Views auf normalisierten Grundlagen
- `semantic` -- document-/graph-nahe Retrieval-Schicht auf normalisierten Inputs
- `episodic/operational` -- Job-, Audit- und Metadata-Kontext fuer Data-Plane-Arbeit

**Regel:** Keine Vector-/Retrieval-Pfade direkt auf ungepruefte Rohdaten.

---

## 5. Canonical Data Model (Mindestfelder)

Jeder normalisierte Datensatz fuehrt mindestens:

- `source_id`, `observed_at`, `effective_at`, `ingested_at`
- `version`, `lineage_ref`, `quality_score`, `confidence_score`

---

## 6. Data Product Ownership

| Product | Owner | Beschreibung |
|:--------|:------|:-------------|
| `market_data_product` | Go Connectors | OHLCV, Quotes, Streams |
| `macro_calendar_product` | Go Connectors (SDMX, TimeSeries) | Makrodaten, Kalender |
| `news_event_product` | Go News Layer | Headlines, RSS, GDELT |
| `geopolitical_event_product` | Go/UIL/GeoMap | ACLED, CrisisWatch, Sanctions |
| `portfolio_state_product` | Go/GCT | Positionen, Orders, Paper Trading |
| `strategy_feature_product` | Python Indicator Service | technische Features, Backtesting |

---

## 7. Storage-Rollen (Zielrichtung)

| Bereich | Technologie (Ziel) |
|:--------|:-------------------|
| Relationale Kernobjekte | Postgres |
| Semantischer Vector-Layer (document-centric) | pgvector |
| Graph-/Knowledge-Layer (entity-centric) | FalkorDB |
| Raw Snapshots / Replay | SeaweedFS (lokal) / S3 |
| Hot Cache / Locks | Valkey (Redis-kompatibel) |
| OHLCV Compute Cache | redb |
| Analytics / Replay SQL | DuckDB |
| Frontend User-KG | KuzuDB WASM + IndexedDB |

### Tabellarische Standardlinie (Ziel)

- `DuckDB + Polars + Arrow/PyArrow + Parquet` ist die Default-Linie fuer neue
  tabellarische Analyse-, Replay- und Worker-Pfade.
- `Arrow Flight` bleibt nur spaeterer Transportpfad fuer echte grosse
  tabellarische Service-Grenztransfers.
- `Iceberg` bleibt spaeteres Tabellenformat ueber `Parquet`, nicht Baseline.

---

## 8. Reifestufen

### A) Baseline (kurzfristig)
- Agent-Chat und Portfolio-Order Contract-Drifts schliessen
- Capability-Enforcement fuer mutation-nahe Pfade haerten
- Snapshot-/Provider-Live-Verify abschliessen

### B) Production-hardened (mittelfristig)
- Backend-owned relationale Metadata-/Index-Schicht produktiv (Postgres)
- Einheitliche degraded/error/provenance Envelopes
- Harte Policy fuer raw -> normalized -> retrieval/vector Kette

### C) Advanced
- Selektive Graph-Layer-Vertiefung bei nachgewiesenen Linkage-Bedarfen
- Data-Quality-Metriken und SLOs je Data Product

---

## 9. Querverweise

- `docs/DATA_AGGREGATION_Master.md` (Bridge/Archiv, vollstaendiger IST Code-Analyse Report)
- `docs/specs/data/AGGREGATION_IST_AND_GAPS.md`
- `docs/specs/data/STORAGE_AND_PERSISTENCE.md`
- `docs/specs/data/SOURCE_STATUS.md`
- `docs/specs/SYSTEM_STATE.md`
- `docs/specs/API_CONTRACTS.md`
- `docs/specs/architecture/ARCHITECTURE_BASELINE.md`
- `docs/specs/architecture/MEMORY_AND_STORAGE_BOUNDARIES.md`
