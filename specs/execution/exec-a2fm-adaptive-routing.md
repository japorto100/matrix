# exec-a2fm: Adaptive Model & Reasoning Routing

**Datum:** 13.04.2026
**Status:** Draft / Research — **Stufe 0 heuristic landed 2026-04-20; Holistic review + ADR-001 + 4 backend-gates + Phase-1 router_node refactor landed 2026-04-23. Rollout blocked behind frontend gates (G5 indicator, G6 Control-UI panel).**
**Abhaengig von:** exec-19 (Stufe 5b/5c fertig), exec-16 (LiteLLM Integration)

> **Implementation-stub (2026-04-20, reviewed 2026-04-23):** A conservative keyword-heuristic cheap-vs-strong router landed as an MVP: `python-backend/agent/llm/smart_routing.py` + migration 026 (`user_llm_settings.smart_routing` JSONB column). **This is NOT yet the A2FM-paper ML-router** — it's a hermes port with multi-domain keyword expansion. Feature is off by default (`{}` = disabled). Holistic review via `sota-contrarian stakes=high` completed 2026-04-23; rollout is blocked behind the 6-gate checklist in [ADR-001](../../docs/superpowers/findings/2026-04-23-adr-smart-routing-rollout-gate.md) (DE keyword set, credential pre-flight, config cache, A/B routing dimension, user-visible indicator, Control-UI panel). Current wire-point in `llm_node.py` is treated as **Phase-0.5 / provisional**; a proper `router_node.py` (Phase-1 target below) is the inversion recommended by the ADR after G1-G4 land. A2FM-paper ML-router remains Phase-2/3.

**Referenzen:**
- Paper: [A2FM: An Adaptive Agent Foundation Model for Tool-Aware Hybrid Reasoning](https://arxiv.org/abs/2510.12838) (arXiv 2510.12838v3, Oct 2025)
- Local: `docs/papers/A2FM-2510.12838v3.pdf`
- [OpenAI GPT-5 Router](https://openai.com/index/introducing-gpt-5/) — ML-based routing between fast/thinking models
- [OpenAI Reasoning Best Practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices)
- [Cursor Auto-Select](https://docs.cursor.com/guides/selecting-models) — task-complexity routing
- [OpenRouter Auto](https://openrouter.ai/openrouter/auto) — prompt-based model selection
- [LiteLLM Routing Strategies](https://docs.litellm.ai/docs/proxy/configs#router-settings)

---

## Warum

Aktuell waehlt der User manuell Model + Reasoning Level. Das ist suboptimal:
- Einfache Fragen ("Was ist 2+2?") verbrauchen teure Reasoning-Tokens unnoetig
- Komplexe Fragen landen auf guenstigen Models die ueberfordert sind
- Tool-intensive Tasks (Web-Suche, DB-Queries) brauchen agentic Models, nicht Reasoning
- User wissen nicht welches Model fuer welchen Task am besten ist

## A2FM Paper — Kernidee

A2FM (Adaptive Agent Foundation Model) vereint **drei Modi** in einem Framework:

| Mode | Wann | Token-Kosten | Beispiel |
|---|---|---|---|
| **Instant** | Einfache, direkte Fragen | Minimal | "Was ist die Hauptstadt von Frankreich?" |
| **Reasoning** | Komplexe Logik, Mathe, Analyse | Hoch (CoT) | "Beweise dass sqrt(2) irrational ist" |
| **Agentic** | Tool-Nutzung, externe Daten | Mittel + Tool-Kosten | "Suche aktuellen BTC Preis und analysiere den Trend" |

### Route-then-Align Architektur

1. **Router**: Das LLM selbst lernt ein `<classification>` Token auszugeben (kein separater Classifier)
2. **Training Stage 1**: Supervised auf 11k Trajektorien mit mode-spezifischen Teachers
   - Reasoning: DeepSeek-R1
   - Agentic: DeepSeek-V3.1
   - Instant: direkte Antworten
3. **Training Stage 2**: Adaptive Policy Optimization (RL)
   - `r_total = r_accuracy * r_adaptive * r_format`
   - `r_adaptive` bestraft Reasoning/Agentic bei einfachen Queries: `1 - p^alpha`
   - 45% Kosteneinsparung vs pure Reasoning, 33% vs pure Agentic

### Ergebnisse (32B Scale)

| Benchmark | Score | Typ |
|---|---|---|
| BrowseComp | 13.4% | Agentic (Web-Browsing) |
| AIME25 | 70.4% | Reasoning (Mathe-Olympiade) |
| HLE | 16.7% | General |
| **Cost/correct** | **$0.00487** | 45% guenstiger als nur Reasoning |

## Industrielle Referenzen

### OpenAI GPT-5 Router
- ML-basiert, trainiert auf: User-Model-Switches, Preference-Rates, gemessener Korrektheit
- Binary: GPT-5 (schnell) vs GPT-5-thinking (deep)
- "Think hard about this" im Prompt → expliziter Override
- Prompt-Trigger + Complexity + Tool-Needs + Conversation-Type als Signale
- [Quelle](https://openai.com/index/introducing-gpt-5/)

### Cursor Auto-Select
- Task-Complexity Routing: einfache Fixes → GPT-4o-mini, komplexe Architektur → Claude
- Context-Requirements: grosse Codebases → Models mit grossem Context
- Verfuegbarkeit: bei Slow-Response automatischer Failover
- Performance-Learning: System lernt was fuer welche Tasks am besten funktioniert
- [Quelle](https://docs.cursor.com/guides/selecting-models)

### OpenRouter Auto (`openrouter/auto`)
- Prompt-basierte Analyse → bestes verfuegbares Model
- Wir koennen NICHT steuern welche Models es waehlt
- Fuer "auto aus meinen selected models" brauchen wir eigenen Router
- [Quelle](https://openrouter.ai/openrouter/auto)

### LiteLLM Routing
- `routing_strategy: "simple-shuffle"` (aktuell) — Round-Robin Failover
- Optionen: `least-busy`, `latency-based-routing`, `cost-based-routing`
- `cost-based-routing`: waehlt guenstigstes Model das den Task erledigen kann
- Kein Complexity-Routing (nur Cost/Latency)
- [Quelle](https://docs.litellm.ai/docs/proxy/configs#router-settings)

---

## Implementation Plan

### Phase 0: Kurzfristig (in exec-19 erledigt)

- [x] `openrouter/auto` als Model-Option im PROVIDER_REGISTRY
- [x] `reasoning_effort` dynamisch (nicht hardcoded, LiteLLM nativ)
- [x] ModelInfo mit `reasoning_type` + `reasoning_levels` aus LiteLLM
- [ ] Agent-Chat Default-Model: User's selected models > `openrouter/auto` > `claude-sonnet-4-6`

### Phase 1: Eigener Router (regelbasiert) — ✅ **LANDED 2026-04-23**

Als eigenständiger LangGraph-Node **vor** dem LLM-Call:

```
START → memory_recall → router → llm_call → [tools → increment → llm_call]* → memory_retain → END
```

- Impl: `python-backend/agent/graph/nodes/router_node.py`
- Runs the bilingual (EN+DE) smart_routing heuristic + G2 credential preflight
- Tool-continuation loop (`increment → llm_call`) bypasses router → "first turn only" by graph construction, no iteration==0 check needed in node
- Output: `routing_reason`, `routing_used`, `routing_picked_model` als state-fields, konsumiert von llm_node für span-attrs + model-selection
- Current heuristic: keyword-based (see `agent/llm/smart_routing.py`). Phase-2 (ML-classifier) ersetzt die Regeln, nicht die Node-Architektur.

**Signale fuer Routing:**
- Prompt-Laenge (kurz → instant, lang → reasoning)
- Tool-Keywords ("suche", "berechne", "analysiere" → agentic)
- Vorhandene Tools im Registry (0 Tools → kein agentic Mode)
- User's selected_models (nur aus diesen waehlen)
- Bisheriger Thread-Kontext (multi-turn → reasoning bevorzugen)

**Implementierung:**
- `python-backend/agent/graph/nodes/router_node.py` (neuer Node)
- Regelbasiert (if/else + keyword matching), kein ML
- Konfigurierbar per User (control-ui: "Auto-Routing aktivieren" Toggle)

### Phase 2: ML-basierter Router (A2FM-inspiriert)

- Kleiner Classifier (z.B. `sentence-transformers` Embedding → 3-class softmax)
- Trainiert auf unseren Audit-Logs: welche Queries brauchten Tools, welche nicht
- Cost-Regularization aus A2FM: bestrafe teures Reasoning bei einfachen Fragen
- Integration in LangGraph als erster Node

### Phase 3: Self-Improving Router

- A2FM's APO-Ansatz: Forced + Adaptive Rollouts
- User-Feedback (Thumbs up/down aus Agent-Chat) als Reward-Signal
- Periodic Retraining auf neuen Audit-Daten
- Trace-basierte Evaluation (exec-17 OTel → welcher Mode war erfolgreich)

---

## Betroffene Files (bekannt)

| Datei | Rolle |
|---|---|
| `python-backend/agent/graph/nodes/llm_node.py` | reasoning_effort → LiteLLM (bereits implementiert) |
| `python-backend/agent/graph/runner.py` | Graph-Ausfuehrung, StepStart Events |
| `python-backend/agent/graph/state.py` | `reasoning_effort` im State |
| `python-backend/agent/control/user_llm.py` | `default_mode`, ModelInfo mit reasoning_type, selected_models |
| `python-backend/agent/graph/nodes/router_node.py` | NEU: Routing-Node (Phase 1) |
| `python-backend/agent/security/credentials.py` | Virtual Key Resolution |
| `python-backend/litellm-gateway/config.yaml` | `openrouter/*` Wildcard, routing_strategy |
| `agent-chat/src/hooks/useChatSession.ts` | default_mode=auto, dynamic reasoning |
| `agent-chat/src/hooks/useAvailableModels.ts` | Routers + selected_models + free fallback |
| `agent-chat/src/hooks/useModelInfo.ts` | reasoning_type, reasoning_levels |
| `agent-chat/src/components/AgentChatToolbar.tsx` | Dynamic reasoning cycle, model picker |
| `control-ui/.../ModelExplorer.tsx` | reasoning_type Filter, ModelInfo Display |
| `control-ui/.../SpendDashboard.tsx` | Cost-per-Model Daten fuer Routing-Optimierung |

## Entscheidungen (getroffen in exec-19)

1. **default_mode = auto** (nicht default_model). User startet im Auto-Modus, kann manuell ueberschreiben.
2. **openrouter/free** als System-Fallback wenn User keine Models konfiguriert hat.
3. **openrouter/auto** mit `plugins` Parameter fuer "auto aus meinen selected_models" (paid).
4. **openrouter/free + /auto sind Routers**, nicht Models — getrennt behandelt in API + UI.
5. **Reasoning: LiteLLM nativ** — kein eigenes Provider-Mapping, alles dynamisch.

## Offene Fragen

1. **User-Control vs Auto**: Entschieden: Option A — Auto als Default, User kann Override.

2. **Selected Models Constraint**: `openrouter/auto` hat `plugins` Parameter fuer Model-Einschraenkung.
   Aber `openrouter/free` hat kein `plugins`. Eigener Router noetig fuer "free aus meinen selected_models".

3. **Cost vs Quality Trade-off**: A2FM's cost-regularized Approach. Fuer Phase 1 (regelbasiert): konservativ.

4. **Latenz**: Router-Entscheidung muss <100ms dauern. Phase 1 (Regeln) trivial. Phase 2 (Classifier) braucht ONNX/klein.

5. **Free Tier Limits**: 50 req/Tag (ohne $10), 1000 req/Tag (mit $10 einmalig). Model-Rotation durch `openrouter/free` hilft.

## Offene Forschung (TODO)

- [ ] WebSearch: Fertige Open-Source Model-Router (nicht trainieren, sondern benutzen)
  - [freerouter](https://github.com/openfreerouter/freerouter) — "14-dimension classifier, self-hosted"
  - NotDiamond (hinter openrouter/auto) — oeffentliches API?
  - RouteLLM, Martian, Unify.ai
- [ ] WebSearch: A2FM Code Release (arxiv 2510.12838 — kein oeffentlicher Code gefunden)
- [ ] WebSearch: Cursor auto-select Algorithmus Reverse Engineering
- [ ] WebSearch: OpenAI GPT-5 Router Details (ML-Training, Signale)
- [ ] Paper: "RouteLLM: Learning to Route LLMs with Preference Data" (UC Berkeley)
- [ ] Paper: "FrugalGPT" — LLM Cascade fuer Kosten-Optimierung
- [ ] Benchmark: eigene Audit-Logs analysieren — welche Queries brauchten Tools, welche nicht
- [ ] Test: `openrouter/auto` mit `plugins` Parameter — funktioniert Model-Einschraenkung?

5. **A2FM Code**: Paper hat keinen oeffentlichen Code-Release. Implementierung muss von Scratch basierend auf Paper-Beschreibung erfolgen.

---

## Relation zu anderen Execs

- **exec-16**: LiteLLM Integration — Basis-Infrastruktur (Routing, Virtual Keys, Spend)
- **exec-17**: OTel Tracing — liefert Audit-Daten fuer Router-Training (Phase 2/3)
- **exec-19**: DevStack — Stufe 5b/5c/5d liefern ModelInfo + Reasoning Pipeline
- **exec-merge-chat**: Agent-Chat UI — Auto-Toggle, Model-Picker mit "Auto" Option
