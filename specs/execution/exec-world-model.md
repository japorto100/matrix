# exec-world-model — Global World Evidence, Claims, KG & Adjudication

> Status: Planung / neuer Owner fuer globale Wissensschichten
> Erstellt: 2026-04-16
> Abhaengigkeiten: [`exec-memory.md`](./exec-memory.md) (Personal Memory), [`exec-context.md`](./exec-context.md) (Runtime-Assembly), [`exec-15-memory-control-ui.md`](./exec-15-memory-control-ui.md) (spaetere Surfaces), [`exec-17-observability-harness-traces.md`](./exec-17-observability-harness-traces.md) (Tracing/Replay), [`exec-18-unified-agent-schema.md`](./exec-18-unified-agent-schema.md) (Persistenz falls noetig)
> Hauptreferenzen:
>   - `memory_kg.md` — aktuelles Zielbild fuer Memory + Context + KG
>   - `main_docs/root/MEMORY_ARCHITECTURE.md` — M2/M4, Self-Baking, Confidence Dampening
>   - `main_docs/root/CONTEXT_ENGINEERING.md` — Retrieval-Policies, Ranking, Merge
>   - `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` — Dual Pipeline, UQ-Gates, GraphRAG

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
