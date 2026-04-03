# PhantomTide — Reverse Engineering & Bewertung

> Analysiert am 02.04.2026 | Repo: https://github.com/tg12/phantomtide | Closed Source (Docs/Feedback only)

## Was ist PhantomTide?

Cross-Domain-Geospatial-Intelligence-Plattform fuer maritime und Airspace OSINT. Closed-Source — das GitHub-Repo ist nur Docs/Feedback-Tracker, kein Code.

**Kernthese:** Der wertvollste Signal ist nicht eine einzelne Datenquelle, sondern die Konvergenz und Widersprueche zwischen mehreren offenen Quellen gleichzeitig.

## Bewertung

| Dimension | Score | Begruendung |
|---|---|---|
| Technisches Konzept | 9/10 | Konvergenz-ueber-Alerts ist der richtige Ansatz fuer Multi-Source OSINT |
| Engineering-Qualitaet | 8/10 | Postmortems zeigen solide Backend-Disziplin |
| Dokumentation | 9/10 | Aussergewoehnlich detailliert fuer ein Solo-Projekt |
| Community | 2/10 | 12 Tage alt, 21 Stars, 1 Issue |
| Openness | 2/10 | Closed Source, keine Lizenz |
| Operational Maturity | 5/10 | 2 Outages in 12 Tagen, beide kompetent gefixt |
| **Gesamt** | **7/10** | |

---

## Datenquellen & Aggregation (Reverse-Engineered)

### Primaere Feeds

| Quelle | Datentyp | Frequenz | Qualitaet |
|---|---|---|---|
| **AIS** | Schiffspositionen | Real-time Stream | Limitiert (ehrlich kommuniziert) |
| **ADS-B** (OpenSky) | Flugzeugpositionen | Real-time | Oeffentlich, gut |
| **NOTAMs** | Luftfahrt-Notices | Periodisch | Offiziell, zuverlaessig |
| **VIIRS** | Thermal-Anomalie-Satellitendaten | ~12h Latenz | NASA, zuverlaessig |
| **NOAA DART** | Tiefsee-Druckbojen | Real-time | Offiziell, zuverlaessig |
| **GPS/GNSS Disruption** (GUIDE) | Stoerungsberichte | Event-basiert | Community-reported |
| **Open-Meteo** | Ozean-/Wind-Daten | Periodisch | Frei, zuverlaessig |
| **Space Weather** | Geomagnetische Indizes | Periodisch | NOAA/SWPC |
| **FleetLeaks** | Sanktionierte Schiffslisten | Aktualisiert | Investigativ |
| **TankerTrackers** | Risikozonen-Polygone | Aktualisiert | Investigativ |

### Statische Referenz-Layer

| Layer | Beschreibung |
|---|---|
| EEZ-Grenzen | Exclusive Economic Zones |
| Unterseekabel | Submarine Cable Routes |
| Schifffahrtsrouten | Major Shipping Lanes |
| Vessel Routing Measures | IMO TSS/ATBA |
| Exploration Areas | Oel/Gas Explorationsgebiete |
| Energie-/Datacenter-Infrastruktur | Kritische Infrastruktur |
| Strategische Chokepoints | Hormuz, Bab-el-Mandeb, Suez, Malakka |

---

## Dataflow-Architektur (Reverse-Engineered aus Postmortems)

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA INGESTION                          │
│                                                             │
│  AIS Stream ──┐                                             │
│  ADS-B Feed ──┤                                             │
│  NOTAMs ──────┤──→ [APScheduler Jobs] ──→ [Redis Sorted Sets]
│  VIIRS ───────┤         (FastAPI)           (Hot State)     │
│  DART ────────┤                                             │
│  GPS/GNSS ────┘                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING PIPELINE                       │
│                                                             │
│  1. JSON Materialization (Redis → Python Objects)            │
│     ⚠️ 70x Memory Inflation (28MB JSON → 2GB in-process)    │
│     Fix: __slots__ Dataclasses + Streaming Hydration         │
│                                                             │
│  2. Spatial Enrichment                                       │
│     - GeoJSON Reference Layer Loading                        │
│     - Spatial Index Construction (Bottleneck: CPU-bound)     │
│     ⚠️ Hot Path: bulk GeoJSON → maritime context → ref layer │
│     Fix: Cached spatial indices, atomic temp-file writes     │
│                                                             │
│  3. Entity Correlation                                       │
│     - AIS ID → Vessel Profile                                │
│     - Vessel → Sanktionsliste (FleetLeaks)                   │
│     - Position → Risikozonen (TankerTrackers Polygone)       │
│     - Position → Infrastruktur-Proximity                     │
│                                                             │
│  4. Convergence Scoring                                      │
│     - source_confidence: Zuverlaessigkeit der Datenquelle    │
│     - quality_score: Datenqualitaet des einzelnen Datenpunkts│
│     - hypothesis.confidence: Staerke einer Einzelhypothese   │
│     - convergence.score: Multi-Source-Konvergenz             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    ANALYTICAL STORAGE                        │
│                                                             │
│  [ClickHouse]                                                │
│  - Batch Inserts from Redis zscan_iter                       │
│  - Schema Migrations                                         │
│  - Historical Query Layer                                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION                              │
│                                                             │
│  [FastAPI + uvicorn (single worker)]                         │
│  - GeoJSON API Endpoints                                     │
│  - Map Rendering (Leaflet/MapLibre GL vermutlich)            │
│  - Proximity Query UI                                        │
│  - Layer Toggle Controls                                     │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack (aus Postmortems erschlossen, hohe Konfidenz)

| Komponente | Technologie | Evidenz |
|---|---|---|
| Web Framework | FastAPI | OOM Postmortem direkt benannt |
| ASGI Server | uvicorn (single-worker) | OOM Postmortem |
| Hot State | Redis (Sorted Sets) | OOM Postmortem, exakte Commands |
| Analytics | ClickHouse | Direkt benannt, Schema-Migrations |
| Scheduler | APScheduler | OOM Postmortem |
| Profiling | py-spy | CPU Outage Postmortem |
| Container | Docker | docker-compose Commands in Postmortems |
| I/O | core/cache_io.py | v1.25.0 Changelog |

---

## Convergence Scoring — Deep Dive

Das Herzsueck der Plattform. 4 separate Scoring-Konzepte:

### 1. Source Confidence
Wie zuverlaessig ist die Datenquelle generell?
- AIS: Mittel (manipulierbar, lueckenhaft)
- VIIRS Satellite: Hoch (physikalisch basiert)
- FleetLeaks: Mittel-Hoch (investigativ, aber nicht offiziell)

### 2. Quality Score
Wie gut ist dieser spezifische Datenpunkt?
- AIS Position mit gueltigem MMSI, normalem Speed: Hoch
- AIS Position mit verdaechtigem Heading-Sprung: Niedrig
- NOTAM mit vollstaendigen Koordinaten: Hoch

### 3. Hypothesis Confidence
Wie stark ist eine Einzelhypothese?
- "Vessel X hat AIS abgeschaltet" (AIS Gap > 6h in bekanntem Korridor): Mittel
- "Vessel X ist in Sanktions-Risikozonen" (Position innerhalb TankerTrackers Polygon): Hoch

### 4. Convergence Score (das Alleinstellungsmerkmal)
Wo konvergieren mehrere unabhaengige schwache Signale?
- AIS Gap + VIIRS Thermal Anomalie + Proximity zu Sanctioned Port → Starke Konvergenz
- GPS Disruption + NOTAM + Military ADS-B Activity → Starke Konvergenz
- Einzelnes AIS Gap ohne weitere Signale → Schwache Konvergenz

### Scoring-Formel (hypothetisch, basierend auf Beschreibungen)

```
convergence_score = weighted_sum(
    for each signal:
        signal.hypothesis_confidence 
        * signal.source_confidence 
        * signal.quality_score
        * independence_factor(signal, other_signals)
) / normalization_factor

Wobei independence_factor > 1 wenn Signale aus unabhaengigen Quellen
und independence_factor < 1 wenn Signale korreliert sind
```

**Entscheidend:** Unabhaengige Quellen erhoehen den Score ueberproportional. Korrelierte Quellen (z.B. zwei AIS-Feeds vom gleichen Anbieter) werden heruntergewichtet.

---

## Was koennen wir fuer unser Geopolitik-KG mitnehmen?

### 1. Multi-Source Convergence Scoring
Die 4-stufige Scoring-Architektur (Source → Quality → Hypothesis → Convergence) ist direkt uebertragbar auf geopolitische Informationen:
- News-Artikel von Reuters vs. Telegram-Kanal → unterschiedliche Source Confidence
- Bestaetigung durch 3 unabhaengige Quellen → hoher Convergence Score

### 2. Temporal + Spatial Correlation
Nicht nur "was passt thematisch" sondern "was passt zeitlich UND raeumlich":
- Truppenbewegung (Satellit) + Mobilfunk-Blackout (OSINT) + Flugverbot (NOTAM) → Konvergenz

### 3. Redis als Hot State + ClickHouse als Analytics
Separation of Concerns: Redis fuer schnelle In-Memory-Korrelation, ClickHouse fuer historische Analysen. Fuer uns: Redis/FalkorDB fuer Live-KG, kuzu/ClickHouse fuer Analytics.

### 4. Atomic Cache Writes
`temp-file + rename` Pattern fuer korruptionsfreie Cache-Updates unter Last.

### 5. Streaming Hydration statt Bulk-Load
`zscan_iter` + Batch-Inserts statt komplettes JSON materialisieren. Vermeidet den 70x Memory-Inflation-Bug.

### 6. Ehrliche Uncertainty-Kommunikation
PhantomTide sagt explizit wo Scoring-Weights noch in Entwicklung sind. Fuer ein KG-System: Confidence-Scores immer mitfuehren, nie falsche Praezision vortaeuschen.

---

## Links

- Repo: https://github.com/tg12/phantomtide
- Entwickler: James Sawyer (tg12), SRE
- Status: Closed Source, 21 Stars, aktive Entwicklung (v1.36.0)
- Postmortems: Im Repo unter docs/ (extrem lesenswert)
