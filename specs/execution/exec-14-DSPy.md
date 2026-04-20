# exec-14-DSPy — Declarative Self-improving Language Programs als matrix-optimization-layer

**Datum:** 2026-04-20 (paper-kopien erweitert 2026-04-20)
**Status:** Draft / Research
**Abhängig von:** exec-14-pddl-formal-planning (thematisch verwandt), exec-harness (DSPy's primäres zuhause in matrix), exec-skills (direkter overlap mit `agent/skills/pareto.py` + `evolver.py`), exec-a2fm (DSPy als routing-optimizer-upgrade), exec-16 (LiteLLM als DSPy-target-layer)

---

## Lokale Paper-Kopien (2026-04-20)

Alle foundation- + comparison-papers sind jetzt in `docs/papers/` verfügbar für offline-review:

| arXiv ID | Titel | Venue | Pages | Lokale datei |
|---|---|---|---|---|
| **2310.03714** | **DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines** — Khattab et al 2023 (Stanford) — **Kern-paper** | ICLR 2024 | 32 | `docs/papers/DSPy-2310.03714.pdf` |
| **2406.11695** | **Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs** (MIPROv2) — Opsahl-Ong et al 2024 | EMNLP 2024 | 28 | `docs/papers/MIPRO-2406.11695.pdf` |
| **2507.19457** | **GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning** — Agrawal et al 2025 — **current SOTA** (+10% vs MIPROv2, +20% vs GRPO at 35× fewer rollouts) | **ICLR 2026 Oral** | 21 | `docs/papers/GEPA-2507.19457.pdf` |
| **2309.03409** | **Large Language Models as Optimizers** (OPRO) — Yang/Wang/Lu/Liu/Le/Zhou/Chen, **Google DeepMind** — konzeptioneller vorgänger, +8% GSM8K / +50% BBH vs human-designed prompts | ICLR 2024 | 42 | `docs/papers/DSPy-2309.03409.pdf` |
| **2406.07496** | **TextGrad: Automatic "Differentiation" via Text** — Yuksekgonul/Bianchi/Zou et al (Stanford) — parallel framework, backprops textual feedback through compound AI systems, +4pp GPT-4o auf GPQA, +20% LeetCode-Hard | arXiv 2024 | 41 | `docs/papers/DSPy-2406.07496.pdf` |
| **2502.16923** | **A Systematic Survey of Automatic Prompt Optimization Techniques** — 2025 | arXiv 2025 | 31 | `docs/papers/DSPy-2502.16923.pdf` |
| **2603.20667** | **REVERE: Reflective Evolving Research Engineer for Scientific Workflows** — **arXiv 2026-03** — DSPy-style reflective evolution applied to research-engineering agent | arXiv 2026 | 24 | `docs/papers/DSPy-2603.20667.pdf` |
| **2604.05150** | **Compiled AI: Deterministic Code Generation for LLM-Based Workflow Automation** — **arXiv 2026-04** — references DSPy as antecedent, new paradigm where LLMs generate code-artifacts during compilation | arXiv 2026 | 14 | `docs/papers/DSPy-2604.05150.pdf` |
| **2604.08801** | **p1: Better Prompt Optimization with Fewer Prompts** — **arXiv 2026-04** — post-GEPA optimizer, benchmarks against MIPROv2 + GEPA | arXiv 2026 | 30 | `docs/papers/DSPy-2604.08801.pdf` |
| **2601.13922** | **Automatic Prompt Optimization for Dataset-Level Feature Discovery** — **arXiv 2026-01** — orthogonal approach to MIPRO/GEPA (dataset-level vs per-sample feedback) | arXiv 2026 | 10 | `docs/papers/DSPy-2601.13922.pdf` |
| **2502.14815** | **LLMSelector: Optimizing Model Selection for Compound AI Systems** — Feb 2025 — **beats DSPy+MIPROv2 by 5-70% accuracy** on compound-AI-systems. **Kritischer benchmark für D-1 decision**. | arXiv 2025 | 18 | `docs/papers/DSPy-2502.14815.pdf` |
| **2507.03041** | **Optimas: Optimizing Compound AI Systems with Globally Aligned Local Rewards** — 2025 Q3 — DSPy-extension, heterogeneous configs + local-optimization data-efficiency | arXiv 2025 | 22 | `docs/papers/DSPy-2507.03041.pdf` |
| 2025 ACL findings | **LLMs as Planning Formalizers: A Survey for Leveraging LLMs to Construct Automated Planning Models** | ACL 2025 findings | — | `docs/papers/LLMs-Planning-Formalizers-Survey-2025.pdf` |
| **2508.13876** | **Improved Generalized Planning with LLMs through Strategy Refinement and Reflection** | arXiv 2025 | 27 | `docs/papers/Generalized-Planning-LLMs-2508.13876.pdf` |

**2026-arxiv papers DSPy-track** (aktivste forschungs-front):
- `2507.19457` GEPA — ICLR 2026 **Oral** (venue 2026, arxiv 2025 v1 → 2026-02 v2)
- `2603.20667` REVERE — reflective evolution scientific workflows (März 2026)
- `2604.05150` Compiled AI — new paradigm, DSPy als antecedent (April 2026)
- `2604.08801` p1 — post-GEPA optimizer (April 2026)
- `2601.13922` Dataset-level feature discovery — compares vs MIPRO/GEPA (Jan 2026)
- (plus PDDL-side 2026-papers — siehe `exec-14-pddl-formal-planning.md §2026-arxiv papers`)

**Reading-priorität für team** (P1 = must-read, P2 = wichtig für entscheidung, P3 = context/reference):

### 🔴 P1 — foundational (muss jeder lesen bevor irgendwas)

1. **DSPy original (2310.03714)** — programming-model, signatures/modules/compile. Ohne das versteht niemand was GEPA/MIPRO überhaupt optimieren.
2. **GEPA (2507.19457, ICLR 2026 Oral)** — current SOTA, aktives forschungs-frontier, reflective-pareto-evolution. Das ist *der* optimizer auf den wir wenn-dann committen.
3. **LLMSelector (2502.14815, Feb 2025)** — **beats DSPy+MIPROv2 by 5-70% accuracy** auf compound-AI-systems via model-selection-optimization. **Kritisch für D-1 decision**: wenn LLMSelector's approach matrix-passender ist als DSPy, kippt D-1 ("replace matrix skill-optimization durch DSPy?") evtl. Richtung "nein, nicht DSPy, eher LLMSelector-pattern".

### 🟡 P2 — entscheidungs-relevant (für D-1..D-6 review)

4. **MIPROv2 (2406.11695, EMNLP 2024)** — bridge von DSPy-v1 zu GEPA, bayesian-optimization-variant. Nötig für verständnis der GEPA-improvements (+10%) und was heutige production-DSPy-deployments einsetzen.
5. **TextGrad (2406.07496, Stanford/Zou-lab 2024)** — **direkter konkurrent zu DSPy**. Kritisch für **D-6 framework-choice decision** (DSPy vs TextGrad vs own-OPRO-style). Ohne dieses paper können wir Option B nicht evaluieren.
6. **p1 (2604.08801, arxiv 2026-04)** — **aktuellster optimizer post-GEPA**. "Better Prompt Optimization with Fewer Prompts". Benchmarks direkt gegen MIPROv2 + GEPA. Wenn wir committen, sollten wir wissen was **nach** GEPA kommt, damit wir nicht ein overnight-SOTA überholen.
7. **Optimas (2507.03041, 2025)** — DSPy-extension für heterogeneous compound-AI configs + local-rewards. Matrix hat multi-modul-setup (harness/skills/a2fm) → Optimas-pattern könnte direkt passen.
8. **Dataset-level Feature Discovery (2601.13922, arxiv 2026-01)** — orthogonaler optimization-approach (dataset-level statt per-sample feedback). Könnte mit MIPRO/GEPA kombiniert werden, relevant für wie matrix per-user-fitness-daten nutzt.

### 🟢 P3 — context / reference (skimmbar, nicht blocker)

9. **OPRO (2309.03409, Google DeepMind ICLR 2024)** — zeigt dass DSPy-style ideen im big-lab-research-stream auch laufen. Gut für "ist das auf dauer relevant?"-argument.
10. **Compiled AI (2604.05150, arxiv 2026-04)** — neues paradigm referenziert DSPy als antecedent. Gut für "wohin entwickelt sich das feld?"-orientation.
11. **REVERE (2603.20667, arxiv 2026-03)** — anwendungs-beispiel (scientific workflows). Domain-transfer-evidenz für DSPy-style reflective evolution.
12. **Prompt-Opt-Survey (2502.16923, 2025)** — breitere literatur-situation, 31 pages. Index zum nachschlagen, nicht linear-lesen.
13. **LLMs-as-Planning-Formalizers-Survey (ACL 2025 findings)** — cross-reference zu PDDL-track, nur relevant wenn DSPy+PDDL integration (exec-14-DSPy Layer 2) angegangen wird.
14. **Generalized-Planning-LLMs (2508.13876, 2025)** — dito, PDDL-cross-reference, optional.

**Wenn knapp an zeit:**
- **Minimal** (contrarian-ready): P1 = 3 papers (~71 pages: DSPy + GEPA + LLMSelector). Reicht für D-1..D-5 mit realistischer option-bewertung (nicht nur DSPy-cheerleading).
- **Standard** (contrarian + D-6 decision): P1 + P2 = 8 papers (~241 pages). Für echte framework-choice.
- **Complete** (research-grade eval): P1+P2+P3 = 14 papers (~341 pages).

Cross-ref: `exec-14-pddl-formal-planning.md` hat parallele "Lokale Paper-Kopien"-tabelle für PDDL-forschung (11 papers). Gleiche `docs/papers/` struktur.

**Framework-links (online):**
- DSPy: [dspy.ai](https://dspy.ai/) · [GitHub stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) (160k monthly downloads, 16k stars, 250+ contributors, April 2026)
- GEPA standalone: [github.com/gepa-ai/gepa](https://github.com/gepa-ai/gepa)
- OPRO code: [github.com/google-deepmind/opro](https://github.com/google-deepmind/opro)
- TextGrad: Stanford-Zou-lab repository (linked in paper)

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
| **Google DeepMind** | Nein direkt — aber **OPRO (arxiv 2309.03409)** ist konzeptioneller vorgänger | Gemini ist DSPy-target. DeepMind hat OPRO als eigenes paper + [google-deepmind/opro](https://github.com/google-deepmind/opro) code. OPRO zeigt: **DSPy-ähnliche ideen sind auch im big-lab-research-stream**, nur nicht unter DSPy-framework-brand. Siehe `docs/papers/DSPy-2309.03409.pdf`. |
| **OpenAI** | Nein | GPT-5 "router" ist konzeptionell ähnlich zu DSPy's compile. OpenAI-API ist DSPy-target. |
| **Databricks** | Ja, integration via Lakehouse | Enterprise-production-user + anthropic-partner |
| **Stanford HAI** | Development-origin | Forschungsheim. Siehe auch **TextGrad** (arxiv 2406.07496, Zou-lab Stanford) — paralleles framework zu DSPy. Gibt dem team optionen: DSPy lock-in vermeidbar wenn TextGrad besser passt. |
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

### D-6. Framework-choice: DSPy vs TextGrad vs own-OPRO-style?

Wir haben heute **drei realistische optionen** für matrix's optimization-layer:

| Option | Framework | Pro | Contra |
|---|---|---|---|
| **a)** | DSPy + GEPA | SOTA optimizer (ICLR 2026 Oral), grösste community (160k downloads), klare programming-abstractions (Signature/Module) | Framework-commitment; matrix's eigene `agent/skills/pareto.py` müsste refactored |
| **b)** | TextGrad | Stanford/Zou-lab, "PyTorch-autograd für text", gleiche Stanford-ökosystem wie DSPy, kein prompt-struktur-commitment nötig | Kleinere community als DSPy; compound-AI-fokus unterschiedlich |
| **c)** | OPRO-style own impl | Kein external dependency, matrix's custom-domain-keywords voll unter kontrolle, direkt adaptiert auf matrix's scorer/fitness | Wir re-building what's in DSPy/TextGrad; maintenance-burden; missen 2026+ research-progress |

**Empfehlung bis contrarian-review:** Option (a) DSPy+GEPA als **baseline-evaluation**, Option (b) TextGrad als **comparison-baseline** in Phase 1. Option (c) nur wenn beides measurable schlecht abschneidet gegenüber unser eigenem `agent/skills/pareto.py` — sehr unwahrscheinlich.

---

## 6. Phase plan (skizze, nicht commitment) — **2026-paper-fokussiert**

**Voraussetzung: Welle 1 (verify-gates) + Welle 2 (Phase-C tail) abgeschlossen bevor DSPy scope-bindet.**

**Grundregel:** implementierungs-entscheidungen basieren auf **2026-current-state-research**. 2023–2024 foundation-papers sind *context* (um zu verstehen woher die konzepte kommen), nicht *implementation-guide*. Wer DSPy 2310.03714 als to-do-liste liest baut das framework von 2023; wir wollen was 2026 current ist.

### Phase 0 — Research + contrarian (1–1.5 tage)

**Fokus: aktuelle SOTA, nicht historie.**

Reading-plan in dieser reihenfolge:

1. **GEPA (2507.19457, ICLR 2026 Oral, v2 Feb 2026)** — current SOTA optimizer. Das ist der technische baseline gegen den alles verglichen wird.
2. **LLMSelector (2502.14815)** — zeigt compound-AI-systems profitieren von model-selection-optimization (+5-70% über DSPy+MIPROv2). Kritisch: könnte matrix-setup besser passen als DSPy's module-internal prompt-optimization.
3. **p1 (2604.08801, arxiv 2026-04)** — post-GEPA, "better with fewer prompts". Wir sollten wissen ob GEPA bereits überholt ist **bevor** wir drauf committen.
4. **Dataset-level features (2601.13922, arxiv 2026-01)** — orthogonal approach. Möglicherweise kombinierbar mit GEPA für matrix's per-user-fitness-daten.
5. **Optimas (2507.03041)** — DSPy-extension für heterogeneous compound-systems. Passt matrix's multi-modul-setup.

DSPy-original (2310.03714) + MIPROv2 (2406.11695) + OPRO (2309.03409) nur **als referenz** bei spezifischen technischen fragen — nicht linear-lesen.

**Deliverable:** sota-contrarian stakes=high input-dokument + Go/No-go decision gegen D-1..D-6 (plus neues D-7: "GEPA vs LLMSelector vs p1 als primary optimization-algorithm?").

### Phase 1 — 2026-SOTA comparison benchmark (1–2 wochen, post-contrarian)

**Fokus: welcher optimizer gewinnt auf matrix-daten, nicht welches framework-brand.**

- Benchmark-setup: einen matrix-flow als target (kandidaten: plan-skill, smart-routing classifier, one scorer-weight configuration)
- **Drei kandidaten** parallel testen auf matrix's historical chat-daten:
  - **GEPA** (via DSPy, als current-SOTA baseline)
  - **p1** (2604.08801, falls open-source ist — check repo first)
  - **LLMSelector-approach** (model-selection statt prompt-optimization — eigene impl ~200 LOC, nicht via DSPy)
- Matrix-eigene pareto (`agent/skills/pareto.py`) als vierte vergleichs-linie.
- Metric: composite fitness (siehe exec-harness §4g), cost per compile-run, rollout-count.

**Ausgang entscheidet D-1 + D-7 empirisch.** Nicht "wir committen auf DSPy weil stanford paper" — sondern "wir committen auf X weil X auf matrix-daten beste fitness-regression liefert."

### Phase 2 — Schema + deployment (nach winner)

Nur wenn Phase 1 einen klaren winner hat:

- Migration `agent.compiled_programs` (jsonb version control) — schema unabhängig vom winner
- `agent/harness/<winner>_compile_worker.py` — Scheduler-integrated background-compile (wie exec-scheduler §8.1 harness-backfill-worker)
- Per-user compile-budget enforcement via `agent.user_llm_settings`

### Phase 3 — A/B integration via Phase-C dispatcher

- Dispatcher variant `"<winner>_compiled"` für selected programs
- `harness_fitness_score` comparison vs langgraph/simple variants
- N ≥ 100 per variant → Welch t-test

### Phase 4 — Scale-out

- Replace matrix-code das der winner measurably schlägt
- Matrix-eigenes (z.B. `agent/skills/pareto.py`) wo es gewinnt **bleibt**

---

## 7. Verify gates

### Phase-0 gates (research, 2026-paper-fokussiert)

- [ ] **P1 papers gelesen** (DSPy + GEPA + LLMSelector = ~71 pages) — minimum für contrarian
- [ ] **Top 2026-arxiv papers skimmed** (p1 2604.08801 + Dataset-level 2601.13922 + Optimas 2507.03041 + Compiled-AI 2604.05150) — decision-tier
- [ ] sota-contrarian stakes=high run gegen D-1..D-7 (neu: D-7 = GEPA vs LLMSelector vs p1 primary-optimizer choice)
- [ ] Go/No-go + empfohlener winner-kandidat (oder "keine empfehlung, Phase 1 entscheidet empirisch") in doc festgehalten
- [ ] 2023–2024 foundation-papers explizit als *background-only* markiert

### Phase-1 gates (2026-SOTA benchmark)

- [ ] Benchmark-harness: historical chat-data + composite-fitness metric wired zu allen 4 kandidaten
- [ ] GEPA-run succeeds auf fixture (via DSPy oder standalone gepa-ai package)
- [ ] p1-run succeeds ODER dokumentiert warum nicht (code-availability, preprocessing-mismatch)
- [ ] LLMSelector-approach als ~200 LOC eigene impl läuft
- [ ] matrix-`agent/skills/pareto.py` baseline-run
- [ ] Comparison-notebook `docs/notebooks/dspy-2026-bench.ipynb` mit fitness/cost/rollouts tabelle
- [ ] **Winner (oder "keiner konklusiv")** dokumentiert in exec-14-DSPy §9 changelog

### Phase-2 gates (schema)

- [ ] Migration `agent.compiled_programs` + rollback tested
- [ ] `<winner>_compile_worker.py` als River-handler (exec-scheduler §8.x pattern)
- [ ] Budget-enforcement via `agent.user_llm_settings` (jsonb key `<winner>_compile`)

### Phase-3 gates (A/B)

- [ ] Dispatcher variant `"<winner>_compiled"` — smoke-test
- [ ] `ab_experiments` rows mit `harness_fitness_score` + variant
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
| 2026-04-20 | **Paper-kopien erweitert + konsolidierte tabelle** (analog zu exec-14-pddl-formal-planning.md). 3 zusatz-papers: **OPRO arxiv 2309.03409** (Google DeepMind, ICLR 2024, DSPy's konzeptioneller vorgänger), **TextGrad arxiv 2406.07496** (Stanford/Zou-lab, paralleles framework), **Prompt-Opt-Survey arxiv 2502.16923** (broader literature-situation). Total 8 papers für DSPy-track. **Neue decision D-6**: framework-choice DSPy+GEPA vs TextGrad vs own-OPRO-style (empfehlung Phase-1: a + b als comparison, c nur fallback). |
| 2026-04-20 | **2026-arxiv papers ergänzt.** `2603.20667` REVERE (reflective evolution für scientific workflows, 24 pages). Plus PDDL-side bekommt 5 × 2026-papers inkl. **2602.21670 TextGrad+PDDL-direct-composition** (validiert das in beiden specs skizzierte pattern), **2603.23844 "Language Model Planners do not Scale, but do Formalizers?"** (kritischer finding für spec-richtung), **2603.06064 PDDL via MCP-interface** (matrix hat bereits MCP!). Cross-ref in `exec-14-pddl-formal-planning.md §2026-arxiv-papers`. Total 9 papers im DSPy-track + 16 im PDDL-track = **25 papers in `docs/papers/`**. |
| 2026-04-20 | **5 weitere 2026-arxiv-ecosystem-papers DSPy-track** (user-frage: asymmetrie DSPy vs PDDL war real). Alle 2026/current-SOTA: **`2604.05150` Compiled AI** (Apr 2026, neues paradigm), **`2604.08801` p1** (Apr 2026, post-GEPA optimizer), **`2601.13922` Dataset-level feature discovery** (Jan 2026, orthogonal to MIPRO/GEPA). Plus 2 kritische 2025-context-papers: **`2502.14815` LLMSelector** (beats DSPy+MIPROv2 5-70% auf compound-AI-systems — promoted zu **P1 must-read** wegen D-1 entscheidungs-relevanz) und **`2507.03041` Optimas** (DSPy compound-AI extension). DSPy-track jetzt 14 papers total. |
| 2026-04-20 | **Phase-plan 2026-focused rewrite** (user-feedback). Fokus: implementierungs-entscheidungen basieren auf 2026-SOTA, 2023–2024 foundations nur als *background*. **Neues D-7**: GEPA vs LLMSelector vs p1 primary-optimizer choice — empirisch via Phase-1 benchmark auf matrix-daten, nicht brand-commitment. Phase-1 testet **4 kandidaten parallel** (GEPA + p1 + LLMSelector + matrix's eigener `agent/skills/pareto.py`) auf historical-chat-data → fitness-winner entscheidet. Verify-gates aktualisiert: P1 papers gelesen + 2026-arxiv-papers skimmed bevor contrarian. |
