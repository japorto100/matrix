# exec-14: PDDL Formale Plan-Validierung fuer Agent-Workflows

**Datum:** 01.04.2026 (paper-kopien ergänzt 2026-04-20)
**Status:** Geplant
**Abhaengig von:** exec-10 (Multi-Agent/LangGraph), exec-12 (Sandbox/Security)
**Herkunft:** exec-12 Phase 5 (ausgelagert), `pddl_phase22b_delta.md`
**Research-Basis:** arXiv `2603.12188` (ICAPS 2026), arXiv `2512.09629`, VeriPlan (CHI 2025),
SagaLLM (VLDB 2025), L2P, GenePlan, NeSIG

---

## Lokale Paper-Kopien (2026-04-20)

Alle kern- und weiteren zitierten papers sind jetzt in `docs/papers/` verfügbar für offline-review + reproduzierbarkeit:

| arXiv ID | Titel | Pages | Lokale datei |
|---|---|---|---|
| 2603.12188 | Compiling Temporal Numeric Planning into Discrete PDDL+ (ICAPS 2026) — **Kern-paper das die spec getriggert hat** | 7 | `docs/papers/PDDL-2603.12188.pdf` |
| 2512.09629 | End-to-end Planning Framework with Agentic LLMs and PDDL | 18 | `docs/papers/PDDL-2512.09629.pdf` |
| 2502.17898 | VeriPlan: Integrating Formal Verification and LLMs into End-User Planning (CHI 2025) | 19 | `docs/papers/PDDL-2502.17898.pdf` |
| 2503.11951 | SagaLLM: Context Management, Validation, and Transaction Guarantees for Multi-Agent LLM Planning (VLDB 2025) | 13 | `docs/papers/PDDL-2503.11951.pdf` |
| 2404.11891 | LLMs Can Solve Real-World Planning Rigorously with Formal Verification Tools (NAACL 2025) | 50 | `docs/papers/PDDL-2404.11891.pdf` |
| 2510.03469 | Bridging LLM Planning Agents and Formal Methods: A Case Study in Plan Verification | 4 | `docs/papers/PDDL-2510.03469.pdf` |
| 1106.4561 | PDDL 2.1 original (Fox/Long 2003) — historische grundlage | 64 | `docs/papers/PDDL-1106.4561.pdf` |
| 2505.22597 | HDDLGym: Multi-Agent HTN (2025) | 10 | `docs/papers/PDDL-2505.22597.pdf` |
| 2509.13691 | SPAR: LLM → PDDL für Aerial Robotics | 8 | `docs/papers/PDDL-2509.13691.pdf` |
| 2509.21543 | Plan2Evolve: LLM Self-Evolution via PDDL Domain Generation | 31 | `docs/papers/PDDL-2509.21543.pdf` |
| 2505.12501 | ALAS: Stateful Multi-LLM Agent for Disruption Recovery | 36 | `docs/papers/PDDL-2505.12501.pdf` |

**Nicht geportet** (URL-only verbleibend):
- PDDL+ Wiki (planning.wiki), HDDL AAAI-paper (ojs.aaai.org), HDDL Extension (uni-ulm), RDDL Spec (anu.edu.au), LTL Wiki (hhu.de) — web-resources, keine arxiv-preprints
- Zwei ACL-anthology surveys (2025.findings-acl.1291, 2025.acl-long.958) + Metagent-P (2025.findings-acl.1169) — auf bedarf downloaden
- PDDL-INSTRUCT (pulkitverma.net) — workshop-pdf, auf bedarf
- L2P + GenePlan + NeSIG — framework-code-refs, keine papers

Cross-ref: `exec-14-DSPy.md` nutzt dieselbe `docs/papers/` struktur für DSPy-foundation-papers.

---

## Motivation

LLMs sind schlecht im Planen — sie halluzinieren Steps, vergessen Constraints, und
koennen keine Deadlines oder Ressourcen-Budgets formal garantieren. Die Forschung
2025/2026 konvergiert auf ein Hybrid-Pattern:

> **LLM generiert Plan → Formaler Solver validiert → Nur valide Plaene werden ausgefuehrt**

Dieses Pattern ist genau was wir brauchen fuer:
- **Morning Research Run** (Deadline vor Market Open)
- **Multi-Agent Workflows** (Ordering-Constraints zwischen Agents)
- **Ressourcen-Budget-Kontrolle** (API-Limits, Token-Budgets)

LangGraph *reagiert* auf Probleme (Loop Detection, Rate Limits). PDDL *verhindert* sie
durch Voraus-Validierung bevor der erste Step ausgefuehrt wird.

### Abgrenzung: Was PDDL ist und was nicht

| Layer | Spezifikation | Rolle | Solver noetig |
|:---|:---|:---|:---|
| Tool Use / Agent-IO | JSON Tool Schemas | LLM-nahe Tool-Vertraege | Nein |
| API / Transport | OpenAPI / JSON Schema | HTTP-/MCP-Validierung | Nein |
| **Formale Ablaufplanung** | **PDDL / ADL** | **Plan-Validierung fuer harte Constraints** | **Ja** |

**Arbeitsregel:** PDDL ergaenzt JSON/OpenAPI, ersetzt sie nicht.
PDDL ist fuer Workflows mit harten zeitlichen/numerischen Constraints.
Nicht fuer triviale CRUD, nicht fuer Low-Latency-Trade-Execution.

---

## PDDL-Sprachfamilie (zu evaluieren)

Die Planning-Community hat ueber die Jahre verschiedene Sprachen und Erweiterungen
entwickelt. Alle sind relevant und sollten evaluiert werden:

| Sprache | Version/Jahr | Was sie kann | Relevanz fuer uns | Status |
|:---|:---|:---|:---|:---|
| **PDDL 2.1** | 2003 (Fox/Long) | Durative Actions, numerische Fluents, Deadlines | **Hoch** — temporale Constraints, unser Startpunkt | Zu evaluieren |
| **PDDL+** | 2006 | Kontinuierliche Prozesse, Events, Hybrid-Systeme | **Mittel** — delayed effects (Paper 2603.12188 kompiliert 2.1→PDDL+) | Zu evaluieren |
| **PDDL 3.0** | 2006 | State-Trajectory Constraints, Preferences | **Mittel** — soft Constraints, Praeferenzen | Zu evaluieren |
| **HDDL** | 2020 (Hoeller et al.) | Hierarchische Task Networks (HTN) | **Mittel-Hoch** — Agent-Workflows sind natuerlich hierarchisch (Task→Subtasks) | Zu evaluieren |
| **RDDL** | 2011 (Sanner) | Probabilistisch, MDPs/POMDPs, Unsicherheit | **Niedrig** — stochastische Maerkte theoretisch passend, aber komplex | Zu evaluieren |
| **MA-PDDL** | 2012 | Multi-Agent PDDL, koordinierte Planung | **Mittel** — wenn mehrere Agents koordiniert planen muessen | Zu evaluieren |
| **SAS+** | 1995 (Baeckstroem/Nebel) | Finite-Domain Variablen, internes Format vieler Solver | **Intern** — FastDownward nutzt SAS+ intern, wir nicht direkt | Referenz |
| **LTL** | Standardlogik | Linear Temporal Logic, sequentielle/Safety-Properties | **Mittel-Hoch** — VeriPlan nutzt LTL statt PDDL, flexibler fuer manche Constraints | Zu evaluieren |
| **STL** | Erweiterung | Signal Temporal Logic, real-valued Signale + Zeit | **Niedrig** — fuer kontinuierliche Zeitreihen (Kurs-Monitoring), Research-Stage | Zu evaluieren |

**Empfehlung Phase 1:** PDDL 2.1 (temporal+numerisch) als Startpunkt.
**Empfehlung Phase 2+:** HDDL fuer hierarchische Workflows evaluieren, LTL als Alternative.

### Sprach-Referenzen

- PDDL 2.1 Spec: https://planning.wiki/ref/pddl21
- PDDL 2.1 Paper: https://arxiv.org/pdf/1106.4561
- PDDL+ Wiki: https://planning.wiki/ref/pddlplus
- HDDL Paper: https://cdn.aaai.org/ojs/6542/6542-13-9767-1-10-20200519.pdf
- HDDL Extension: https://www.uni-ulm.de/fileadmin/website_uni_ulm/iui.inst.090/Publikationen/2020/Hoeller2020HDDL.pdf
- HDDLGym (Multi-Agent HTN, 2025): https://arxiv.org/html/2505.22597v1
- RDDL Spec: https://users.cecs.anu.edu.au/~ssanner/IPPC_2011/RDDL.pdf
- MA-PDDL: Teil von PDDL 3.1 Erweiterungen
- LTL Model Checking: https://prob.hhu.de/w/index.php?title=LTL_Model_Checking
- PDDL Wiki (Gesamtuebersicht): https://planning.wiki/guide/whatis/pddl
- LearnPDDL Tutorial: https://fareskalaboud.github.io/LearnPDDL/

---

## Research-Basis (Stand April 2026)

### Kern-Paper

1. **arXiv 2603.12188** — "Compiling Temporal Numeric Planning into Discrete PDDL+"
   Micheli, Scala, Valentini — **ICAPS 2026 accepted**
   URL: https://arxiv.org/abs/2603.12188
   - Erste praktische Kompilierung PDDL 2.1 Level 3 → diskretes PDDL+
   - Polynomial, Plan-Laenge mit konstantem Overhead, sound/complete
   - Annahme: non-self-overlapping actions (konservativ, fuer uns ausreichend)
   - Kernkonzepte: overall conditions, no-moving-target, mutex/non-interference
   - Delayed effects + timed initial literals via Event-Mechanik

2. **arXiv 2512.09629** — "End-to-end Planning Framework with Agentic LLMs and PDDL"
   URL: https://arxiv.org/abs/2512.09629
   - Multi-Agent Orchestrator: LLM → JSON → PDDL → Solver → Validated Plan
   - Spezialisierte Agents: SyntaxPDDL, TemporalConsistency, DeepThinkConstraints,
     FastDownwardsAdapter
   - Solver: FastDownward, POPF, LPG
   - Results: +12% Google Natural Plan, +15% PlanBench vs. reines LLM
   - Constraint-Encoding direkt in PDDL statt Post-hoc-Checks
   - 45.8% Cost Reduction durch Plan-Optimierung

3. **VeriPlan** (CHI 2025) — "Integrating Formal Verification and LLMs into Planning"
   URL: https://arxiv.org/abs/2502.17898
   - Model Checking (PRISM + Stormpy) statt klassischem PDDL-Solver
   - LTL (Linear Temporal Logic) fuer Constraint-Spezifikation
   - 7 Template-Kategorien: sequential order, concurrent events, conditional constraints, ...
   - Flexibility Sliders: soft vs hard Constraints (User-kontrolliert)
   - User Study (n=12): signifikant bessere Performance (p=.0011), Usefulness (p=.047)
   - Model Checking als "Safety Net" fuer LLM-Exploration

4. **SagaLLM** (VLDB 2025) — "Context Management, Validation, and Transaction
   Guarantees for Multi-Agent LLM Planning"
   URL: https://arxiv.org/abs/2503.11951
   GitHub: https://github.com/genglongling/SagaLLM
   - **Saga-Pattern** aus Microservices auf Agent-Workflows angewandt
   - Jede Action T_i hat Compensation C_i → Rollback bei Fehler in Rueckwaertsreihenfolge
   - 3 Frameworks:
     - **Context Management:** Persistent Memory gegen LLM Attention-Degradation
     - **Validation:** Unabhaengiger GlobalValidationAgent prueft jeden Output vor Commit
       (nicht Self-Validation — externes System, Goedel-Argument)
     - **Transaction:** Atomare Operations + Compensations, Dependency-Graph-Analyse
   - Standalone-LLMs (Claude 3.7, GPT-4o) versagen bei interdependenten Constraints
   - **Komplementaer zu PDDL:** PDDL validiert VOR Ausfuehrung, SagaLLM sichert WAEHREND

5. **arXiv 2404.11891** — "Large Language Models Can Solve Real-World Planning
   Rigorously with Formal Verification Tools"
   URL: https://arxiv.org/abs/2404.11891 (NAACL 2025)
   - SMT-Solver (Z3) generiert formal verifizierte Plaene
   - Bei Constraint-Violation: Solver gibt unsatisfiable reasons → LLM updated Plan iterativ
   - Formal korrekte Plaene fuer reale Planungsprobleme

6. **arXiv 2510.03469** — "Bridging LLM Planning Agents and Formal Methods:
   A Case Study in Plan Verification"
   URL: https://arxiv.org/abs/2510.03469
   - Systematische Untersuchung LLM + formale Verifikation
   - Plan Verification als eigenstaendiger Schritt nach Plan-Generierung

### ICAPS 2026 relevante Accepted Papers

URL: https://icaps26.icaps-conference.org/program/accepted/

- "Compiling Temporal Numeric Planning into Discrete PDDL+" (unsere Research-Basis)
- "GenePlan: Evolving Better Generalized PDDL Plans using LLMs"
  (Murray, Dervovic, Pozanco, Cashmore — evolutionaerer Ansatz)
- "Planning in the LLM Era: Building for Reliability and Efficiency"
  (Katz, Kokel, Srinivas, Sohrabi)
- "Successor-Generator Planning with LLM-generated Heuristics"
  (Tuisov, Vernik, Shleyfman)
- "Improved Generalized Planning with LLMs through Strategy Refinement and Reflection"
  (Stein, Hodel, Fišer, Hoffmann, Katz, Koller)
- "PDDL Axioms Are Equivalent to Least Fixed Point Logic"
  (Grundke, Roeger)
- "Compiling Expressive Planning With Data Types"
  (Espasa Arxer, Villaret, Miguel, Davesa Sureda)
- "Learning Distributed Scheduling via LLM-Augmented Reinforcement Learning"
  (Liu, Feng, Fan, Gao, Sun)

### Weitere relevante Paper

- **LLM+P** (Liu et al.): LLM als Goal-Extractor + klassischer Planner
- **PROC2PDDL**: NL-Prozessbeschreibungen → PDDL Domains
- **AutoPlanBench 2.0**: https://coli-saar.github.io/autoplanbench
  Automatische Prompt-Generierung fuer LLM-Planning in PDDL
- **SPAR**: LLM → PDDL fuer Aerial Robotics: https://arxiv.org/html/2509.13691
- **Plan2Evolve**: LLM Self-Evolution via PDDL Domain Generation: https://arxiv.org/html/2509.21543
- **Generating consistent PDDL domains with LLMs**: https://arxiv.org/abs/2404.07751
  Multi-Stage Pipeline mit automated consistency checking
- **PDDL-INSTRUCT**: Enhancing Symbolic Planning: https://pulkitverma.net/assets/pdf/vlfms_lm4plan25/vlfms_lm4plan25.pdf
- **LLMs as Planning Formalizers** (Survey, ACL 2025): https://aclanthology.org/2025.findings-acl.1291.pdf
- **A Modern Survey of LLM Planning Capabilities** (ACL 2025): https://aclanthology.org/2025.acl-long.958.pdf
- **Metagent-P**: Neuro-Symbolic Planning Agent: https://aclanthology.org/2025.findings-acl.1169.pdf
- **ALAS**: Stateful Multi-LLM Agent for Disruption Recovery: https://arxiv.org/pdf/2505.12501

### Neuro-Symbolic Planning

- **NeSIG** — Neuro-Symbolic Instance Generator
  URL: https://www.sciencedirect.com/science/article/pii/S0004370225001900
  Erste domain-unabhaengige Methode fuer automatische PDDL-Problem-Generierung.
  Kombiniert Neural Network (Diversitaet) + symbolische Constraints (Validitaet).
  **Status: Research-Phase** — kein PyPI-Package, kein Production-Tooling.
  Relevant fuer uns als Inspiration fuer Regression-Suite (14.10):
  statt 5 Testfaelle manuell → hunderte automatisch generieren.

- **Neuro-Symbolic Robot Action Planning** (Frontiers 2024):
  https://www.frontiersin.org/journals/neurorobotics/articles/10.3389/fnbot.2024.1342786/full
  LLM → PDDL → Heuristic Planner → Code (Hybrid Sense-Plan-Code-Act)

- **Fast Neuro-Symbolic Task Planning** (2024):
  https://arxiv.org/html/2409.19250v1
  LLM zerlegt Tasks in Subgoals → symbolischer Planner oder MCTS-LLM je nach Komplexitaet

### Automatische PDDL-Domain-Generation

- **L2P Library** (v0.3.3, Feb 2026)
  GitHub: https://github.com/AI-Planning/l2p
  PyPI: Nicht auf PyPI (pip install via GitHub)
  NL → PDDL Pipeline: DomainBuilder, TaskBuilder, FeedbackBuilder
  Unterstuetzt: OpenAI, HuggingFace, OpenAI-kompatible Provider
  FastDownward als Submodule integriert
  51 Stars, 294 Commits, aktiv gepflegt
  **Wichtig:** LLM-generierte Domains haben nur 24-35% semantische Korrektheit
  → Domains manuell schreiben, LLM nur fuer Problem-Instanzen nutzen

- **GenePlan** (ICAPS 2026): Evolutionaerer Ansatz — LLM generiert Population
  von PDDL-Plaenen, beste werden selektiert und weiterentwickelt

- **SPAR** (2025): Fokus auf UAV/Robotik, aber Methodik uebertragbar
  https://arxiv.org/html/2509.13691

### Trend

Die Forschung konvergiert klar: LLMs allein sind "brittle" beim Planen,
aber LLM + symbolischer Solver ist besser als beides allein.
Kein einzelnes Paper schlaegt reines LLM-Planning fuer constraint-heavy Domains vor.

---

## Solver-Landschaft

### Primaere Solver (via unified-planning)

| Solver | PyPI Package | Version | Staerke | Unser Use-Case |
|:---|:---|:---|:---|:---|
| **FastDownward** | `up-fast-downward` | >=0.5.2 | Schnellster klassischer Planner, SAS+ intern, groesste Community | Ordering-Constraints, Tool-Sequenzen |
| **Tamer** | `up-tamer` | >=1.1.6 | Temporal + numerisch, PDDL 2.1 nativ | Deadlines, Dauer-Constraints. **Einstiegs-Solver** |
| **ENHSP** | `up-enhsp` | >=0.1.0 | Expressiv numerisch, satisficing + optimal | API-Budgets, Token-Limits (numerische Fluents) |
| **POPF** | manuell | — | Temporal Planner, durative actions nativ | Deadlines + parallele Actions. **Bester Fit fuer Morning Research** |
| **LPG** | `up-lpg` | >=0.1.2 | Local-search, gut fuer grosse Domains, Anytime | Backup wenn FD/POPF zu langsam |
| **Pyperplan** | `up-pyperplan` | >=1.1.0 | Einfach, educational, reines Python | Debugging, Verstaendnis |
| **Aries** | `up-aries` | >=0.4.0 | Hierarchisch (HTN) + temporal, Rust-basiert | HDDL Evaluation (Phase 2+) |
| **SymK** | `up-symk` | >=1.3.0 | Symbolische Suche, optimale Plaene | Optimale Loesungen wenn noetig |

### Weitere Solver (nicht via unified-planning)

| Solver | Typ | URL | Relevanz |
|:---|:---|:---|:---|
| **VAL** | Plan Validator (kein Solver) | In FastDownward enthalten | Unabhaengige Plan-Validierung als Double-Check |
| **Z3** | SMT-Solver | `pip install z3-solver` | Numerische Constraint-Satisfiability, Alternative zu PDDL |
| **PRISM** | Model Checker | https://www.prismmodelchecker.org/ | LTL Model Checking (VeriPlan Pattern) |
| **Stormpy** | Model Checker (Python) | `pip install stormpy` | Python-Binding fuer Storm Model Checker |

### Installation

```bash
# Phase 1: Kern-Solver
uv pip install "unified-planning[tamer,fast-downward,enhsp]"

# Phase 2+: Alle Engines
uv pip install "unified-planning[engines]"
# Installiert: pyperplan, tamer, enhsp, fast-downward, lpg, fmap, aries, symk

# Formale Verifikation (Phase 3)
uv pip install z3-solver        # SMT-Solver fuer numerische Constraints
# stormpy                       # Model Checker (Linux only, C++ Deps)
```

### Solver-Referenzen

- unified-planning PyPI: https://pypi.org/project/unified-planning/
- unified-planning GitHub: https://github.com/aiplan4eu/unified-planning
- unified-planning Docs: https://unified-planning.readthedocs.io/
- unified-planning Setup (alle Extras): https://github.com/aiplan4eu/unified-planning/blob/master/setup.py
- up-fast-downward PyPI: https://pypi.org/project/up-fast-downward/
- up-fast-downward GitHub: https://github.com/aiplan4eu/up-fast-downward/
- FastDownward Homepage: https://www.fast-downward.org/
- FastDownward GitHub: https://github.com/aibasel/downward
- FastDownward Planning Wiki: https://planning.wiki/ref/planners/fd
- up-enhsp GitHub: https://github.com/aiplan4eu/up-enhsp
- ENHSP AI-on-Demand: https://www.ai4europe.eu/research/ai-catalog/enhsp-unified-planning-interface
- AIPlan4EU Organisation: https://github.com/aiplan4eu
- Temporal Planning Algorithms: https://github.com/aig-upf/temporal-planning
- SoftwareX Paper (unified-planning): https://www.sciencedirect.com/science/article/pii/S2352711024003820

---

## Tech Stack

### Python Packages (Phase 1)

```
unified-planning>=1.3.0          # Planner-agnostische Python API (Apache 2.0)
up-fast-downward>=0.5.2          # FastDownward Integration (klassisch + heuristisch)
up-tamer>=1.1.6                  # Tamer: klassisch + numerisch + temporal
up-enhsp>=0.1.0                  # ENHSP: expressiv numerisch + temporal
```

### Python Packages (Phase 2+)

```
up-lpg>=0.1.2                   # LPG: local-search, Anytime
up-aries>=0.4.0                 # Aries: HTN + temporal (Rust-basiert)
up-symk>=1.3.0                  # SymK: symbolische Suche, optimale Plaene
z3-solver                       # Z3 SMT-Solver (numerische Constraints)
```

### Unified-Planning API (Temporal Example)

```python
from unified_planning.shortcuts import *
from unified_planning.model.timing import StartTiming, EndTiming

# Domain
problem = Problem("morning_research")
data_loaded = Fluent("data_loaded", BoolType())
features_ready = Fluent("features_ready", BoolType())
problem.add_fluent(data_loaded, default_initial_value=False)
problem.add_fluent(features_ready, default_initial_value=False)

# Durative Action: Load Market Data (2-5 min)
load_data = DurativeAction("load_market_data")
load_data.set_fixed_duration(3)  # 3 Minuten
load_data.add_effect(EndTiming(), data_loaded, True)
problem.add_action(load_data)

# Durative Action: Refresh Features (braucht data_loaded)
refresh = DurativeAction("refresh_features")
refresh.set_fixed_duration(5)
refresh.add_condition(StartTiming(), data_loaded)  # Precondition
refresh.add_effect(EndTiming(), features_ready, True)
problem.add_action(refresh)

# Goal: alles fertig
problem.add_goal(features_ready)

# Deadline Constraint (vor Market Open)
problem.add_timed_goal(Timing(delay=10), features_ready)  # Innerhalb 10 min

# Solve
with OneshotPlanner(name="tamer") as planner:
    result = planner.solve(problem)
    if result.status == PlanGenerationResultStatus.SOLVED_SATISFICING:
        print(result.plan)
    else:
        print("Plan nicht machbar — Replan noetig")
```

---

## Architektur-Integration

```
┌─────────────────────────────────────────────────────┐
│  LangGraph Agent Loop (bestehend)                   │
│                                                     │
│  llm_call → approval_gate → tool_execute → ...      │
│       │                                             │
│       ▼                                             │
│  ┌─────────────────────────────────┐                │
│  │  PDDL Validation Node (neu)    │                 │
│  │                                │                 │
│  │  1. LLM generiert Plan-Steps   │                 │
│  │  2. Steps → PDDL Problem       │                 │
│  │  3. Solver validiert           │                 │
│  │  4. Valid → Execute            │                 │
│  │  5. Invalid → Replan           │                 │
│  └─────────────────────────────────┘                │
│                                                     │
│  ┌─────────────────────────────────┐                │
│  │  SagaLLM Transaction Layer     │  (Phase 2.5)    │
│  │                                │                 │
│  │  - Compensation pro Action     │                 │
│  │  - GlobalValidationAgent       │                 │
│  │  - Context Persistence         │                 │
│  │  - Rollback bei Runtime-Fehler │                 │
│  └─────────────────────────────────┘                │
│                                                     │
│  Bestehende Guards bleiben:                         │
│  - Consent (exec-12)                                │
│  - Rate Limits (exec-12)                            │
│  - Loop Detection                                   │
│  - Capability Envelope                              │
└─────────────────────────────────────────────────────┘
```

### Integration Points

| Komponente | Datei | Aenderung |
|:---|:---|:---|
| Validation Node | `agent/graph/nodes/pddl_node.py` (neu) | Plan → PDDL → Solve → Valid/Invalid |
| Domain Registry | `agent/planning/domains/` (neu) | PDDL Domain-Files je Workflow-Typ |
| Problem Builder | `agent/planning/builder.py` (neu) | Runtime-State → PDDL Problem |
| Graph Integration | `agent/graph/agent_graph.py` | Conditional Node vor tool_execute |
| Config | `consent_policy.yaml` | `pddl_validation: enabled/disabled` Toggle |

---

## Phase 1: Pilot "Morning Research Run"

### Domain-Modell

Minimaler Ablauf mit temporalen + numerischen Constraints:

1. **load_macro_data** (2-3 min) — Makrodaten + News laden
   - Precondition: keine
   - Effect: `macro_data_loaded = true`
   - Resource: 1 API-Call

2. **load_calendar** (1 min) — Wirtschaftskalender laden
   - Precondition: keine (parallel zu #1 moeglich)
   - Effect: `calendar_loaded = true`
   - Resource: 1 API-Call

3. **refresh_features** (3-5 min) — Feature-Vektoren aktualisieren
   - Precondition: `macro_data_loaded AND calendar_loaded`
   - Effect: `features_fresh = true`
   - Resource: 2 API-Calls

4. **consistency_check** (1 min) — Frische-Gates pruefen
   - Precondition: `features_fresh`
   - Effect: `consistency_ok = true`

5. **generate_briefing** (2-3 min) — Research-Briefing erstellen
   - Precondition: `consistency_ok`
   - Effect: `briefing_ready = true`
   - Resource: 1 LLM-Call

### Constraints

- **Deadline:** `briefing_ready` muss innerhalb 15 min erreicht sein
- **API-Budget:** max 5 API-Calls total
- **Parallelitaet:** Steps 1+2 duerfen parallel laufen
- **Fallback:** Wenn Primary-Provider fehlschlaegt → Fallback-Action mit +2 min Dauer
- **Non-self-overlapping:** Kein Step darf sich selbst ueberlappen

### Implementation Steps

- [ ] **14.1:** `unified-planning` + Engines in pyproject.toml
  - `unified-planning>=1.3.0`
  - `up-tamer>=1.1.6` (temporal)
  - `up-fast-downward>=0.5.2` (klassisch)
  - `up-enhsp>=0.1.0` (numerisch)
- [ ] **14.2:** PDDL Domain fuer Morning Research Run
  - `agent/planning/domains/morning_research.py` — unified-planning API
  - Durative Actions mit Start/End Conditions + Effects
  - Numerische Fluents fuer API-Budget
  - Deadline als timed goal
- [ ] **14.3:** Problem Builder
  - `agent/planning/builder.py` — Runtime-State → Problem-Instanz
  - Liest aktuellen State (welche Daten schon geladen, wieviel Budget uebrig)
  - Erzeugt `Problem` mit korrekten Initial-Values
- [ ] **14.4:** PDDL Validation Node
  - `agent/graph/nodes/pddl_node.py` — LangGraph Node
  - Empfaengt geplante Steps vom LLM
  - Mapped Steps auf PDDL Actions
  - Ruft Solver auf (Tamer fuer temporal, ENHSP fuer numerisch)
  - Bei Valid: gibt Plan an tool_execute weiter
  - Bei Invalid: gibt Fehlergrund zurueck ans LLM (Replan)
- [ ] **14.5:** Graph Integration
  - Conditional Edge in `agent_graph.py`: wenn Workflow-Typ PDDL-faehig → pddl_node
  - Toggle via `consent_policy.yaml` oder ENV
  - Graceful Degradation: wenn Solver nicht installiert → Skip (Warning)
- [ ] **14.6:** Replan-Mechanismus
  - Invalid-Plan Fehlerklassen definieren (Deadline-Verletzung, Budget-Ueberschreitung,
    Ordering-Verletzung, Parallelitaets-Konflikt, Provider-Ausfall)
  - Solver-Feedback als System-Message an LLM: "Plan ungueltig weil: X. Bitte anpassen."
  - Max 3 Replan-Versuche, danach Fallback auf LangGraph-only

## Phase 2: Erweiterung + Evidence

- [ ] **14.7:** Zweiten Workflow modellieren (z.B. "Portfolio Rebalancing Check")
- [ ] **14.8:** Solver-Vergleich: Tamer vs ENHSP vs FastDownward vs POPF vs LPG
  - Solve-Time, Plan-Qualitaet, Feature-Support je Domain
  - Dokumentierte Staerken/Schwaechen je Solver
- [ ] **14.9:** Performance-Messung: p95 Solve-Time (Ziel: <= 2s)
- [ ] **14.10:** Semantik-Regression-Suite: `overall`, `no-moving-target`, `mutex`
  - Optional: NeSIG-Pattern fuer automatische Problem-Generierung evaluieren
  - NeSIG Paper: https://www.sciencedirect.com/science/article/pii/S0004370225001900
  - Status: Research-Phase, kein Production-Tooling
- [ ] **14.11:** Evidence-Matrix je Research-Claim (abgedeckt/teilweise/nicht abgedeckt)

## Phase 2.5: SagaLLM Compensation Pattern

- [ ] **14.12:** Compensation-Definitions fuer Agent-Actions
  - Jede PDDL-Action bekommt eine Compensation-Action
  - Dependency-Graph fuer Rollback-Reihenfolge
  - Pattern: Saga S = {T1, T2, ..., Tn, Cn, ..., C2, C1}
- [ ] **14.13:** GlobalValidationAgent (unabhaengige Validierung)
  - Externer Agent prueft Outputs vor Commit
  - Nicht Self-Validation (LLM prueft sich selbst = unzuverlaessig)
  - Prueft: Syntax, Semantik, Constraint-Adherence, Dependencies
- [ ] **14.14:** Context Persistence fuer lange Workflows
  - Persistent Memory gegen Attention-Degradation
  - Goals, Constraints, Dependencies bleiben erhalten
- [ ] **14.15:** Runtime-Rollback bei Fehler
  - Fehler in Step N → Compensations C(N-1)...C(1) ausfuehren
  - State wiederherstellen → Replan mit aktualisiertem State
  - SagaLLM Referenz: https://arxiv.org/abs/2503.11951
  - SagaLLM GitHub: https://github.com/genglongling/SagaLLM

## Phase 3: Produktionsreife + Evaluation weiterer Ansaetze

- [ ] **14.16:** Lock-/Interference-Modell als Runtime-Policy-Mapping
- [ ] **14.17:** Event-Muster fuer delayed effects + timed initial literals
- [ ] **14.18:** Multi-Agent Plan Coordination (exec-10 Sub-Agents, MA-PDDL evaluieren)
- [ ] **14.19:** LLM-assisted PDDL Problem Generation (L2P Library evaluieren)
  - L2P GitHub: https://github.com/AI-Planning/l2p
  - Achtung: LLM-generierte Domains nur 24-35% semantisch korrekt
  - → Domains manuell, LLM nur fuer Problem-Instanzen
- [ ] **14.20:** GenePlan-Pattern: Evolutionaere PDDL-Plan-Optimierung (ICAPS 2026)
- [ ] **14.21:** VeriPlan-Pattern: LTL Constraints + Model Checking als Alternative zu PDDL
  - VeriPlan Paper: https://arxiv.org/abs/2502.17898
  - PRISM Model Checker: https://www.prismmodelchecker.org/
  - Stormpy (Python): https://moves-rwth.github.io/stormpy/
- [ ] **14.22:** Z3 SMT-Solver fuer numerische Constraint-Satisfiability
  - Z3 GitHub: https://github.com/Z3Prover/z3
  - Python: `pip install z3-solver`
  - Use-Case: Rein numerische Constraints ohne temporale Planung
    (z.B. Portfolio-Gewichtung, Budget-Allokation)
- [ ] **14.23:** VAL Plan Validator als unabhaengiger Double-Check
  - VAL in FastDownward enthalten
  - Validiert ob LLM-/Solver-generierter Plan korrekt ist
- [ ] **14.24:** HDDL Evaluation fuer hierarchische Workflows
  - Aries Solver unterstuetzt HTN: `up-aries>=0.4.0`
  - HDDLGym fuer Multi-Agent HTN: https://arxiv.org/html/2505.22597v1
- [ ] **14.25:** RDDL Evaluation fuer probabilistische Szenarien (niedrige Prioritaet)
  - Nur wenn stochastische Marktmodellierung benoetigt wird

---

## Go/No-Go-Kriterien

Adopt nur wenn alle Punkte stabil erfuellt:

- Plan-Validitaet >= 95% auf definiertem Testset
- p95 Planerzeugung + Validierung <= 2s (Pilot-Szenarien)
- Deadline-Adherence verbessert oder mindestens baseline-neutral
- Replan-Rate sinkt in Konfliktfaellen gegenueber rein heuristischem Planner
- Keine signifikante Runtime-Komplexitaet fuer Standardfaelle

**Defer** wenn Modellierungs-/Betriebsaufwand den Nutzen uebersteigt.

---

## Verify-Gates

### Phase 1: Pilot
- [ ] unified-planning + Engines installiert und importierbar
- [ ] Morning Research Run Domain loest korrekt (valid plan in < 2s)
- [ ] Invalid-Plan wird korrekt geblockt (Deadline-Verletzung)
- [ ] Replan bei Constraint-Verletzung funktioniert (LLM bekommt Fehlergrund)
- [ ] PDDL Node in LangGraph Graph integriert (conditional edge)
- [ ] Graceful Degradation: Solver nicht installiert → Skip mit Warning
- [ ] API-Budget Constraint wird enforced (numerischer Fluent)

### Phase 2: Evidence
- [ ] p95 Solve-Time <= 2s auf Pilot-Szenarien
- [ ] Solver-Vergleich dokumentiert (Tamer vs ENHSP vs FD vs POPF vs LPG)
- [ ] Semantik-Tests decken overall/no-moving-target/mutex ab
- [ ] Evidence-Matrix vollstaendig und auditierbar
- [ ] Go/No-Go Entscheid dokumentiert

### Phase 2.5: SagaLLM
- [ ] Compensation-Actions definiert fuer Pilot-Workflow
- [ ] Rollback bei Runtime-Fehler funktioniert (Compensation-Chain)
- [ ] GlobalValidationAgent prueft Outputs unabhaengig

### Phase 3: Erweiterungen
- [ ] Mindestens ein weiterer Workflow modelliert und validiert
- [ ] HDDL oder LTL als Alternative evaluiert mit dokumentiertem Ergebnis
- [ ] Z3 oder VAL als zusaetzlicher Validator getestet

---

## Herkunft: Delta-Mapping von pddl_phase22b_delta.md

Dieser Slice konsolidiert `pddl_phase22b_delta.md` (Phase 22b, Rev. 3, 16.03.2026).
Original archiviert unter `specs/execution/archive/pddl_phase22b_delta.md`.

| Original-Delta | exec-14 Step | Status |
|:---|:---|:---|
| P22B1 Pilot-Domain modellieren | 14.2 | Geplant |
| P22B2 Zeit-/Ressourcen-Constraints | 14.2 (Deadline + API-Budget) | Geplant |
| P22B3 Non-self-overlapping festhalten | 14.2 (Annahme dokumentiert) | Abgedeckt in Spec |
| P22B4 FastDownward via subprocess | 14.1 (up-fast-downward Package) | Geplant |
| P22B5 unified_planning evaluieren | 14.1 (unified-planning als Basis) | Entschieden: JA |
| P22B6 Runtime-Hook Planner↔Executor | 14.4 + 14.5 (PDDL Node + Graph) | Geplant |
| P22B7 Invalid-Plan Fehlerklassen | 14.6 (Replan-Mechanismus) | Geplant |
| P22B8 Sprach-/Spec-Grenzen doku | Motivation-Section (Layer-Tabelle) | Abgedeckt in Spec |
| P22B9 Go/No-Go Evidence | Go/No-Go-Kriterien Section | Abgedeckt in Spec |
| P22B10 Semantik-Regression-Suite | 14.10 | Geplant |
| P22B11 Lock-/Interference-Modell | 14.16 (Phase 3) | Geplant |
| P22B12 Event-Muster delayed effects | 14.17 (Phase 3) | Geplant |
| P22B13 Solver-Vergleich FD vs UP | 14.8 (Phase 2) | Geplant |
| P22B14 Evidence-Matrix | 14.11 (Phase 2) | Geplant |
| P22B15 Failure-Taxonomie | 14.6 (Fehlerklassen) | Geplant |
| P22B16 Konsolidierung Research-TXT | Erledigt (TXT superseded) | ✅ |

Verify-Gates P22B.V1–V10 sind in den exec-14 Verify-Gates vollstaendig abgebildet.

---

## Referenzen

### Kern-Papers
- arXiv 2603.12188: Compiling Temporal Numeric Planning into Discrete PDDL+ (ICAPS 2026)
  https://arxiv.org/abs/2603.12188
- arXiv 2512.09629: End-to-end Planning Framework with Agentic LLMs and PDDL
  https://arxiv.org/abs/2512.09629
- VeriPlan (CHI 2025): Integrating Formal Verification and LLMs into End-User Planning
  https://arxiv.org/abs/2502.17898
- SagaLLM (VLDB 2025): Context Management, Validation, and Transaction Guarantees
  https://arxiv.org/abs/2503.11951
- arXiv 2404.11891: LLMs Can Solve Planning with Formal Verification (NAACL 2025)
  https://arxiv.org/abs/2404.11891
- arXiv 2510.03469: Bridging LLM Planning Agents and Formal Methods
  https://arxiv.org/abs/2510.03469

### ICAPS 2026
- Accepted Papers: https://icaps26.icaps-conference.org/program/accepted/
- Call for Papers: https://icaps26.icaps-conference.org/calls/cfp/
- Special Tracks: https://icaps26.icaps-conference.org/calls/special_tracks/

### Tools + Libraries
- unified-planning: https://github.com/aiplan4eu/unified-planning
- unified-planning Docs: https://unified-planning.readthedocs.io/
- unified-planning Temporal Planning: https://unified-planning.readthedocs.io/en/latest/notebooks/03-temporal-planning.html
- up-fast-downward: https://github.com/aiplan4eu/up-fast-downward/
- up-enhsp: https://github.com/aiplan4eu/up-enhsp
- FastDownward: https://www.fast-downward.org/
- FastDownward GitHub: https://github.com/aibasel/downward
- L2P (NL→PDDL): https://github.com/AI-Planning/l2p
- SagaLLM GitHub: https://github.com/genglongling/SagaLLM
- Z3 SMT-Solver: https://github.com/Z3Prover/z3
- PRISM Model Checker: https://www.prismmodelchecker.org/
- Stormpy: https://moves-rwth.github.io/stormpy/

### Spezifikationen
- PDDL 2.1: https://planning.wiki/ref/pddl21
- PDDL Wiki: https://planning.wiki/guide/whatis/pddl
- LearnPDDL: https://fareskalaboud.github.io/LearnPDDL/
- HDDL Paper: https://cdn.aaai.org/ojs/6542/6542-13-9767-1-10-20200519.pdf

### Surveys + weitere Paper
- LLMs as Planning Formalizers (ACL 2025): https://aclanthology.org/2025.findings-acl.1291.pdf
- Modern Survey of LLM Planning (ACL 2025): https://aclanthology.org/2025.acl-long.958.pdf
- AutoPlanBench 2.0: https://coli-saar.github.io/autoplanbench
- NeSIG (Neuro-Symbolic Instance Gen): https://www.sciencedirect.com/science/article/pii/S0004370225001900
- HDDLGym: https://arxiv.org/html/2505.22597v1
- Temporal Planning Algorithms: https://github.com/aig-upf/temporal-planning
- pddl_phase22b_delta.md (Hauptprojekt — Original-Spec, superseded)
