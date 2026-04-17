# Memory, Context, KG, Ingestion, Fusion

Stand: 2026-04-16

## Zweck

Dieses Dokument ist ein bewusst ausfuehrliches Architektur-Memo fuer den
aktuellen Stand in `matrix` rund um:

- persoenliches Memory
- Context Assembly / Retrieval / Prompt Composition
- `memory_fusion`
- MemPalace / Hindsight
- Ingestion / Extraction / Embedding
- persoenliche vs globale Wissensschichten
- globaler KG / globaler Vectorstore
- Unsicherheit, Provenance, Konflikte und sinnvolle Ausbau-Reihenfolge

Ziel ist nicht, einen "perfekten" Masterplan zu schreiben, sondern:

1. den Ist-Zustand sauber festzuhalten
2. die beobachteten Luecken klar zu benennen
3. die Begriffe zu entwirren
4. eine sinnvolle Zielarchitektur und Reihenfolge festzulegen
5. spaeteres Vergessen zu vermeiden

Dieses Dokument basiert auf:

- direkt gelesenen Code-Pfaden in diesem Repo
- bestehenden Projekt-Dokumenten
- `Memory_with_Uncertainty`
- `MEMORY_ARCHITECTURE.md`
- `CONTEXT_ENGINEERING.md`
- `AGENT_ARCHITECTURE.md`
- `AGENT_RUNTIME_ARCHITECTURE.md`
- `AGENT_HARNESS.md`
- `AGENT_SECURITY.md`
- direkt gelesenen Upstream-Webquellen fuer MemPalace und Hindsight
- einer direkt gelesenen Survey zu Memory fuer autonome LLM-Agents

Wichtig: Das Dokument trennt bewusst zwischen:

- `raw evidence`
- `derived memory`
- `world knowledge`
- `heavy ingestion`
- `context assembly`
- `reasoning`

Genau diese Trennung ist der rote Faden.

Zusatz seit diesem Update:

Dieses Dokument soll jetzt **nicht nur** die grobe Memory-/KG-Architektur
festhalten, sondern auch die wichtigsten **Context-Prinzipien** mittragen:

- Memory beantwortet: **was wird wo gespeichert?**
- Context beantwortet: **wer bekommt wann welchen Ausschnitt davon?**

Die spaeteren Execs koennen darauf aufbauen:

- `exec-memory.md` als operativer Slice fuer Write-/Read-/Eval-Pfade
- `exec-context.md` als operativer Slice fuer Runtime-Assembly, Budgets,
  Caching und Degradation

## Kurzfazit

Der aktuelle Stack hat **mehrere gute Bausteine**, aber noch **keine sauber
durchgezogene Gesamtarchitektur** fuer:

- persoenliches episodisches Memory
- persoenliches abgeleitetes Memory
- globale Wissensakquise
- globalen World-/Event-/Market-KG
- Unsicherheit / Promotion / Konflikte

Die wichtigste Einsicht ist:

> `ingestion` ist nicht dasselbe wie `memory`.

Noch wichtiger:

> `global world knowledge` ist nicht dasselbe wie `personal/user/agent memory`.

Die sinnvolle Trennung ist derzeit aus meiner Sicht:

1. **Global World Evidence**
   - geteilte, weltbezogene Dokumente / News / Research / Berichte / Feeds
   - globaler Vectorstore / globaler Dokumentstore

2. **Global World KG**
   - Weltentitaeten, Events, Assets, Claims, Relationen, Zeitlichkeit, Provenance

3. **Personal Raw Evidence**
   - Chats, Notes, Tool-Outputs, Session-Episoden
   - MemPalace-artiger oder MemPalace-inspirierter Evidence-Store

4. **Personal Derived Memory**
   - Preferences, Observations, Mental Models, wiederkehrende Muster
   - Hindsight-artige Schicht

5. **Personal Knowledgebase**
   - bewusst gespeicherte persoenliche Artefakte
   - PDFs, Webseiten, YouTube-Transcripts, Bookmarks, Highlights, Notizen
   - kuratierter Wissensraum, nicht bloss Session-Memory

6. **Reasoning / Composition**
   - kombiniert 1-5, aber vermischt sie nicht stillschweigend zu einer Wahrheit

## Wichtige Korrekturen seit dem ersten Draft

Seit dem ersten Draft dieses Dokuments wurde im Gespraech klarer:

1. Die aelteren `tradefusion`-/`main_docs`-Begriffe wie `fastlane` und
   `slowlane` entstanden **vor** MemPalace und Hindsight in ihrer heutigen Form.
   Man darf sie deshalb nicht 1:1 auf den aktuellen Stack mappen.
2. Ein **globaler slow lane KG/vector** bleibt sehr wahrscheinlich noetig, weil
   er das kuratierte Weltmodell abbildet.
3. Ein separater **globaler fastlane** ist **nicht default-noetig**. Der alte
   persoenliche/schnelle Fastlane-Gedanke wird heute weitgehend durch
   `Personal Raw Evidence` plus `Personal Derived Memory` getragen.
4. Hindsight und MemPalace decken persoenliche graph-/memory-nahe Rollen ab,
   sind aber **kein Ersatz** fuer ein globales World Model.
5. `memory_fusion` sollte deshalb nicht auf einen dritten grossen
   "Fastlane-Store" hinauslaufen, sondern auf eine saubere Trennung aus
   personal raw, personal derived, personal knowledgebase und global world
   layers.
6. Der Begriff `overlay graph` ist fuer v1 eher verwirrend. Praktisch sinnvoller
   ist zuerst eine **Personal Knowledgebase** mit Auto-Links, spaeter optionalen
   Graph-Views und nur sehr leichter manueller Curation.

## Das zentrale Problem

Das Repo hat aktuell mehrere semantisch unterschiedliche Systeme, die
teilweise schon existieren, aber im Alltag noch leicht verwechselt werden:

- `agent/memory` bzw. Hindsight-nahe Runtime
- `memory_fusion`
- MemPalace-Referenzlogik
- `ingestion`
- `extraction_layout`
- `kg_pipeline`
- die Idee einer separaten persoenlichen Knowledgebase
- die Idee eines separaten globalen KG

Ohne explizite Trennung entstehen typische Verwechslungen:

- "Ingestion ist doch auch Memory"
- "Hindsight hat KG-like, also reicht das als KG"
- "MemPalace ist fuer Chat, Ingestion fuer Docs"
- "bewusst gespeicherte persoenliche Wissensartefakte sind dasselbe wie Session-Memory"
- "Wenn alles in Postgres ist, ist es doch ein gemeinsamer Space"
- "Observation kann schon als Wahrheit gelten, weil sie evidenzbasiert ist"
- "Der alte Fastlane-Begriff bedeutet automatisch, dass wir heute noch einen
  extra globalen Fastlane-Store brauchen"

Genau gegen diese Verwechslungen richtet sich dieses Dokument.

## Kernbegriffe

### Raw Evidence

Primarquelle. Nicht automatisch wahr, aber primar.

Beispiele:

- User-Input
- Tool-Output
- Log-Zeilen
- Dokument-Absatz
- Webpage-Chunk
- PDF-Chunk
- OCR-Text
- Audio-Transkript

### Derived Memory

Abgeleitet aus Raw Evidence. Darf nie mit Primarevidenz verwechselt werden.

Beispiele:

- Observation
- Preference
- Stable Pattern
- Mental Model
- reasoning summary

### Personal Memory

Wissen ueber:

- User
- Agent
- Interaktionen
- vergangene Sessions
- persoenliche Arbeitsweisen
- persoenliche Artefakte

### Personal Knowledgebase

Bewusst kuratierter persoenlicher Wissensraum.

Nicht primaer:

- "was ist in der Session passiert?"

Sondern:

- "was will der User absichtlich behalten, ordnen und spaeter wiederfinden?"

Beispiele:

- gespeicherte Artikel
- PDFs
- YouTube-Videos mit Transcript
- Webclips
- Bookmarks
- Highlights
- eigene Research-Notizen

Wichtige Abgrenzung:

- `personal memory` ist interaktionsnah
- `personal knowledgebase` ist kurationsnah
- beides darf verlinkt sein, ist aber nicht dieselbe Schicht

### Global World Knowledge

Wissen ueber:

- Firmen
- Staaten
- Regulierungen
- Rohstoffe
- Preise
- Makro
- Konflikte
- globale Events
- Markt- und Event-Kausalitaet

### Heavy Ingestion

Aufwaendige Artefaktverarbeitung, z. B.:

- Dateityperkennung
- Extractor-Auswahl
- OCR / Layout
- strukturierte Extraktion
- Chunking
- Reindex / Dedup
- multimodale Vorverarbeitung

Heavy Ingestion ist **Knowledge Acquisition**, nicht automatisch Memory.

### Truth / Belief / Scenario

Diese drei Ebenen muessen explizit auseinandergehalten werden:

- `truth`
  - validierte, provenance-getragene Welt-Claims oder belastbare Evidenz
  - Kandidat fuer globalen KG / World Model
- `belief`
  - abgeleitete Beobachtung, Arbeitsannahme oder persoenliche Verdichtung
  - kann gut begruendet sein, ist aber nicht automatisch Weltwahrheit
- `scenario`
  - hypothetische oder kontrafaktische Sicht
  - Planungs-/Simulations-/Was-waere-wenn-Ebene

Wichtige Regel:

- User-Input startet als **Evidenzquelle**, nicht als `truth`
- User-Input startet auch nicht automatisch als `belief`
- zuerst kommt Rohmaterial / Claim / Einordnung, erst spaeter Verdichtung

### Epistemische Trennung

Die wichtigste Trennung im gesamten System:

- Rohmaterial ist nicht dasselbe wie Verdichtung
- User-Aussage ist nicht dasselbe wie verifizierte Weltwahrheit
- Agent-Output ist nicht dasselbe wie Primarevidenz
- Weltwissen ist nicht dasselbe wie persoenliche Erinnerung

### Memory vs Context

Diese Achse ist genauso wichtig wie raw-vs-derived:

- `memory`
  - definiert, **was** gespeichert wird
  - definiert, **wo** es liegt
  - definiert, welcher Store record-of-truth ist
- `context`
  - definiert, **wer** auf welche Schicht zugreifen darf
  - definiert, **wann** welche Schicht gezogen wird
  - definiert, **wie viel** davon in die Runtime / den Prompt darf

Praktische Formel:

- Memory = Bibliothek
- Context = Bibliothekar

Wichtige Folge:

- ein gutes Memory-System kann trotzdem schlechtes Context Assembly haben
- ein gutes Context-System kann schlechtes Memory nicht heilen

### Artefakt-Hierarchie

Aus `Memory_with_Uncertainty` bleibt diese Hierarchie zentral:

- **primaere Artefakte**
  - User-Input
  - Docs
  - Logs
  - Tool-Outputs
  - extrahierte Evidenz-Chunks
- **sekundaere Artefakte**
  - Agent-Antworten
  - agentische Zwischenzusammenfassungen
  - Hilfstexte fuer die Runtime
- **tertiaere Artefakte**
  - Observations
  - Mental Models
  - andere Verdichtungen ueber Verdichtungen

Wichtige Regel:

- sekundaere oder tertiaere Artefakte duerfen nie still als neue Primaerevidenz
  recycelt werden

### Fastlane / Slowlane neu eingeordnet

Die alten Begriffe bleiben nuetzlich, aber nur in sauberer Uebersetzung:

- `slowlane`
  - entspricht heute am ehesten `Global World Evidence` plus `Global World KG`
  - also dem kuratierten, nachvollziehbaren Weltmodell
- `fastlane`
  - war historisch eher die Idee eines schnellen persoenlichen
    Arbeits-/Memory-/KG-Raums
  - diese Rolle wird heute zu grossen Teilen schon abgedeckt durch
    `Personal Raw Evidence` plus `Personal Derived Memory`

Wichtige Korrektur:

- Aus dem alten Begriff `fastlane` sollte **nicht automatisch** ein neuer,
  separater globaler Produktiv-Store abgeleitet werden.

### Overlay Graph neu eingeordnet

Falls der Begriff doch weiterverwendet wird, dann aus meiner Sicht nur in diesem
Sinn:

- nicht als eigener Truth-Store
- nicht als Pflicht-Kernschicht
- eher als moegliche spaetere Ansicht / Projektion ueber:
  - `Personal Knowledgebase`
  - `Personal Memory`
  - evtl. globale Entities

Praktisch pflegt kaum jemand langfristig viele manuelle Relationstypen.
Realistischer sind:

- Auto-Links
- Tags
- Watchlists
- Pins
- thematische Buckets
- wenige manuelle Verweise

Deshalb ist fuer v1 eine `Personal Knowledgebase` das stabilere Konzept als ein
frueh erzwungener `overlay graph`.

## Was momentan im Repo existiert

### 1. Hindsight-nahe Memory-Runtime

Es gibt eine existierende Memory-Runtime ueber `agent/memory` und einen
separaten Umbaupfad in `memory_fusion`.

Beobachtete relevante Pfade:

- `python-backend/agent/memory/`
- `python-backend/memory_fusion/engine.py`
- `python-backend/memory_fusion/fusion_engine.py`
- `python-backend/memory_fusion/providers.py`
- `python-backend/memory_fusion/summary_builder.py`
- `python-backend/memory_fusion/loci.py`

Aktueller Charakter:

- Hindsight ist funktional schon das Rueckgrat fuer Recall/Retain/Reflect
- `memory_fusion` ist aktuell ein produktiver Umbaupfad auf Postgres/pgvector
- MemPalace-Ideen sind teilweise als Metadaten / Utilities uebernommen
- die Trennung zwischen summary/verbatim ist aktuell noch zu stark
  Hindsight-zentriert und noch nicht die saubere Evidence-vs-Derived-Architektur

### 2. `memory_fusion`

`memory_fusion` ist heute nicht einfach "MemPalace + Hindsight", sondern
praktisch:

- zwei Hindsight-basierte Routen
- plus MemPalace-inspirierte Hilfslogik
- plus Route-Merging

Beobachtete Merkmale:

- `fusion_engine.py` erstellt `summary` und `verbatim` Pfade
- beide gehen heute in Hindsight-Engines
- Trennung aktuell ueber Bank-IDs wie `__summary` und `__verbatim`
- Method-of-Loci wird als Metadaten-/Tag-System modelliert
- Query Sanitizer wird aus MemPalace-Ideen uebernommen

Staerken:

- produktiver Postgres-first Pfad
- gute API-Naehe zur Hindsight-Welt
- lokaler Test-/Eval-Harness vorhanden
- Loci-Metadaten und Provenance sind schon eingebaut

Schwaechen:

- zu viel "zwei Routen in Hindsight" statt echte Evidence-vs-Derived-Trennung
- noch kein sauberer Claim-/Validator-/Arbiter-Layer
- `reflect` ist noch nicht sauber Evidence-joined
- keine voll ausgearbeitete Unsicherheits-/Promotion-Logik

### 3. MemPalace-Referenzwelt

Im Repo existiert `_ref/mempalace/` als Referenz und eval-faeiger Vergleichspfad.

Wichtig:

- MemPalace ist klar raw/verbatim/retrieval-zentriert
- spatial hierarchy: wings, rooms, halls, closets, drawers
- KG-artige Teile existieren, aber memory-nah und lokal
- das ist kein Ersatz fuer einen echten globalen World-KG

Im produktiven `memory_fusion` ist MemPalace derzeit **nicht** als voller
separater Runtime-Storage uebernommen, sondern eher als Ideen-/Verhaltensquelle.

### 4. Ingestion-Worker

Die Ingestion-Pipeline ist ein eigener Worker und bereits deutlich strukturierter
als einfache Memory-Writes.

Beobachtete relevante Pfade:

- `python-backend/ingestion/worker.py`
- `python-backend/ingestion/pipelines/document.py`
- `python-backend/ingestion/pipelines/note.py`
- `python-backend/ingestion/pipelines/link.py`
- `python-backend/ingestion/core/config.py`
- `python-backend/ingestion/core/types.py`
- `python-backend/ingestion/sinks/hindsight_sink.py`
- `python-backend/ingestion/sinks/storage_sink.py`
- `python-backend/ingestion/sinks/kg_sink.py`
- `python-backend/agent/control/ingestion.py`

Der aktuelle Pipeline-Charakter:

- detect
- load
- extract
- normalize
- chunk
- embed
- sink write
- tracking / audit / dedup

Das ist **nicht** nur "Memory abspeichern", sondern eine richtige
Artefaktverarbeitung.

### 5. `extraction_layout`

`extraction_layout` ist aktuell **kein voll aktiver Produktivpfad**, sondern
noch ein Skeleton / Stub.

Beobachtete Pfade:

- `python-backend/extraction_layout/worker.py`
- `python-backend/ingestion/extractors/remote.py`

Status:

- Health antwortet
- `/extract` liefert aktuell `503`
- Docling / Marker / MinerU sind als Phase-2-Richtung sichtbar
- die JSON-zu-`ExtractedDocument` Rueckuebersetzung ist noch nicht fertig

Wichtige Konsequenz:

- konzeptionell ist der Pfad sinnvoll
- praktisch ist er heute noch nicht "reif"

### 6. `kg_pipeline`

Es gibt einen `kg_pipeline`-Pfad, aber aktuell ebenfalls nur als sehr mageres
Skeleton.

Beobachtete Pfade:

- `python-backend/kg_pipeline/core/types.py`
- `python-backend/ingestion/sinks/kg_sink.py`

Status:

- `kg_sink` ist vorgesehen
- Entitaeten/Relationen sind aktuell Stub-Dataclasses
- keinerlei ausgearbeiteter Graph-of-record sichtbar

Wichtige Konsequenz:

- KG ist im System als Idee vorgesehen
- aber nicht als belastbare, ausgearbeitete Wahrheitsschicht umgesetzt

### 7. Eval-/Spec-Lage

Es existieren bereits etliche Memory-Eval-Dokumente und Harnesses.

Wichtige Pfade:

- `specs/execution/exec-memory.md`
- `python-backend/experiments/memory_eval/README.md`
- `python-backend/experiments/memory_eval/BENCHMARK_COVERAGE.md`
- `python-backend/experiments/memory_eval/run_hindsight_eval.py`
- `python-backend/experiments/memory_eval/run_mempalace_eval.py`
- `python-backend/experiments/memory_eval/run_fusion_eval.py`
- `python-backend/experiments/memory_eval/run_long_context_smoke.py`

Gut:

- Harness und Coverage-Denken sind da
- gemeinsame Korpus-/Ground-Truth-Idee ist da

Offen:

- Architektur ist weiter als der Begriffshaushalt
- Evals beantworten noch nicht die ganze KG-/Memory-Trennungsfrage

## Was aus Paperwatcher uebernommen wurde

Dieser Punkt ist wichtig, weil die aktuelle Ingestion-/Extraction-Welt
offensichtlich teilweise aus `paperwatcher` stammt und noch mager ist.

Direkt im Code sichtbar:

- `python-backend/ingestion/extractors/base.py`
  - "Adopted from paperwatcher/paperwatcher/core/doc_extractor/base.py."
- `python-backend/ingestion/core/types.py`
  - "1:1 copy with JobStatus + Job + PipelineKind enums added on top"
- `python-backend/ingestion/extractors/pymupdf_ext.py`
  - "Adopted ... (1:1)"
- `python-backend/ingestion/chunkers/token_chunker.py`
  - "Adopted ... chunking.py"
- `python-backend/ingestion/extractors/__init__.py`
  - mehrere in-process Extractors als aus Paperwatcher uebernommen beschrieben
- `python-backend/ingestion/tracking/dedup.py`
  - "paperwatcher merkle pattern"
- `python-backend/kg_pipeline/core/types.py`
  - "will be filled in when adopting paperwatcher kg-module"

Das heißt:

1. die aktuelle Ingestion-Welt hat einen realen, sinnvollen Ursprung
2. sie ist aber noch deutlich im Uebernahme-/Bootstrap-Zustand
3. der KG-Teil ist besonders mager / unvollstaendig
4. man sollte `paperwatcher` als Referenz explizit nennen und nicht so tun, als
   sei das alles schon originell oder fertig im Matrix-Repo ausgebaut

## Was `Memory_with_Uncertainty` zwingend vorgibt

`Memory_with_Uncertainty` ist fuer diese Architektur nicht optional, sondern
praktisch die wichtigste Leitplanke.

Die wichtigsten Regeln daraus:

1. **Derived Memory darf nie allein antworten**
2. **Observation/Mental Model brauchen Evidence-Join**
3. **User-Input, Docs, Logs, Tool-Outputs sind primaere Evidenz**
4. **Agent-Antworten sind sekundaere Artefakte**
5. **Observations/Mental Models sind tertiaere Artefakte**
6. **support_count / conflict_count / source_diversity / freshness muessen
   modelliert werden**
7. **Konflikte sichtbar machen statt weichzubuegeln**
8. **Mental Models sind Accelerator, nicht oberste Wahrheit**

Die wichtigste Formulierung dafuer:

> Hindsight darf nie seine eigene Quelle sein.

Und praktisch:

> Der Agent darf nicht aus Observation allein antworten; rohe Evidenz muss
> mitkommen.

## Was das fuer die Architektur bedeutet

### Nicht sinnvoll

- ein einziger "Memory Space" fuer alles
- ein gemeinsames Wahrheitsmodell fuer MemPalace, Hindsight und Weltwissen
- Docs direkt wie Chat behandeln
- globales Weltwissen aus Agent-Reflexionen still erzeugen
- Agent-Output als primaere Evidenz recyceln
- aus alten `fastlane`-Begriffen direkt einen neuen globalen Runtime-Store
  ableiten

### Sinnvoll

- klare Schichtung
- klare Write-Rules
- klare Privacy-Scope-Regeln
- klare "record of truth"-Definition pro Schicht
- klare Join-/Link-Regeln zwischen den Schichten
- alte Begriffe (`fastlane`, `slowlane`) in die neuen Achsen
  `personal/global`, `raw/derived`, `truth/belief/scenario` uebersetzen

## Was aktuell fehlt oder ausgebaut werden muss

### A. Klare Layer-Definitionen

Aktuell gibt es gute Bausteine, aber keine kompromisslos dokumentierte
Systemtrennung.

Es braucht explizit:

- welchen Store es gibt
- welche Datenklasse dort record-of-truth ist
- wer hinein schreiben darf
- ob der Store personal oder global ist
- wie Konflikte modelliert werden
- wie RAG/reflect darauf zugreifen

### B. Echte Trennung zwischen personal und global

Aktuell ist die Idee da, aber kein durchgezogener technischer Schnitt.

Es braucht:

- `global shared world evidence`
- `global world graph`
- `personal raw evidence`
- `personal derived memory`

und Links zwischen diesen Schichten, aber keine stille Verschmelzung.

### C. Claim-Layer

Der Claim-Layer fehlt aktuell als ernsthafte Zwischenschicht.

Noetig:

- `RawMemory -> Claim -> Observation -> MentalModel`

Ohne Claim-Layer passieren zwei schlechte Dinge:

1. Rohdaten werden zu schnell verdichtet
2. globale Graph-/Weltbehauptungen werden unsauber aus Freitext abgeleitet

### D. Unsicherheitsmodell

Aktuell ist kein ausgearbeitetes Unsicherheitsmodell als produktive Schicht
sichtbar.

Noetig:

- source priors
- support / conflict
- freshness
- provenance completeness
- candidate/stable/conflicted/stale/deprecated
- query-time evidence coverage

### E. World KG als eigener Graph

Hindsight-Graph-like reicht nicht als globaler KG.

Es braucht einen separaten World-KG fuer:

- Events
- Firmen
- Staaten
- Policies
- Commodities
- Makro
- Assets
- Kausalrelationen
- konkurrierende Claims

### F. Globaler Vectorstore

Neben einem globalen KG ist sehr wahrscheinlich auch ein globaler Vectorstore
sinnvoll.

Warum:

- Graph ist praezise, aber kein guter unscharfer Zugang fuer alles
- semantischer Einstieg ueber globale Evidenz / Claims / Entities ist nuetzlich
- Graph of record und semantischer Access-Index sollten getrennt sein

### G. Ingestion nicht direkt nur nach Hindsight

Heute schreibt die Dokument-Ingestion in `HindsightSink`.

Das ist als Zwischenstand nachvollziehbar, aber langfristig zu flach.

Sinnvoller Zielzustand:

- `ingestion` erzeugt zuerst qualitaetsgesicherte Primaerevidenz
- dann:
  - in globalen Evidence-Store
  - oder in persoenlichen Evidence-Store
  - optional Claims / KG / Hindsight nachgelagert

### H. `extraction_layout` und `kg_pipeline` wirklich ausbauen

Beide sind derzeit eher Platzhalter als ernsthafte Runtime-Schichten.

### I. RAPTOR / advanced hierarchical ingestion

In `exec-memory.md` ist `RAPTOR + Late Chunking aus Paperwatcher` als offener
Portierungspunkt explizit genannt. Im aktuell gelesenen `python-backend` ist
kein aktiver produktiver RAPTOR-Pfad sichtbar.

Das bedeutet:

- die Idee existiert
- der Ausbau ist aber noch offen

### J. Bayesian RAG richtig einordnen

Bayesian RAG bzw. uncertainty-aware retrieval ist interessant, aber kein Ersatz
fuer die eigentliche Architektur.

Sinnvolle Rolle:

- query-time reranking
- confidence weighting
- Penalizing unsichere / widerspruechliche Treffer
- Mischung aus `support_count`, `conflict_count`, `freshness`, Priors und
  Retrieval-Scores

Nicht die Rolle:

- kein Ersatz fuer Claim-Layer
- kein Ersatz fuer globalen KG
- kein Ersatz fuer epistemische Trennung
- kein Ersatz fuer Evidence-Join

## Was nicht vermischt werden sollte

### 1. Globaler KG vs Hindsight-KG-like

Hindsight darf gerne graph-artige Strukturen intern verwenden, aber:

- das ist Memory-zentriert
- bank-/agent-/user-zentriert
- observation-/mental-model-zentriert

Ein globaler KG ist:

- weltzentriert
- eventzentriert
- asset-/entity-/relation-zentriert
- conflict-/claim-/provenance-zentriert

Beides darf verlinkt sein, aber nicht dieselbe Schicht sein.

### 2. MemPalace vs Ingestion

MemPalace-artige Logik ist stark fuer:

- schnelle, billige, verbatim-nahe Speicherung
- episodische Session-Daten
- auditierbares Raw-Memory

Ingestion ist stark fuer:

- schwere Artefaktverarbeitung
- Extractor-/Layout-/Chunking-Logik
- Dokumentqualitaet
- multimodale Vorverarbeitung

Die saubere Aussage ist deshalb:

> Ingestion ist eher `knowledge acquisition`, MemPalace eher `raw episodic memory`.

### 3. Personelle Knowledgebase vs globale Knowledgebase

Auch das darf nicht vermischt werden.

Beispiele fuer persoenliche Knowledgebase:

- private PDFs
- persoenliche Notizen
- eigene Screenshots
- Arbeitsunterlagen
- persoenliche Webclips

Beispiele fuer globale Knowledgebase:

- Nachrichten
- Filings
- Research Reports
- Regierungsdokumente
- Marktberichte

Beide koennen heavy ingestion brauchen.
Beide sind aber **nicht automatisch dasselbe**.

## Empfohlene Zielarchitektur

### Layer 0: Global World Evidence

Scope:

- optional shared fuer alle User
- evtl. teilweise auch team-/workspace-scoped

Inhalt:

- News
- Reports
- Filings
- Research PDFs
- Webseiten
- strukturierte Markt-/Makro-Dokumente

Store-Typ:

- Dokumentstore
- Chunkstore
- globaler Vectorstore

Record of truth:

- der rohe / extrahierte Evidenz-Chunk

Schreibregeln:

- nur ueber Ingestion
- keine Agent-Reflexionen direkt hinein

### Layer 1: Global World KG

Scope:

- shared / global

Inhalt:

- Entity
- Event
- Asset
- Claim
- Source
- Relation

Noetige Kanten:

- `MENTIONS`
- `AFFECTS`
- `LOCATED_IN`
- `PART_OF`
- `SUPPORTS`
- `CONTRADICTS`
- `SUPERSEDES`
- `PRECEDES`
- `CITED_IN`

Record of truth:

- strukturierte, versionierte Graphobjekte und Claims mit Provenance

Schreibregeln:

- aus globaler Ingestion / Claim-Extraction / Validator
- keine direkten Hindsight-Observations als Weltwahrheit

### Layer 2: Personal Raw Evidence

Scope:

- per user
- per agent
- per workspace / bank

Inhalt:

- Chatturns
- Notes
- Tool outputs
- Session-Episoden

Store-Typ:

- MemPalace-artiger Evidence-Store
- oder Postgres-first Evidence-Store mit MemPalace-Semantik

Record of truth:

- raw episodic evidence

Schreibregeln:

- direkte user/agent/tool/session ingestion
- bewusst gespeicherte persoenliche Artefakte gehen primaer in die
  `personal knowledgebase`
- Agent-Output nur markiert als sekundaeres Artefakt

### Layer 3: Personal Derived Memory

Scope:

- per user / per agent / per bank

Inhalt:

- preferences
- observations
- repeated patterns
- mental models
- learned workflows

Store-Typ:

- Hindsight-artige Derived-Layer

Record of truth:

- observation / mental model mit Evidence-Backlinks und Status

Schreibregeln:

- nur aus raw evidence / claims
- nie selbstreferenziell
- nie ohne Provenance

### Layer 4: Personal Knowledgebase

Scope:

- per user
- optional per workspace
- klar user-owned

Inhalt:

- gespeicherte Artikel
- gespeicherte PDFs
- YouTube-Videos mit Transcript
- Webclips
- Bookmarks
- Highlights
- eigene langfristige Notizen
- importierte persoenliche Wissenssammlungen

Store-Typ:

- persoenlicher Dokument-/Notiz-/Artefaktstore
- kann ueber heavy ingestion angereichert werden
- darf Auto-Links / Entity-Links / semantische Suche haben
- darf optional eine lokale / offline-faehige User-Oberflaeche oder einen
  verschluesselten lokalen Teilindex haben

Record of truth:

- das bewusst gespeicherte Artefakt plus user-nahe Annotationen

Schreibregeln:

- expliziter User-Save, Import oder Curation-Flow
- nicht automatisch jeder Chatturn
- nicht automatisch Weltwissen
- nicht automatisch dasselbe wie personal memory

### Trennung `Personal Knowledgebase` vs `Personal Memory`

`Personal Memory` ist:

- interaktionsnah
- sessionnah
- user/agent/tool-Episoden
- raw plus derived Learnings

`Personal Knowledgebase` ist:

- kurationsnah
- artefaktzentriert
- "das will ich behalten"
- UI-/Inbox-/Notebook-nah

Beides darf sich referenzieren, sollte aber nicht dasselbe Write-Ziel sein.

### `Recall` / `TriliumNext` als Produktreferenzen

Die Diskussion um `Recall` und `TriliumNext` macht diese Schicht greifbarer:

- `Recall` ist eine gute Referenz fuer die Produktidee einer AI-gestuetzten
  persoenlichen Knowledgebase:
  - Browser-/Mobile-Capture
  - YouTube mit Transcript
  - PDFs / Webseiten / Notes
  - Summaries / Chat / Graph-Ansichten
- `TriliumNext` ist eine gute Referenz fuer eine self-hosted PKM-/KB-Oberflaeche:
  - Tree / Outliner
  - Web Clipper
  - Inbox-Logik
  - Notes / Labels / Attributes

Wichtige Designentscheidung:

- `Recall` / `TriliumNext` sind hier **Produkt-/UX-Referenzen**
- nicht die Source of Truth fuer globalen KG
- nicht der Ersatz fuer MemPalace oder Hindsight
- nicht automatisch die zentrale Runtime fuer den Python-Backend-Stack

Aktuell sinnvollste Richtung:

- `TriliumNext` eher als UI-/UX-Inspirationsquelle
- sinnvoll erscheinende Oberflaechen-/Capture-Muster teilweise uebernehmen
- den TypeScript-Backend-Stack **nicht** zum zentralen Backend machen
- System of record bleibt im Matrix-Stack sauber getrennt
- ein lokaler user-owned Surface-Layer ist moeglich, aber kein zweiter
  Wahrheits-Store

### Pragmatisches 4-Schichten-Bild fuer Produkt und Umsetzung

Fuer Gespraeche ueber das Produkt ist die folgende Verdichtung vermutlich
klarer als die interne Feingranularitaet:

1. `Global World Model`
   - = `Global World Evidence` + `Global World KG`
2. `Personal Memory`
   - = `Personal Raw Evidence` + `Personal Derived Memory`
3. `Personal Knowledgebase`
   - = bewusst gespeicherte persoenliche Wissensartefakte
4. `Reasoning / Context Assembly`
   - = Query Routing, Retrieval, Evidence Join, Prompt Assembly

Die feinere Layer-Aufteilung oben bleibt trotzdem sinnvoll fuer technische
Write-Regeln und Ownership.

### Layer 5: Reasoning / Context Assembly Layer

Funktion:

- Query Routing
- Retrieval Policy
- Evidence Join
- Graph traversal
- ranking / reranking
- multi-source merging
- token-budgeted context assembly
- degradation handling
- final prompt composition

Wichtige Regel:

- derived memory darf nie alleine antworten
- world KG darf nie ohne Evidence-Kontext als magische Wahrheit wirken
- personal memory und world knowledge muessen explizit zusammengesetzt werden

### KG als Schiedsrichter / Arbiter

Die Runtime sollte nicht nur "viel Retrieval" machen, sondern auch urteilen.

Die saubere Minimalpipeline ist:

1. **Retrieve**
   - hole passende Raw Evidence
   - hole Claims / KG-Zustaende
   - hole Derived Memory
2. **Normalize**
   - bringe Treffer in eine gemeinsame Vergleichsform
   - Aussage, Typ, Zeit, Quelle, Confidence, Konflikte
3. **Adjudicate**
   - neuere Primaerevidenz schlaegt aeltere Observation
   - Gegenbelege senken Status / Confidence
   - ungestuetzte Mental Models werden nicht bevorzugt
4. **Compose**
   - Antwort enthaelt verdichtete Orientierung **plus** Evidenzbasis

Das ist die praktischere Form von:

> der KG ist nicht nur Speicher, sondern Schiedsrichter zwischen Evidenz,
> Claims und Verdichtung.

### Context-Consumer

Fuer die Runtime sind mindestens diese Consumer relevant:

| Consumer | Ziel | Typischer Output | Charakter |
|---|---|---|---|
| LLM-Agent | reasoning / synthesis / action | Prompt-Kontext | tiefster, teuerster Consumer |
| Frontend-UI | schnelle persoenliche Sicht | JSON / Panel-Daten | lokal, latenzkritisch |
| Signal-/Scoring-Pipeline | strukturierte Features | Dict / JSON / Cache | schmal, deterministisch |
| Merge-Layer | user + global kombinieren | Hybrid-Result | verbindet lokale und globale Schichten |

### Grundregeln fuer Context Assembly

1. **Persistence vor Retrieval**
   - `source selection -> onboarding -> fetch/cache/snapshot -> normalize -> retrieval/context`
2. **Kein stiller Fallback**
   - degradierte Context-Zustaende muessen sichtbar markiert werden
3. **Struktur vor Semantik**
   - exakte KG-/Scope-Treffer vor unscharfer Similarity Search bevorzugen
4. **Derived nie ohne Evidence Join**
   - Verdichtung nur zusammen mit Rohbasis in die Runtime
5. **Context ist budgetiert**
   - nicht alles, was gespeichert ist, darf automatisch ins Prompt

## Context-Retrieval und Assembly

### Retrieval-Policies nach Consumer

| Consumer | Primaere Schichten | Sekundaere Schichten | Nicht default |
|---|---|---|---|
| LLM-Agent | Global World KG, Personal Memory, Global/Personal Evidence | Personal Knowledgebase | blinder Vollscan ueber alles |
| Frontend-UI | Personal Knowledgebase, user-nahe lokale Daten, leichte Merge-Resultate | Global KG ueber Merge-Layer | direkter tiefer Runtime-Scan ueber alle Server-Schichten |
| Signal-/Scoring-Pipeline | strukturierte KG-/Cache-/Feature-Resultate | gezielte Episodenaggregate | lange freie semantische Retrieval-Loops |
| Merge-Layer | Personal KB / user-owned Daten + Global KG | relevante Episodic / Evidence-Snippets | unmarkierte Hintergrundmagie |

### Standard-Reihenfolge fuer LLM-nahe Queries

Wenn kein spezialisierter Query-Modus greift:

1. Working / Hot Cache / bereits bekannte Runtime-Fragmente
2. Global World KG oder andere strukturierte Fakten
3. Personal Derived Memory
4. Personal Raw Evidence
5. Personal Knowledgebase
6. globale Evidence-/Vector-Treffer

Wichtige Korrektur:

- diese Reihenfolge ist **nicht** dieselbe wie Write-Prioritaet
- sie ist eine Runtime-Optimierung fuer Assembly, nicht eine Wahrheits-Hierarchie

### Degradation-Regeln

Wenn eine Schicht fehlt, muss die Runtime das sichtbar machen.

Beispiele:

- `NO_KG_CONTEXT`
- `NO_VECTOR_CONTEXT`
- `NO_PERSONAL_MEMORY`
- `LOW_EVIDENCE_COVERAGE`

Keine stille Regel:

- Kontext darf reduziert laufen
- Wahrheit darf dabei nicht still gleich behauptet werden

### Relevance- und Ranking-Dimensionen

Aus `CONTEXT_ENGINEERING.md` bleiben diese Dimensionen zentral:

- `freshness`
- `query fit`
- `user proximity`
- `confidence`
- `regime/domain fit`, wenn die Query stark domanenspezifisch ist

Praktisch heisst das:

- frischere Evidenz schlaegt aeltere, wenn sonst gleich
- user-nahe Kontexte duerfen persoenlich priorisiert werden
- Confidence unter einer Mindestschwelle sollte nicht unmarkiert in den Prompt
- strukturierte KG-Treffer koennen bei gleicher Relevanz ueber semantischen
  Vektor-Treffern priorisiert werden

### Merge-Regeln fuer Multi-Source Context

Wenn mehrere Schichten dieselbe Sache aus verschiedenen Blickwinkeln liefern:

1. Primaere Evidenz nicht durch Verdichtung ersetzen
2. Strukturierte KG-Claims nicht ohne Zeit-/Statuskontext zeigen
3. Semantische Treffer nur dann hochziehen, wenn sie neue Perspektive liefern
4. pro Schicht Caps setzen, damit keine Schicht den ganzen Kontext dominiert
5. Diversity Floor behalten, damit das System nicht in Echo-Chambers kollabiert

### Token-Budget und Compaction

Auch mit grossen Context Windows bleibt Budgetierung sinnvoll.

Leitregeln:

- System-/Guard-Teil bleibt klein und stabil
- strukturierte Fakten vor langen Rohpassagen
- retrieved evidence wird vor dem Prompt ggf. komprimiert / gepruned
- Compaction ist nicht nur Kompression, sondern auch Rehydration / Wiederaufbau
  des noetigen Arbeitskontexts

Dieses Dokument ist **nicht** der operative Owner fuer konkrete Schwellen.
Die Feinarbeit dafuer gehoert spaeter weiter in `exec-context.md`.

## Write-/Routing-Matrix

### Chat turn

Default:

- direkt in personal raw evidence

Optional:

- spaeter claim extraction
- spaeter personal derived memory

Nicht default:

- global KG

### Tool output

Default:

- personal raw evidence

Optional:

- persoenlicher Claim-Layer
- global KG nur wenn es weltbezogene harte Evidenz ist und durch passende
  Validator-/Domain-Logik geht

### Note

Default:

- abhaengig vom Charakter:
  - sessionnahe Scratch-Note -> personal raw evidence
  - bewusst gepflegte Langzeit-Notiz -> personal knowledgebase

Optional:

- derived memory

### Private PDF

Default:

- heavy ingestion
- dann personal knowledgebase

Optional:

- personal raw evidence, wenn das PDF Teil einer laufenden Session/Task-Episode ist
- derived memory

### Global research paper / filing / market report

Default:

- heavy ingestion
- global world evidence

Optional:

- global KG
- evtl. persoenliche Bookmark-/KB-Referenz

### Webpage / webfetch

Abhaengig vom Kontext:

- im Chat ad hoc referenziert / zusammen mit Session benutzt -> personal raw
  evidence
- bewusst gespeichert / geclippt / gebookmarkt -> personal knowledgebase
- als bewusste externe Quelle / Research-Artefakt ingestiert -> global world
  evidence

Wichtige Regel:

- `webfetch` oder ein Link im Chat wird nicht automatisch Weltwissen
- erst Scope-Entscheid, dann Evidence-Layer, dann spaeter optional Claim/KG

### Image / screenshot

Default:

- im Session-Kontext entstanden -> personal raw evidence
- bewusst gespeichert / gesammelt -> heavy ingestion und dann personal
  knowledgebase
- globale Quelle -> heavy ingestion und dann global world evidence

### Audio / video

Default:

- im Session-Kontext entstanden -> personal raw evidence
- bewusst gespeichert / gesammelt -> heavy ingestion / transcription /
  segmentation und dann personal knowledgebase
- globale Quelle -> heavy ingestion / transcription / segmentation und dann
  global world evidence

### Bookmark / Webclip / Saved Link

Default:

- personal knowledgebase

Optional:

- spaeter entity linking
- spaeter global evidence reference
- spaeter derived memory, falls aus dem Material wirklich persoenliches Lernen
  entsteht

### YouTube / Podcast / Vortrag mit Transcript

Default:

- heavy ingestion / transcript acquisition
- dann personal knowledgebase

Optional:

- global world evidence, falls es als geteilte Weltquelle kuratiert wird
- personal derived memory, falls daraus langfristige Learnings abgeleitet werden

### Import aus externer PKM / Notizsammlung

Default:

- personal knowledgebase

Optional:

- nachgelagerte Chunking-/Embedding-/Entity-Linking-Pipeline

### Praktische Zuordnungsmatrix

| Artefakttyp | Default Layer | Optionale Downstream Writes | UI Owner | System of Record |
|---|---|---|---|---|
| Chatturn | Personal Memory (`raw`) | Claim-Extraction, `derived` | Chat-UI | Personal Raw Evidence |
| Tool-Output | Personal Memory (`raw`) | Claim-Extraction, evtl. global KG bei harter Weltevidenz | Chat-/Task-UI | Personal Raw Evidence |
| Session-Scratch-Note | Personal Memory (`raw`) | `derived` | Chat-/Workspace-UI | Personal Raw Evidence |
| Langzeit-Research-Note | Personal Knowledgebase | Embeddings, Entity-Links, evtl. `derived` | KB-/Notebook-UI | Personal Knowledgebase |
| Gespeicherter Artikel / Webclip | Personal Knowledgebase | Embeddings, Entity-Links, evtl. global evidence reference | KB-/Clipper-UI | Personal Knowledgebase |
| Private PDF | Personal Knowledgebase | Heavy ingestion, embeddings, entity links, evtl. `derived` | KB-/Library-UI | Personal Knowledgebase |
| YouTube / Podcast mit Transcript | Personal Knowledgebase | Transcript extraction, chunking, embeddings, evtl. global evidence reference | KB-/Clipper-UI | Personal Knowledgebase |
| Globale News / Filing / Marktbericht | Global World Model (`evidence`) | Claim extraction, KG write | Research-/Ops-UI | Global World Evidence |
| Markt-/Event-Claim | Global World Model (`KG`) | Conflict handling, support/conflict updates | Graph-/Ops-UI | Global World KG |
| Observation / Preference | Personal Memory (`derived`) | Evidence-joined retrieval | Memory-/Agent-UI | Personal Derived Memory |

Interpretation:

- `UI Owner` meint die natuerliche Bedienoberflaeche, nicht zwingend ein schon
  existierendes Modul.
- `System of Record` ist absichtlich nicht immer identisch mit dem ersten
  Erfassungsort.
- dieselbe Quelle darf referenziert werden, sollte aber nur **eine** primaere
  Wahrheitsschicht haben.

## Sinnvolle Reihenfolge des Ausbaus

### Phase 1: Begriffe und Schichten festziehen

Vor allem anderen:

1. explizite Layer-Doku
2. klare Schreibregeln
3. Privacy-/Scope-Modell pro Layer
4. record-of-truth pro Layer
5. alte Begriffe wie `fastlane` / `slowlane` explizit in die neue Architektur
   uebersetzen
6. `memory` vs `context` explizit trennen

Ohne diesen Schritt wird spaeter jeder Store ueberladen.

### Phase 2: Personal Raw vs Personal Derived sauber schneiden

Praktisch:

1. `memory_fusion` nicht mehr nur als summary/verbatim-Hindsight-Doppelpfad denken
2. echten personal raw evidence path definieren
3. Hindsight ausdruecklich als derived-only definieren
4. Agent-Output-Markierung einziehen
5. Observation nur mit Evidence-Backlinks surfacen

### Phase 3: Personal Knowledgebase als eigene Schicht etablieren

Praktisch:

1. bewusst gespeicherte Artefakte nicht still in `personal raw memory` werfen
2. KB-Inbox / Save-Flow / Import-Flow definieren
3. Trennung `session memory` vs `curated knowledge` technisch sichtbar machen
4. UI-/Capture-Muster fuer diese Schicht festlegen
5. `TriliumNext` explizit als UI-/UX-Referenz behandeln, nicht als Kern-Backend

### Phase 3b: Context-Policies explizit machen

Praktisch:

1. Consumer-Typen festhalten
2. Retrieval-Reihenfolgen definieren
3. Degradation-Flags definieren
4. Caps / Diversity / Evidence-Join als Runtime-Regeln festziehen
5. operative Schwellen spaeter in `exec-context.md` ziehen

### Phase 4: Ingestion entkoppeln von "direkt nur Hindsight"

Praktisch:

1. Ingestion-Output zuerst als Evidence behandeln
2. danach optional:
   - personal evidence
   - global evidence
   - claim extraction
   - KG write
   - Hindsight write

### Phase 5: Global World Evidence + globaler Vectorstore

Zuerst globalen Evidenz-Layer bauen, bevor der globale KG zu ambitioniert wird.

Warum:

- man braucht primaere weltbezogene Evidenz
- semantischer Zugriff muss moeglich sein
- KG ohne gute Evidence-Basis wird zu frueh spekulativ

### Phase 6: Global World KG

Erst dann:

1. minimale Ontologie
2. Claim/Source/Entity/Event/Asset
3. Provenance- und Konfliktlogik
4. Relationstypen klein, aber sauber halten

### Phase 7: Claim-Layer und Unsicherheitsmodell

Parallel zu 4/5 oder direkt danach:

1. `RawMemory -> Claim`
2. `Claim -> Observation`
3. `Claim -> World KG`
4. support/conflict/freshness/status

### Phase 7b: Confidence Dampening + Self-Baking + Access Policy

Praktisch:

1. Confidence-Caps und Decay-Regeln einfuehren
2. episodische / rohe Daten periodisch in stabilere Schichten aggregieren
3. Baking strikt additiv halten
4. `MemoryAccessPolicy` fuer zentrale Agent-/Consumer-Rollen definieren
5. Anti-Bias-Loop-Regeln runtime-verbindlich machen

### Phase 8: `extraction_layout` und `kg_pipeline` erwachsen machen

Praktisch:

1. echte Remote-Extractor aktivieren
2. JSON-zu-`ExtractedDocument` vollenden
3. KG-Typen und worker wirklich ausarbeiten
4. spaeter RAPTOR / hierarchical chunking / late chunking

## Konkrete Anforderungen fuer Unsicherheit

### Pro Raw Evidence

Noetige Felder:

- `source_type`
- `source_ref`
- `source_quality_prior`
- `source_scope`
- `ingested_at`
- `event_time`
- `retrieval_score`
- `verbatim_ref`

### Pro Claim

Noetige Felder:

- `claim_text`
- `claim_type`
- `derived_from_ids`
- `extraction_confidence`
- `entity_link_quality`
- `contradiction_risk`
- `scope`

### Pro Observation / Belief

Noetige Felder:

- `support_count`
- `conflict_count`
- `source_diversity`
- `recency_weight`
- `freshness_score`
- `provenance_completeness`
- `status`

Empfohlene Status:

- `candidate`
- `supported`
- `stable`
- `conflicted`
- `stale`
- `deprecated`

### Query-time Regel

Finale Antwort sollte idealerweise enthalten:

- Top Observations
- Top Raw Evidences
- Konfliktflags
- KG-Status / Claim-Status

Nicht:

- Observation-only answer

### Erste Arbeitsformel fuer Evidence-Score

Als pragmatischer Startpunkt aus `Memory_with_Uncertainty`:

```text
evidence_score =
log(1 + support_count)
* source_diversity_factor
* recency_factor
/ (1 + conflict_count)
```

Wichtig:

- das ist kein metaphysischer Wahrheits-Score
- es ist ein Runtime-/Promotion-Hilfswert
- die genaue Formel kann spaeter pro Layer / Domain differenziert werden

### Promotion- und Demotion-Gates

Ein sinnvoller Minimalpfad ist:

- `Raw Evidence -> Claim`
- `Claim -> Observation`
- `Observation -> Mental Model`

Mit harten Gates:

#### Claim -> Observation

Nur wenn:

- `support_count >= 3`
- `source_diversity >= 2`
- `conflict_count <= 1`
- `entity_link_quality` ueber Mindestschwelle

#### Observation -> Stable

Nur wenn:

- ueber Zeit bestaetigt
- keine starke aktuelle Gegenquelle
- hohe Provenance-Vollstaendigkeit

#### Stable -> Mental Model

Nur wenn:

- haeufig gebraucht
- ausreichend frisch
- kuratiert oder validiert
- als Query-Accelerator wirklich nuetzlich

#### Demotion

Runterstufen wenn:

- frische Gegenbelege auftauchen
- Evidenz veraltet
- Source-Diversity zu schmal bleibt
- Provenance-Luecken sichtbar werden

### Confidence Dampening / Anti-Feedback-Loop

Aus der aelteren `MEMORY_ARCHITECTURE.md` bleibt dieses Prinzip sehr wertvoll:

- Confidence-Increment mit Hard-Cap
- Fehler senken Confidence staerker als Erfolge sie heben
- monatlicher Baseline-Decay fuer nicht-strukturelle Knoten/Kanten
- Mindestconfidence statt hartem Loeschen

Praktischer Start:

- Cap bei `0.95`
- Decrement strenger als Increment
- monatlicher Decay fuer event-/hypothesennahe Kanten
- strukturelle Kanten koennen langsamer oder gar nicht decayn

Ziel:

- Self-Fulfilling Prophecy vermeiden
- Re-Validierung erzwingen
- historische Information behalten, ohne sie immer gleich stark zu gewichten

### Self-Baking

Aus `MEMORY_ARCHITECTURE.md` bleibt auch `Self-Baking` wichtig:

- rohe, hochentropische episodische Daten bleiben im Evidence-/Episodic-Layer
- periodische Jobs aggregieren sie zu kompakteren, stabileren Claims oder
  KG-Statistiken
- Baking ist additiv, nicht destruktiv

Das heisst:

- Roh-Eintraege bleiben fuer Audit und Debugging erhalten
- gebackene Ergebnisse gehen in stabilere Schichten
- Baking ersetzt keine Primarevidenz

### MemoryAccessPolicy / Layer-Zugriff

Nicht jeder Agent und nicht jeder Consumer sollte jede Schicht gleich lesen oder
schreiben duerfen.

Noetig sind mindestens Regeln fuer:

- wer `personal raw evidence` lesen darf
- wer `personal derived memory` schreiben darf
- wer `personal knowledgebase` aendern darf
- wer `global world kg` promoten oder invalidieren darf

Die praktische Konsequenz:

- Context Assembly ist auch eine **Policy-Entscheidung**
- nicht nur eine Relevance-Entscheidung
- die Root-SSOT liegt in `main_docs/root/AGENT_ARCHITECTURE.md`,
  `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md`,
  `main_docs/root/AGENT_SECURITY.md` und `main_docs/root/AGENT_HARNESS.md`
- `exec-memory.md` und `exec-context.md` referenzieren diese Root-Docs und
  duplizieren die Policy-/Harness-Regeln nicht erneut

## Was ich fuer die naechsten Iterationen explizit beachten wuerde

### 1. Nicht alles im Namen "Memory" zusammenziehen

`memory`, `ingestion`, `kg`, `vectorstore`, `world model`, `reflect`,
`observation`, `event graph` sind unterschiedliche Dinge.

### 2. Kein stiller Truth-Upgrade

Nichts sollte automatisch passieren wie:

- user says X
- agent stores X
- observation says X
- system behandelt X als Weltwahrheit

### 3. Global und personal muessen technisch isolierbar sein

Mindestens logisch, spaeter wahrscheinlich auch physisch:

- andere Stores / Schemas / Namespaces / privacy scopes

### 3b. Personal Memory und Personal Knowledgebase muessen ebenfalls getrennt sein

Auch im persoenlichen Bereich gibt es zwei verschiedene Arbeitsmodi:

- `memory`
  - was waehrend Interaktion passiert
- `knowledgebase`
  - was der User absichtlich kuratiert

Wenn beides in denselben Write-Pfad faellt, werden spaeter Recall, Privacy,
Ownership und UI schnell unklar.

### 4. Heavy ingestion kostet mehr und muss nicht fuer jeden Chatturn laufen

Das spricht klar dafuer, normale Chat-/Tool-Episoden anders zu behandeln als
schwere Artefakte.

### 5. Trotzdem darf "im Chat auftauchendes PDF" nicht als bloesser Chatturn gelten

Das Artefakt bleibt ein Artefakt und sollte ueber heavy ingestion laufen.

### 6. Hindsight intern darf nicht zum Weltmodell mutieren

Hindsight ist stark fuer persoenliches / agentisches Learned Memory.
Es ist nicht dein globaler Market-/Politics-KG.

### 7. Der alte persoenliche Fastlane-Gedanke ist heute weitgehend absorbiert

Wenn `fastlane` urspruenglich den persoenlichen, schnellen Arbeitsraum meinte,
dann wird das heute zu grossen Teilen schon getragen von:

- MemPalace-/Evidence-Logik fuer raw Episoden
- Hindsight fuer derived Learnings

Deshalb sollte man nicht vorschnell einen dritten persoenlichen Hauptstore
einziehen, bevor die Luecken zwischen raw und derived wirklich sichtbar sind.

### 7b. Trotzdem braucht kuratierte persoenliche Wissenssammlung eine eigene Heimat

Der vorige Punkt gilt fuer einen abstrakten `fastlane`.
Er gilt **nicht** dagegen, bewusst gespeicherte persoenliche Wissensartefakte
einfach in Session-Memory zu schieben.

Fuer:

- Clips
- Bookmarks
- PDFs
- YouTube-Transcripts
- Research-Notizen

ist eine `Personal Knowledgebase` die klarere Heimat.

### 8. MemPalace-Ideen sind wertvoll, aber nicht automatisch ausreichend

Method-of-Loci, raw/verbatim, scoped retrieval und spatial hierarchy sind
nuetzlich. Sie loesen aber:

- keine globale Ontologie
- keine globale Konfliktlogik
- keine World-Claim-Adjudication

### 9. Bayesian RAG eher als Modul denn als Zielarchitektur sehen

Bayesian / uncertainty-aware retrieval kann spaeter sehr nuetzlich werden,
insbesondere fuer:

- Reranking
- Konflikt-sensitive Antwortselektion
- Confidence-Anzeige

Aber:

- es heilt keine vermischten Layer
- es ersetzt keine Claim-/Evidence-Struktur
- es ersetzt kein sauberes World Model

### 10. TriliumNext als UI-/UX-Referenz, nicht als Backend-Abkuerzung sehen

`TriliumNext` ist interessant fuer:

- Tree-/Notebook-UI
- Web-Clipper-Flows
- Inbox-Denken
- persoenliche Wissensnavigation

Aber:

- der TypeScript-Backend-Stack loest nicht automatisch unsere Python-seitige
  Trennung von Memory / KB / KG
- UI-Inspiration ist wertvoller als Backend-Uebernahme

### 11. Paperwatcher-Importe ehrlich als Zwischenzustand behandeln

Die Uebernahmen sind sinnvoll, aber noch keine fertige, tiefe Eigenarchitektur.

## Minimaler Zielzustand, der zuerst erreicht werden sollte

Wenn nicht alles gleichzeitig gebaut werden soll, dann ist dies der sinnvolle
Minimalplan:

1. **Personal raw evidence sauber definieren**
2. **Personal derived memory sauber definieren**
3. **Personal knowledgebase sauber definieren**
4. **Memory vs Context sauber trennen**
5. **Ingestion aus direkter Hindsight-Kopplung loesen**
6. **Global world evidence + vectorstore anlegen**
7. **Minimalen globalen KG auf Claim-/Entity-/Event-Basis anlegen**
8. **Unsicherheits-, Dampening- und Konfliktmodell einfuehren**

Alles andere kann danach iterativ wachsen.

## Konkrete offene Fragen

1. Soll personal raw evidence voll in Postgres/pgvector leben oder teilweise
   weiter ein separater lokaler Store bleiben?
2. Wie stark soll personal raw evidence von global world evidence technisch
   isoliert werden?
3. Soll `personal knowledgebase` einen eigenen Store / Namespace / UI bekommen
   oder nur eine logische Schicht ueber denselben Artefaktstores sein?
4. Wie stark soll `personal knowledgebase` von `personal memory` technisch
   isoliert werden?
5. Welche Teile von `TriliumNext` wollen wir nur als UI-/UX-Muster uebernehmen
   und welche bewusst nicht?
6. Welche Context-Consumer brauchen eigene Retrieval-Policies statt einer
   gemeinsamen Default-Pipeline?
7. Welche Degradation-Flags und Policy-Gates muessen fuer produktive Runtime
   verpflichtend sein?
8. Wird der globale KG einen eigenen Graph-DB-Store bekommen oder zuerst als
   relationale/JSON-hybride Schicht starten?
9. Welche Artefakttypen sollen "global by default" vs "personal by default"
   sein?
10. Welche Validator-/Promotion-Regeln sind fuer Welt-Claims stricter als fuer
   persoenliche Observations?
11. Wie weit soll Hindsight-Mental-Model-Nutzung produktiv gehen, wenn
   `Memory_with_Uncertainty` Derived-only plus Evidence-Join fordert?

## Meine Empfehlung in einem Satz

Die saubere Matrix-Architektur ist wahrscheinlich:

> **heavy ingestion fuer Artefakte, MemPalace-/Evidence-Layer fuer rohe
> persoenliche Episoden, Hindsight fuer abgeleitete persoenliche Learnings,
> eine separate Personal Knowledgebase fuer bewusst gespeicherte user-eigene
> Wissensartefakte, globaler Vectorstore fuer Welt-Evidenz und ein separater
> globaler KG fuer strukturierte Welt-Claims und Relationen.**

Ein separater globaler `fastlane` ist in diesem Zielbild nicht
Pflichtbestandteil.

Nicht:

> ein grosser gemeinsamer "Memory/KG"-Topf.

## Direkt gelesene interne Quellen

### Spezifikationen / Dokumente

- `Memory_with_Uncertainty`
- `specs/execution/exec-memory.md`
- `main_docs/root/MEMORY_ARCHITECTURE.md`
- `main_docs/root/UNIFIED_INGESTION_LAYER.md`
- `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md`
- `main_docs/root/CONTEXT_ENGINEERING.md`
- `main_docs/specs/data/DATA_ARCHITECTURE.md`
- `python-backend/experiments/memory_eval/README.md`
- `python-backend/experiments/memory_eval/BENCHMARK_COVERAGE.md`

### Memory / Fusion

- `python-backend/memory_fusion/engine.py`
- `python-backend/memory_fusion/fusion_engine.py`
- `python-backend/memory_fusion/providers.py`
- `python-backend/memory_fusion/summary_builder.py`
- `python-backend/memory_fusion/loci.py`
- `python-backend/memory_fusion/mempalace_engine.py`

### Ingestion / Extraction / KG

- `python-backend/ingestion/worker.py`
- `python-backend/ingestion/pipelines/document.py`
- `python-backend/ingestion/pipelines/note.py`
- `python-backend/ingestion/pipelines/link.py`
- `python-backend/ingestion/core/config.py`
- `python-backend/ingestion/core/types.py`
- `python-backend/ingestion/extractors/base.py`
- `python-backend/ingestion/extractors/__init__.py`
- `python-backend/ingestion/extractors/pymupdf_ext.py`
- `python-backend/ingestion/extractors/remote.py`
- `python-backend/ingestion/chunkers/token_chunker.py`
- `python-backend/ingestion/tracking/dedup.py`
- `python-backend/ingestion/sinks/hindsight_sink.py`
- `python-backend/ingestion/sinks/storage_sink.py`
- `python-backend/ingestion/sinks/kg_sink.py`
- `python-backend/extraction_layout/worker.py`
- `python-backend/kg_pipeline/core/types.py`
- `python-backend/agent/control/ingestion.py`

## Direkt gelesene angrenzende Projektquellen

Diese Quellen liegen ausserhalb dieses Repos, wurden aber fuer die Einordnung
dieses Dokuments direkt gelesen:

- `/home/lipfi/code/trading-project/docs/BIG_PICTURE.md`
- `/home/lipfi/code/trading-project/docs/MEMORY_ARCHITECTURE.md`
- `/home/lipfi/code/trading-project/docs/UNIFIED_INGESTION_LAYER.md`
- `/home/lipfi/code/trading-project/docs/RAG_GRAPHRAG_STRATEGY_2026.md`
- `/home/lipfi/code/trading-project/docs/archive/KG_MERGE_AND_OVERLAY_ARCHITECTURE.md`
- `/home/lipfi/code/trading-project/docs/archive/MASTER_ARCHITECTURE_SYNTHESIS_2026.md`
- `/home/lipfi/code/trading-project/docs/archive/ai_retrieval_knowledge_infra_full.md`
- `/home/lipfi/code/trading-project/docs/geo/GEOMAP_ONTOLOGY_GRAPH_RUNTIME.md`

## Direkt gelesene externe Quellen

### MemPalace

- `https://mempalace.net/`

Wesentliche verwendete Punkte:

- verbatim storage
- wings / rooms / halls / closets / drawers
- local-first positioning
- raw-memory / retrieval Fokus

### Hindsight

- `https://hindsight.vectorize.io/`
- `https://hindsight.vectorize.io/developer/reflect`
- `https://hindsight.vectorize.io/developer/observations`

Wesentliche verwendete Punkte:

- retain / recall / reflect
- memory hierarchy
- observations
- mental models
- reflect priority
- evidence grounding / freshness

### Recall

- `https://www.recall.it/`
- `https://docs.getrecall.ai/getting-started/2-add-content`

Wesentliche verwendete Punkte:

- persoenliche AI-Knowledgebase als Produktidee
- Browser-/Mobile-Capture
- YouTube mit Transcript
- PDFs / Webseiten / Notes
- Chat / Summaries / Graph-Ansichten

### TriliumNext

- `https://github.com/TriliumNext/Trilium`
- `https://docs.triliumnotes.org/user-guide/setup/web-clipper`

Wesentliche verwendete Punkte:

- self-hosted persoenliche Knowledgebase / PKM
- Web Clipper
- Tree / Outliner / Inbox-Naehe
- Notes / Labels / Attributes
- starke UI-/UX-Referenz fuer eine persoenliche KB, ohne deren Backend zum
  zentralen Runtime-Stack machen zu muessen

### Survey

- `https://arxiv.org/abs/2603.07670`
- `https://arxiv.org/html/2603.07670v1`

Wesentliche verwendete Punkte:

- memory als write-manage-read loop
- retrieval / reflective memory / hierarchical memory / control policy
- engineering realities
- contradiction handling
- trustworthy reflection

## Sekundaere Referenzen, die im Projektkontext relevant sind

Diese wurden im Gespraech und in bestehenden Projekttexten als relevant
identifiziert, aber fuer dieses Dokument nicht alle gleich tief direkt
nachrecherchiert:

- `_ref/mempalace/`
- `_ref/hindsight/`
- `paperwatcher` als Herkunft mehrerer Ingestion-Bausteine
- moegliche spaetere Ontologie-/World-KG-Bausteine wie Wikidata, GeoNames,
  GDELT/CAMEO, FIBO, OpenAlex

## Abschlusshinweis

Die wichtigste Leitplanke fuer alle naechsten Umbauten lautet:

> **Nicht zuerst Speichertechnologie vereinheitlichen, sondern erst
> Erkenntnisebenen trennen.**

Anders gesagt:

- zuerst epistemische Ordnung
- dann Write-Pfade
- dann Stores
- dann Performance / Fancy Retrieval

Sonst landet zu viel Unterschiedliches in derselben Schicht und spaeter wird
jedes Eval, jede Privacy-Frage und jede Konfliktlogik unnötig schwer.
