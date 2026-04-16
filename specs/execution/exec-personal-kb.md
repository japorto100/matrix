# exec-personal-kb — Personal Knowledgebase, Capture, Curation & Retrieval

> Status: Planung / neuer Owner fuer user-kuratierte Wissensartefakte
> Erstellt: 2026-04-16
> Abhaengigkeiten: [`exec-memory.md`](./exec-memory.md) (Personal Memory), [`exec-context.md`](./exec-context.md) (Runtime-Assembly), [`exec-15-memory-control-ui.md`](./exec-15-memory-control-ui.md) (Surfaces), [`exec-17-observability-harness-traces.md`](./exec-17-observability-harness-traces.md) (Tracing), [`exec-18-unified-agent-schema.md`](./exec-18-unified-agent-schema.md) (Persistenz falls noetig)
> Hauptreferenzen:
>   - `memory_kg.md` — aktuelles Zielbild fuer Personal Knowledgebase
>   - `main_docs/root/CONTEXT_ENGINEERING.md` — Retrieval-/Merge-Policies
>   - `main_docs/root/MEMORY_ARCHITECTURE.md` — User-KG / Privacy / Offline-Muster
>   - `https://www.recall.it/` + `https://docs.getrecall.ai/getting-started/2-add-content`
>   - `https://github.com/TriliumNext/Trilium` + `https://docs.triliumnotes.org/user-guide/setup/web-clipper`

---

## 0. Warum ein eigenes Exec?

`personal knowledgebase` ist weder:

- `personal memory`
- noch `global world model`
- noch bloss eine UI-Variante von bestehendem Recall

Es ist eine eigene Schicht:

- bewusst gespeicherte Artefakte
- explizite User-Curation
- persoenliche Langzeit-Notizen
- Webclips, Bookmarks, PDFs, YouTube/Podcast mit Transcript

Wenn das in `exec-memory` bleibt, wird alles wieder in einen Memory-Topf gezogen.

Dieses Exec ist Owner fuer:

1. Capture / Save / Import
2. KB-Inbox / Library / Note-Layer
3. KB-spezifische Retrieval-Regeln
4. KB-spezifische UI-/Curation-Patterns

Nicht Owner:

- Session-Memory / agentische Episoden
- globale Weltquellen
- Prompt-Caching / Compaction
- weltweiter KG / Claim-Adjudication

---

## 1. Zielbild

### Was die Personal Knowledgebase ist

Ein user-owned, kuratierter Wissensraum fuer Dinge wie:

- gespeicherte Artikel
- PDFs
- YouTube-Videos mit Transcript
- Podcasts / Vortraege mit Transcript
- Webclips / Bookmarks
- Highlights
- eigene dauerhafte Notes
- importierte PKM-/Markdown-Sammlungen

### Was sie nicht ist

- nicht automatisch jeder Chatturn
- nicht die implizite Erinnerung zwischen User und Agent
- nicht automatisch globales Weltwissen
- nicht zwingend ein manuell gepflegter Graph

### Record of truth

- das bewusst gespeicherte Artefakt
- plus user-nahe Annotationen / Highlights / Labels

---

## 2. Produktbild / UX-Referenzen

### `Recall`

Nuetzlich als Produktreferenz fuer:

- Browser-/Mobile-Capture
- YouTube mit Transcript
- PDFs / Webseiten / Notes
- Chat / Summaries / Graph-Ansichten
- persoenliche AI-Knowledgebase als Produktidee

### `TriliumNext`

Nuetzlich als UI-/UX-Referenz fuer:

- Tree / Outliner / Notebook
- Web Clipper
- Inbox-Logik
- Notes / Labels / Attributes
- self-hosted PKM-Feeling

Wichtige Entscheidung:

- `TriliumNext` ist fuer uns **UI-/UX-Inspiration**
- nicht der zentrale Backend-Stack
- der TypeScript-/Node-Backend-Teil wird nicht zur neuen Source of Truth

### Praktische Produktentscheidung

Wir uebernehmen eher:

- Capture-Flows
- Inbox / Library / Note-Surfaces
- Clipper-Muster
- Notebook-/Outliner-Muster
- lokale / user-owned Anmutung

Nicht blind uebernehmen:

- Backend-Architektur
- Datenhaltung als zweite Wahrheit neben Matrix
- manuelle Graphpflege als Kernworkflow

---

## 3. Write-Pfad

### Default-Flows

| Artefakt | Default-Ziel |
|---|---|
| gespeicherter Artikel / Webclip | Personal Knowledgebase |
| private PDF | Personal Knowledgebase |
| YouTube / Podcast mit Transcript | Personal Knowledgebase |
| Langzeit-Research-Note | Personal Knowledgebase |
| externer PKM-/Markdown-Import | Personal Knowledgebase |

### Nicht default KB

| Artefakt | Gehoert primaer woanders hin |
|---|---|
| Chatturn | Personal Memory |
| Tool-Output | Personal Memory |
| globale News / Filing / Marktbericht | Global World Model |

### Wichtige Regel

Ein Artefakt kann spaeter verlinkt werden mit:

- Personal Memory
- globalen Entities
- globaler Evidenz

Aber:

- es soll nur **eine** primaere Heimat / System-of-record haben

---

## 4. Retrieval / Runtime-Rolle

`exec-context` bleibt Owner fuer das gesamte Context Assembly.

Dieses Exec definiert, wie die KB als Schicht daran teilnimmt:

- KB ist kurationsnah, nicht sessionnah
- KB ist ein eigener Retrieval-Kandidat bei user-spezifischen Wissensfragen
- KB darf Auto-Links / Entity-Links / semantische Suche haben
- KB sollte nicht denselben Retrieval-Pfad wie Session-Memory erzwingen

### Typische Query-Typen

- "Was hatte ich zu Thema X gespeichert?"
- "Zeig mir meine gesammelten Quellen zu Firma Y"
- "Finde die Stelle in meinem gespeicherten PDF / Transcript"
- "Welche meiner gespeicherten Artefakte haengen mit Entity Z zusammen?"

### Runtime-Regeln

- KB-Treffer duerfen personal memory nicht verdrängen, sondern ergaenzen
- KB-Treffer duerfen nicht still als Weltwahrheit erscheinen
- KB-Notizen duerfen nicht automatisch zu `derived memory` promotet werden
- KB-Retrieval ist besonders wertvoll fuer user-nahe, nicht fuer rein globale
  Fragen

---

## 5. UI-Surfaces

Dieses Exec ist Owner fuer die inhaltliche Produktlogik hinter folgenden
Surfaces; konkrete UI-Umsetzung lebt spaeter in `exec-15`.

### Kern-Surfaces

- Inbox
- Library
- Document / Transcript View
- Note View / Editor
- Clipper / Save Flow
- Import Flow
- Highlight / Annotation Layer

### Sekundaere Surfaces

- Entity Sidebar
- Related Saves / Auto-Links
- KB Search
- Source Detail View

### Nicht default als Kern-Surface

- manueller Relation-Editor fuer dutzende Kanten
- persoenlicher Mini-Neo4j als Alltagsworkflow

Realistischer Workflow:

- sammeln
- annotieren
- labeln
- pinnen
- thematisch gruppieren
- automatisch verlinken lassen

---

## 6. Implementation-Checkliste

### Phase A — Grenzen / Vertraege

- [ ] `Personal Knowledgebase` gegen `Personal Memory` klar im Code-/API-Scope abgrenzen
- [ ] Artefakt-Typen `KB by default` vs `Memory by default` verbindlich machen
- [ ] System-of-record fuer KB-Artefakte festlegen
- [ ] KB-spezifische Metadaten definieren (`saved_at`, `saved_from`, `artifact_type`, `annotation_count`, `source_ref`, `entity_links`)

### Phase B — Capture / Import

- [ ] Save-Flow fuer Links / Webclips definieren
- [ ] Save-Flow fuer PDFs / Files definieren
- [ ] Save-Flow fuer YouTube / Podcast / Transcript definieren
- [ ] Import-Flow fuer Markdown / PKM / Bookmark-Exports definieren
- [ ] KB-Inbox als Sammelziel fuer neue Artefakte definieren

### Phase C — Notes / Annotationen / Links

- [ ] Notes / Highlights / Labels / Pins definieren
- [ ] Auto-Links / Entity-Links / semantische Aehnlichkeit definieren
- [ ] manuelle leichte Curation erlauben ohne Graphpflicht
- [ ] klare Trennung von Artefakttext vs. User-Annotationen festhalten

### Phase D — Retrieval / Context

- [ ] KB-spezifische Retrieval-Policy fuer `exec-context` definieren
- [ ] KB-Treffer bei user-nahen Queries priorisieren
- [ ] KB nicht still als Weltwissen ausgeben
- [ ] Entity-/Topic-Links fuer KB-Retrieval nutzbar machen

### Phase E — UI / Product

- [ ] Inbox / Library / Document / Note-Surfaces mit `exec-15` abstimmen
- [ ] `Recall`-artige Produktmuster dokumentieren die wir wirklich wollen
- [ ] `TriliumNext`-artige UI-Muster dokumentieren die wir wirklich uebernehmen wollen
- [ ] lokale / user-owned / offline-faehige Elemente optional planen

### Phase F — Schema / Persistenz

- [ ] falls noetig: KB-spezifisches Schema / Namespace in `exec-18` vorbereiten
- [ ] Bridges zu Personal Memory / globalen Entities definieren
- [ ] Deletion / Reindex / Reingest fuer KB-Artefakte festlegen

---

## 7. Verify Gates

- [ ] Ein bewusst gespeicherter Link landet in der KB und nicht still im Session-Memory
- [ ] Ein privates PDF kann ingestiert und spaeter ueber KB-Retrieval wiedergefunden werden
- [ ] Ein YouTube-/Podcast-Artefakt kann mit Transcript in die KB
- [ ] KB-Notizen und User-Annotationen bleiben mit dem Artefakt verbunden
- [ ] KB-Treffer koennen in Runtime auftauchen ohne als Weltwahrheit ausgegeben zu werden
- [ ] KB-UI-Surfaces bleiben klar getrennt von Memory Browser / Episodes

---

## 8. Querverweise

- Personal Memory: [`exec-memory.md`](./exec-memory.md)
- Runtime / Context: [`exec-context.md`](./exec-context.md)
- World Model / Global KG: [`exec-world-model.md`](./exec-world-model.md)
- UI / Control Surfaces: [`exec-15-memory-control-ui.md`](./exec-15-memory-control-ui.md)
- Schema / Persistenz: [`exec-18-unified-agent-schema.md`](./exec-18-unified-agent-schema.md)
- Traces / Replay: [`exec-17-observability-harness-traces.md`](./exec-17-observability-harness-traces.md)

---

## 9. Offene Punkte

1. Eigener KB-Store / Namespace oder nur logische Schicht ueber bestehende Artefaktstores?
2. Wie viel lokale / offline Persistenz wollen wir fuer user-owned KB wirklich?
3. Welche Teile von `TriliumNext` wollen wir bewusst als UI-/UX-Muster uebernehmen?
4. Wie stark soll die KB spaeter mit globalen Entities / Claims verlinkt werden?
5. Welche KB-Surfaces brauchen wir in `exec-15` zuerst: Inbox, Library, Notes oder Transcript View?
