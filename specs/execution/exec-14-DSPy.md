# exec-14-DSPy — Declarative Self-improving Language Programs als matrix-optimization-layer

**Datum:** 2026-04-20
**Status:** Draft / Research
**Abhängig von:** exec-14-pddl-formal-planning (thematisch verwandt), exec-harness (DSPy's primäres zuhause in matrix), exec-skills (direkter overlap mit `agent/skills/pareto.py` + `evolver.py`), exec-a2fm (DSPy als routing-optimizer-upgrade), exec-16 (LiteLLM als DSPy-target-layer)

**Referenzen (alle PDFs in `docs/papers/`):**
- DSPy original: Khattab et al 2023 — `docs/papers/DSPy-2310.03714.pdf` (ICLR 2024, 32 pages)
- MIPROv2: Opsahl-Ong et al 2024 — `docs/papers/MIPRO-2406.11695.pdf` (EMNLP 2024, 28 pages)
- GEPA: Agrawal et al 2025 — `docs/papers/GEPA-2507.19457.pdf` (**ICLR 2026 Oral**, 21 pages)
- LLMs as Planning Formalizers Survey 2025 — `docs/papers/LLMs-Planning-Formalizers-Survey-2025.pdf`
- Generalized Planning with LLMs + Strategy Refinement — `docs/papers/Generalized-Planning-LLMs-2508.13876.pdf` (27 pages)
- DSPy framework: [dspy.ai](https://dspy.ai/) · GitHub [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) (160k monthly downloads, 16k stars, 250+ contributors)
- GEPA standalone package: [github.com/gepa-ai/gepa](https://github.com/gepa-ai/gepa)

---

## 0. Warum ein eigenes exec

DSPy ist **nicht** ein planning-framework — es ist ein **LLM-program-compiler mit metric-driven self-improvement**. Es steht neben exec-14-PDDL thematisch als "exotisches" programming-paradigm für LLMs: wo PDDL formal-symbolic-plans validiert, compiliert DSPy LLM-programme gegen fitness-metriken. **Beide zusammen** ergeben das hybrid-neuro-symbolic-planning-pattern das die 2025/26-forschung (siehe survey-paper) als richtung identifiziert.

Warum separat von exec-14-PDDL:
- PDDL = symbolisch-deterministisch (preconditions, effects, goals) — validiert ja/nein
- DSPy = neuronal-probabilistisch (signatures, modules, optimizers) — verbessert via metric
- DSPy kann den NL→PDDL-translator **bauen + selbst optimieren** (compose, not replace)

Warum nicht in exec-harness vergraben:
- DSPy spannt **mehrere matrix-module** (harness + skills + a2fm + PDDL-translator). Umbrella-spec analog zu `exec-security` für redact/HITL/audit.

---

## 1. Big-tech adoption — reality check

Vor dem "sollen wir DSPy übernehmen?"-entscheid:

| Firma | Nutzt DSPy intern? | Realität (2026-04) |
|---|---|---|
| **Anthropic** | Nein (kein public signal) | Claude ist ein DSPy-target (provider) via Anthropic SDK. Anthropic-internal: Claude Skills, Claude Code, nicht DSPy. |
| **Google DeepMind** | Nein direkt — aber OPRO ist konzeptionell nah | Gemini ist DSPy-target. DeepMind hat eigene internal-tools. |
| **OpenAI** | Nein | GPT-5 "router" ist konzeptionell ähnlich zu DSPy's compile. OpenAI-API ist DSPy-target. |
| **Databricks** | Ja, integration via Lakehouse | Enterprise-production-user + anthropic-partner |
| **Stanford HAI** | Development-origin | Forschungsheim |
| **Enterprise** (Haize, Weaviate, MLflow, Langfuse) | Ja (production / observability / tutorials) | Community-driven adoption |

**Fazit:** DSPy ist **community-framework, nicht big-tech-internal-tool**. Die grossen labs bauen **konzeptionell ähnliches intern** (Google OPRO, OpenAI routing, Anthropic skills). DSPy ist der **offene framework-standard** für das gleiche paradigm.

**Was heißt das für matrix:** DSPy zu adopten ist ein **framework-commitment**, kein "what anthropic does" copycat. Entscheidungs-axis: bauen wir das pattern selbst (status quo matrix `agent/skills/` + `agent/harness/` tun das bereits teilweise) oder konsolidieren wir auf DSPy.

---

## 2. DSPy 101

**Kern-abstraktionen** (sparse, damit jeder im team's das gleiche modell hat):

### 2.1 Signature

Typed I/O deklaration einer LLM-aufgabe:

```python
class AnswerQuestion(dspy.Signature):
    """Answer the question based on the context."""
    context = dspy.InputField()
    question = dspy.InputField()
    answer = dspy.OutputField(desc="Short factual answer")
```

### 2.2 Module

Executable LLM-pattern, parameterized über eine signature:

- `dspy.Predict(signature)` — base LLM-call
- `dspy.ChainOfThought(signature)` — CoT wrapper
- `dspy.ReAct(signature, tools)` — tool-use loop
- `dspy.Refine(module)` — self-refinement
- Custom `dspy.Module` subclasses — komposite pipelines

### 2.3 Optimizer (compile)

Nimmt ein DSPy-program + metric + training-set, findet **optimale prompts + few-shot-examples + optional fine-tune-weights**:

| Optimizer | Method | Quality-gain vs manual | Paper |
|---|---|---|---|
| **BootstrapFewShot** | Few-shot example selection | baseline | DSPy 2023 |
| **MIPROv2** | Bayesian optimization über instructions + few-shot | **+13% avg** on 5 multi-stage programs | MIPRO 2024 |
| **GEPA** | Reflective pareto-frontier-evolution | **+10% vs MIPROv2**, **+20% vs GRPO (RL)** using **35× fewer rollouts** | GEPA 2025, ICLR 2026 Oral |

**GEPA ist der aktuelle SOTA** (April 2026). Reflective prompt-evolution schlägt reinforcement-learning in both quality und sample-efficiency.

### 2.4 Compile ≠ training

`program.compile(trainset, metric)` produziert einen **statischen optimierten prompt-graph**. Kein separates model-fine-tuning nötig (obwohl möglich). Das macht DSPy **laufzeit-kompatibel mit matrix** — die optimierten prompts sind standard-text, gehen durch LiteLLM gateway genau wie manuelle prompts.

---

## 3. DSPy vs PDDL — composition, nicht konkurrenz

Kritischer framing-punkt: DSPy und PDDL sind **orthogonale layers**, nicht konkurrierende approaches.

```
User natural-language intent
        ↓
┌─────────────────────────────┐
│  DSPy-compiled translator   │   ← GEPA/MIPRO optimiert den prompt
│  (NL → PDDL)                │
└─────────────────────────────┘
        ↓
   PDDL program (symbolic)
        ↓
┌─────────────────────────────┐
│  PDDL solver (Fast Downward, │   ← exec-14-PDDL owns
│   Pyperplan, etc.)           │
└─────────────────────────────┘
        ↓
   Validated plan (or refusal)
        ↓
    Agent execution
        ↓
    Outcome-metric feedback
        ↓
  DSPy optimizer learns from solver-rejections
  → proposes better NL→PDDL prompts
```

Die research-trend 2025/26 (siehe 3 planning-papers in `docs/papers/`): **LLM generiert + symbolischer solver validiert + meta-optimizer schliesst den loop**. DSPy ist ein natural-fit für den meta-optimizer-step.

---

## 4. Matrix integration map — vier natürliche häuser

DSPy hat in matrix **vier modul-ebenen** wo es direkt andocken kann:

### 4.1 `agent/harness/` — PRIMARY home

**Status heute:** matrix hat `agent/harness/scorer.py` (composite_fitness, Phase-C §4g) + `agent/harness/evolver.py` + ein selbst-gebautes meta-optimization-loop.

**DSPy-overlap:** GEPA **IST** meta-optimization. `composite_fitness` → DSPy-metric. `score_session` → DSPy-evaluate. Die gesamte harness-struktur ist ein DSPy-program im ungemalten zustand.

**Integrations-option A (aggressive):** refactor harness auf DSPy. `agent.harness.scorer.score_session()` wird eine `dspy.Metric`. `agent.harness.evolver` wird ein `dspy.GEPA` instance. Bestehende `agent.harness.pareto` wird ersetzt durch DSPy-GEPA-pareto-frontier.

**Integrations-option B (konservativ):** DSPy zusätzlich, alles bestehende bleibt. Neue agent-programme (plan-skill, A2A-coordinator) werden als `dspy.Module`s gebaut, alte paths bleiben.

### 4.2 `agent/skills/` — direkter overlap

**Status heute:** `agent/skills/evolver.py`, `refiner.py`, `pareto.py`, `iterative_search.py`, `rl_trainer.py`, `trigger_quality.py`, `offline_refiner.py` — matrix hat ein EvoSkill-style skill-optimization-system.

**DSPy-overlap:** DSPy's GEPA **is** pareto-frontier-based prompt-evolution. Matrix's skill-pareto ist konzeptionell identisch. Wir haben möglicherweise eine eigene DSPy gebaut, unterinformiert.

**Decision-point:** sind `agent/skills/` optimizers **architektonisch different** von DSPy-GEPA (z.B. RL-trainer ist specifisch für skill-RLHF, nicht DSPy-shaped)? Oder könnten wir sie durch dspy.GEPA ersetzen? **sota-contrarian stakes=high** review nötig bevor refactor.

### 4.3 `agent/a2fm` / smart-routing — routing-optimizer

**Status heute:** `agent/llm/smart_routing.py` — keyword-heuristik (Stufe 0). `exec-a2fm` Stufe 1 = ML-router (planned).

**DSPy-integration:** ML-router als `dspy.Predict(RouteClassifier)` mit signature `(user_message) -> route_decision`. GEPA kompiliert den classifier-prompt auto-optimiert auf historical routing-quality-metric. Das ist Stufe 1 ohne eigenes model-training.

### 4.4 `exec-14-pddl-formal-planning` — als Layer 2 über PDDL

**Layer 0 (DONE):** skill-based plan-mode (`agent/skills/global/plan/SKILL.md`).
**Layer 1 (exec-14-PDDL core, planned):** PDDL-validator.
**Layer 2 (hier, dieser spec):** DSPy-compiled NL→PDDL translator + self-improving via solver-feedback.

**Research-footing:** die papers in `docs/papers/` (Planning-Formalizers-Survey, Generalized-Planning-LLMs) zeigen empirisch dass LLMs allein **schlechte planners** sind aber **gute PDDL-generatoren** wenn richtig optimiert.

---

## 5. Wichtigste entscheidungen

Vor jedem commitment:

### D-1. Replace matrix's custom skill-optimization durch DSPy?

**Pro:** weniger code zu warten, community-gehärteter optimizer (GEPA SOTA), upstream-innovationen kostenfrei.
**Contra:** matrix's `agent/skills/rl_trainer.py` + `trigger_quality.py` sind spezifisch-getunte module; DSPy-style refactor = invasive change an gerade-produktiver maschinerie.
**Entscheidungs-hilfe:** sota-contrarian stakes=high auf matrix-skills vs DSPy-overlap benchmark.

### D-2. DSPy-`dspy.Module` als standard-interface für neue agent-patterns?

**Pro:** einheitlicher programming-model, auto-optimizer-ready aus der box.
**Contra:** matrix hat bereits LangGraph runner + SimpleLoop (Phase-C); dritter runner-pattern wäre fragmentierung.
**Entscheidungs-hilfe:** DSPy-modules **sind keine eigene loop**, sie sind compositable-units. Könnten innerhalb LangGraph nodes oder SimpleLoop laufen. Kein dritter runner.

### D-3. DSPy-compile-output versioning + deployment?

DSPy-compile produziert ein optimiertes prompt-artefakt. Wohin speichert matrix das? Optionen:
- **Postgres JSONB** (neue column `agent.compiled_programs`) — live-reload, versioniert
- **File-based** in `agent/skills/compiled/`
- **DSPy's built-in MLflow integration** — tracking + artifact-store

Enterprise-pattern für matrix: **DB-backed versioning mit user_id-scoping**. Migration nötig.

### D-4. DSPy integration mit Phase-C A/B dispatcher?

Können DSPy-compiled programs als **dritte variant** im Phase-C dispatcher laufen? `variant="dspy_compiled"` → misst harness_fitness_score von DSPy-optimized vs LangGraph vs SimpleLoop. Das wäre die **cleanste empirical-grundlage** für alle D-1/D-2 entscheidungen.

### D-5. Cost-model

GEPA: 35× fewer rollouts als RL, aber **MIPROv2 + GEPA sind selbst LLM-calls** (optimizer-LM generiert prompt-proposals). Compile-run ist teuer. Matrix muss:
- compile-run-jobs **nicht synchronously** im chat-path haben (Scheduler-worker ist richtig)
- compile-budget per-user limitieren (via `agent.user_llm_settings.dspy_compile_budget_usd_per_month`)
- compile-results **cachen** (nicht jede turn neu compile)

---

## 6. Phase plan (skizze, nicht commitment)

**Voraussetzung: Welle 1 (verify-gates) + Welle 2 (Phase-C tail) abgeschlossen bevor DSPy scope-bindet.**

### Phase 0 — Research + contrarian (0.5–1 tag)
- Diesen spec durchgehen
- sota-contrarian stakes=high auf D-1..D-5
- Go/No-go decision

### Phase 1 — Exploratory integration (1–2 wochen, post-contrarian)
- DSPy als python-backend dependency
- Einen konkreten existing matrix-flow als `dspy.Module` re-implementieren (kandidaten: plan-skill, skill-refiner, smart-routing classifier)
- MIPROv2 oder GEPA-compile gegen historischen chat-daten
- Fitness-vergleich: custom-impl vs DSPy-compiled

### Phase 2 — Schema + deployment
- Migration `agent.compiled_programs` (jsonb version control)
- `agent/harness/dspy_compile_worker.py` — Scheduler-integrated background-compile
- Per-user compile-budget enforcement

### Phase 3 — A/B integration
- Phase-C dispatcher variant `"dspy_compiled"` for selected programs
- harness_fitness_score comparison vs langgraph/simple variants

### Phase 4 — Scale-out
- Replace decisions from Phase 1 benchmark: custom matrix-code that DSPy-GEPA measurably beats gets refactored
- Custom-code that beats DSPy (edge cases) stays

---

## 7. Verify gates

### Phase-0 gates (research)
- [ ] Alle 5 papers in `docs/papers/` durchgelesen
- [ ] sota-contrarian stakes=high run gegen D-1..D-5
- [ ] Go/No-go in doc festgehalten

### Phase-1 gates (exploratory)
- [ ] DSPy als optional-dependency in `python-backend/pyproject.toml`
- [ ] Ein existing-flow als `dspy.Module` re-implementiert — code + test
- [ ] MIPROv2- oder GEPA-compile-run succeeds gegen historical-data fixture
- [ ] Fitness-benchmark: custom vs DSPy-compiled — reproducible notebook in `docs/notebooks/`

### Phase-2 gates (schema)
- [ ] Migration für `agent.compiled_programs` + rollback tested
- [ ] DSPy-compile-worker als River-handler (exec-scheduler §8.x pattern)
- [ ] Budget-enforcement via `agent.user_llm_settings` (jsonb key `dspy_compile`)

### Phase-3 gates (A/B)
- [ ] Dispatcher variant `"dspy_compiled"` — smoke-test
- [ ] ab_experiments rows mit harness_fitness_score + variant for DSPy
- [ ] N ≥ 100 per variant → Welch t-test significance

---

## 8. Cross-refs

- `exec-14-pddl-formal-planning.md` — PDDL layer 1 (DSPy hier ist layer 2)
- `exec-harness.md §4g` — fitness-metriken + composite_fitness, DSPy's primary home
- `exec-skills.md` — evolver/pareto/refiner overlap (direct replacement candidates)
- `exec-a2fm-adaptive-routing.md` — smart-routing Stufe 1 upgrade path
- `exec-16-llm-provider-gateway.md` — DSPy → LiteLLM → providers
- `exec-blocking.md §C10` — per-model thresholds via meta-harness-regression (DSPy GEPA ist das fehlende teilchen)
- `EXECUTION-ORDER.md` Cluster K (planning) + Welle 3 research (wo DSPy hingehört nach Welle 2)

---

## 9. Changelog

| Datum | Änderung |
|---|---|
| 2026-04-20 | Erstversion. 5 foundation-papers in `docs/papers/` heruntergeladen (DSPy 2023 + MIPROv2 2024 + GEPA 2025 ICLR-2026-oral + Planning-Formalizers-Survey 2025 + Generalized-Planning-LLMs 2025). Integration-map über 4 matrix-häuser (harness/skills/a2fm/PDDL). 5 offene entscheidungs-punkte (D-1..D-5) für sota-contrarian stakes=high review. Phase-plan skizziert. NOT committed to implementation — research/eval phase. |
