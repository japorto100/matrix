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
      - Refactored zu Per-Entry Keys (exec-12 Code Review #16):
        Jeder Entry eigener Cache Key (`tradeview:m5:session:{sid}:entry:{eid}`),
        eliminiert Read-Modify-Write Race Condition bei parallelen Sub-Agents.
        Neuer `working_memory_get_entry()` fuer O(1) Einzelzugriff.
  - Kein separates Protokoll noetig

---

## Phase 5: deer-flow Patterns (zusaetzlich)

- [x] **5.1:** Middleware Chain ✅ (31.03.2026)
  - `agent/middleware/` Package erstellt mit 4 Middlewares:
    - `loop_detection.py` — LoopDetector: Hash-basiert, Warn@3, HardStop@5 (deer-flow Pattern)
    - `dangling_tool_call.py` — Patcht verwaiste Tool-Calls mit Placeholder (deer-flow Pattern)
    - `guardrails.py` — AllowlistProvider + RoleBasedProvider (deer-flow + LangChain Pattern)
    - `summarization.py` — 3-Stufen Context-Management (siehe 5.5)
  - Dangling + Summarization in loop.py eingebunden

- [x] **5.2:** Skill Management REST API ✅ (31.03.2026)
  - `GET /api/v1/skills` — Alle Skills listen (3-Tier, Filter: category/user/team)
  - `PUT /api/v1/skills/{name}` — Skill enable/disable
  - In agent/app.py registriert

- [x] **5.3:** GitHub / SkillsMP Import ✅ (31.03.2026)
  - `agent/skills/importer.py` — `import_from_github(repo_url, tier, owner)`
  - Shallow clone → SKILL.md suchen → in Tier-Verzeichnis kopieren
  - API: `POST /api/v1/skills/import` mit repo_url + tier + owner
  - Kompatibel mit: anthropics/skills, microsoft/skills, SkillsMP Repos
  - SKILL.md ist offener Standard (agentskills.io, 30+ Tools adoptiert)

- [x] **5.4:** Skill .skill ZIP Archive Support ✅ (31.03.2026)
  - `agent/skills/importer.py` — `install_from_archive(path, tier, owner)`
  - Sicherheits-Checks (deer-flow Pattern): Path Traversal, Symlinks, Size 50MB, Max 100 Files
  - API: `POST /api/v1/skills/install` mit path + tier + owner
  - Validiert SKILL.md Frontmatter im Archive

- [x] **5.5:** Context Summarization Middleware ✅ (31.03.2026)
  - `agent/middleware/summarization.py` — 3-Stufen SOTA Pattern ("Deep Agents"):
    - Stufe 1: Offload — grosse Tool-Results kuerzen (>500 chars)
    - Stufe 2: Summarize — aeltere Messages via LLM zusammenfassen (keep=20)
    - Stufe 3: Truncate — Hard-Fallback wenn immer noch zu gross
  - Trigger: 70% Context-Window (konfigurierbar via AGENT_SUMMARIZE_THRESHOLD)
  - In loop.py eingebunden (vor LangGraph + Legacy Loop)
  - ENV: AGENT_SUMMARIZE_THRESHOLD, AGENT_SUMMARIZE_KEEP_MESSAGES, AGENT_SUMMARIZE_MODEL

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
- [ ] Skills ins System-Prompt injiziert (format_skills_for_prompt)
- [ ] 3-Tier Loading: Global → Team → Personal (Override-Semantik)
- [ ] Auto-Skill-Generation: Failure → neuer SKILL.md in personal/{user_id}/
- [ ] Generierter Skill wird beim naechsten Run geladen
- [ ] Skill Deduplication: gleicher Failure generiert keinen doppelten Skill
- [ ] Temporal Context: letzte 24h Aktivitaet im System-Prompt sichtbar

### Gate 4: A2A
- [ ] Agent Cards als JSON serialisierbar
- [ ] A2A Client: send_message an lokalen Agent → Response
- [ ] Inter-Agent Delegation via Orchestrator + a2a_node

### Gate 5: Middleware (Phase 5)
- [ ] Context Summarization: bei 70% Context-Window werden alte Messages zusammengefasst
- [ ] Offload: Tool-Results ueber 500 chars werden gekuerzt
- [ ] Loop Detection: Warning nach 3x gleiche Tool-Calls, Hard-Stop nach 5x
- [ ] Dangling Tool Calls: verwaiste Tool-Calls bekommen Placeholder-Response
- [ ] Guardrails: AllowlistProvider blockiert unerlaubte Tools
- [ ] RoleBasedProvider: Fundamentals-Agent kann kein set_chart_state aufrufen

### Gate 6: Skill Management API
- [ ] GET /api/v1/skills listet alle Skills (3-Tier + Filter)
- [ ] PUT /api/v1/skills/{name} enabled/disabled
- [ ] POST /api/v1/skills/import klont GitHub Repo → installiert SKILL.md Files
- [ ] POST /api/v1/skills/install extrahiert .skill ZIP Archive sicher

### Gate 7: RL Infrastructure (deaktiviert, nur Infra-Check)
- [ ] PRM: ProcessRewardModel instanziierbar (AGENT_PRM_ENABLED=false)
- [ ] LoRA: LoRATrainer instanziierbar (AGENT_RL_ENABLED=false)
- [ ] OMLS: IdleWindowDetector erkennt Inaktivitaet korrekt
- [ ] TrajectoryLogger: schreibt .json Files in .trajectories/

---

## Paper-Insights + Implementation

### Paper 1: MetaClaw (https://arxiv.org/html/2603.17187)
- Continual Meta-Learning: Skill-Driven Fast Adaptation + Opportunistic RL
- Per-User Skill Learning, Federated Sharing als Zukunftsvision
- Skill Generation Versioning, OMLS Idle-Window Detection
- **Status:** Production-ready (Proxy-Pattern, kein GPU noetig)
- **Limitation:** Sequentielle Skill-Generierung (kein Batch), Idle-Detection user-konfiguriert
- **Bei uns implementiert:** SkillEvolver, 3-Tier Skills, TrajectoryLogger, PRM, LoRA, OMLS (✅)

### Paper 2: Trace2Skill (https://arxiv.org/html/2603.25158v2)
- Parallele Skill-Generierung aus Trajectory-Pools (statt sequentiell wie MetaClaw)
- Hierarchische Konsolidierung: idiosynkratische Patches rausfiltern, generalisierbare behalten
- Skills transferieren zwischen Models (+57.65% cross-model transfer)
- **Status:** Research-only, kein Code veroeffentlicht, "work in progress"
- **Limitation:** Kein kausales Tracking, kein automatisches Pruning
- **Hybrid-Ansatz:** MetaClaw sofort (single-failure) + Trace2Skill periodisch (batch nightly)

### Paper 3: Natural-Language Agent Harnesses / NLAH (https://arxiv.org/html/2603.25723v1)
- Agent-Orchestrierung als editierbare NL-Specs statt Code
- File-backed State: Artifacts auf Disk → Recovery bei Crashes
- Explicit Contracts: Structured Output + Completion Gates pro Rolle
- **Status:** Theoretisch/experimentell, kein Code, GPT-5.4 + Codex CLI
- **Limitation:** NL weniger praezise als Code, Runtime-Contamination moeglich
- **Was wir uebernehmen:** Completion Gates, File-backed State (funktioniert, rest ist Theorie)

---

## Phase 6: Paper-Insights Implementation

### 6.1 Trace2Skill Hybrid (Paper 2)
- [x] **6.1a:** Batch-Consolidation als LangGraph Sub-Graph ✅ (31.03.2026)
  - `agent/graph/subgraphs/consolidation_graph.py`
  - 3 Nodes: Error-Analyst → Success-Analyst (parallel) → Consolidator
  - Alle LLM-Calls via `agent/llm_helper.py` (provider-agnostisch)
  - Speichert konsolidierten Skill in `personal/{user_id}/consolidated-{name}/`
  - `references/patterns.md` Subdirectory fuer identifizierte Patterns
  - Confidence-Schwelle (0.5): nur generalisierbare Skills werden gespeichert
- [x] **6.1b:** Skill-Hierarchie ✅
  - SKILL.md Hauptdokument + `references/` Subdirectory
  - Consolidation Graph erzeugt references/patterns.md automatisch

### 6.2 NLAH Patterns (Paper 3 — nur was funktioniert)
- [x] **6.2a:** Completion Gates pro Trading-Rolle ✅ (31.03.2026)
  - `agent/middleware/completion_gates.py` — LLM-as-Judge Validation
  - `TRADING_ROLE_CONTRACTS` in `agent/roles.py`
  - Researcher MUSS Bull + Bear, Trader MUSS Entry/Exit/Stop, RiskManager MUSS Approval
  - Nutzt `llm_helper.py` (provider-agnostisch)
- [x] **6.2b:** File-backed State ✅ (31.03.2026)
  - `agent/state_store.py` — FileBackedState Klasse
  - Pattern: `agent/state/{thread_id}/{role}_output.json`
  - save/load/has_checkpoint Methoden

### 6.3 LLM-Call Refactoring
- [x] **6.3:** Shared LLM Helper ✅ (31.03.2026)
  - `agent/llm_helper.py` — einziger Ort fuer Utility-LLM-Calls
  - Provider-Routing via ENV: AGENT_PROVIDER / AGENT_USE_LITELLM / OPENAI_BASE_URL
  - `llm_call(prompt, model, max_tokens, system)` → Text
  - `extract_json(text)` → dict (Code-Block aware)
  - Alle Utility-Calls refactored: evolver, rl_trainer, summarization, completion_gates, consolidation
  - Tool-Calling Nodes (`llm_node.py`, Legacy Loop) nutzen weiterhin SDKs direkt (provider-spezifisch)

---

## Verify Gate 8: Paper-Insights
- [ ] Batch-Consolidation: 5 Trajectories → 1 konsolidierter Skill (nicht 5 einzelne)
- [ ] Completion Gate: Researcher ohne Bull/Bear Argumente wird abgelehnt
- [ ] File-backed State: Zwischen-Ergebnis auf Disk, Recovery nach Restart moeglich

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

agent/middleware/__init__.py             — NEU: Middleware Package
agent/middleware/summarization.py        — NEU: 3-Stufen Context-Management (5.5)
agent/middleware/loop_detection.py       — NEU: Loop Detection (5.1)
agent/middleware/dangling_tool_call.py   — NEU: Dangling Tool Call Patcher (5.1)
agent/middleware/guardrails.py           — NEU: Allowlist + RoleBased Provider (5.1)
agent/skills/importer.py                — NEU: GitHub Import + ZIP Install (5.3 + 5.4)
agent/loop.py                           — GEAENDERT: +Summarization, +Dangling, +Skills, +Temporal
agent/app.py                            — GEAENDERT: +Skill API Endpoints, +Field(max_length), +path restriction

# Phase 6: Paper-Insights + Refactoring
agent/llm_helper.py                     — NEU: Shared provider-agnostischer LLM Helper
agent/state_store.py                    — NEU: File-backed State (NLAH Pattern)
agent/middleware/completion_gates.py     — NEU: Rollen-Contract Validation (NLAH Pattern)
agent/graph/subgraphs/__init__.py       — NEU
agent/graph/subgraphs/consolidation_graph.py — NEU: Trace2Skill LangGraph (Error+Success+Merge)
agent/roles.py                          — ERWEITERT: +TRADING_ROLE_CONTRACTS
agent/skills/evolver.py                 — REFACTORED: BatchConsolidator raus, llm_helper statt hardcoded
agent/skills/rl_trainer.py              — REFACTORED: llm_helper statt hardcoded AsyncAnthropic
agent/middleware/summarization.py        — REFACTORED: llm_helper statt hardcoded
agent/validators/trading.py             — GEAENDERT: needs_approval ctx optional
agent/a2a/client.py                     — GEAENDERT: text-delta packet type fix
agent/graph/nodes/tool_node.py          — GEAENDERT: TOOL_TIMEOUT_SEC from ENV
agent/graph/agent_graph.py              — GEAENDERT: MAX_ITERATIONS from ENV
agent/skills/importer.py                — GEAENDERT: URL host validation (SSRF prevention)
.env                                    — AKTUALISIERT: alle exec-10 ENV vars
.env.example                            — AKTUALISIERT: alle exec-10 ENV vars dokumentiert
.gitignore                              — GEAENDERT: +agent/state/
```

## Code Review (31.03.2026)

32 Issues gefunden, 8 gefixt in exec-10. Offene Issues verteilt auf exec-11/12.

---

## Phase 7: Orchestrator-Refactor + Per-User-Agent-Routing (Planned, 2026-04-21)

> **Auslöser:** Diskussion 2026-04-21 (siehe `exec2-04 §O.2`). Heute routet go-appservice
> multi-agent-mentions (`@agent-trading`, `@agent-research`) via body-regex. Ziel-Architektur:
> **ein orchestrator-agent pro user**, der subagents intern (LangGraph-Nodes) delegiert.

### 7.1 Status-Bestandsaufnahme (was existiert bereits)

- ✅ **LangGraph Orchestrator-Graph** (Phase 1-3) — Supervisor-Pattern möglich
- ✅ **Per-user LLM-settings** (`agent/control/user_llm.py:get_user_default_model(sender)`) — bridge berücksichtigt bereits
- ✅ **Appservice-Namespace** (`@agent-.*:matrix.local`) — deckt beliebige agent-user-IDs on-demand ab
- ✅ **NATS `target_agent` im InboundMessage** — Go extractet den agent-namen und publisht ihn
- ✅ **Bridge dynamic reply routing** (2026-04-21): `bridge/nats_handler.py:_resolve_reply_user_id()` baut reply-user-id aus `target_agent`, fallback auf config-default
- ✅ **A2A-Protokoll** (Phase 4) — agent-to-agent delegation infrastruktur, nie live-getestet (heiß!)

### 7.2 Was fehlt für vollen Orchestrator-Pattern

**Body-Parsing deprecaten:**
- [ ] `go-appservice/internal/handler/server.go:extractAgentName()` — obsolet sobald orchestrator-default-routing steht
- [ ] `isAgentUser()` bleibt (Namespace-check)
- [ ] Alternative: `target_agent` wird aus DM-room-member abgeleitet (falls room ein DM zwischen user und `@agent-<user>` ist), nicht aus body

**Default-agent-routing (in absence of explicit mention):**
- [ ] Convention: User alice DM-t ihren `@agent-alice` direkt — keine mention nötig, go leitet automatisch `target_agent=alice`
- [ ] Go-handler: neue helper `resolveTargetAgentForRoom(roomID, sender)` — prüft room-members, extrahiert `@agent-*` member falls DM oder kleiner room
- [ ] Fallback: falls no agent-member → default-mention-routing (body regex, legacy) oder skip

**Username-Sanitization (trading-project integration):**
- [ ] Neue `agent/identity/matrix_names.py` utility:
  - `sanitize_matrix_localpart(raw: str) -> str` — Matrix-Spec: lowercase + `[a-z0-9._=\-/]` erlaubt; ersetze ungültige chars mit `_`
  - `matrix_user_id(username, server) -> str` — `@<sanitized>:<server>`
  - `agent_user_id(username, server, prefix="agent-") -> str` — `@agent-<sanitized>:<server>`
- [ ] Test-cases: `alice.smith`, `alice_smith`, `ALICE`, `alice+smith`, `müller` (unicode), leading-digit, extremely-long
- [ ] Trading-project registration-hook ruft beide mapping-funktionen auf, speichert in `user_settings.matrix_user_id` + `user_settings.agent_user_id`

**Orchestrator-Default-Model pro user:**
- [ ] Heute: `get_user_default_model(sender)` liefert model pro human-user-id
- [ ] Erweiterung: per-user-agent auch eigenen system-prompt, memory-scope, skill-set, tool-allowlist — alles gated durch user_id
- [ ] `user_agent_settings` Tabelle (neu) oder Erweiterung von `user_llm_settings`

**Subagent-Design (explizit als WIP markiert):**
- [ ] **OFFEN:** welche Subagents gibt's? (trading, research, memory, planning, skills)
- [ ] **OFFEN:** Subagent-Routing-Logik — intent-classifier-LLM (meta-agent klassifiziert first) vs. tool-based-routing (jeder tool-call entspricht subagent) vs. rule-based (keywords → subagent)
- [ ] **OFFEN:** Subagent-Visibility — LangGraph-Nodes-only (unsichtbar für user) vs. A2A-Matrix-Identity (eigene `@subagent-<type>` user die im workspace-room posten) vs. hybrid
- [ ] **OFFEN:** Parallel vs. sequential subagent-execution
- [ ] **OFFEN:** Wie teilen Subagents state/memory? (shared conversation-state in graph vs. isolated per subagent)
- [ ] Design-Session vor Implementation notwendig — sota-contrarian stakes=high review

**E2EE-Scaling-Entscheidung:**
- [ ] Status quo: Shared OlmMachine im go-appservice handled alle `@agent-*` users (MSC3202 Appservice E2EE). Skaliert gut bis ~1000s agent-users.
- [ ] Alternative (deferred nach `exec-05c`): per-agent-user OlmMachine für echte crypto-isolation. Nur triggern wenn Security-Audit es fordert.
- [ ] **Entscheidung:** Status quo ausreichend bis 1000+ concurrent agent-users oder compliance-trigger — siehe `exec-blocking §C4`.

### 7.3 Abhängigkeiten + Sequence

1. **Username-sanitizer** (`agent/identity/matrix_names.py`) — unabhängig, kann jederzeit gebaut
2. **DM-room-based default-routing** in go-appservice — unabhängig, kleine change
3. **Subagent-design-session** + sota-contrarian — blockierend für 7.4
4. **Orchestrator-supervisor-refactor** in LangGraph — nach Design-Session
5. **Body-parsing deprecate** — letzter Schritt, wenn default-routing + orchestrator stabil

### 7.4 Cross-ref mit trading-project

- MAS/OIDC-provisioning für matrix-user blockiert (siehe `exec-matrix-monitor §M4`)
- Sobald entblockt: trading-registration → `sanitize_matrix_localpart(trading_username)` → matrix-user erstellt → `@agent-<sanitized>` namespace-virtuell verfügbar ohne weiteren call
- DM-room zwischen beiden auto-create beim ersten Login (exec2-03b §A2)

### 7.5 Done in dieser Session (2026-04-21)

- [x] **Bridge dynamic reply routing** — `bridge/nats_handler.py:_resolve_reply_user_id()` nutzt `target_agent` aus payload, fallback auf config
- [x] **Env-loader** lädt `.env.development` via `APP_ENV` (für OpenRouter-key)
- [x] **ADR-lites** in `exec2-04 §O` (bridge architecture decision C, orchestrator target-pattern)
- [x] **Authentication-Cleanup (partial)**: `setup-users.sh` legt `@agent-bot` nicht mehr explizit an — Appservice-Namespace + auto-invite-accept (`server.go:641-650`) materialisiert jeden `@agent-*` on-demand. Alice + Bob bleiben password-users (kein MAS/OIDC im matrix-repo, das hat trading-project).
- [x] **Go-Appservice BootstrapAgents (rudimentär, env-basiert)**: `handler/server.go:BootstrapAgents()` aufgerufen aus `main.go` nach `Start()`, iteriert `cfg.DefaultAgents` aus env-var `DEFAULT_AGENTS=alice,bob`, ruft `EnsureProfile` pro name → `@agent-<name>` im Tuwunel user-directory sichtbar, autocomplete funktioniert. Nutzt dead-code `intent/agent.go:EnsureProfile` den es schon gab.
  - **⚠️ Rudimentär:** Env-var ist nur für dev/test. In prod muss das **dynamisch pro user-registration** passieren (siehe §7.6 "BootstrapAgents dynamisch").
  - Benennungs-convention: `alice → @agent-alice`, `bob → @agent-bob`. **Kein shared general-agent** (widerspricht Orchestrator-Pattern mit user-isolation).
  - **⚠️ Kein ownership-check:** bob könnte `@agent-alice` mentionen → würde fälschlicherweise antworten. Access-control in §7.6 "User-Agent-Ownership" scope.

### 7.6 Authentication-Cleanup (open, in Phase 7 scope)

**Kontext:** setup-users.sh war legacy (inklusive `@agent-bot`-register mit password + token-write in python-backend/.env.development). Teilweise entrümpelt (2026-04-21). Noch offen:

- [ ] **Frontend-Login-UX** — aktuell wird alice-Token in `frontend_merger/.env.local:MATRIX_ACCESS_TOKEN` injiziert (dev-convenience, one-click-login). SOTA: Browser-Login-Flow (email+password → token in localStorage, prod-parity). Frontend_merger braucht Login-Komponente (prüfen ob cinny-basierte vorhanden).
- [ ] **`MATRIX_BOT_ACCESS_TOKEN` feature-flag refactor** — `python-backend/agent/control/security.py:63` checkt `bool(os.environ.get("MATRIX_BOT_ACCESS_TOKEN"))` als "is matrix wired up". SOTA: stattdessen `appservice.registered` aus go-appservice-state lesen (via health-endpoint). Token-based-check ist legacy aus matrix-nio-era.
- [ ] **Trading-project per-user-provisioning** — wenn OIDC/MAS-blocker (`exec-matrix-monitor §M4`) gelöst: user-registration hook → sanitize(username) → auto-create `@<userid>:matrix.local` (password oder MAS) + namespace-managed `@agent-<userid>:matrix.local` (on-demand) + auto-DM-room. Siehe §7.2 username-sanitizer.
- [ ] **User-Agent-Ownership + Access-Control** (🚨 security-relevant, muss vor prod) — aktuell weiß das system nicht automatisch welcher human-user welchem agent gehört:
  - Heute: Alice muss explizit `@agent-alice` mentionen. Bob könnte auch `@agent-alice` adressieren — kein owner-check. Cross-access ist offen.
  - **Neue DB-table** `agent_ownership` (owner_user_id PRIMARY KEY → agent_user_id). Go-appservice pflegt das.
  - **DM-based auto-routing:** Go-handler erkennt "DM zwischen @alice und @agent-alice" → `target_agent=alice` automatisch gesetzt, keine mention nötig. Alice chattet natürlich ohne `@`.
  - **Cross-access-block:** Mention von `@agent-alice` durch bob → Message nicht an bridge weitergeleitet, optional warn-reply "Nicht dein agent".
  - **Auto-DM bei registration:** dev-script (setup-users.sh) oder trading-project registration-hook → createDM(user, @agent-user) + INSERT agent_ownership. User sieht seinen agent sofort in der room-list.
  - Cross-ref: ownership-tabelle wird auch von BootstrapAgents dynamisch (§7.6 erster bullet) beim agent-register-call gefüllt.

- [ ] **BootstrapAgents dynamisch statt env-basiert** — aktueller `DEFAULT_AGENTS` env-var ist nur für dev-test workable (fixed liste beim go-start). Prod-pattern:
  - Admin-HTTP-API `POST /admin/agents/register` am go-appservice (authenticated via HS_TOKEN oder internal-secret)
  - Payload: `{"username": "alice.smith", "display_name": "Alice"}`
  - Handler: `sanitize_matrix_localpart(username)` → `AgentSender.EnsureProfile(@agent-<sanitized>, display_name)` + optionales auto-DM-create mit human-user
  - Trading-project user-registration-hook calls diesen endpoint bei jedem neuen account
  - Delete-counterpart: `DELETE /admin/agents/<username>` → tear down auf account-löschung (GDPR compliance)
  - Persistence: liste der registered agents in postgres (`agent.registered_agents` table) → survived über restarts, kein env-var-reload nötig
  - BootstrapAgents beim go-start liest DB statt env → rehydratisiert user-directory falls tuwunel DB mal gewiped wurde
