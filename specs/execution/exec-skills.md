# exec-skills — Skill Discovery, Refinement & Evolution

> Status: Evaluation / Phase 1 implementierbar
> Erstellt: 2026-04-13
> Abhaengigkeiten: exec-10 (Multi-Agent), exec-11 (Hindsight Memory), exec-17 (Harness/Pareto), exec-18 (Schema — DB-Tabellen siehe [`exec-18-unified-agent-schema.md`](./exec-18-unified-agent-schema.md); Agno-Referenz `_ref/agno/`), exec-ebm (Energy Scoring), [`exec-context.md`](./exec-context.md) (Skill-Position im Prompt, Cache-freundliche Reihenfolge), [`exec-memory.md`](./exec-memory.md) (episodisches Skill-Feedback, Retain)
> Referenzen (ArXiv kanonisch): **2604.04323** Skills in the Wild; **2602.08234** SkillRL; **2601.03192** MemRL; PDFs unter `docs/` falls vorhanden
> Hauptprojekt-Docs:
>   - `main_docs/root/AGENT_TOOLS.md` — Tool-Taxonomie, MCP Apps (Sek. 3.3), Memory-Read/Write-Interfaces
>   - `main_docs/root/AGENT_SECURITY.md` — Capability Envelope fuer Skill/Tool-Execution, Tool Proxy
>   - `main_docs/root/CONTEXT_ENGINEERING.md` — Consumer, Merge, Token-Budget — mit **exec-context** zur Prompt-Runtime konsolidieren

---

## 0. Kontext

Skills sind wiederverwendbare, domaenenspezifische Wissensartefakte (Workflows, Anleitungen,
Prozeduren) die Agents bei der Aufgabenbearbeitung unterstuetzen.

**Problem (Studie 2604.04323):** Der Nutzen von Skills bricht unter realistischen Bedingungen
stark ein. Nicht das Skill-Format ist der Engpass, sondern:
1. **Skill-Auswahl** — Agent findet den richtigen Skill nicht
2. **Skill-Anpassung** — Skill passt nicht exakt zum Task
3. **Skalierung** — Mehr Skills = mehr Noise = schlechtere Ergebnisse

**Loesung laut Studie:** Retrieval + Query-specific Refinement. Nicht bessere Skills schreiben,
sondern bessere Skill-Nutzung.

---

## 1. IST-Zustand

### Bestehende Module

| Modul | Pfad | Funktion | Status |
|-------|------|----------|--------|
| Loader | `agent/skills/loader.py` | 3-Tier SKILL.md Parsing (Global → Team → Personal), Merge, Prompt Injection, `filesystem|db|hybrid` | Implementiert |
| Finder | `agent/skills/finder.py` | BM25 + optional Dense + RRF, Top-K Selection | Implementiert |
| Refiner | `agent/skills/refiner.py` | Query-specific Verfeinerung, ephemer pro Turn | Implementiert, hinter Feature-Flag |
| DB Store | `agent/skills/store_db.py` | Duenner Runtime-/Seed-Zugriff fuer `agent.agent_skills` | Implementiert |
| Evolver | `agent/skills/evolver.py` | Auto-Generierung aus fehlgeschlagenen Sessions (MetaClaw Sec. 3.2) | Implementiert, hinter Feature-Flag |
| Importer | `agent/skills/importer.py` | Skill Import | Implementiert |
| RL Trainer | `agent/skills/rl_trainer.py` | RL-basiertes Skill Training | Platzhalter |
| Global Skills | `agent/skills/global/` | 4 manuell erstellte Skills (market-research, memory-usage, risk-assessment, trading-analysis) | Aktiv |
| Team Skills | `agent/skills/team/` | Team-shared Skills | Leer |
| Personal Skills | `agent/skills/personal/` | Auto-generierte User-Skills | **Abzuschaffen** — ersetzt durch Promotion-Pipeline |

### Hauptprobleme

1. `loader.py` laedt ALLE Skills und injiziert sie komplett in den Prompt. Skaliert nicht.
2. Skills auf Dateisystem — nicht multi-instance-faehig, kein Hot-Reload, kein Audit Trail.
3. Keine Verbindung zwischen Skills und Memory.
4. Kein Scoring welche Skills funktionieren.

---

## 2. Forschungsgrundlage

### Papers — Direkt Skill-bezogen

| Paper | Arxiv | Kern-Beitrag | PDF |
|-------|-------|-------------|-----|
| **Skills in the Wild** (UCSB/MIT, 04/2026) | 2604.04323 | Benchmark: Skill-Nutzen bricht unter realen Bedingungen ein. Query-specific Refinement als Loesung. | `docs/Skills_Wild_2604.04323.pdf` |
| **SkillRL** (02/2026) | 2602.08234 | RL-basierte Skill Evolution. SkillBank (General + Task-Specific). Recursive Co-Evolution von Skills und Policy. | `docs/SkillRL_2602.08234.pdf` |
| **EvoSkill** (Sentient AGI, 03/2026) | 2603.02766 | 5-Stage Skill Evolution Loop: Base Agent → Proposer → Generator → Evaluator → Frontier. Agent-agnostic, cross-task transferability. Skills als `.claude/skills/` Dirs versioniert ueber Git Branches. | [GitHub](https://github.com/sentient-agi/EvoSkill) |
| **MemRL** (01/2026) | 2601.03192 | Q-Value-basierte Skill-Auswahl aus Episodic Memory. Zwei-Phasen-Retrieval: semantisch → Q-Value Ranking. | `docs/MemRL_2601.03192.pdf` |

### Papers — Verbundene Systeme (Skills haengen von Memory + Harness ab)

| Paper | Arxiv | Verbindung zu Skills | PDF |
|-------|-------|---------------------|-----|
| **Meta-Harness** (03/2026) | 2603.28052 | Holistische Harness-Optimierung via Trace-informiertem Proposer. Pareto-Frontier. **Nicht direkt skill-bezogen** — betrifft den gesamten Agent-Harness (Prompts, Memory, Tools, Context). Eigenes Exec: [`exec-harness.md`](./exec-harness.md). Skill-Pareto (Phase 3c) ist Pattern-Uebertrag, nicht Paper-Kernbefund. | `docs/Meta-Harness-2603.28052v1.pdf` |
| **MetaClaw** | — | Skill Generation Versioning (Sec. 3.2) → direkt in `evolver.py`. Deduplication → verhindert doppelte Skills bei gleichem Failure-Pattern. | Referenz in evolver.py |
| **Memory for Autonomous LLM Agents** (03/2026) | 2603.07670 | 5 Memory-Familien Taxonomie. Skills sind **procedural memory** — getrennt von episodic (Hindsight) und semantic (KG). Die fehlende Integration dieser drei ist das Kernproblem. | `docs/Memory_Autonomous_LLM_Agents_2603.07670v1.pdf` |
| **Hindsight** (12/2025) | 2512.12818 | Episodic Memory als Datenquelle fuer Skill-Feedback (Phase 3a). Recall informiert finder.py welche Skills historisch funktioniert haben. | `docs/Hindsight_2512.12818v1.pdf` |
| **Unsupervised Ensemble via EBM** (01/2026) | 2601.20556 | Energy-Based Scoring fuer Multi-Agent Ensemble — uebertragbar auf Skill-Kombinations-Bewertung (Phase 4b). | `docs/Maymon2025_Unsupervised_Ensemble_Deep_EBM.pdf` |

### Zusammenhang der Studien

```
MetaClaw ──→ evolver.py (Skill Generierung + Versioning)
                ↓
EvoSkill ──→ 5-Stage Loop (Propose → Generate → Evaluate → Frontier)
          └──→ Evaluator Stage = fehlende A/B-Eval-Stufe (§8b.3)
                ↓
Skills in the Wild ──→ finder.py + refiner.py (Retrieval + Refinement)
                ↓
SkillRL ──→ rl_trainer.py (Recursive Skill Evolution, Phase 4a)
        └──→ General always-load vs Task-Specific retrieval (§8b offener Punkt)
                ↓
MemRL ──→ Q-Value Skill Selection aus Episodic Memory (Phase 4c)
                ↓
Hindsight ──→ Episodic Memory als Skill-Feedback Store (Phase 3a)
                ↓
Memory Taxonomy ──→ Skills = Procedural Memory, integriert mit Episodic + Semantic
                ↓
EBM ──→ Energy Scoring fuer Skill-Kombinationen (Phase 4b)
                ↓
Meta-Harness ──→ agent/harness/ (holistische Agent-Optimierung) → exec-harness.md
AutoResearch ──→ Parameter-Sweep isolierte Komponenten → exec-harness.md
```

### GitHub Repos

| Repo | Nuetzlicher Code |
|------|-----------------|
| [UCSB-NLP-Chang/Skill-Usage](https://github.com/UCSB-NLP-Chang/Skill-Usage) | `search_server/` (BM25 + Semantic + Hybrid), `scripts/query_specific_refinement.py`, `scripts/query_agnostic_refinement.py`, 34k Skill Collection |
| [aiming-lab/SkillRL](https://github.com/aiming-lab/SkillRL) | SkillBank Architektur, Experience-based Distillation, Recursive Evolution |
| [sentient-agi/EvoSkill](https://github.com/sentient-agi/EvoSkill) | 5-Stage Loop (Propose → Generate → Evaluate → Frontier), `.claude/skills/` Integration, GEPA/DSPy-Patterns. **Evaluator-Stage (Stage 4)** ist Pattern fuer unsere fehlende A/B-Eval-Stufe. Frontier tracking via Git Branches — analog zu unserem `generation` + `parent_skill_id` in DB. |
| find-skills (lokal: `~/.agents/skills/find-skills/`) | Blueprint fuer Skill Discovery Pattern |

---

## 3. Architektur-Entscheidungen

### 3a. Skill Storage: Alles in PostgreSQL

**Dateisystem ist nicht production-viable** bei Multi-User/Multi-Instance:
- Mehrere Container → Dateisystem nicht shared
- Skill-Aenderung braucht Redeploy
- Kein Audit Trail

**Zielbild:** Alles in PostgreSQL. Git bleibt Source-of-Truth fuer Entwicklung,
beim Deploy werden Curated Skills in DB geschrieben (Seed Pattern, wie `seed_data.py`).

**Ist-Stand (2026-04):** Wir sind in einer **Uebergangsphase**:
- Filesystem bleibt Default (`AGENT_SKILLS_SOURCE=filesystem`)
- DB-Pfad ist vorbereitet (`agent.agent_skills`, `user_skill_preferences`)
- Runtime kann bereits `filesystem|db|hybrid`
- Team/Personal liegen weiter auf Dateisystem; nur **globale** Skills sind aktuell sinnvoll fuer den DB-Seed

```sql
agent_skills (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT,
    content TEXT NOT NULL,
    tier TEXT CHECK (tier IN ('global', 'team', 'promoted')),
    owner_id TEXT,                  -- user_id oder team_id (NULL fuer global)
    generation INT DEFAULT 0,
    parent_skill_id UUID,
    created_from_session TEXT,
    success_count INT DEFAULT 0,
    usage_count INT DEFAULT 0,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)

user_skill_preferences (
    user_id TEXT NOT NULL,
    skill_id UUID NOT NULL REFERENCES agent_skills(id),
    disabled BOOLEAN DEFAULT false,
    PRIMARY KEY (user_id, skill_id)
)
```

**Entwicklung → Runtime Flow (Zielbild):**
```
Git: agent/skills/global/*.md  →  Deploy: Seed Script  →  PostgreSQL agent_skills
Runtime: loader.py liest NUR aus PostgreSQL
```

**Uebergang (realer Code-Stand):**
```
Git: agent/skills/global/*.md
  ├─ Runtime heute: filesystem (Default)
  ├─ optional: hybrid (Dateisystem + DB overlay)
  └─ nach Seed + Flip: db
```

**Schema-Referenz:** exec-18 (Unified Agent Schema) — `014_agent_skills.py` fuer `agent_skills` + `user_skill_preferences`.

### 3b. Tier-System: Personal abschaffen, Promotion-Pipeline stattdessen

| Tier | Wer sieht es | Wie entsteht es | Wer entfernt es |
|------|-------------|-----------------|-----------------|
| `global` | Alle User | Curated (Git Seed) ODER automatisch promoted | Pareto-Eviction oder Admin |
| `team` | Team-Mitglieder | Admin weist promoted Skill einem Team zu | Admin |
| `promoted` | Nur der erstellende User | Automatisch aus wiederkehrenden erfolgreichen Refinements | Pareto-Eviction (dominiert → disabled) |

**Zielbild:** Personal entfaellt — ersetzt durch `promoted`. Unterschied: Personal war statisch
(Evolver generiert einmal). Promoted ist datengetrieben (entsteht erst nach wiederholtem Erfolg).

**Ist-Stand:** Code und Control-UI kennen noch `personal`; das bleibt bis Promotion-Pipeline + DB-Modell final migriert sind.

**Zielbild:** User kann Skills deaktivieren via `user_skill_preferences.disabled=true`.
Finder filtert diese vor der Suche raus. Disabled-Count fliesst als Negativ-Signal in Pareto.

**Ist-Stand:** Disable laeuft aktuell ueber `agent.skills_state`; Finder respektiert diesen Toggle bereits.

### 3c. Promotion-Pipeline: Promoted → Global

```
User Session
     ↓
finder.py → Top-K Skills aus DB
     ↓
refiner.py → Query-specific Anpassung (ephemer, nur fuer diesen Turn)
     ↓
Session Ergebnis → Hindsight Retain (Skill + Outcome)
     ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Background (nach 10+ Sessions mit aehnlichem Refinement-Pattern):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ↓
Pattern Detection: "Refinement X wurde 8x aehnlich gemacht, 7x erfolgreich"
     ↓
Evolver: Generiert Promoted Skill aus erfolgreichen Refinements
     ↓
→ DB: tier='promoted', owner_id=user_id
     ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pareto Promotion Gate (automatisch, z.B. woechentlich):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ↓
Pareto-Check ueber 4 Dimensionen:
  1. success_rate     — % Sessions wo Skill zum Erfolg beitrug
  2. usage_rate       — Wie oft wird Skill geladen (Trigger-Qualitaet)
  3. token_efficiency — Token-Kosten / Ergebnis-Qualitaet
  4. refinement_stability — Wie oft braucht Skill noch Refinement
     ↓
Promotion-Schwellenwerte:
  - Nicht-dominiert auf Pareto-Frontier
  - 20+ Sessions Usage
  - 3+ verschiedene User mit Erfolg (nicht nur ein User)
  - Kein aktives Disable von Usern
     ↓
JA → Automatisch tier='global', owner_id=NULL
NEIN → Bleibt promoted oder wird disabled (dominiert)
     ↓
Rollback: Wenn promoteter Skill bei anderen Usern schlecht performt
          → naechster Pareto-Check degradiert zurueck
```

**Voll-automatisch.** Admin-Review nur als optionaler Override, nicht als Gate.
Pareto-Frontier IST die Qualitaetskontrolle.

---

## 4. Implementierungsplan

### Klar getrennt: Was braucht Training vs. was ist sofort implementierbar

```
KEIN TRAINING NOETIG                    TRAINING NOETIG
========================                ========================
Phase 1: finder.py (Search)            Phase 4a: SkillRL / RL Trainer
Phase 2: refiner.py (LLM-Call)         Phase 4b: EBM Skill Scoring
Phase 3: Hindsight Skill-Memory        Phase 4c: MemRL Q-Values
Phase 3b: Promotion Pipeline
Phase 3c: Pareto Ranking
```

---

### Phase 1: `finder.py` — Skill Discovery (KEIN Training)

**Was:** BM25 + Semantic Hybrid Search ueber alle Skills statt blindes Laden.

**Blueprint:** Skill-Usage `search_server/` + find-skills SKILL.md

```python
# agent/skills/finder.py

# 1. Index aufbauen (einmalig bei Startup, refresh bei Skill-Aenderung)
#    - BM25 Index ueber name + description aller Skills aus DB
#    - Embedding Index ueber description + content (sentence-transformers)

# 2. Search (pro Agent-Turn)
#    Input:  user_query + agent_role + conversation_context
#    BM25:   keyword match gegen Skill descriptions
#    Dense:  cosine similarity gegen Skill embeddings
#    Hybrid: Reciprocal Rank Fusion (RRF)
#    Filter: user_skill_preferences.disabled Skills ausschliessen

# 3. Optional: Hindsight Boost (Phase 3)
#    Recall historische Skill-Performance, boost erfolgreiche Skills

# 4. Token-Budget-aware Top-K
#    Default: max 3 Skills oder 2000 Tokens (konfigurierbar)
```

**Aenderung an `loader.py`:** `format_skills_for_prompt(query=...)` ruft finder auf
statt alle Skills zu laden. Ohne query → Fallback auf alle (Rueckwaertskompatibel).

**Aufwand:** Klein. BM25 ~50 LOC, RRF ~20 LOC, Embeddings via bestehende sentence-transformers.

---

### Phase 2: `refiner.py` — Query-specific Refinement (KEIN Training, 1 LLM-Call)

**Was:** Gefundenen Skill an konkreten Task anpassen bevor er in den Prompt geht.

**Blueprint:** Skill-Usage `scripts/query_specific_refinement.py`

```python
# agent/skills/refiner.py
# Input:  Skill Content + User Query + Agent Context
# LLM:    "Passe diesen Skill an die folgende Aufgabe an.
#          Entferne Irrelevantes, ergaenze fehlenden Kontext."
# Output: Refined Skill Content (kuerzer, task-spezifisch)
# Kann mehrere Skills kombinieren ("synthesize across multiple skills")
```

**Refined Skills sind ephemer** — leben nur fuer diesen Turn im Prompt.
Nicht persistent. Optional: erfolgreiche Refinements in Hindsight retainen.

**Feature-Flag:** `AGENT_SKILL_REFINEMENT=true` (default: false)

---

### Phase 3: Skill-Memory + Promotion + Pareto (KEIN Training, nutzt bestehende Infra)

**3a. Skill-Feedback in Hindsight:**
```python
# Nach jeder Session in agent/harness/scorer.py:
retain(
    content=f"Skills used: {skill_names}. Outcome: {success}. Task: {task_type}",
    tags=["skill_feedback", task_type]
)
```
Finder nutzt Recall als Boost-Signal. Erst nach ~50+ Sessions sinnvoll.

**3b. Promotion Pipeline:**
- Background Job erkennt wiederkehrende Refinement-Patterns
- Evolver generiert Promoted Skill aus erfolgreichen Refinements
- Gespeichert in DB als `tier='promoted'`

**3c. Pareto Ranking:**
- Gleiche Logik wie `agent/harness/pareto.py` (Meta-Harness)
- 4 Dimensionen: success_rate, usage_rate, token_efficiency, refinement_stability
- Automatische Promotion (promoted → global) bei Pareto-Optimalitaet + User-Diversitaet
- Automatische Eviction (dominiert → disabled) beim naechsten Pareto-Check
- User-Disable als Negativ-Signal in Pareto-Berechnung

---

### Phase 4: Learned Scoring (BRAUCHT TRAINING)

Erst relevant wenn Skill-Pool > 30, Session-Daten > 100, Phase 1-3 zeigen Grenzen.

**4a. SkillRL Pattern (arxiv 2602.08234):**
- Experience-based Distillation: Trajectories → Skills/Lessons
- Maps auf: `rl_trainer.py` + `evolver.py`

**4b. EBM Skill Scoring (exec-ebm):**
- Energy-Funktion ueber Skill-Task-Paare
- Kann Kombinationen bewerten

**4c. MemRL Q-Values (arxiv 2601.03192):**
- Gelernter Nutzwert pro Skill pro Situation
- Braucht RL-Training Loop

---

## 5. Verbindung zu Memory (exec-memory)

Skills und Memory sind aktuell **nicht verbunden**. Das ist eine Luecke.

| Pfad | Wie | Wo |
|------|-----|-----|
| **Skill-Feedback als Episodic Memory** | Hindsight speichert welche Skills wann funktioniert haben | Phase 3a: scorer.py → Hindsight Retain |
| **Skill-Ranking aus Memory** | Finder nutzt Hindsight Recall als Boost-Signal | Phase 3a: finder.py → Hindsight Recall |
| **Skill-Generierung aus Memory** | Evolver nutzt Recall um wiederkehrende Failure-Patterns zu erkennen | Phase 3b: evolver.py → Hindsight Recall |
| **Context-aware Loading** | Working Memory (M5) + Conversation-Context informiert finder.py | Phase 1: finder.py Input |
| **Promotion aus Memory** | Pattern Detection ueber Hindsight: "Refinement X wurde 8x aehnlich gemacht" | Phase 3b: Background Job |

### 5a. Verbindung zu exec-context (Prompt-Oekonomie)

Skills sind **procedural memory** (Paper **2603.07670**) und landen idealerweise im **stabilen Prefix** (nach System/Rolle/Tools, vor dynamischem Recall/History), damit **Provider Prompt Caching** und feste Merge-Reihenfolge greifen — siehe [`exec-context.md`](./exec-context.md) §5–6.

| Aspekt | Konsequenz |
|:--------|:-----------|
| finder Top-K + refiner | Token-Budget fuer Skill-Block; vermeidet „alle Skills laden“ (§1 Problem) |
| Cache-Breaking | Keine volatile IDs/Timestamps in Skill-Render-Header; deterministische Sortierung wo moeglich |
| Compaction | Bei Schrumpfen des Fensters: Skill-**Inhalt** ggf. erneut refinen; **Outcomes** weiter ueber Hindsight Retain (exec-memory) |

---

## 6. Paper-Abgleich: Memory for Autonomous Agents (2603.07670v1) — Skill-Relevante Punkte

| Paper-Abschnitt | Thema | Relevanz fuer exec-skills | Massnahme |
|-----------------|-------|--------------------------|-----------|
| **3.1** Procedural Memory | Skills = ausfuehrbarer Code, indiziert nach NL-Beschreibung (Voyager Pattern) | Unser SKILL.md Format ist NL-beschrieben, aber nicht ausfuehrbar | Langfristig: Skills mit ausfuehrbarem Code-Teil (scripts/ Unterordner) |
| **4.5** Policy-Learned Management | AgeMem: Memory Ops (store/retrieve/update/summarize/discard) als RL-Policy | Direkt anwendbar auf Skill-Ops (find/refine/promote/disable/evolve) | Phase 4: SkillRL als Skill-Policy-Learning |
| **6.3** Compositional Skill Reuse | Skills kreativ verketten, nicht nur einzeln nutzen (Voyager: 3.3x Unique Items) | **Adressiert** — `refiner.py` compose-Mode merged N Skills → 1 synthesized Block (Paper 2604.04323 §4.1). | Langfristig: Skill Dependency Graph (Skill A erfordert Skill B als Voraussetzung). |
| **6.6** Schema Drift | Gespeicherte Tool-Usage-Patterns werden ungueltig bei API-Aenderung | Relevant fuer Skill-Feedback (Phase 3a): veraltete Skills. `AGENT_TOOLS.md` Sek. 2 definiert Tool-Taxonomie. | `api_version` Feld auf `agent_skills`. Bei API-Aenderung: Skills mit alter Version flaggen. Tool Proxy aus `AGENT_SECURITY.md` als Enforcement-Punkt. |
| **6.7** Cross-Domain Transfer | Debugging-Skills aus Python fuer Java wiederverwendbar? | Unser Tier-System (promoted → global) ist impliziter Transfer | Skill-Metadata: `transferable: true/false` + Domain-Tags |
| **7.7** Observability | Skill-Usage Logs: welche Skills werden geladen/ignoriert/refined? | **Adressiert** — `AuditAction.SKILL_FOUND/REFINED/USED` in `agent/audit/logger.py`, `trigger_quality.py` CLI, `usage_count` Increment. | Vertiefung: Compliance-Rate (§8b.2b), Harness-Level Aggregation (exec-harness). |

---

## 7. Studien-Ergebnisse als Leitlinien

| Erkenntnis | Konsequenz fuer uns |
|------------|-------------------|
| Skill-Nutzen bricht bei realistischer Auswahl ein | Phase 1 (finder.py) ist Pflicht bevor Skill-Pool waechst |
| Query-specific Refinement bringt groessten Gewinn | Phase 2 (refiner.py) ist der wichtigste Hebel |
| Refinement wirkt als Multiplikator, nicht als Generator | Skill-Qualitaet bleibt wichtig — Refinement rettet keine schlechten Skills |
| Agents benutzen verfuegbare Skills nur in 49% der Faelle | Trigger-Description muss praezise sein |
| Agentic Search (iterativ) > Direct Search | finder.py sollte optional iterative Queries unterstuetzen |
| Viele Skills ≠ besser | Qualitaet > Quantitaet. Top-K Limit ist richtig |

---

## 8. Naechste Schritte

**Sofort (kein Training):**
- [x] DB Schema: `agent_skills` + `user_skill_preferences` — Alembic `python-backend/alembic/versions/014_agent_skills.py`. **Verifiziert** 2026-04-15: `alembic upgrade 014_agent_skills` gegen podman-PG 5433/hindsight_dev durchgelaufen (nach Fix: 008 revision-chain + 014 self-ref FK mit Schema-Qualifier).
- [x] Seed Script: `python-backend/scripts/seed_agent_skills.py`. **Verifiziert** idempotent: 4 Global Skills geschrieben, zweiter Run tut UPDATE (kein Duplikat).
- [x] Phase 1: `agent/skills/finder.py` (BM25 + optional Dense + RRF). **Verifiziert** DB+hybrid+filter_disabled.
- [x] `loader.py` + `agent/graph/runner.py`: Finder bei User-Query; `AGENT_SKILLS_SOURCE=filesystem|db|hybrid`.
- [x] Bestehende 4 Global Skills mit Use-When Trigger-Descriptions.

**Kurzfristig (kein Training, 1 LLM-Call):**
- [x] Phase 2: `agent/skills/refiner.py` hinter Feature-Flag (`AGENT_SKILL_REFINEMENT`). **Erweitert:** `AGENT_SKILL_REFINE_MODE=compose|per_skill` (default compose, Paper 2604.04323 §4.1 — merge/synthesize across multiple skills).
- [x] **Coverage Gate** `agent/skills/coverage.py` (Paper §4.2): LLM-Judge 1-5 auf initial retrieved set, skip Refinement wenn Score < Threshold (`AGENT_SKILL_COVERAGE_THRESHOLD`, default 3.5). Verhindert Regressions bei niedriger Coverage (Paper: Kimi 33.5→26.7 ohne Gate).
- [x] **Agentic Iterative Retrieval** `agent/skills/iterative_search.py` (Paper §3.2): LLM reformuliert Query wenn initial top-k schwach. Env `AGENT_SKILL_ITERATIVE_SEARCH=1`, Max-Rounds via `AGENT_SKILL_ITERATIVE_MAX_ROUNDS` (default 2).
- [x] **Offline Refinement (query-agnostic, Paper §4.1)** — `agent/skills/offline_refiner.py` + `scripts/refine_skills_offline.py`. Generiert synthetische Tasks pro Skill, rewrited Skill-Body gezielt für diese Tasks, schreibt als `generation+1` mit `parent_skill_id`-Link in DB. Paper: erlaubt query-specific Refinement zur Laufzeit nur auf besseren initial-Skills ansetzen, reduziert Inference-Kosten. Smoke gegen mocked LLM 2026-04-16 verifiziert — gen 0 deaktiviert, gen 1 enabled, loader liest neuste Generation.

**Mittelfristig (nutzt bestehende Infrastruktur):**
- [x] **Phase 3a (Beobachtung):** `AuditAction.SKILL_FOUND/SKILL_REFINED/SKILL_USED` in `agent/audit/logger.py` — keine neue Tabelle, `agent.audit_events` reicht. Loader schreibt bei jeder Skill-Nutzung. **Hindsight-Retain-Hook für 3a Outcome-Feedback bleibt offen** (wartet auf cursor's exec-memory Scorer-Integration).
- [x] **Direct Counters:** `agent.agent_skills.usage_count` wird bei `skill_used` per `increment_usage_counts()` in `store_db.py` inkrementiert. `success_count` bleibt bis Session-Outcome-Feedback verdrahtet ist.
- [x] **Phase 3c (optional):** `agent/skills/pareto.py` — 4-Dim-Frontier (success_rate, usage_count, token_efficiency, refinement_stability), Promotion/Eviction-Kandidaten aus bestehenden Tabellen. **Note:** Pareto-über-Skills ist Pattern-Übertrag aus Meta-Harness (2603.28052), nicht durch Skill-Paper mandatiert — dokumentiert im Modul-Header. Helpers `compute_pareto()` / `eviction_candidates()` / `promotion_candidates()`, Domination-Logik via synthetischem success_count-Mutieren verifiziert.

- [x] **Trigger-Quality CLI** — `agent/skills/trigger_quality.py` + `scripts/skill_trigger_quality.py`. Aggregiert aus `agent.audit_events` per-Skill: `n_found`, `n_with_score`, `avg_coverage`, `false_rate` (Anteil mit `coverage_score < 2.5`). Verdict-Labels: `OK | BROAD_TRIGGER_review_description | LOW_AVG_COVERAGE_review | INSUFFICIENT_DATA | NO_COVERAGE_SCORES`. **Paper-Abgleich:** motiviert durch Paper §6.7 Observability + Memory §7.7 Skill Operation Log — Paper selbst misst Loading-Rate (Fig 2b) und Coverage (Tbl 3), *aber keine "false-trigger-rate" als expliziten Begriff.* Formel + Schwellen sind unsere Ableitung. Guards gegen non-array JSONB-metadata sind drin (offline_refiner schreibt skill_refined ohne source_skills-Array).

- [x] **Model-aware Coverage Threshold** — `agent/skills/coverage.py:_coverage_threshold(model)` mit Prioritäts-Lookup: global override `AGENT_SKILL_COVERAGE_THRESHOLD` → per-family override `AGENT_SKILL_COVERAGE_THRESHOLD_{CLAUDE|QWEN|KIMI}` → eingebaute Defaults (`claude=3.0, qwen=4.0, kimi=4.5`) → Fallback 3.5. Model wird entweder explizit an `should_refine(model=...)` gereicht oder aus `AGENT_DEFAULT_UTILITY_MODEL` env gelesen. **Paper-Abgleich:** Paper 2604.04323 §4.2 + Tbl 3 gibt **globale** Coverage-Werte (3.49 / 3.83 / 4.01) und zeigt **qualitativ** dass Kimi auf SKILLSBENCH w/ curated regressiert (33.5→26.7), Qwen auch (31.6→26.2), Claude nicht. Die konkreten per-family Zahlen (3.0/4.0/4.5) sind **unsere Interpretation** dieser qualitativen Finding, **nicht Paper-Tabellenwerte**. Ehrlich dokumentiert im Modul-Kommentar (`_MODEL_THRESHOLD_DEFAULTS`). Per-family-Env-Overrides erlauben Tuning pro Deployment sobald echte Eval-Daten vorliegen. Unit-Tests über alle 5 Prioritäts-Ebenen.
- [x] **Migration 015 skill_extensions** (2026-04-16): `ALTER TABLE agent_skills ADD skill_type TEXT + assets JSONB`. SkillRL §3.2: General always-load vs Task-Specific retrieval-gated. Verifiziert gegen podman-PG.
- [x] **A1 api_version:** Seed setzt `api_version='v1'`, `store_db.upsert_global_skill()` schreibt es, `_row_to_skill()` liest es, Skill-Dataclass hat `api_version: str | None`. Schema-Drift Detection (§6.6).
- [x] **A2 user_skill_preferences Cutover:** `db_state.py` liest aus `agent.user_skill_preferences` (JOIN mit `agent_skills`), Fallback auf Legacy `skills_state`. `control/skills.py:patch_skill()` schreibt in `user_skill_preferences` (UUID-Lookup), Fallback fuer Filesystem-only Skills.
- [x] **A3 General/Task-Specific Split:** `memory-usage` = `skill_type: general` (always-loaded), Rest = `task_specific` (via Finder). Loader trennt: `general + iterative_find(task_specific, query)`. Verifiziert: memory-usage erscheint im Prompt auch bei unrelatierter Query.
- [x] **A4 assets JSONB:** Spalte da, Seed schreibt `{}`, `parse_skill_file()` scannt `scripts/examples/templates/` Subdirs (<10KB Text-Dateien), DB-backed via `_row_to_skill()`/`upsert_global_skill()`.
- [ ] Phase 3b: Promotion Pipeline (Background Job — Pattern-Detection → Evolver → tier='promoted').
- [ ] Control-UI Disable-Toggle (exec-15).

**Langfristig (braucht Training + Daten):**
- [ ] Phase 4: SkillRL / EBM / MemRL evaluieren
- [ ] Skill-Pool auf 30+ erweitern

---

## 8b. Offene Punkte: MiniMax-inspiriert + Paper §4 nicht abgedeckt

### 2b) Skill-Compliance-Rate via Response-Analyse

**Kontext.** MiniMax M2.7 berichtet 97% Skill-Compliance auf MM Claw (40+ Skills à >2000 Tokens). Das misst ob ein Agent NACH dem Laden eines Skills dessen guidance **tatsaechlich in der Response umsetzt** — haerteres Signal als reine Loading-Rate. Skills in the Wild (2604.04323 Fig 2b) misst Loading (49% bei Claude, trotz verfuegbarer Skills), aber nicht Compliance.

**Warum das fuer uns relevant ist.** Wir injizieren Skills unconditional in den System-Prompt — Loading ist bei uns trivial 100%. Der echte Analog ist Compliance: *hat die Agent-Response die Skill-Guidance umgesetzt?* Das ist ein direkter Qualitaetsindikator fuer (a) Trigger-Description (wurde das richtige Skill gewaehlt?), (b) Skill-Inhalt (war er befolgbar?), (c) Model-Stärke.

**Umsetzung (skizziert).**
- Batch-Job nach Session-Ende (offline, nicht inline — 1 LLM-Call pro [skill, session]-Paar):
  1. Query `agent.audit_events` fuer alle `skill_used` Events einer Session
  2. Query Final-Response des Agenten aus derselben Session (`llm_response` audit action oder `session.summary` wenn exec-18 `agent.sessions` landet)
  3. LLM-Judge mit System-Prompt: *"Given this skill's guidance G and the agent's final response R for task T — did R follow G? Score 0-5."*
  4. Persist: neues `skill_complied` audit-event mit `{skill_id, session_id, score, judge_model}`; increment `agent.agent_skills.success_count` wenn score >= 3
- Aggregation via neuem Feld in `agent/skills/trigger_quality.py` oder separatem `compliance.py`

**Kosten.** 1 LLM-Call pro (geladene Skill × Session). Bei 4 Skills × 100 Sessions/Tag = 400 Calls/Tag. Utility-Model OK.

**Dependencies.**
- **Blockiert von:** cursor's exec-memory Scorer-Integration (Session-Outcome-Feedback). Aktuell keine sauberen Session-Ende-Signale in `agent.audit_events`.
- **Enabled durch:** exec-18 Migration 011 (`agent.sessions` Tabelle, wenn gebaut) — dann ist `session_id` + Final-Output queryable statt ueber `thread_id`-Joins rekonstruiert.

**Referenzen.** MiniMax M2.7 Model Card (Hugging Face), MiniMax News Blog `minimax-m27-en` — beide erwaehnen die 97% Compliance-Zahl ohne Verfahren zu detaillieren. Wir bauen das Verfahren selbst.

### 3) Composition-on-top-of-offline-refined — A/B Evaluation

**Kontext.** Zwei Paper-Hebel laufen jetzt parallel:
- Offline Refinement (Paper §4.1 query-agnostic, `scripts/refine_skills_offline.py`) — hebt initial Skill-Qualitaet als Preprocessing.
- Inference-time Composition (Paper §4.1 query-specific, `refiner.py` compose-Mode) — mergt N Skills → 1 synthesized Block zur Laufzeit.

Paper argumentiert beide Hebel additiv, **zeigt das aber nicht mit ablation**. Fuer unsere Trading-Domain ist empirisch offen, ob offline+composition den inference-composition-only Baseline wirklich schlaegt — oder ob die 2 zusaetzlichen offline LLM-Calls pro Skill verschwendet sind.

**Eval-Design.**
Neuer Ordner `python-backend/experiments/skill_eval/` (nicht zu verwechseln mit cursor's `experiments/memory_eval/`).

Varianten:
| Variante | Skills | Inference-Mode |
|---|---|---|
| baseline_none | gen 0 originals | kein Refinement |
| baseline_compose | gen 0 originals | compose |
| offline_only | gen 1+ refined | kein Refinement |
| offline+compose | gen 1+ refined | compose |

Test-Set: 50-100 synthetische Trading-Queries (via LLM aus SKILL.md-Descriptions generiert, wie `offline_refiner._generate_tasks` aber breiter). Oder echte aus `agent.audit_events` `user_request`-Payloads wenn genug Daten.

Metrik: LLM-Judge 1-5 "Given query Q and response R generated with skill variant V, how well does R address Q's task?"

Output: CSV mit (query, variant, score) + Aggregation {mean, std, n} pro Variante × Model. Optional: per-Query Paired-T-Test zwischen Varianten.

**Kosten.** ~200 LLM-Calls pro Variante (N=50 Queries × avg 4 LLM-Steps pro Query inkl. Agent-Response-Gen + Judge). 4 Varianten × 2-3 Modelle = ~2400 Calls. Utility-Model fuer Judge, echtes Modell fuer Agent-Response.

**Dependencies.** Keine. Alle benoetigten Module existieren (finder, refiner, offline_refiner, coverage). Nur Harness-Skript + Test-Set.

**Ziel.** Empirisch validieren:
1. Lohnt sich offline-refinement ueberhaupt (baseline_compose vs offline+compose)?
2. Wenn ja, fuer welche Models (Claude tolerant, Kimi/Qwen evtl. sensibler — siehe Threshold-Diskussion in `coverage.py`)?
3. Gibt es Query-Typen wo eine Variante systematisch gewinnt (z.B. offline hilft bei vagen Queries, compose hilft bei spezifischen)?

**Priority.** Sobald cursor's eval-infra (`memory_eval/aggregate_memory_suite.py`) Stabilitaet hat, Pattern hinueberuebernehmen. Skill-Eval ist simpler als Memory-Eval — wir haben klare Ground-Truth via LLM-Judge, keine Recall-at-k-Kette.

---

## 9. Verify / offene Punkte

**Verify Gates:**

- [x] `alembic upgrade 014_agent_skills` gegen echte PG (podman 5433) durchgelaufen (2026-04-15)
- [x] `scripts/seed_agent_skills.py` idempotent verifiziert — 4 Skills, zweiter Run = UPDATE
- [x] `AGENT_SKILLS_SOURCE=db` + `hybrid` gecheckt — loader liest DB-Skills mit `db_id`
- [x] `filter_disabled_skills` respektiert `agent.skills_state.enabled=false` (smoke 2026-04-15)
- [x] Finder BM25 und BM25+Dense verifiziert — Top-1 matcht erwartetes Skill für 4 probe queries
- [x] Refiner E2E (mocked LLM): compose-mode produziert 1 synthesized Skill aus N Sources; per_skill-mode produziert N refined copies
- [x] Coverage-Gate unterdrückt Refine bei Score < 3.5 (mocked LLM-Judge Test)
- [x] Iterative Search: Reformulation-Loop funktioniert bei unsatisfied judge, merged top-k dedupliziert
- [x] Audit Events landen in `agent.audit_events` mit action IN (`skill_found`, `skill_refined`, `skill_used`); metadata enthält `search_rounds`, `reformulations`, `coverage_score`, `source_skills`
- [x] `agent_skills.usage_count` inkrementiert korrekt (bei compose mode: source-Skills, nicht der composed placeholder)
- [x] `store_db.py` bleibt bewusst duenn: Fetch/Upsert/Seed-Helfer + direkte Counter-Updates, keine ORM-Schicht
- [x] Offline-Refiner E2E (mocked LLM): gen 0 deaktiviert + gen 1 enabled + `parent_skill_id` FK gesetzt, Loader liest neueste Generation (smoke 2026-04-16)
- [x] Trigger-Quality CLI smoke: aggregiert 4 Global-Skills aus seeded Audit-Daten, liefert Verdict-Labels, filtert composed-Placeholder korrekt als INSUFFICIENT_DATA
- [x] Model-aware Coverage Threshold: 5 Prioritäts-Ebenen unit-getestet + E2E gegen Kimi-Family (threshold 4.5 blockt coverage_score=4)
- [x] Migration 015 skill_extensions: `skill_type TEXT` + `assets JSONB` auf `agent_skills` (2026-04-16)
- [x] Seed setzt `api_version='v1'`, `skill_type` korrekt (`memory-usage`=general, rest=task_specific), `assets={}` (2026-04-16)
- [x] `user_skill_preferences` Cutover: `db_state.py` liest aus neuer Tabelle (JOIN), Fallback auf Legacy. `control/skills.py:patch_skill` schreibt in `user_skill_preferences` (UUID-Lookup). (2026-04-16)
- [x] General/Task-Specific Split: `memory-usage` erscheint im Prompt auch bei query='bitcoin stop loss' (unrelatiert). Finder rankt nur task_specific Skills. (2026-04-16)
- [x] Harness-Proposer liest SKILL_* Events + Trigger-Quality als Input (exec-harness Stream 3, 2026-04-16)
- [x] Harness-Scorer trackt `skills_loaded` + `skill_events` pro Session (2026-04-16)
- [x] Search-Set erweitert auf 15 Queries mit `expected_skills[]` (2026-04-16)
- [x] PostgresSpanProcessor in `agent/tracing.py` — OTel Spans persistent in `agent.traces`+`agent.spans` (`AGENT_PERSIST_TRACES=1`) (2026-04-16)
- [x] `agent/graph/runner.py` erstellt `agent.sessions` Row bei Agent-Start, updated bei Completion/Error (2026-04-16)
- [ ] `AGENT_SKILL_REFINEMENT=true` gegen echtes LLM (LiteLLM/Provider) — bisher nur mocked
- [ ] `AGENT_SKILL_ITERATIVE_SEARCH=1` gegen echtes LLM — bisher nur mocked
- [ ] `scripts/refine_skills_offline.py` gegen echtes LLM — bisher nur mocked
- [ ] Trigger-Quality CLI gegen echte Production-Audit-Daten (aktuell nur Smoke)
- [ ] Pareto-Frontier mit > 20 Usage-Events verifiziert (aktuell Smoke-Daten)
- [ ] Model-aware Thresholds empirisch validiert / tuned (aktuelle Defaults sind Paper-Interpretation, nicht gemessen)

**Offene Punkte (bewusst vertagt):**

- ~~Trigger-Descriptions der 4 globalen Skills schaerfen~~ → erledigt (Use-When Style, 2026-04-15)
- Team/Personal aus DB statt Dateisystem nur bei echtem Bedarf migrieren
- ~~`refiner.py` + Feature-Flag noch nicht implementiert~~ → erledigt (compose + per_skill Mode, `AGENT_SKILL_REFINEMENT` Flag, 2026-04-15)
- ~~Hindsight-Feedback / Promotion / Pareto nur dokumentiert, nicht verdrahtet~~ → Pareto gebaut (`agent/skills/pareto.py`, 2026-04-15); Hindsight-Feedback + Promotion bleiben offen (Phase 3a/3b)
- Umstellung von `agent.skills_state` auf `user_skill_preferences` erst nach Runtime-/UI-Migration
- `assets JSONB` Spalte auf `agent_skills` fuer Scripts/Examples/Templates (diskutiert, noch nicht migriert)
- General always-load vs Task-Specific retrieval-gated Split (SkillRL §3.2, Ablation: -13% ohne) — `skill_type` Feld + Loader-Trennung
- Differential Distillation: evolver.py auf Success+Failure erweitern statt nur Failures (SkillRL §3.1)
- Anthropic `skill-creator` Meta-Skill-Prompt in offline_refiner integrieren (Skills Wild §4.1)
- With/Without A/B-Loop im offline_refiner (Skills Wild §4.1 full process) — aktuell single-pass
- Harness-Optimierung → **nicht exec-skills Scope, sondern [`exec-harness.md`](./exec-harness.md)**
