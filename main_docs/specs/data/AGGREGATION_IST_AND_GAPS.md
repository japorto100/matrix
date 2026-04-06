# AGGREGATION IST AND GAPS

> **Stand:** 16. Maerz 2026  
> **Zweck:** Kompakter IST-Status der Datenaggregation basierend auf Code-Verifikation,
> inklusive bekannter Gaps und offener Pfade.
> **Source-of-Truth-Rolle:** Aggregierter IST-Snapshot. Vollstaendiger Report in
> `docs/DATA_AGGREGATION_Master.md` (Bridge/Archiv).

---

## 1. Aggregations-IST (Stand 16.03.2026)

### 1.1 Produktiv und verifiziert

| Bereich | Komponente | Notizen |
|:--------|:-----------|:--------|
| Market/Macro-Routing | Go RoutedMacroClient, QuoteClient | Prefix-/Provider-Logik aktiv |
| OHLCV Streaming | Go SSE-Handler -> Valkey -> Next.js | Basis-Streaming-Pfad steht |
| News / Headlines | Go news-connector, RSS, GDELT | Normalisierer vorhanden |
| Geopol / Sanctions | ACLED, CrisisWatch, UN-Sanctions Adapters | Adapters existent |
| Portfolio / GCT | Go GCT-Modul; Paper-Trading lokal | GCT via go module replace |
| Indicator/Compute | Python + Rust PyO3 cdylib | redb fuer Batch-Compute-Cache |
| UIL Ingest | Go UIL-Route + Python Preprocessor | PDF/Audio Scaffold, NLP-Partial |
| Source Metadata | SQLite source_snapshot_metadata | Bootstrap-Tabelle produktiv |

### 1.2 Scaffold / Partial

| Bereich | Status | Offen |
|:--------|:-------|:------|
| agent-service WebSocket | Scaffold/Echo-Endpunkt | echte Routing-Logik fehlt |
| Agent-Chat Next->Go | Route-Stub, kein vollstaendiger Handler | Contract-Drift |
| Portfolio-Order-Route | Mux-Route fehlt; Middleware referenziert | Contract-Drift |
| Vector/pgvector | Pfad definiert; Ingestion-Pipeline partial | Einheitliche Upsert-Logik offen |
| FalkorDB Linking | Modul vorhanden; Prod-Load-Tests fehlen | Scale-Validation offen |
| Semantic Cache | Valkey Embeddings-Cache geplant | noch nicht produktiv |

---

## 2. Bekannte Gaps

### 2.1 Contract-Drifts (kritisch)

- `/api/v1/agent/chat` -- Next erwartet; Go nicht vollstaendig registriert
- `/api/v1/portfolio/order` -- Middleware referenziert; Mux-Route fehlt
- Capability-Enforcement -- teils fail-open / Feature-Flag-gated bei mutations

### 2.2 Provider-Drift

| Provider | IST | Soll |
|:---------|:----|:-----|
| Alpha Vantage | Backup-Fallback | nutzbar aber nicht Primary |
| Tiingo | Pfad vorhanden | fehlt in primarer Routing-Matrix |
| Yahoo Finance | Community-Adapter | kein SLA; nicht fuer Prod-Primary |
| SDMX/ECB | Aktiv | Zeitreihenparsing robust |
| OECD | Aktiv | einige Endpoints timeout-sensitiv |

### 2.3 UIL-Gaps

- PDF-Ingest: Extraktion produktiv; Post-NLP-Phase partial
- Audio: Whisper-Pipeline Scaffold; kein Prod-Load
- Multimodal: Blueprint-Phase

---

## 3. Prioritaet der Gap-Schliessungen

| Prio | Aktion | Owner |
|:-----|:-------|:------|
| P0 | Agent-Chat Contract schliessen | Go Gateway + BFF |
| P0 | Portfolio-Order Mux-Route registrieren | Go Gateway |
| P0 | Capability-Enforcement haerten (mutation paths) | Go Gateway |
| P1 | Provider-Routing-Matrix aktualisieren (Tiingo, Alpha Vantage) | Go Connectors |
| P1 | Vector-Upsert-Pipeline normalisieren | Python Vector Service |
| P2 | UIL-Audio produktiv machen | Python UIL |
| P2 | Semantic Cache aktivieren | Go/Python |

---

## 4. Querverweise

- `docs/DATA_AGGREGATION_Master.md` (Bridge/Archiv, vollstaendiger Code-Verifikations-Report)
- `docs/specs/data/DATA_ARCHITECTURE.md`
- `docs/specs/data/SOURCE_STATUS.md`
- `docs/specs/SYSTEM_STATE.md`
- `docs/specs/API_CONTRACTS.md`
