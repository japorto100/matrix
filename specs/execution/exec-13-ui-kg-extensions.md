# exec-13: UI + Knowledge Graph Extensions

**Datum:** 30.03.2026
**Status:** Geplant
**Abhaengig von:** exec-11 (Hindsight Memory Engine) ✅, exec-09 (MCP/Generative UI) ✅
**Referenz-Repos:** `_ref/hindsight`, `_ref/supermemory` (UI-Referenz), `_ref/graphiti`, `_ref/cognee`

---

## Kontext

Aus exec-11 ausgelagerte Features die ueber die Core-Memory-Engine hinausgehen:
- **Graphiti/Cognee:** Knowledge Graph Layer als Hindsight Extension
- **Memory Graph Visualisierung:** Interaktive Graph-UI (Supermemory-Referenz)
- **Control Panel:** Hauptprojekt-Settings, Memory-Dashboard, Agent-Config
- **Content Ingestion:** Dokumente/Files → Memory Engine Pipeline

---

## Phase 1: Graphiti als Custom GraphRetriever

### 1.1 Graphiti Integration
Hindsight bietet `GraphRetriever(ABC)` als Extension Point:
- [ ] `GraphitiRetriever` implementieren (nutzt Graphiti's Temporal Knowledge Graph)
- [ ] Graphiti installieren (`pip install graphiti-core`)
- [ ] Neo4j oder FalkorDB als Graph-Backend evaluieren
- [ ] Temporal Edges: Fakten haben Zeitstempel, alte werden invalidiert
- [ ] Entity Resolution: Graphiti's eigene Entity-Merging-Pipeline

### 1.2 Cognee als Structured Knowledge Layer
- [ ] Cognee installieren (`pip install cognee`)
- [ ] Document → Knowledge Graph Pipeline (PDF, Markdown, Code)
- [ ] Cognee's LLM-basierte Triplet Extraction
- [ ] Integration mit Hindsight: Cognee Facts als `world` Memories retainen

### 1.3 Unified Search API
- [ ] RRF Fusion ueber alle Backends (Hindsight + Graphiti + Cognee)
- [ ] Fallback-Kette: Hindsight (immer) → Graphiti (wenn Neo4j) → Cognee (wenn konfiguriert)
- [ ] Search API Endpoint: `/api/memory/search?q=...&backends=all`

---

## Phase 2: Memory Graph Visualisierung

### 2.1 Graph Component (Supermemory-Referenz)
`_ref/supermemory/packages/memory-graph/` als UI-Referenz:
- [ ] React Force-Graph oder react-flow fuer Memory-Graph Darstellung
- [ ] Nodes: Facts, Entities, Observations, Skills
- [ ] Edges: Temporal, Semantic, Entity, Causal Links
- [ ] Zoom/Pan/Filter (nach Zeitraum, Memory-Typ, Rolle)

### 2.2 Memory Timeline
- [ ] Chronologische Ansicht aller Memories pro User
- [ ] Consolidation-History: Fakt → Observation → Skill Kette sichtbar
- [ ] Memory-Qualitaet Indikatoren (Confidence, Freshness, Relevance)

### 2.3 Agent-Chat Integration
- [ ] Memory-Panel im AgentChatPanel (neben tldraw Canvas)
- [ ] Inline Memory-Referenzen in Agent-Responses (klickbar)
- [ ] "Warum weisst du das?" → zeigt Memory-Source

---

## Phase 3: Control Panel

### 3.1 Agent Configuration UI
- [ ] Rollen-Konfiguration (Trading Roles) — UI fuer `roles.py` Einstellungen
- [ ] Skill-Management: Skills aktivieren/deaktivieren, Personal Skills bearbeiten
- [ ] Memory-Settings: Retain an/aus, Recall-Budget, Tag-Filter

### 3.2 Memory Dashboard
- [ ] Memory-Statistiken: Anzahl Facts, Observations, Entities pro User
- [ ] Consolidation-Status: Pending Tasks, Worker Health
- [ ] Memory-Suche mit Facetten (Typ, Rolle, Zeitraum, Entitaet)

### 3.3 Project Settings
- [ ] ENV-Variablen Editor (read-only Anzeige + sichere Aenderungen)
- [ ] Service-Status: PostgreSQL, NATS, LiveKit, Agent, Bridge
- [ ] Log-Viewer mit Filter

---

## Phase 4: Content Ingestion

### 4.1 Filesystem Integration
- [ ] Hauptprojekt: File Upload → Agent verarbeitet
- [ ] Unterstuetzte Formate: PDF, Markdown, CSV, JSON, Code
- [ ] Chunking-Strategie: Semantic Splitting (nicht fixed-size)

### 4.2 Document → Memory Pipeline
- [ ] Upload → Cognee Extraction → Hindsight Retain
- [ ] Metadata: Dateiname, Upload-Datum, User-ID als Tags
- [ ] Deduplizierung: document_id basiert auf Content-Hash

### 4.3 exec-05b Bridge (Messaging → Memory)
- [ ] NATS Messages → Memory Engine (selektiv, nicht alle)
- [ ] Filter: nur Agent-relevante Conversations retainen
- [ ] Bridge-Config: welche Rooms/Channels → Memory

---

## Verify-Gates

### Gate 1: Graphiti/Cognee
- [ ] GraphitiRetriever registriert und liefert Ergebnisse
- [ ] Cognee Document-Pipeline: PDF → Facts in Hindsight
- [ ] Unified Search: Query liefert Ergebnisse aus allen Backends

### Gate 2: Visualisierung
- [ ] Memory Graph rendert im Browser (>50 Nodes fluessig)
- [ ] Timeline zeigt Memories chronologisch
- [ ] Klick auf Memory-Node zeigt Details + Source

### Gate 3: Control Panel
- [ ] Agent-Rollen konfigurierbar via UI
- [ ] Memory-Dashboard zeigt aktuelle Statistiken
- [ ] Service-Status korrekt angezeigt

### Gate 4: Content Ingestion
- [ ] File Upload → Fakten in Memory (E2E)
- [ ] Deduplizierung: gleiche Datei zweimal hochladen → keine Duplikate
- [ ] NATS Bridge: Agent-Messages → Memory (selektiv)

---

## Phase 5: Computer Use (verschoben aus exec-12, 01.04.2026)

### 5.1 Playwright MCP (Browser Automation)

- [ ] **5.1.1:** Playwright MCP Server im Agent-Stack
  - 33+ Tools (Navigate, Click, Type, Screenshot, Accessibility Tree)
  - Agent kann Websites bedienen
- [ ] **5.1.2:** Playwright CLI als Alternative (4x weniger Tokens)
  - Fuer wiederholbare Flows (CI/CD, Testing)
  - MCP fuer explorative Tasks
- [ ] **5.1.3:** Integration in Sandbox (exec-12 Phase 1)
  - Playwright laeuft innerhalb OpenSandbox Container
  - Isoliert vom Host-Browser

### 5.2 WebMCP

- [ ] **5.2.1:** WebMCP Spec beobachten
- [ ] **5.2.2:** Trading-Pages exposen Capabilities via `navigator.modelContext`
  - Chart-State, Portfolio-Daten, Indikator-Werte als Tools
  - Agent ruft sie nativ auf (kein DOM-Scraping)

### 5.3 Anthropic Computer Use (Evaluation)

- [ ] **5.3.1:** Evaluieren fuer Desktop-Agent Use-Cases
  - Claude sieht Screen + klickt (Cloud-side)
  - Aktuell nicht prioritaer

## Phase 6: Artifacts UI (verschoben aus exec-12, 01.04.2026)

- [ ] **6.1:** E2B Fragments als UI-Inspiration
  - Artifacts-Style: Agent generiert Code → Preview im Chat
  - Split-View: Code links, Output rechts
- [ ] **6.2:** Sandpack fuer leichtgewichtige Browser-Previews
  - Kein Server noetig, laeuft komplett im Browser
  - React/JS Code-Previews direkt im Chat
- [ ] **6.3:** OpenSandbox fuer schwere Execution
  - Python Data-Analysis, File-Processing, API Calls
  - Results als Artifacts im Chat (Charts, Tables, Files)

---

## Referenzen

- `_ref/supermemory/packages/memory-graph/` — UI-Referenz fuer Graph Component
- `_ref/graphiti/` — Temporal Knowledge Graph (Zep)
- `_ref/cognee/` — Structured Knowledge Layer
- Hindsight Extension Points: `GraphRetriever(ABC)`, `MemoryEngineInterface(ABC)`
