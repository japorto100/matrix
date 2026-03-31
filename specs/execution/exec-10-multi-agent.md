# exec-10: Multi-Agent Orchestrierung (LangGraph + A2A + deer-flow Skills)

**Datum:** 30.03.2026 (Implementation 30-31.03.2026)
**Status:** Phase 1-4 implementiert — Verify-Gates ausstehend
**Abhaengig von:** exec-08 (Python Backend) ✅, exec-09 (Protokolle) ✅
**Referenz-Repos:** `_ref/TradingAgents`, `_ref/deer-flow`, `_ref/MetaClaw`, `_ref/A2A`

---

## Phase 1: LangGraph Grundlage

- [x] **1.1:** Dependencies ✅
  - `langgraph>=0.4.0` + `langchain-core>=0.3.0` in pyproject.toml
  - `uv sync` erfolgreich

- [x] **1.2:** Agent State Schema ✅
  - `agent/graph/state.py` — AgentGraphState(TypedDict)
  - ToolCall, ToolResult Typed Dicts
  - Reducer: messages (append), tool_results (append)

- [x] **1.3:** LangGraph Agent Graph ✅
  - `agent/graph/agent_graph.py` — StateGraph mit 4 Nodes
  - Nodes: llm_call → approval_gate → tool_execute → increment
  - Conditional edges: tool_calls → approval, sonst → END
  - Max iterations check, MemorySaver checkpointer
  - interrupt_before=["approval_gate"] fuer human-in-the-loop

- [x] **1.4:** Provider-agnostischer LLM Node ✅
  - `agent/graph/nodes/llm_node.py`
  - Unified: _call_anthropic, _call_openai, _call_litellm
  - Reasoning-Effort Support (Anthropic thinking budget)

- [x] **1.5:** Tool Execution Node ✅
  - `agent/graph/nodes/tool_node.py`
  - Parallel execution via asyncio.gather
  - Per-tool timeout (30s), validation, capability check
  - Wiederverwendet ToolRegistry + TradingTool ABC

- [x] **1.6:** Approval Gate Node ✅
  - `agent/graph/nodes/approval_node.py`
  - LangGraph `interrupt()` fuer human-in-the-loop
  - Prueft needs_approval() pro Tool

- [x] **1.7:** loop.py Refactoring ✅ (31.03.2026)
  - `run_agent_loop()` routet zu LangGraph Graph oder Legacy Loop
  - `_loop_langgraph()`: Graph erstellen, ausfuehren, Events als SSE streamen
  - `_loop_legacy()`: bestehender while-Loop (Anthropic/OpenAI/LiteLLM)
  - Skill Injection: `load_skills(user_id)` → `format_skills_for_prompt()` → System-Prompt
  - ENV: `AGENT_USE_LANGGRAPH=true` (default) vs `false` (legacy fallback)
  - LiteLLM weiterhin unterstuetzt in beiden Pfaden

---

## Phase 2: Trading-Agent Rollen

- [x] **2.1:** Rollen-Definitionen ✅
  - `agent/roles.py` erweitert: TradingRole Enum (6 Rollen)
  - TRADING_ROLE_PROMPTS: System-Prompt pro Rolle
  - TRADING_ROLE_TOOLS: erlaubte Tools pro Rolle
  - Rollen: Fundamentals, Sentiment, Technical, Researcher, Trader, RiskManager

- [x] **2.2:** Role-Specific Tool Filtering ✅
  - `ToolRegistry.filter_by_names(allowed)` — gibt gefilterte Registry zurueck
  - Fundamentals: get_portfolio_summary, get_chart_state, memory
  - Trader: alle read + set_chart_state (mit approval)

- [x] **2.3-2.4:** Orchestrator Graph ✅
  - `agent/graph/orchestrator.py`
  - Parallel: Fundamentals + Sentiment + Technical
  - Aggregate → Researcher → Trader → RiskManager → END
  - Role-Nodes mit rollen-spezifischem System-Prompt

---

## Phase 3: deer-flow Skills System

- [x] **3.1:** Skills Directory ✅
  - `agent/skills/trading-analysis/SKILL.md`
  - `agent/skills/risk-assessment/SKILL.md`
  - `agent/skills/market-research/SKILL.md`
  - YAML Frontmatter (name, description, category) + Markdown Body

- [x] **3.2:** 3-Tier Skill Loader ✅ (MetaClaw Insights)
  - `agent/skills/loader.py` — 3-Tier System:
    - Tier 1 Global: `agent/skills/global/` — von uns erstellt, fuer alle User
    - Tier 2 Team: `agent/skills/team/{team_id}/` — team-shared
    - Tier 3 Personal: `agent/skills/personal/{user_id}/` — auto-generiert pro User
  - Loading: Global → Team → Personal (Override-Semantik bei gleichem Name)
  - `load_skills(user_id, team_id, category)` — merged alle Tiers
  - Skill Dataclass: +tier, +owner, +generation (MetaClaw Versioning)

- [x] **3.3:** Skill Injection ✅
  - `format_skills_for_prompt(skills)` mit Tier-Badge [personal]/[team]
  - Per-Rolle: category matching (trading, risk, research)

- [x] **3.4:** Auto-Skill-Generation (MetaClaw Pattern) ✅
  - `agent/skills/evolver.py` — SkillEvolver mit 3-Tier Support
  - Generiert in `agent/skills/personal/{user_id}/{skill_name}/SKILL.md`
  - Skill Generation Versioning (MetaClaw Paper Sec. 3.2)
  - Deduplication via Failure-Hash (.failure_hash Datei)
  - TrajectoryLogger: loggt Agent-Sessions fuer PRM + Skill-Evolution
  - ENV: `AGENT_SKILL_EVOLUTION=true` (default false)

- [x] **3.5b:** RL Training Infrastruktur (deaktiviert) ✅
  - `agent/skills/rl_trainer.py` — 3 Komponenten:
    - ProcessRewardModel: LLM-as-Judge, scored Trajectories (0-10)
    - LoRATrainer: Fine-Tuning Infrastruktur (OpenAI API / Unsloth Self-Hosted)
    - IdleWindowDetector: OMLS Pattern (Training nur bei User-Inaktivitaet)
  - Alles deaktiviert via ENV:
    - `AGENT_PRM_ENABLED=false`
    - `AGENT_RL_ENABLED=false`
    - `AGENT_RL_BACKEND=openai` (oder `unsloth`)
    - `AGENT_RL_MIN_SAMPLES=50`
    - `AGENT_IDLE_THRESHOLD_MIN=30`

- [x] **3.5:** Temporal Context ✅ (31.03.2026)
  - `agent/temporal_context.py` — `get_temporal_context(user_id, lookback_hours=24)`
  - Liest letzte Trajectories aus `.trajectories/` Logs
  - Formatiert als "## Recent Activity" Abschnitt fuer System-Prompt
  - In `loop.py` neben Skills injiziert (beide optional, kein Fehler bei Failure)

---

## MetaClaw Paper Insights (arXiv 2603.17187)

### Zwei Lern-Schleifen
1. **Schnell (sofort):** Failure → Skill Evolver → SKILL.md → Prompt Injection ← implementiert
2. **Langsam (Stunden):** Trajectories → PRM Score → LoRA Fine-Tuning → besseres Model ← Infrastruktur da

### Wichtige Erkenntnisse
- **Per-User Skill Learning:** Jeder User baut eigene Skill-Library auf (Paper: "serves a user over a stream of tasks")
- **Federated Skill Sharing:** Zukunftsvision — anonymisierte Skills team-/org-uebergreifend teilen
- **Skill Generation Versioning:** Jede Trajectory gestempelt mit Generation-Index, alte Daten geflusht wenn Skill-Generation steigt
- **Deduplication:** Gleiche Failures erzeugen nicht doppelte Skills
- **OMLS:** Training nur in Idle-Windows (Schlaf, Keyboard-Idle >30min, Calendar)
- **Benchmarks:** Schwaeche Models profitieren mehr (+90% fuer Kimi-K2.5 vs +7% fuer GPT-5.2)

### SkillsMP Marketplace
Es existiert ein Community-Marketplace mit 66K+ Skills im SKILL.md Format (skillsmp.com).
Wir koennten Skills von dort importieren fuer Tier 1 (Global).

### Nicht CLI-Agent spezifisch
MetaClaw ist fuer CLI-Agents konzipiert (OpenClaw/CoPaw). Unsere Web-App Anpassungen:
- OMLS: Letzte API-Aktivitaet statt Keyboard-Idle
- Skill Storage: DB-backed statt Filesystem (spaeter)
- Multi-Tenant: 3-Tier System statt flat directory

---

## Phase 4: A2A Protocol (Grundlage)

- [x] **4.1:** Agent Cards ✅
  - `agent/a2a/agent_card.py`
  - AgentCard + AgentSkill Dataclasses
  - TRADING_AGENT_CARDS: 6 vordefinierte Cards
  - to_dict() fuer JSON Serialisierung

- [x] **4.2:** A2A Client ✅
  - `agent/a2a/client.py`
  - send_message(agent_url, message) → A2ATask
  - HTTP+JSON Transport (vereinfacht, kein gRPC)
  - SSE Response parsing

- [x] **4.3:** Inter-Agent Delegation ✅ (31.03.2026)
  - `agent/graph/nodes/a2a_node.py` — A2A Delegation Node
  - Remote-Agent URLs via ENV: `AGENT_REMOTE_{ROLE}=http://host:port`
  - Orchestrator kann lokal (Sub-Graph) oder remote (A2A) delegieren
  - A2A Client ruft Remote-Agent auf → SSE Response → State Update

- [x] **4.4:** ACP Memory Sharing evaluiert ✅ (31.03.2026)
  - ACP (IBM) ist seit Sept 2025 in A2A (Google) aufgegangen → Linux Foundation
  - "ACP Memory Sharing" war Missverstaendnis — ACP/A2A ist Message-Passing, nicht Memory-Sharing
  - Memory-Sharing zwischen Agents abgedeckt durch:
    - LangGraph shared AgentGraphState (lokal)
    - Supermemory (exec-11, zentraler Memory Store)
    - Working Memory M5 (Redis, session-basiert)
  - Kein separates Protokoll noetig

---

## Phase 5: deer-flow Patterns (zusaetzlich)

- [ ] **5.1:** Middleware Chain (deer-flow Pattern)
  - Ordered pipeline fuer Cross-Cutting Concerns
  - Kandidaten: Summarization, Guardrail, TodoList, DanglingToolCall
  - deer-flow hat 10+ Middlewares, wir uebernehmen selektiv
  - Ref: `_ref/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py:208-270`

- [ ] **5.2:** Skill Management REST API
  - `POST /api/v1/skills/install` — Skill installieren
  - `PUT /api/v1/skills/{name}` — Skill enable/disable
  - `GET /api/v1/skills` — Alle Skills listen (mit Tier + Status)
  - deer-flow Pattern: `_ref/deer-flow/backend/app/gateway/routers/skills.py`

- [ ] **5.3:** SkillsMP Import evaluieren
  - Community Marketplace mit 66K+ Skills (skillsmp.com)
  - SKILL.md Format kompatibel mit unserem Loader
  - Import-Script: GitHub Repo → agent/skills/global/

- [ ] **5.4:** Skill .skill ZIP Archive Support
  - deer-flow Pattern: ZIP mit SKILL.md + Scripts + Assets
  - Install via API oder CLI

- [ ] **5.5:** Context Summarization Middleware
  - Wenn Context-Window voll → aeltere Messages zusammenfassen
  - deer-flow: SummarizationMiddleware (auto-trigger bei Token-Limit)
  - Wichtig fuer lange Multi-Agent Sessions

---

## Verify-Gates

### Gate 1: LangGraph Grundlage
- [ ] `create_agent_graph()` kompiliert erfolgreich (CompiledStateGraph)
- [ ] Graph: LLM Call → Tool Call → Tool Execute → LLM → Response
- [ ] Approval Gate: interrupt() pausiert Graph, resume() setzt fort
- [ ] Max iterations: Graph stoppt nach 10 Iterationen
- [ ] Legacy fallback: AGENT_USE_LANGGRAPH=false nutzt alten Loop

### Gate 2: Trading-Rollen
- [ ] 6 Rollen mit eigenen System-Prompts
- [ ] Role-specific Tool Filtering: Fundamentals sieht nur 4 Tools
- [ ] Orchestrator: Parallel Analyse → Aggregate → Sequential Decision
- [ ] Researcher synthetisiert Bull/Bear Argumente

### Gate 3: Skills
- [ ] 3 SKILL.md Files geladen (trading-analysis, risk-assessment, market-research)
- [ ] Skills ins System-Prompt injiziert
- [ ] Auto-Skill-Generation: Failure → neuer SKILL.md in auto-generated/
- [ ] Generierter Skill wird beim naechsten Run geladen

### Gate 4: A2A
- [ ] Agent Cards als JSON serialisierbar
- [ ] A2A Client: send_message an lokalen Agent → Response
- [ ] Inter-Agent Delegation via Orchestrator

---

## Neue/Geaenderte Dateien

```
.gitignore                              — GEAENDERT: +_ref/
pyproject.toml                          — GEAENDERT: +langgraph, +langchain-core

agent/graph/__init__.py                 — NEU
agent/graph/state.py                    — NEU: AgentGraphState
agent/graph/agent_graph.py              — NEU: Haupt-Graph (4 Nodes)
agent/graph/orchestrator.py             — NEU: Multi-Agent Orchestrator (6 Rollen)
agent/graph/nodes/__init__.py           — NEU
agent/graph/nodes/llm_node.py           — NEU: Provider-agnostischer LLM Node
agent/graph/nodes/tool_node.py          — NEU: Parallel Tool Execution
agent/graph/nodes/approval_node.py      — NEU: Human-in-the-Loop (interrupt)

agent/roles.py                          — ERWEITERT: +TradingRole, +Prompts, +Tools
agent/tools/registry.py                 — ERWEITERT: +filter_by_names()

agent/skills/__init__.py                        — NEU
agent/skills/loader.py                          — NEU: 3-Tier Skill Loader + Formatter
agent/skills/evolver.py                         — NEU: Auto-Skill-Generation + TrajectoryLogger
agent/skills/rl_trainer.py                      — NEU: PRM + LoRA + OMLS (deaktiviert)
agent/skills/global/trading-analysis/SKILL.md   — NEU: Trading Analysis Skill
agent/skills/global/risk-assessment/SKILL.md    — NEU: Risk Assessment Skill
agent/skills/global/market-research/SKILL.md    — NEU: Market Research Skill
agent/skills/team/                              — NEU: Team-shared Skills (leer)
agent/skills/personal/                          — NEU: Per-User Skills (auto-generated)

agent/temporal_context.py                — NEU: Zeitbasierter Kontext (3.5)
agent/a2a/__init__.py                   — NEU
agent/a2a/agent_card.py                 — NEU: Agent Cards (A2A Protocol)
agent/a2a/client.py                     — NEU: A2A HTTP Client
agent/graph/nodes/a2a_node.py           — NEU: A2A Delegation Node (4.3)
```
