# exec-skills — Skill Discovery, Refinement & Evolution

> Status: Evaluation / Phase 1 implementierbar
> Erstellt: 2026-04-13
> Abhaengigkeiten: exec-10 (Multi-Agent), exec-11 (Hindsight Memory), exec-17 (Harness/Pareto), exec-18 (Schema), exec-ebm (Energy Scoring)
> Referenzen: Skill-Usage Studie (arxiv 2604.04323), SkillRL (arxiv 2602.08234), MemRL (arxiv 2601.03192)
> Hauptprojekt-Docs:
>   - `main_docs/root/AGENT_TOOLS.md` — Tool-Taxonomie, MCP Apps (Sek. 3.3), Memory-Read/Write-Interfaces
>   - `main_docs/root/AGENT_SECURITY.md` — Capability Envelope fuer Skill/Tool-Execution, Tool Proxy

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
| Loader | `agent/skills/loader.py` | 3-Tier SKILL.md Parsing (Global → Team → Personal), Merge, Prompt Injection | Implementiert |
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
| **MemRL** (01/2026) | 2601.03192 | Q-Value-basierte Skill-Auswahl aus Episodic Memory. Zwei-Phasen-Retrieval: semantisch → Q-Value Ranking. | `docs/MemRL_2601.03192.pdf` |

### Papers — Verbundene Systeme (Skills haengen von Memory + Harness ab)

| Paper | Arxiv | Verbindung zu Skills | PDF |
|-------|-------|---------------------|-----|
| **Meta-Harness** (03/2026) | 2603.28052 | Pareto-Frontier Optimierung — gleiche Logik fuer Skill-Ranking (Phase 3c). Harness-as-Code Pattern ermoeglicht Skill-Integration in maschinenlesbaren Config. | `docs/Meta-Harness-2603.28052v1.pdf` |
| **MetaClaw** | — | Skill Generation Versioning (Sec. 3.2) → direkt in `evolver.py`. Deduplication → verhindert doppelte Skills bei gleichem Failure-Pattern. | Referenz in evolver.py |
| **Memory for Autonomous LLM Agents** (03/2026) | 2603.07670 | 5 Memory-Familien Taxonomie. Skills sind **procedural memory** — getrennt von episodic (Hindsight) und semantic (KG). Die fehlende Integration dieser drei ist das Kernproblem. | `docs/Memory_Autonomous_LLM_Agents_2603.07670v1.pdf` |
| **Hindsight** (12/2025) | 2512.12818 | Episodic Memory als Datenquelle fuer Skill-Feedback (Phase 3a). Recall informiert finder.py welche Skills historisch funktioniert haben. | `docs/Hindsight_2512.12818v1.pdf` |
| **Unsupervised Ensemble via EBM** (01/2026) | 2601.20556 | Energy-Based Scoring fuer Multi-Agent Ensemble — uebertragbar auf Skill-Kombinations-Bewertung (Phase 4b). | `docs/Maymon2025_Unsupervised_Ensemble_Deep_EBM.pdf` |

### Zusammenhang der Studien

```
MetaClaw ──→ evolver.py (Skill Generierung + Versioning)
                ↓
Meta-Harness ──→ harness/pareto.py (Pareto Ranking) ──→ Skill Pareto (Phase 3c)
                ↓
Skills in the Wild ──→ finder.py + refiner.py (Retrieval + Refinement)
                ↓
SkillRL ──→ rl_trainer.py (Recursive Skill Evolution, Phase 4a)
                ↓
MemRL ──→ Q-Value Skill Selection aus Episodic Memory (Phase 4c)
                ↓
Hindsight ──→ Episodic Memory als Skill-Feedback Store (Phase 3a)
                ↓
Memory Taxonomy ──→ Skills = Procedural Memory, integriert mit Episodic + Semantic
                ↓
EBM ──→ Energy Scoring fuer Skill-Kombinationen (Phase 4b)
```

### GitHub Repos

| Repo | Nuetzlicher Code |
|------|-----------------|
| [UCSB-NLP-Chang/Skill-Usage](https://github.com/UCSB-NLP-Chang/Skill-Usage) | `search_server/` (BM25 + Semantic + Hybrid), `scripts/query_specific_refinement.py`, `scripts/query_agnostic_refinement.py`, 34k Skill Collection |
| [aiming-lab/SkillRL](https://github.com/aiming-lab/SkillRL) | SkillBank Architektur, Experience-based Distillation, Recursive Evolution |
| find-skills (lokal: `~/.agents/skills/find-skills/`) | Blueprint fuer Skill Discovery Pattern |

---

## 3. Architektur-Entscheidungen

### 3a. Skill Storage: Alles in PostgreSQL

**Dateisystem ist nicht production-viable** bei Multi-User/Multi-Instance:
- Mehrere Container → Dateisystem nicht shared
- Skill-Aenderung braucht Redeploy
- Kein Audit Trail

**Loesung:** Alles in PostgreSQL. Git bleibt Source-of-Truth fuer Entwicklung,
beim Deploy werden Curated Skills in DB geschrieben (Seed Pattern, wie `seed_data.py`).

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

**Entwicklung → Runtime Flow:**
```
Git: agent/skills/global/*.md  →  Deploy: Seed Script  →  PostgreSQL agent_skills
Runtime: loader.py liest NUR aus PostgreSQL
```

**Schema-Referenz:** exec-18 (Unified Agent Schema) — neue Migration fuer `agent_skills` + `user_skill_preferences`.

### 3b. Tier-System: Personal abschaffen, Promotion-Pipeline stattdessen

| Tier | Wer sieht es | Wie entsteht es | Wer entfernt es |
|------|-------------|-----------------|-----------------|
| `global` | Alle User | Curated (Git Seed) ODER automatisch promoted | Pareto-Eviction oder Admin |
| `team` | Team-Mitglieder | Admin weist promoted Skill einem Team zu | Admin |
| `promoted` | Nur der erstellende User | Automatisch aus wiederkehrenden erfolgreichen Refinements | Pareto-Eviction (dominiert → disabled) |

**Personal entfaellt** — ersetzt durch `promoted`. Unterschied: Personal war statisch
(Evolver generiert einmal). Promoted ist datengetrieben (entsteht erst nach wiederholtem Erfolg).

**User kann Skills deaktivieren:** `user_skill_preferences.disabled=true`.
Finder filtert diese vor der Suche raus. Disabled-Count fliesst als Negativ-Signal in Pareto.

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

---

## 6. Paper-Abgleich: Memory for Autonomous Agents (2603.07670v1) — Skill-Relevante Punkte

| Paper-Abschnitt | Thema | Relevanz fuer exec-skills | Massnahme |
|-----------------|-------|--------------------------|-----------|
| **3.1** Procedural Memory | Skills = ausfuehrbarer Code, indiziert nach NL-Beschreibung (Voyager Pattern) | Unser SKILL.md Format ist NL-beschrieben, aber nicht ausfuehrbar | Langfristig: Skills mit ausfuehrbarem Code-Teil (scripts/ Unterordner) |
| **4.5** Policy-Learned Management | AgeMem: Memory Ops (store/retrieve/update/summarize/discard) als RL-Policy | Direkt anwendbar auf Skill-Ops (find/refine/promote/disable/evolve) | Phase 4: SkillRL als Skill-Policy-Learning |
| **6.3** Compositional Skill Reuse | Skills kreativ verketten, nicht nur einzeln nutzen (Voyager: 3.3x Unique Items) | Refiner kann Skills kombinieren, aber kein Composition-Framework | Langfristig: Skill Dependency Graph (Skill A erfordert Skill B als Voraussetzung) |
| **6.6** Schema Drift | Gespeicherte Tool-Usage-Patterns werden ungueltig bei API-Aenderung | Relevant fuer Skill-Feedback (Phase 3a): veraltete Skills. `AGENT_TOOLS.md` Sek. 2 definiert Tool-Taxonomie. | `api_version` Feld auf `agent_skills`. Bei API-Aenderung: Skills mit alter Version flaggen. Tool Proxy aus `AGENT_SECURITY.md` als Enforcement-Punkt. |
| **6.7** Cross-Domain Transfer | Debugging-Skills aus Python fuer Java wiederverwendbar? | Unser Tier-System (promoted → global) ist impliziter Transfer | Skill-Metadata: `transferable: true/false` + Domain-Tags |
| **7.7** Observability | Skill-Usage Logs: welche Skills werden geladen/ignoriert/refined? | **Nicht adressiert** | Skill Operation Log: jeder Find/Refine/Load mit Timestamp + Query + Ergebnis. Basis fuer Pareto-Scoring. |

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

## 7. Naechste Schritte

**Sofort (kein Training):**
- [ ] DB Schema: `agent_skills` + `user_skill_preferences` Tabellen (→ exec-18 Migration)
- [ ] Seed Script: Bestehende 4 Global Skills von Dateisystem in DB
- [ ] Phase 1: `agent/skills/finder.py` (BM25 + Semantic + RRF)
- [ ] `loader.py` anpassen: Liest aus DB statt Dateisystem, nutzt finder bei query
- [ ] Bestehende 4 Global Skills mit besseren Trigger-Descriptions

**Kurzfristig (kein Training, 1 LLM-Call):**
- [ ] Phase 2: `agent/skills/refiner.py` hinter Feature-Flag
- [ ] Testen ob Refinement auf Trading-Skills hilft

**Mittelfristig (nutzt bestehende Infrastruktur):**
- [ ] Phase 3a: Skill-Feedback als Hindsight Retain
- [ ] Phase 3b: Promotion Pipeline (Background Job)
- [ ] Phase 3c: Pareto Ranking fuer Skills (gleiche Logik wie harness/pareto.py)
- [ ] User Skill Disable im Control UI (exec-15)

**Langfristig (braucht Training + Daten):**
- [ ] Phase 4: SkillRL / EBM / MemRL evaluieren
- [ ] Skill-Pool auf 30+ erweitern
