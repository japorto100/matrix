# exec-10: Multi-Agent Orchestrierung (LangGraph + A2A + deer-flow Skills)

**Datum:** 30.03.2026
**Status:** Geplant
**Abhaengig von:** exec-08 (Python Backend), exec-09 (Protokolle)
**Spec:** `specs/agent-ui/06-protocols-roadmap.md`

---

## Phase 1: LangGraph Einfuehrung

- [ ] **1.1:** `langgraph` + `langchain-core` in `python-backend/pyproject.toml`
- [ ] **1.2:** `agent/loop.py` als LangGraph Graph refactoren
  - Bestehender manueller Loop → Graph mit Nodes (LLM Call, Tool Execution, Response)
  - Checkpointing aktivieren (Agent kann pausieren/resumieren)
  - Fallback: manueller Loop bleibt als Option
- [ ] **1.3:** State Management zwischen Graph-Nodes
  - Conversation History, Tool Results, Agent Decisions
- [ ] **1.4:** Sub-Agent Spawning Grundlage
  - LangGraph kann Sub-Graphs aufrufen (z.B. Research Sub-Agent)

## Phase 2: Trading-Agent Rollen (TradingAgents-Pattern)

- [ ] **2.1:** Rollen-Definition (inspiriert von TauricResearch/TradingAgents):
  - Fundamentals Analyst
  - Sentiment Analyst
  - Technical Analyst
  - Researcher
  - Trader
  - Risk Manager
- [ ] **2.2:** Jede Rolle als eigener LangGraph Sub-Graph
  - Eigener System-Prompt, eigene Tools, scoped Context
- [ ] **2.3:** Orchestrator-Graph der Rollen koordiniert
  - Task Decomposition: User-Anfrage → relevante Rollen aktivieren
  - Ergebnisse aggregieren → Response

## Phase 3: deer-flow Skills System

- [ ] **3.1:** `python-backend/agent/skills/` Ordner erstellen
- [ ] **3.2:** Skills als Markdown `.md` Files (deer-flow Pattern)
  - Workflow-Beschreibung + Best Practices + Referenzen
  - Beispiel: `skills/trading-analysis.md`, `skills/risk-assessment.md`
- [ ] **3.3:** Skill-Loader: Skills per Task retrieven und ins Prompt injizieren
- [ ] **3.4:** MetaClaw-Pattern: Auto-Skill-Generation aus Failure-Trajectories
  - Agent schlaegt fehl → LLM analysiert → neuer Skill wird generiert
  - Skill in Library gespeichert → naechstes Mal automatisch injiziert
- [ ] **3.5:** Temporal Context (last30days Pattern)
  - Agent bekommt automatisch zeitbasierten Kontext
  - Letzte Trades, Portfolio-Aenderungen, Market Events

## Phase 4: A2A Protocol

- [ ] **4.1:** A2A SDK evaluieren (Google, gRPC, Agent Cards)
- [ ] **4.2:** Agent Cards fuer unsere Agents definieren (Capabilities, Endpoints)
- [ ] **4.3:** Inter-Agent Delegation: Trading-Agent delegiert Research an Research-Agent
- [ ] **4.4:** ACP Memory Sharing evaluieren (IBM)
  - Agents teilen Erkenntnisse ohne Context Window Overhead

---

## Verify-Gates

- [ ] LangGraph: Agent-Loop laeuft als Graph (nicht manueller while-Loop)
- [ ] Checkpointing: Agent kann nach Tool-Call pausieren und spaeter resumieren
- [ ] Sub-Agent: Orchestrator delegiert Research-Task an Research Sub-Agent
- [ ] Skill-Injection: Agent bekommt relevante Skills aus Library per Prompt
- [ ] Auto-Skill: Nach Failure wird neuer Skill automatisch generiert
- [ ] Temporal Context: Agent kennt letzte 30 Tage Aktivitaet
