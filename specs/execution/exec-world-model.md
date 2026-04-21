# exec-world-model — Global World Evidence, Claims, KG & Adjudication

> Status: Planung / neuer Owner fuer globale Wissensschichten
> Erstellt: 2026-04-16
> Abhaengigkeiten: [`exec-memory.md`](./exec-memory.md) (Personal Memory), [`exec-context.md`](./exec-context.md) (Runtime-Assembly), [`exec-15-memory-control-ui.md`](./exec-15-memory-control-ui.md) (spaetere Surfaces), [`exec-17-observability-harness-traces.md`](./exec-17-observability-harness-traces.md) (Tracing/Replay), [`exec-18-unified-agent-schema.md`](./exec-18-unified-agent-schema.md) (Persistenz falls noetig)
> Hauptreferenzen:
>   - `memory_kg.md` — aktuelles Zielbild fuer Memory + Context + KG
>   - `main_docs/root/MEMORY_ARCHITECTURE.md` — M2/M4, Self-Baking, Confidence Dampening
>     _(Trading-Project-Doc, aelter als dieser Exec — unser Modell ist weiter)_
>   - `main_docs/root/CONTEXT_ENGINEERING.md` — Retrieval-Policies, Ranking, Merge
>   - `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` — Dual Pipeline, UQ-Gates, GraphRAG
>   - arXiv:2604.11364 (Roynard 2026, peer-reviewed TMLR) — 4-Layer Cognitive Architecture
>     _(Knowledge / Memory / Wisdom / Intelligence — unser Exec folgt diesem Zielbild)_
>   - `_ref/NornicDB` — Global KG Backend-Kandidat (Graph+Vector+Temporal+Bolt, MIT)
>   - `_ref/Researchwatcher/kg-module` — IE-Pipeline Referenz (GLiNER2, ReLiK, FalkorDB/Neo4j)
>   - `trading-project/docs/MEMORY_ARCHITECTURE.md` §6.3 — Fast/Slow-Lane-KG, GraphMERT-Verweis

---

## 0. Warum ein eigenes Exec?

`global world model` ist **nicht** dasselbe wie `memory`.

Es hat eine andere Aufgabe:

- Welt-Evidenz aufnehmen
- Claims extrahieren
- Konflikte und Provenance verwalten
- einen globalen KG / globalen semantischen Access-Layer aufbauen
- bei der Runtime als **Schiedsrichter** zwischen Evidenz, Claims und Verdichtung dienen

Wenn das in `exec-memory` bleibt, vermischen sich:

- personal raw / derived memory
- persoenliche Knowledgebase
- globale Weltquellen
- Claim-/Validator-/Promotion-Logik

Dieses Exec ist deshalb Owner fuer:

1. `Global World Evidence`
2. `Claim Layer`
3. `Global World KG`
4. globale Retrieval-/Adjudication-Regeln

Nicht Owner:

- sessionnahes Personal Memory
- Hindsight-/MemPalace-Read/Write-Pfade
- Prompt-Caching / Compaction
- user-kuratierte Personal Knowledgebase

---

## 1. Zielbild

### Layer A: Global World Evidence

Enthaelt:

- News
- Reports
- Filings
- Webseiten
- Research-Artefakte
- Markt-/Makro-/Eventquellen

Record of truth:

- extrahierter, provenance-markierter Evidenz-Chunk

### Layer B: Claim Layer

Zwischenschicht zwischen Roh-Evidenz und KG:

- `claim_text`
- `claim_type`
- `derived_from_ids`
- `source_quality_prior`
- `entity_link_quality`
- `contradiction_risk`
- `scope`

Warum first-class:

- Roh-Evidenz soll nicht direkt als Weltrelation behandelt werden
- KG soll nicht ungeprueft aus Freitext wachsen
- Promotion / Demotion braucht eine explizite Schicht

### Layer C: Global World KG

Enthaelt:

- `Entity`
- `Event`
- `Asset`
- `Claim`
- `Relation`
- `Source`

Noetige Status:

- `candidate`
- `supported`
- `stable`
- `conflicted`
- `stale`
- `deprecated`

### Layer D: Adjudication / Arbitration

Der KG ist hier nicht nur Speicher, sondern Urteilshilfe:

1. Retrieve
2. Normalize
3. Adjudicate
4. Compose

Harte Regel:

- neuere primaere Evidenz schlaegt aeltere Verdichtung

---

## 2. Write-Pfad

### Betriebsreihenfolge

`source selection -> source onboarding -> fetch/cache/snapshot -> normalize -> evidence -> claim extraction -> validator/adjudication -> kg write`

Wichtige Regel:

- kein direkter Produktionspfad von Rohdownload -> KG

### Global-by-default Artefakte

- News
- Filings
- Marktberichte
- geteilte Research-Quellen
- strukturierte Event-/Makroquellen

### Nicht default global

- Chatturns
- User-Notes
- persoenliche PDFs
- persoenliche Webclips
- agentische Zwischenantworten

---

## 3. Read-Pfad / Runtime-Rolle

`exec-context` bleibt Owner fuer Prompt-/Context-Assembly.

Dieses Exec definiert die **Weltseite** des Read-Pfads:

- welche globalen Claims retrieval-eligible sind
- wie Status / Freshness / Konflikte einfliessen
- wie Evidenz-Join fuer Weltwissen aussieht

### Runtime-Regeln

- Welt-KG nie ohne Status / Zeit / Provenance betrachten
- semantische Treffer nie ueber strukturierte Gegenbelege heben
- `conflicted` / `stale` / `deprecated` muessen in Runtime sichtbar bleiben
- Answer-Time: Claim + Evidenz + Konfliktlage zusammen ausgeben

### Degradation-Flags

Dieses Exec ist Owner fuer globale Flags wie:

- `NO_WORLD_KG`
- `NO_WORLD_EVIDENCE`
- `LOW_WORLD_EVIDENCE_COVERAGE`
- `WORLD_CLAIM_CONFLICT`

`exec-context` ist spaeter Owner dafuer, wie diese Flags in Runtime/Prompt/UI
surfaced werden.

---

## 4. Kernentscheidungen

### 4.1 Graph vs. Vector

Nicht entweder/oder:

- Graph fuer exakte Struktur, Kausalitaet, Status, Promotion
- Vector fuer unscharfen semantischen Einstieg

### 4.2 Graph of Record vs. Access Index

Auch wenn FalkorDB o. ae. beides tragen kann, bleiben die Rollen getrennt:

- Graph of record = Welt-Claims und Relationen
- semantischer Access Index = Retrieval-Einstieg

### 4.3 Confidence / Dampening

Keine unendliche Selbstverstaerkung:

- Confidence-Cap
- staerkeres Downweighting bei Fehlern
- Baseline-Decay
- unterschiedliche Decay-Regeln fuer strukturelle vs. eventnahe Kanten

### 4.4 Self-Baking

Aggregationen aus Episoden / Welt-Evidenz duerfen in stabilere Schichten
uebergehen, aber:

- additiv
- auditierbar
- nicht destruktiv

### 4.5 Roynard 4-Layer Mapping (arXiv:2604.11364, TMLR 2026)

| Roynard Layer | Funktion | Unser Aequivalent |
|---|---|---|
| **Knowledge** | stabil, geteilt, weltweit | Slow Lane KG |
| **Memory** | episodisch, temporal, personell | Fast Lane KG + Personal KG |
| **Wisdom** | evidence-gated, validiert | GraphMERT-Validierungsschicht (Slow Lane) |
| **Intelligence** | ephemer, session-lokal | Agent-Context / exec-context |

Konsequenz: unser Exec ist Owner fuer Knowledge + Memory (weltliche Haelfte) und
die Wisdom-Gate-Logik (Adjudikation). Intelligence bleibt bei exec-context.

### 4.6 KG Tiering: Fast Lane / Slow Lane

Zwei operative Lanes, kein einheitlicher globaler KG-Monolith.

#### Fast Lane — temporale Ereignisdaten

| Themenbereich | Quellen (Beispiele) |
|---|---|
| Geopolitische Ereignisse | ACLED, GDELT, Reuters, AP |
| Live-Marktdaten | Boersen-Feeds, Options-Flow |
| Nachrichten / Breaking | News-API, RSS-Aggregatoren |
| Sanktionen / Regulierung | OFAC, EUR-Lex, BIS |
| Wirtschaftsindikatoren | FRED, Eurostat, Bloomberg |
| Ernaennungen / Personalwechsel | Cabinet/Board-Change-Feeds |

Regeln:
- kurze TTL (Stunden bis wenige Tage)
- Temporal Weight Decay (Kalman-Filter-Ansatz wie in NornicDB vorhanden)
- **kein GraphMERT** — Latenz und Instabilitaet nicht vereinbar
- Status `candidate -> supported -> stale` im Schnelltakt

#### Slow Lane — Strukturwissen

| Themenbereich | Quellen (Beispiele) |
|---|---|
| Game-Theory / Stratagemen | Fachliteratur, kuratierte Wissensbasis |
| Strukturelle Geopolitik | Regionale Machtmuster, Allianz-Cluster |
| Sektor-Relationen | Lieferketten, Abhaengigkeiten, Substitution |
| Makro-Regime-Merkmale | Inflationsregimes, Rate-Cycles, Krisenmuster |
| Selective Research | Zentralbank-Papiere (Fed, ECB, BIS), Biotech-Trials (wenn Trading-relevant), Quant-Finance-Papers |

Regeln:
- lange TTL (Wochen bis Monate)
- Confidence Decay (nicht linear: strukturelle Kanten langsamer als Event-Kanten)
- **GraphMERT als Batch-Validator** — Triples werden nach Aufnahme async validiert
- Status `candidate -> supported -> stable`; Downgrade via Contradiction Detection

#### Personal KG

- Overlay ueber Fast+Slow Lane — kein eigener Truth-Store
- user-kuratierte Annotationen, Highlights, eigene Hypothesen
- Owner: exec-personal-kb (nicht dieses Exec)

### 4.7 IE Pipeline

Standardpfad fuer globale Quellen (Fast Lane ohne GraphMERT, Slow Lane mit):

Klassisches 4-Schritt-Modell (konzeptuell, Anpassungen vorbehalten):

```
source selection → fetch/normalize → IE (Entity + Relation) → KG write
```

Detaillierte Layerstruktur (Researchwatcher-Referenzimpl.):

```
Dokument / Event-Feed
    │
    ▼
L0  Heuristic Layer     → Metadaten-Entities + strukturierte Relationen (immer aktiv)
    │
    ▼
L1  ReLiK EL            → Freetext-Entities mit KB-Links (Wikipedia/Wikidata)
    │
L2  GLiNER NER          → Zero-Shot-Schema-Entities (alternativ/ergaenzend zu L1)
    │
    ▼
L3  GLiREL RE           → Zero-Shot-Relationsextraktion auf ML-Entities mit Char-Offsets
    │
    ▼
L4  Post-Processing     → Merge, Deduplizierung, Normalisierung auf KGSchema
    │
    ▼
L5  Claim Reification   → High-Confidence-Relationen → ExtractedClaim-Nodes
                          (subject / predicate / object / confidence / status=asserted)
    │
    ▼ (nur Slow Lane)
L6  GraphMERT Validation → Tail-Predictor (head + relation → tail), Score-Filter
                           validiert Plausibilitaet, demotiert unwahrscheinliche Triples
```

Empfohlener Backend-Stack (`StructuredExtractor`, `relik_glirel`):
- ReLiK (L1) + GLiREL (L3) — maximale Qualitaet fuer strukturierte Domains
- Fastino GLiNER2 (L1+L3 in einem Modell) — schneller, fuer High-Throughput

GraphMERT-Details (L6):
- RoBERTa-Backbone (~80M Parameter), TMLR-peer-reviewed Maerz 2026
- kein oeffentliches Community-Checkpoint fuer Financial/Geopolitical Domain
- Deployment-Plan: Fine-Tune auf UMLS-/Wikidata5M-Basis mit domain-spezifischen Negativen
- Batch-Modus: laeuft nicht inline, sondern als async Refinement-Job

Referenz-Impl: `_ref/Researchwatcher/kg-module`
- `StructuredExtractor` — L0-L5 implementiert (`extraction.py:137`)
- `FalkorIngestor` — Graph-Write (Entities → Relations → Chunks → Reified Claims, `falkordb/ingest.py:22`)
- `Neo4jIngestor` — analoges Backend fuer Neo4j (`neo4j/ingest.py`)
- `KGEngine._reify_and_persist_claims()` — orchestriert L5-Persistenz (`engine.py`)
- `PIIGuardService` — PII-Filter vor Ingest (`ragbits_custom/basic/guardrails/pii.py`)
- L6 GraphMERT — noch **nicht implementiert** (offene Aufgabe)

**Wichtige Einschraenkung:** Researchwatcher kg-module ist aktuell auf Paper-Ingest
ausgerichtet (Paper-Schema, arxiv-IDs als source_id, akademische Relationstypen).

**Wir muessen weiter denken als nur fuer Papers.**

Unser Zielbild ist ein Global World KG fuer Trading / Geopolitik / Makro — das
bedeutet vollkommen andere Quelltypen, Entities und Relationen. Die IE-Pipeline
aus Researchwatcher ist eine wertvolle Referenz fuer die Extraktionslogik, aber
das Schema und die Source-Abstraktion muessen von Grund auf fuer unseren Domain
neu gedacht werden:

- **neue Entity-Typen:** Event, Asset, Country, Organization, Regulation, Indicator, Person (Amt)
- **neue Relationstypen:** SANCTIONS, AFFECTS\_MARKET, CAUSES\_EVENT, MEMBER\_OF, REPLACES, ISSUED\_BY, CORRELATED\_WITH
- **neue Source-Types:** news feed, regulatory filing, market data, geopolitical event, central bank statement, earnings report
- **TTL / Decay-Felder** fuer Fast-Lane-Entities (nicht im Paper-Schema vorhanden)
- **Event-Temporalitaet:** Start/End-Zeitstempel, Ongoing-Flag — Papers haben das nicht
- **Provenance-Tiefe:** Quellenglaubwuerdigkeit, Region-Bias, Agentur vs. Primaerquelle

### 4.8 NornicDB — Global KG Backend

NornicDB (`_ref/NornicDB`, MIT) ist der primaere Backend-Kandidat fuer den Global World KG.

Relevante Eigenschaften:
- **Bolt-Protokoll** (Port 7687) + Cypher — drop-in kompatibel zu Neo4j/FalkorDB/Kuzu
- **Temporal Weight Decay** — Kalman-Filter-basiert, native fuer Fast-Lane-TTL
- **Vector Index** — semantischer Einstieg integriert (kein separater Store noetig)
- **MVCC** — konsistente Reads unter parallelen Writes
- **Heimdall** — LLM-Guardian (Anomalie-Detektion, Memory Curation) — optional, CGo
- **BadgerDB** — LSM+Value-Log Storage, performant fuer hohe Write-Rates
- **MIT-Lizenz** — keine Vendor-Lock-Probleme

Anbindung an matrix:
- `python-backend/memory_engine/kg_store.py` — `KGStore` Protocol (Z. 88–96)
- geplante Impl: `NornicDBKGStore` via `neo4j` Python Driver (Bolt/7687)
- Cypher-Kompatibilitaet erlaubt spaeteres Wechseln zu FalkorDB/Kuzu ohne API-Aenderung

Einschraenkung: `executor.go` (Query-Planung) noch in frueherer Entwicklungsphase —
komplexe Joins / Multi-Hop bis zur Produktionsreife evaluieren.

### 4.9 Promotion Gate — Offene Forschungsfrage

Der automatische Transfer Fast Lane → Slow Lane ist **kein geloestes Problem**.

Bekannte Kriterien aus Literatur:
- Multi-Source-Corroboration (>= N unabhaengige Quellen bestaetigen Claim)
- Zeitspanne (Claim haelt sich ueber T ohne Widerspruch)
- Contradiction Absence (keine konfligierenden Evidenzen in Fenster W)
- Confidence-Score ueber Schwelle θ nach GraphMERT-Validation

Offene Fragen:
- Wie gross N, T, W, θ in unserem Domain (Financial/Geopolitical)?
- Automatisch vs. kuratorisch — wo ist die Grenze fuer autonome Promotion?
- Wie Promotion rueckgaengig machen (Demotion / Supersession)?
- Wie Promotion-Entscheidung auditierbar machen?

Referenzen fuer Brainstorming:
- **AriGraph** (IJCAI-2025) — episodic-to-semantic transfer via recurrence
- **Zep / Graphiti** — Validity Windows, temporal scoping fuer episodic facts
- **MAGMA 2026** — Lambda-Architektur auf KGs (Batch + Speed Layer)
- **Synapse 2026** — Multi-Lane KG mit automatischen Promotion-Heuristiken

Naechster Schritt: Brainstorming-Session mit sota-contrarian vor Implementation.

#### [BRAINSTORM — keine Anweisung] User-/Agent-Interaktion als Promotions-Signal?

_Das Folgende ist ein offener Gedanke, kein Design-Entscheid._

Frage: Sollten User-Gespraeche oder Agent-Queries mitbestimmen, was von Fast nach
Slow befoerdert wird?

Argument dafuer (kollektives Signal):
- Viele unabhaengige Agents/User referenzieren denselben Claim konsistent
  → koennte als schwaches Korroborationsindiz zaehlen
- Query-Frequenz als Relevanz-Signal: was oft gebraucht wird, verdient stabilen Status

Argument dagegen (und wahrscheinlich staerker):
- Global KG repraesentiert Weltwahrheit, nicht Nutzerinteresse
- haeufig gefragt ≠ faktisch stabil (Manipulation, Selection Bias, Noise)
- Roynard Wisdom-Layer ist explizit *evidence-gated* — epistemischer, kein sozialer Prozess
- ein aktiver User / Agent koennte Signal unverhältnismaessig dominieren

Wahrscheinliche Trennung:
- **Personal KG**: User-Interaktion darf stark gewichtet werden (persoenliches Interesse,
  eigene Hypothesen, Annotation)
- **Global KG**: User/Agent-Signal maximal als tiebreaker oder Relevanz-Indikator,
  nie als primaerer Promotion-Trigger — Primaer bleibt multi-source corroboration +
  Zeitspanne + GraphMERT

Offen: ob und wie ein kollektives Signal (nicht ein einzelner User) sauber
definierbar ist, ohne Manipulation-Vektoren aufzumachen.

---

## 5. Implementation-Checkliste

### Phase A — Begriffe / Vertraege

- [ ] `Global World Evidence`, `Claim Layer`, `Global World KG` als getrennte Zielschichten in Code/Docs festziehen
- [ ] `source_scope` / `source_type` / `source_ref` / `source_quality_prior` fuer globale Quellen verbindlich machen
- [ ] Claim-Statusmaschine (`candidate` ... `deprecated`) fuer Weltseite definieren
- [ ] Artefakt-Klassifikation `global by default` vs `personal by default` festziehen

### Phase B — Storage / Schema

- [ ] Ziel-Topologie fuer globalen Evidence-Store festlegen
- [ ] Ziel-Topologie fuer globalen KG festlegen
- [ ] Claim-Objekte persistent modellieren
- [ ] globalen semantischen Index / Vector-Zugriff modellieren
- [ ] klare Namespace-/Schema-Trennung zu Personal Memory sicherstellen

### Phase C — Extraction / Validation

- [ ] Claim Extraction Worker / Pipeline definieren
- [ ] Entity Linking fuer globale Claims vertraglich festziehen
- [ ] Contradiction Detection als eigene Stufe einfuehren
- [ ] Promotion-/Demotion-Engine definieren
- [ ] Confidence Dampening / Decay operationalisieren

### Phase D — Adjudication / Runtime

- [ ] `Retrieve -> Normalize -> Adjudicate -> Compose` als produktive World-Query-Pipeline festziehen
- [ ] Welt-spezifische Degradation-Flags definieren
- [ ] Evidence-Coverage fuer World Queries definieren
- [ ] Query-time Merge-Regeln fuer KG + Evidence + Vector festziehen

### Phase E — Observability / Governance

- [ ] Claim-Promotion und Demotion im Audit/Tracing sichtbar machen
- [ ] Replay / Diff fuer Welt-Claims ermoeglichen
- [ ] Verify Gates fuer Konflikte / Staleness / Coverage definieren
- [ ] Deletion / Invalidation / Supersession-Pfade dokumentieren

### Phase F — UI / Ops

- [ ] spaetere World-Model-Surfaces mit `exec-15` abstimmen
- [ ] Conflict-/Status-Visualisierung planen
- [ ] World-Claim-Detailansicht mit Provenance und Gegenbelegen planen

---

## 6. Verify Gates

- [ ] Eine globale Quelle kann als `evidence` ingestiert werden, ohne sofort KG-Wahrheit zu werden
- [ ] Ein Claim kann `candidate -> supported -> stable` durchlaufen
- [ ] Ein Gegenbeleg setzt sichtbar `status=conflicted`
- [ ] Ein veralteter Claim kann `stale` werden ohne aus dem Audit zu verschwinden
- [ ] Runtime fuer Weltwissen liefert Claim + Evidenz + Status statt nackter Behauptung
- [ ] Degradation-Flags fuer fehlende Weltschichten sind sichtbar

---

## 7. Querverweise

- Personal Memory: [`exec-memory.md`](./exec-memory.md)
- Runtime / Context / Prompt: [`exec-context.md`](./exec-context.md)
- Personal Knowledgebase: [`exec-personal-kb.md`](./exec-personal-kb.md)
- UI / Control Surfaces: [`exec-15-memory-control-ui.md`](./exec-15-memory-control-ui.md)
- Schema / Persistenz: [`exec-18-unified-agent-schema.md`](./exec-18-unified-agent-schema.md)
- Tracing / Replay / Harness: [`exec-17-observability-harness-traces.md`](./exec-17-observability-harness-traces.md), [`exec-harness.md`](./exec-harness.md)

---

## 8. Offene Punkte

1. Graph-DB als eigener Store oder zuerst relationale/JSON-hybride Weltseite?
2. Wie viel des globalen Vector-Zugriffs kann spaeter in den Graph-Store absorbiert werden?
3. Welche Promotion-Regeln sind fuer Welt-Claims strenger als fuer persoenliche Observations?
4. Welche Weltquellen duerfen automatisch ingestiert werden und welche brauchen kuratierten Onboarding-Pfad?
5. Welche Rolle uebernimmt der globale KG spaeter gegenueber Frontend-/Merge-Layern genau?
