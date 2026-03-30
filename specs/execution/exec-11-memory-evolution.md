# exec-11: Memory + Self-Evolution (Supermemory + MetaClaw Pattern + ACP)

**Datum:** 30.03.2026
**Status:** Geplant
**Abhaengig von:** exec-10 (Multi-Agent, LangGraph)
**Spec:** `specs/agent-ui/06-protocols-roadmap.md`

---

## Phase 1: Supermemory Integration

- [ ] **1.1:** Supermemory evaluieren (API vs Self-Hosted)
  - API: supermemory.ai (Cloud, <300ms Retrieval, 100B+ Tokens/Monat)
  - Self-Hosted: Open Source Core
- [ ] **1.2:** Supermemory SDK in `python-backend/` einbinden
  - `pip install supermemory` (Python SDK)
  - Oder REST API direkt
- [ ] **1.3:** Memory-Service (`python-backend/memory/`) anbinden
  - Supermemory als primärer Store ODER ergaenzend zu KuzuDB/ChromaDB
  - Auto-Extraction aus Agent Conversations
  - Deduplication + Profile Building
- [ ] **1.4:** `supermemory-mcp` MCP Server einrichten
  - Agent greift auf Memory zu via MCP Standard
  - Kompatibel mit `use-mcp` Hook im Frontend
- [ ] **1.5:** Memory Graph Visualisierung in Agent UI
  - Supermemory bietet Graph-Visualisierung
  - In tldraw Canvas oder eigenes Panel einbetten

## Phase 2: MetaClaw Skill-Evolution Pattern

- [ ] **2.1:** Skills-Library in `python-backend/agent/skills/`
  - Manuell erstellte Skills (Markdown .md Files, deer-flow Pattern)
  - Automatisch generierte Skills (MetaClaw Pattern)
- [ ] **2.2:** Failure-to-Skill Pipeline
  - Agent schlaegt fehl → Failure-Trajectory wird gespeichert
  - LLM-Evolver analysiert Trajectory → destilliert zu kompaktem Skill
  - Skill wird in Library gespeichert (Supermemory oder lokal)
  - Format: `{ trigger: "...", instruction: "...", examples: [...] }`
- [ ] **2.3:** Skill-Retrieval per Task
  - Embedding-basierte Similarity-Search
  - Top-K Skills werden als System-Prompt Addon injiziert
  - Sofort wirksam, kein Fine-Tuning
- [ ] **2.4:** Skill-Versioning
  - Skills haben Version + Timestamp
  - Veraltete Skills werden nach N erfolglosen Anwendungen degradiert
  - Erfolgreiche Skills werden hoeher gewichtet

## Phase 3: ACP Agent Memory Sharing

- [ ] **3.1:** ACP Protocol evaluieren (IBM/Linux Foundation, BeeAI)
- [ ] **3.2:** Memory-Sharing zwischen Trading-Agents
  - Agent A findet RSI-Anomalie → teilt via ACP mit Agent B
  - Agent B hat Kontext ohne eigene Analyse
- [ ] **3.3:** Shared Memory Store
  - Zentraler Store auf den alle Agents zugreifen koennen
  - Read/Write Permissions per Agent-Rolle
- [ ] **3.4:** Memory Decay / Relevance Scoring
  - Aeltere Memories verlieren Relevanz ueber Zeit
  - Scoring basierend auf Nutzungshaeufigkeit + Erfolgsrate

---

## Verify-Gates

- [ ] Supermemory: Agent speichert Conversation-Erkenntnisse, retrievet sie in naechster Session
- [ ] Auto-Skill: Agent versagt bei Task → neuer Skill generiert → naechster Versuch erfolgreich
- [ ] Skill-Retrieval: Relevante Skills werden korrekt per Embedding-Search gefunden
- [ ] Memory Graph: Visualisierung zeigt Agent-Wissen als vernetzte Nodes
- [ ] ACP Sharing: Agent A's Erkenntnis ist fuer Agent B ohne Re-Analyse verfuegbar
