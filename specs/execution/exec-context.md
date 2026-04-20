# exec-context — Context Assembly, Compaction & Prompt-Economics

> Status: Evaluation / operativer Owner fuer Runtime-Context
> Erstellt: 2026-04-15
> Abgrenzung: **Nicht** Memory-Storage (Schichten, Stores, Hindsight vs MemPalace) — das ist [`exec-memory.md`](./exec-memory.md) + `main_docs/root/MEMORY_ARCHITECTURE.md`. Hier: **was zur Laufzeit in welcher Reihenfolge in den Prompt geht**, Token-Budget, **Compaction-Orchestrierung**, **Provider-/Engine-Caching**, und Anbindung an `context/merge.py` / `agent/llm_client.py`.
> Root-Agent-Referenzen: `main_docs/root/AGENT_ARCHITECTURE.md`, `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md`, `main_docs/root/AGENT_SECURITY.md`, `main_docs/root/AGENT_HARNESS.md`

---

## 0. Warum ein eigenes Exec

`main_docs/root/CONTEXT_ENGINEERING.md` definiert Policies, Consumer und Merge — ist die **normative** „Bibliothekar“-Schicht, aber **älter** (Stand 22.02.2026) und nicht an alle Matrix-Agent-Runtime-Details gebunden.

| Thema | Owner |
|:------|:------|
| Verbatim Store, Hindsight Retain, Tiered Storage, MemPalace-Vergleich | **exec-memory** |
| Global World Evidence / Claims / KG / Adjudication | **exec-world-model** |
| Personal Knowledgebase / Capture / Curation / KB-Retrieval | **exec-personal-kb** |
| Skill Finder/Refiner, `agent_skills` DB, Promotion | **exec-skills** |
| Prompt-Block-Reihenfolge, Compaction-Schwellen, LiteLLM `cache_control`, KV-Cache (self-hosted), Metriken | **exec-context** (dieses Dokument) |

**Regel:** Änderungen an `context/merge.py` oder globalem Prompt-Layout **erst** hier und in `CONTEXT_ENGINEERING.md` spiegeln (SSOT bleibt `main_docs`; dieses Exec ist **Umsetzungs- und Gate-Dokument**).

**Oberflächen (Backend-Verträge zuerst):** [`exec-15-memory-control-ui.md`](./exec-15-memory-control-ui.md) (Control UI); Agent-Chat — [`exec-06-agent-chat-integration.md`](./exec-06-agent-chat-integration.md), [`exec-merge-chat.md`](./exec-merge-chat.md). Gleiche APIs für Model, Kontext, ggf. Memory/Skill-Toggles — keine zweite Wahrheit neben diesem Exec.

---

## 1. Hauptprojekt-Docs (Pflichtlektüre)

| Dokument | Rolle |
|:---------|:------|
| `main_docs/root/CONTEXT_ENGINEERING.md` | Retrieval-Policies, Relevance, Token-Budget, Multi-Source-Merge, Consumer-Matrix |
| `main_docs/root/MEMORY_ARCHITECTURE.md` | M1–M5, Working Memory, epistemische Trennung |
| `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md` | verbindliche Policy-Tiers und Memory-/Retrieval-Grenzen |
| `main_docs/root/AGENT_SECURITY.md` | Retrieval Broker, Capability Envelope, Source-/Policy-Gates |
| `main_docs/root/AGENT_HARNESS.md` | Constrain/Inform/Verify/Correct, Runtime-Governance |
| `main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` | Dual Pipeline, UQ-Gates — wenn RAG-Teile in den Kontext gemerged werden |
| `main_docs/specs/EXECUTION_PLAN.md` | ggf. `agent_memory_context_delta` / verwandte Deltas |

**Querverweise (Eval-Slices):**

- [`exec-memory.md`](./exec-memory.md) — Pre-Compaction **Verbatim Retain** (Speicher-Seite), Eval Hybrid, MemPalace-Hooks
- [`exec-world-model.md`](./exec-world-model.md) — globale Wissensseite: Evidence, Claims, KG, Konflikte
- [`exec-personal-kb.md`](./exec-personal-kb.md) — user-kuratierte Knowledgebase als eigene Retrieval-Schicht
- [`exec-skills.md`](./exec-skills.md) — Skills im **statischen Prefix** (Top-K, Refinement)
- [`exec-16-llm-provider-gateway.md`](./exec-16-llm-provider-gateway.md) — LiteLLM-Gateway, Multi-Provider, OpenRouter-Wildcards

### 1.1 Runtime-Stack (Ist)

| Schicht | Rolle |
|:--------|:------|
| **LiteLLM** | Einheitliche OpenAI-kompatible API im Agent — **ein** Integrationspfad in `agent/llm_client.py` (kein paralleles Anthropic-SDK nur für Caching). |
| **OpenRouter** (aktuell) | Primärer Modellzugang über `openrouter/...`-Strings; OpenRouter routet zum **jeweiligen Upstream** (Anthropic, OpenAI, Google, …). Caching-Verhalten hängt vom **Upstream-Modell** ab, nicht von der Marke „OpenRouter“. |
| **Self-hosted** (optional) | vLLM / SGLang / LMCache — nur wenn Inference lokal/ohne kommerzielle API; orthogonal zu §1.1. |

### 1.2 Provider-agnostisches Token Caching (Umsetzungsregeln)

1. **Code:** Cache-relevante Parameter über **LiteLLM** setzen (inkl. Übersetzung/`extra_body` je Ziel); `drop_params`/Feature-Detection nutzen, statt fest „nur Anthropic“ zu codieren.
2. **Pro Modell prüfen:** `cached_tokens` (o.ä.) in der Usage-Response — typische `openrouter/<upstream>/...`-Kombinationen einzeln testen; kein globaler „ein Wert für alle Modelle“-Anspruch.
3. **Prompt-Layout (§5):** immer — stabiler Prefix hilft allen prefix-basierten Caches und schadet nicht, wenn ein Modell keinen API-Cache exponiert.
4. **Router/Deployments:** LiteLLM-**Sticky Routing** beachten, sonst Cache-Miss trotz stabilem Prefix (siehe LiteLLM-Doku Prompt Caching / Deployment-Checks).

---

## 2. Papers & externe Referenzen (kanonisch per ArXiv / DOI)

| ID | Titel / Thema | Nutzen fuer exec-context |
|:---|:--------------|:---------------------------|
| **2603.07670** | Memory for Autonomous LLM Agents — Taxonomie, **4.1** Summarization Drift, **4.1** quadratic cost | Begründung für Compaction + Kosten; Drift-Risiko bei Rolling Summary |
| **2604.04323** | Skills in the Wild | Skills nur sinnvoll mit stabilem Prefix + Retrieval — Verbindung zu Prompt-Order |
| **2601.06007** | Don’t Break the Cache: Prompt Caching for Long-Horizon Agentic Tasks | Evaluierung: Cache-Breaking bei Agent-Loops; Design-Hinweise für Breakpoints |
| **2601.07190** | Active Context Compression (Focus) — agentische Kontext-Kompression | Referenz für aktive, phasenbasierte Kompression (nicht nur Sliding Window) |

**Provider-Dokumentation (laufend aktualisieren, nicht spiegeln):**

- Anthropic Prompt Caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching — `cache_control`, Breakpoints, TTL
- LiteLLM Prompt Caching: https://docs.litellm.ai/docs/completion/prompt-caching — `cached_tokens`, Auto-Injection, Router-Sticky-Deployments
- OpenRouter: https://openrouter.ai/docs — Routing/Model-Strings; Caching folgt dem **Upstream**, den OpenRouter ansteuert

---

## 3. SOTA-Snapshot (Stand 15.04.2026) — Kurz

**Prompt / Prefix Caching (API-Ebene):**

Über **LiteLLM** abstrahiert; konkretes Verhalten **pro Upstream** prüfen (bei uns oft indirekt via **OpenRouter**):

- **Anthropic (direkt oder über OpenRouter):** typ. explizites Opt-in (`cache_control` / ephemeral); stabiler **Prefix** entscheidend (siehe Anthropic-Doku).
- **OpenAI-kompatibel:** oft automatisches Prefix-Caching ab Schwellen — Usage-Felder beobachten.
- **Weitere Upstreams (Gemini, …):** eigene Caching-Mechanismen — nicht ohne Test auf „einheitliches“ Verhalten schließen.
- **LiteLLM:** vereinheitlicht Metriken (`prompt_tokens_details.cached_tokens` o.ä.) — **Router:** bei Load-Balancing **sticky routing** zum gleichen Deployment, sonst Cache-Miss.

**Compaction / Kontext-Management (Agent-Runtime, nicht nur „mehr Tokens“):**

- Dominantes Muster: **Sliding Window + Rolling Summary** für ältere Turns; jüngste N Turns verbatim.
- **Verlustbewusstsein:** Zusammenfassung entfernt Zahlen/Details → **externer** Verbatim-/Episodic-Store nötig (siehe exec-memory §3e–3f Verknüpfung).
- **Aktive Kompression:** Tool-/Phasen-gestütztes Verdichten (Forschungsrichtung, z. B. Focus / Active Compression — siehe Paper-Tabelle).

**Self-hosted Inference (KV-Cache):**

- **vLLM:** Automatic Prefix Caching (APC) mit PagedAttention — Standard für lange stabile Prefixe.
- **SGLang:** RadixAttention — stark bei chat-/RAG-lastigen Prefixen.
- **LMCache:** optionaler Layer für geteilten KV-Cache über Instanzen — erst relevant bei eigenem Inference-Cluster.

---

## 4. Architektur: Drei Schichten (orthogonal)

```
[4a] Provider Prompt Cache (API)     — Kosten/Latenz, Prefix unverändert
[4b] Inference KV-Cache (lokal)      — vLLM / SGLang / LMCache
[4c] Client Prompt-Layout            — Reihenfolge der Blöcke in merge.py (maximiert 4a/4b)
```

**Compaction** ändert den **Inhalt** der Konversation im Fenster; **Caching** nicht — deshalb zuerst Verbatim/Retain (Memory), dann Compaction (Context), siehe §6.

---

## 5. Ziel-Prompt-Reihenfolge (statisch → dynamisch)

Reihenfolge für **maximale Cache-Treffer** und klare Semantik (Align mit exec-memory / exec-skills):

1. System / Policy (selten geändert)
2. Agent-Rolle, harte Guards
3. **Tool-Definitionen** (stabil halten; keine dynamischen IDs im Prefix)
4. **Top-K Skills** (nach finder + optional refiner) — procedural layer
5. **L0 Identity / L1 Essential** (wenn verwendet; langsam ändernd)
6. Dynamisch: **L2 Memory-on-demand**, frische Retrieval-Blöcke, aktuelle History, User-Turn

**Explizit vermeiden im langen Prefix:** Timestamps, Session-IDs, zufällige UUIDs in den ersten Blöcken — **Cache-Breaking** (vgl. „Don’t Break the Cache“, Web-Best-Practices zu deterministischer Serialisierung).

**Code-Anker:** `context/merge.py`, `agent/llm_client.py`.

---

## 6. Compaction-Orchestrierung

### 6.1 Schwellen (modellrelativ)

| Stufe | Bedingung (Anteil am **aktuellen** Kontextfenster) | Aktion |
|:------|:--------------------------------------------------|:-------|
| Pre-Save | ≥ **80%** | Verbatim Retain / Session-Persist **fertig** vor nächstem Schritt (siehe exec-memory) |
| Compaction | ≥ **85%** | Rolling Summary älterer Turns; letzte N Turns verbatim |
| Emergency | ≥ **95%** | Aggressiv: minimal System + kurze History + kritische Blöcke |

Fenster und Token-Zählung: Modell-Registry oder LiteLLM-Metadata; Zähler pro Turn (`tiktoken` oder provider-spezifisch).

**Kritisch:** Pre-Save **blockiert** Compaction nicht endlos, aber Compaction darf nicht starten, bevor das für euch definierte Verbatim-Minimum geschrieben ist (Race Condition vermeiden).

### 6.2 Beziehung zu exec-memory

- **exec-memory** beschreibt **warum** Verbatim + Hindsight parallel (Informationserhalt).
- **exec-context** definiert **wann** im Turn die Triggers feuern und wie sie ans Merge-Layer gebunden sind.

---

## 7. Implementierungs-Checkliste

Explizite Arbeitspunkte (Inhalt früher in `exec-memory` §3f — **nicht entfernt**, hier zentralisiert, damit eine Quelle für Context/Prompt/Caching bleibt).

**Compaction & Fenster**

- [ ] **Compaction-Trigger:** Modell-Kontextfenster auslesen (LiteLLM `get_model_info` / eigene Registry / ModelInfo), **Token-Count pro Turn** tracken, **≥80 % Pre-Save** (Verbatim/Audit) vor Rolling Summary / Compaction (§6)
- [ ] Schwellen **85 % / 95 %** wie in §6 verdrahten; Race: Pre-Save fertig vor Compaction-Start

**Provider-agnostisch über LiteLLM (aktuell v. a. OpenRouter-Upstreams)**

- [ ] **`agent/llm_client.py`:** LiteLLM-konforme Cache-Parameter — **nicht** provider-spezifisch parallel verdrahten; Übersetzung über LiteLLM; typische `openrouter/...`-Modelle einzeln verifizieren (`cached_tokens` in Usage)
- [ ] **`context/merge.py`:** Prompt-Reihenfolge **statisch vorne, dynamisch hinten** (§5) für Cache-Treffer wo der Upstream Prefix-Caching unterstützt

**Observability**

- [~] Usage auslesen: `cached_tokens` / Äquivalent; `llm_node` hebt `prompt_tokens_details.cached_tokens` jetzt in Runtime-/Session-Metadaten, Logging für Compaction-Triggers + geschätzte Kontextauslastung bleibt offen

**Frontend-Vertrag (nicht nur Backend)**

- [~] `python-backend/agent/streaming.py`: `MessageMetaPacket` bleibt generisch, traegt jetzt aber via `runner.py` echte Context-Diagnostik (`sourceLayerCounts`, `degradationFlags`, `provider`, `contextBlocks`)
- [x] `python-backend/agent/graph/runner.py`: Runtime-Merge-/Context-Signale gehen jetzt als echte SSE-Metadaten raus statt `threadId` + Token-Platzhalter
- [x] `control-ui/src/app/api/control/[...path]/route.ts`: generischer BFF reicht jetzt auch `/control/context` an den Go-/Python-Pfad weiter
- [x] `python-backend/agent/control/context.py` + `agent/control/context_runtime.py`: kanonischer Runtime-/Prompt-Inspector-Vertrag fuer `control-ui` existiert jetzt als eigener `/api/v1/control/context`-Pfad
- [x] `control-ui/src/features/control/components/ContextTab.tsx`: eigener `Context`-Tab surfacet Layer-/Provenance-/Degradation-Signale und trennt diese Sicht bewusst von `/memory`
- [x] `agent-chat/src/hooks/useChatSession.ts`: liest jetzt neben `promptTokens`/`completionTokens` auch Context-/Layer-Metadaten aus `message.metadata`
- [x] `agent-chat/src/components/AgentChatEventRail.tsx`: surfacet jetzt neben `contextPressure` auch sichtbare Layer-/Degradation-Signale
- [~] `agent-chat/src/components/AgentChatSources.tsx` und/oder `agent-chat/src/components/AgentChatMessage.tsx`: Message-Badge zeigt jetzt `cachedTokens`, eigentliche Memory-/World-/KB-Provenance im Message-Body bleibt offen
- [~] `agent-chat/src/app/api/agent/chat/route.ts` + `go-appservice/internal/handlers/http/agent_chat_handler.go`: bestehender Pass-through bleibt intakt und neue Metadata-Frames gehen unveraendert durch; expliziter Verify-Lauf steht noch aus

**Consumer- und Layer-Policies (aus `memory_kg.md`)**

- [ ] Consumer-spezifische Retrieval-Policies explizit machen: mindestens `LLM-Agent`, `Frontend-UI`, `Signal-/Scoring-Pipeline`, `Merge-Layer`
- [ ] Default-Reihenfolge fuer LLM-nahe Runtime-Queries festziehen: `working/hot cache -> global world KG -> personal derived memory -> personal raw evidence -> personal knowledgebase -> globale evidence/vector hits`
- [ ] `Personal Knowledgebase` als eigene Runtime-Schicht verdrahten, nicht still in `personal memory` aufgehen lassen
- [ ] Weltwissen nur evidence-joined surfacen: `claim + provenance + status`, nicht nackte KG-Behauptung
- [~] Merge-Regeln festziehen: `derived` nie ohne Backlink/Beleg, `global world KG` nie ohne Status/Freshness, `personal KB` nie still als Weltwahrheit — `memory_fusion` enforced den `derived`-Teil bereits, World/KB-Merge-Regeln im Context-Pfad noch offen

**Degradation / Policy Flags**

- [ ] Sichtbare Flags fuer fehlende Schichten definieren und im Merge-Pfad mitfuehren: z. B. `NO_WORLD_KG`, `NO_WORLD_EVIDENCE`, `NO_PERSONAL_MEMORY`, `NO_PERSONAL_KB`, `WORLD_CLAIM_CONFLICT`
- [ ] Keine stillen Fallbacks: wenn `world`/`KB`/`memory` fehlt, muss der Prompt-/Response-Metadatenpfad das markieren
- [~] Response-/Context-Metadaten pro Block vorsehen: `source_layer`, `source_type`, `provenance_ref`, `status`, `freshness` — `memory_fusion` liefert bereits `memory_layer`/`source_type`/`provenance_ref`/`grounding_status`; `control-ui` surfacet jetzt Block-Metadaten, `freshness`/vollstaendige Policy-Signale bleiben noch offen

**Mittelfrist**

- [ ] LiteLLM-Router: Sticky-Routing oder dokumentierte Einschränkung bei Multi-Deployment
- [ ] Feature-Flags: `AGENT_CONTEXT_COMPACTION`, `AGENT_PROMPT_CACHE` getrennt
- [ ] Regression: Prompt-Layout-Änderungen → Cache-Hit-Rate / Kosten pro Turn

**Self-hosted (optional — nur ohne Cloud-Upstream)**

- [ ] vLLM APC evaluieren
- [ ] **SGLang** RadixAttention oder **LMCache** evaluieren (Mehrwert vs. Komplexität)

---

## 8. Observability & Verify Gates

- Metriken: `cache_hit_rate`, Tokens pre/post Compaction, Latenz p95 pro Provider, **Kosten pro Turn** (Memory-Paper 5.5: Cost gehört ins Eval)
- Tests: „gleiche Session, gleicher Prefix“ → erwartete `cached_tokens` > 0 (wo Provider das hergibt)
- Gate: Kein Production-Compaction ohne definiertes Verbatim- oder Audit-Backstop (exec-memory)
- Gate: Kein Production-Merge auf Personal-Memory-Daten, bevor der Memory-seitige Postgres-E2E-Smoke fuer Guardrails dokumentiert gruen ist (`python-backend/experiments/memory_eval/run_memory_fusion_e2e_smoke.py`)
- Gate: Kein Production-Merge ohne sichtbare Layer-/Degradation-Flags wenn `world`, `personal KB` oder `memory` fehlen
- [ ] Verify E2E: live `control-ui`-Request auf `/control/context` und `/memory` laeuft ueber `control-ui/src/app/api/control/[...path]/route.ts` bzw. `control-ui/src/app/api/memory/[...path]/route.ts` -> `go-appservice/internal/handlers/http/control_proxy_handler.go` -> `python-backend/agent/control/context.py` / `python-backend/agent/control/memory.py` und liefert **nicht nur Mock-Fallback**, sondern echte `activeSession`, `sourceLayerCounts`, `contextBlocks`, `degradationFlags`, `worldClaims`
  - Blockiert bis lokale `.env`/Gateway-/Frontend-Voraussetzungen vorhanden sind: mindestens `control-ui`-Dev-Server, Go Appservice, Python Agent-Service und deren Base-URLs/Auth-Header muessen wirklich laufen
  - Verify muss explizit pruefen, dass React Query nicht auf `mockContextInspector` / `mockMemoryOverview` faellt, sondern echte HTTP-Responses aus dem Runtime-Pfad rendert
- Gate: `global world KG`-Treffer werden im Runtime-Output nicht ohne `status` / `provenance` verwendet
- Gate: `personal knowledgebase` wird als eigene Schicht getestet und nicht nur ueber `memory`-Queries zufaellig mitgezogen
- Gate: `control_ui` surfacet Context nicht nur als grobe Health-/Ops-Daten, sondern als eigener Inspector-Tab mit Layer-/Provenance-/Degradation-Signalen (`control-ui/src/features/control/components/ContextTab.tsx`, `control-ui/src/app/api/control/[...path]/route.ts`, `python-backend/agent/control/context.py`)
- Gate: Agent-Chat surfacet Context nicht nur als Web-`Sources`, sondern kann Layer-/Provenance-/Degradation-Signale aus `message.metadata` oder gleichwertigem Vertrag sichtbar machen (`agent-chat/src/hooks/useChatSession.ts`, `agent-chat/src/components/AgentChatEventRail.tsx`, `agent-chat/src/components/AgentChatSources.tsx`, `agent-chat/src/components/AgentChatMessage.tsx`)

---

## 9. Offene Punkte

1. `CONTEXT_ENGINEERING.md` **Stand** anheben und §5/6 mit dieser Reihenfolge und Caching **synchronisieren** (Single Source of Truth in `main_docs`)
2. Claude Code / OAuth-Pfade: bekannte `cache_control`-Einschränkungen im Deployment dokumentieren (siehe Community-Issues zu OAuth + caching)
3. Abgleich mit `exec-16-llm-provider-gateway.md` sobald Gateway-Spec aktiv ist

---

## 10. Changelog

| Datum | Änderung |
|:------|:---------|
| 2026-04-15 | Erstversion; ausgelagert aus exec-memory §3f (Compaction + Token Caching) mit SOTA-Referenzen |
| 2026-04-15 | §1.1/1.2 LiteLLM + OpenRouter; provider-agnostisches Caching; §7 Checkliste explizit (gleiche Punkte wie früher exec-memory, zentral hier) |
| 2026-04-20 | exec-hermes Phase-B P2 stubs added: §11 pre_compression-event contract (P5), §12 cost-metrics hooks (P4), §13 LiteLLM model_info-based thresholds TODO. |

---

## 11. `pre_compression` event contract (Phase-B P5 stub)

**Status:** STUB — filled in exec-hermes Phase-B P5.
**Cross-ref:** `exec-hermes.md §0` (context_compressor row), plan `~/.claude/plans/ja-mach-explore-daf-r-glimmering-gizmo.md §P5`.

When `ContextEngine.stage_for(tokens, window) == ContextStage.emergency`, `middleware/compression.py` (P5 new) MUST emit a `pre_compression` hook BEFORE running LLM-summary reduction. Two consumer-tiers:

- **Data-preserving** (MemPalace verbatim-retain) — synchronously awaited with 500ms timeout (`memory_manager.on_pre_compress(messages, timeout=0.5)`). If MemoryManager is None OR timeout exceeded → emit `archive.miss` metric and continue compression. Never silently lose context-content.
- **Observational** (metrics, audit-log, exec-17) — span-event `pre_compression` (fire-and-forget), attributes `messages_count` + `tokens_estimate` + `stage`.

Full contract + consumer-ordering guarantee filled during P5 implementation. Implementation-ref: `exec-memory.md §3h` (MemoryProvider.on_pre_compress ABC addition).

## 12. Cost-metrics hooks (Phase-B P4 stub)

**Status:** STUB — filled in exec-hermes Phase-B P4.
**Cross-ref:** `exec-hermes.md §0` (usage_pricing + insights rows), `exec-16.md §2.10`.

After P4 lands:
- `llm_node.py` emits span-attribute `llm.cost_usd` + `llm.cost_status` + `llm.prompt_cache_tokens` per call
- `InsightsEngine.generate(user_id, days)` aggregates CanonicalUsage across spans for billing-API
- `agent/harness/scorer.py` uses same InsightsEngine for meta-harness cost-per-task fitness signal
- Cache-savings (prompt-cache-hit tokens × cost-delta) tracked as `ratelimit.cache.saved_usd` span-attribute

Full schema + API-shape filled in `exec-16.md §2.10` when P4 implements.

## 13. LiteLLM model_info-based thresholds TODO (Phase-B P4/P5)

Current `ContextEngineConfig.default_window: int = 200_000` is a hardcoded fallback. P4 introduces `agent/llm/model_metadata.py::get_model_context_window(model)` wrapper over `litellm.get_model_info()`. P5 then adds `DefaultContextEngine.stage_for_model(*, tokens, model) -> ContextStage` (additive, ABC signature stays stable per Contrarian-2 CRITICAL-1 fix) that resolves window via the wrapper. Hardcoded `default_window` remains as absolute-fallback for LiteLLM-unknown models.

Runner.py temporary `_fallback_model_max_tokens(model)` helper (introduced P1) gets replaced by `get_model_context_window()` in P4.
