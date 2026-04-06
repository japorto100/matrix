# UNSTRUCTURED INGESTION UIL

> **Stand:** 16. Maerz 2026  
> **Zweck:** Key Contracts und Architekturgrenze fuer die Unified Ingestion Layer (UIL)
> fuer unstrukturierte Datenquellen.
> **Source-of-Truth-Rolle:** Autoritativ fuer UIL-Grenzkontrakte und Ownership-Regeln.
> Vollstaendige Pipeline-Beschreibung inkl. Konfiguration, Klassifizierung und
> Training-Loop in `docs/UNIFIED_INGESTION_LAYER.md`.

---

## 1. UIL-Scope und Abgrenzung

### Was die UIL ist

Die UIL verarbeitet **unstrukturierte** Quellen (YouTube-Transcripts, Reddit, Copy/Paste,
Chat-Exports, Paywall-Artikel) die nicht als tabellarische API-Daten vorliegen und erst
durch LLM/NLP-Verarbeitung strukturiert und klassifiziert werden muessen.

### Was die UIL NICHT ist

| Concern | Zustaendig |
|:--------|:-----------|
| Strukturierte OHLCV/Macro-Daten | Go Data Router |
| News-Headlines von APIs (NewsData, GNews, GDELT) | Go News Fetcher |
| Indikator-Berechnung | Python + Rust/PyO3 |
| GeoMap Event-Persistenz und Timeline | GeoMap Engine |

**Kernprinzip:** UIL produziert Candidates — nie finale Daten. Canonical-Truth-Mutationen
laufen nur ueber Claim/Evidence/Review-Gates.

---

## 2. Sprachgrenzen-Vertrag (verbindlich)

| Sprache | UIL-Verantwortung | Regel |
|:--------|:------------------|:------|
| **Go** | Externes Fetching: YouTube-Transcripts, Reddit, RSS-Feed-Monitoring | Einziger Ort fuer externe Datenbeschaffung |
| **Python** | Verarbeitung: LLM-Summarization, Entity Extraction, Classification, Confidence Scoring, Dedup | Python holt keine Daten selbst — alle Rohdaten kommen von Go |
| **Next.js/TS** | User-Input: Copy/Paste, Chat-Import, Paywall-Snippets; Review-UI | User-Input ist kein externes Fetching |
| **Rust** | Nicht in UIL v1; spaeter: Dedup-Hashing, Similarity in rust-core | Erst bei messbarem Performance-Bedarf |

---

## 3. Gemeinsames Pipeline-Muster

```
1. Beschaffung     → Go (auto) oder Next.js (User-Input)
2. LLM-Verarbeitung → Python (Summarize, Extract, Classify, Score)
3. Dedup/Hash       → Python (SHA256, Similarity)
4. Review-Queue     → Frontend (Human-in-the-Loop)
5. Routing          → Ziel-Subsystem (GeoMap, Macro, Trading, Research)
```

---

## 4. Source-Confidence und Canonicalization-Gate

- Open-Web-/unstrukturierte Quellen sind Discovery- und Gap-Fill-Layer.
- UIL darf keine direkte Canonical-Truth-Mutation ausloesen.
- Promotion in stabilere Schichten erfolgt nur ueber Claim/Evidence/Review-Gates.
- `source_confidence` wird explizit mitgefuehrt (nicht implizit aus Quelle erraten).

---

## 5. IST-Status (16.03.2026)

| Bereich | Status |
|:--------|:-------|
| Go UIL-Route + Python Preprocessor Basis | Partial produktiv |
| PDF-Ingest (Extraktion) | Produktiv |
| PDF Post-NLP-Phase | Partial |
| Audio (Whisper-Pipeline) | Scaffold; kein Prod-Load |
| YouTube-Transcript Connector | Geplant; Connector-Stub vorhanden |
| Reddit-Migration Go | Geplant; aktuell noch TS-seitig |
| Multimodal | Blueprint-Phase |
| NATS JetStream Async Queue (UIL-Backbone) | Offen (Aladdin-Gap) |
| Review-UI (Human-in-the-Loop) | Konzept; kein produktiver UI-Block |

---

## 6. Konfigurierte Source-Kanaele (persistent, per Flag enable/disable)

**YouTube-Kanaele:** Euro Dollar University, Marc Friedrich, Lyn Alden, George Gammon,
Money & Macro, Patrick Boyle, Steve Keen, Richard J Murphy, Jack Mallers u.a.

**Reddit-Subreddits:** r/StockMarket, r/investing, r/algotrading, r/Commodities, r/quant

**Blog-RSS:** Tax Research UK, fx:macro, MacroAnchor, Wolf Street

Vollstaendige Liste und Konfigurationsregeln: `docs/UNIFIED_INGESTION_LAYER.md` Sek. 2.1-2.3.

---

## 7. Event-Backbone (offener Gap)

**Aladdin-Gap:** Async Job-Queue, Replay, Fanout fuer UIL-Candidates.
Ziel-Stack: NATS JetStream. Prioritaet: Hoch.
Verknuepft mit: `docs/specs/architecture/ORCHESTRATION_AND_MESSAGING.md`.

---

## 8. Querverweise

- `docs/UNIFIED_INGESTION_LAYER.md` (vollstaendige Spec)
- `docs/specs/UIL_ROUTE_MATRIX.md`
- `docs/specs/data/DATA_ARCHITECTURE.md`
- `docs/specs/architecture/ORCHESTRATION_AND_MESSAGING.md`
- `docs/specs/data/SOURCE_STATUS.md`
