# Memory Eval — MemPalace vs Hindsight (A/B)

Siehe [`specs/execution/exec-memory.md`](../../../specs/execution/exec-memory.md) §5 (Phasen 1–3).

Stack-Schnitt siehe auch [`STACKS.md`](./STACKS.md):
- MemPalace-only lokal
- Hindsight minimal mit `postgres`
- Hindsight + LiteLLM
- voller DevStack erst fuer end-to-end

Coverage / Gaps siehe [`BENCHMARK_COVERAGE.md`](./BENCHMARK_COVERAGE.md).

## Phase 1 (isolierter MemPalace-Test)

1. Sessions/Transkripte exportieren (Audit/JSONL wo vorhanden).
2. `_ref/mempalace/` lokal ausfuehren — gleiche Fragen wie in Phase 2 vorbereiten.
3. Metriken: Recall-Qualitaet, Latenz, Speicher — **pro Query-Typ** notieren.

### Minimal lauffaehiger MemPalace-Pfad

```bash
uv run python experiments/memory_eval/run_mempalace_eval.py \
  experiments/memory_eval/sample_mempalace_queries.json \
  --out mempalace.json --remine
```

Der Runner importiert das echte Submodul unter `_ref/mempalace/` direkt und
unterstuetzt zwei Modi:
- bestehendes Palace via `palace_path`
- frisches Palace aus Exporten via `convo_dir` (+ optional `--remine`)

Wenn Query-Items `expected_refs` statt `expected_ids` mitgeben, normalisiert der
Runner seine Treffer auf `source_file#chunk_index` und schreibt die internen
Drawer-IDs zusaetzlich nach `retrieved_drawer_ids`. Das ist der sauberste
Zwischenschritt, bis Hindsight und MemPalace ueber dieselbe kanonische
Ground-Truth-Referenz verglichen werden.

## Phase 2 (Hindsight Gegentest)

Gleicher Korpus, gleiche Fragen, Retrieval ueber Hindsight Recall.

### Minimal lauffaehiger Hindsight-Pfad

```bash
uv run python experiments/memory_eval/run_hindsight_eval.py \
  experiments/memory_eval/sample_queries.json \
  --out hindsight.json
```

`sample_queries.json` ist nur ein Schema-/Starter-File. Fuer echte A/B-Evals
muessen `bank_id` + Query-Set auf reale Session-/Corpus-Daten zeigen.

## Phase 3 (Hybrid)

Nur nach Phase 1+2: Verbatim-Store / Fallback bei niedrigem Recall-Score — siehe exec-memory §3.

### Postgres-first `memory_fusion`

`memory_fusion/` ist jetzt der neue Umbaupfad fuer die produktive Fusion:
- Runtime-Basis aus `agent/memory` uebernommen, ohne `agent/memory` direkt anzufassen
- keine produktiven Runtime-Imports aus `_ref/mempalace`
- `FusionMemoryEngine` nutzt zwei Hindsight/Postgres-Baenke:
  - `bank_id__summary`
  - `bank_id__verbatim`
- Summary-Route und Verbatim-Route laufen damit beide auf Postgres/pgvector; die
  lokalen vendorten MemPalace-Bausteine (`query_sanitizer`, Method-of-Loci,
  Provenance-Metadaten) dienen als Verhaltensquelle, nicht als separater
  produktiver Storage-Stack
- Method-of-Loci lebt jetzt im Postgres-Pfad ueber kanonische Metadaten und Tags:
  - `wing`
  - `room`
  - `hall`
  - `closet_id`
  - `drawer_id`
- entsprechende Recall-/List-Filter sind verfuegbar (`wing`, `room`, `hall`,
  `closet`, `drawer`)

### Gemeinsamer Korpus fuer Hindsight / MemPalace / Fusion

1. Gemeinsamen Mini-Korpus laden:

```bash
uv run python experiments/memory_eval/load_benchmark_corpus.py \
  experiments/memory_eval/sample_shared_corpus.json \
  --target both \
  --palace-path .tmp/mempalace_eval/shared-palace \
  --reset-palace
```

2. Hindsight-Run:

```bash
AGENT_MEMORY_ENGINE=hindsight \
HINDSIGHT_DB_URL=postgresql://postgres:postgres@127.0.0.1:5433/hindsight_dev \
HINDSIGHT_SYNC_TASKS=true \
HINDSIGHT_API_LLM_PROVIDER=none \
uv run python experiments/memory_eval/run_hindsight_eval.py \
  experiments/memory_eval/sample_shared_queries.json \
  --out hindsight-shared.json
```

3. MemPalace-Run:

```bash
AGENT_MEMORY_ENGINE=mempalace \
MEMPALACE_PALACE_PATH=.tmp/mempalace_eval/shared-palace \
uv run python experiments/memory_eval/run_mempalace_eval.py \
  experiments/memory_eval/sample_shared_queries.json \
  --out mempalace-shared.json
```

4. Fusion-Run:

```bash
HINDSIGHT_DB_URL=postgresql://postgres:postgres@127.0.0.1:5433/hindsight_dev \
HINDSIGHT_API_LLM_PROVIDER=none \
uv run python experiments/memory_eval/run_fusion_eval.py \
  experiments/memory_eval/sample_shared_queries.json \
  --palace-path .tmp/mempalace_eval/shared-palace \
  --out fusion-shared.json
```

5. Suite aggregieren:

```bash
uv run python experiments/memory_eval/aggregate_memory_suite.py \
  hindsight-shared.json mempalace-shared.json fusion-shared.json \
  --out suite-shared.json
```

Die Suite enthaelt zusaetzlich `eval_classes` fuer `verbatim`, `derived`,
`cross_session` und `forgetting`. Jede Klasse fuehrt dieselben Task-, Quality-,
Efficiency- und Governance-Metriken wie die Top-Level-Summary, damit
Cost/Latency/Provenance-Regressions getrennt von Retrieval Accuracy sichtbar
bleiben.

### Verifizierter Smoke-Stand

Der gemeinsame Mini-Korpus wurde lokal gegen den Minimal-Stack verifiziert:
- `hindsight`: `mean_recall=1.0`
- `mempalace`: `mean_recall=1.0`
- `fusion`: `mean_recall=1.0`

Die zugehoerige Aggregation liegt nach dem Lauf in `python-backend/.tmp/suite-shared.json`.

### Verifizierter Langkontext-Smoke (`memory_fusion`)

Zusatzlich wurde ein groesserer synthetischer Corpus (aktuell `84` Items, also
~100k+ Kontext) gegen die drei Routen gefahren:

```bash
HINDSIGHT_DB_URL=postgresql://postgres:postgres@127.0.0.1:5433/hindsight_dev \
HINDSIGHT_API_LLM_PROVIDER=none \
uv run python experiments/memory_eval/run_long_context_smoke.py \
  --out .tmp/long-context-smoke.json
```

Aktueller Stand aus `/tmp/memory-fusion-long-context-ingest.json`:
- `summary`: `mean_recall=1.0`, `top1_hit_rate=1.0`, `evidence_hit_rate=1.0`
- `verbatim`: `mean_recall=1.0`, `top1_hit_rate=1.0`, `evidence_hit_rate=1.0`
- `fusion`: `mean_recall=1.0`, `top1_hit_rate=1.0`, `evidence_hit_rate=1.0`

Wichtige Einordnung:
- dieser verifizierte Lauf lief lokal mit `summary_llm_provider=none`
- damit forciert Hindsight den Summary-Pfad effektiv in einen chunk-/verbatim-nahen Modus
- deshalb unterscheiden sich die drei Routen in diesem lokalen Run metrisch nicht

Der Runner ist jetzt aber so gebaut, dass bei echtem LLM-backed Summary-Pfad
(`MEMORY_FUSION_SUMMARY_LLM_PROVIDER` gesetzt) dieselbe Eval-Logik die
Route-Unterschiede wieder sichtbar machen kann.

Der Runner unterstuetzt jetzt zusaetzlich:
- `--bank-id` fuer einen festen Ziel-Banknamen
- `--skip-retain` fuer Recall-only-Wiederholungen ohne Re-Embedding
- `--session-count` fuer schnellere/lokale Testgroessen
- `--max-queries` und `--routes ...` fuer schnelle Teil-Smokes

### Verifizierter Reuse-/Recall-only-Pfad

Der Split zwischen Ingest und Recall wurde lokal gegen eine bereits befuellte
Fusion-Bank verifiziert:
- `bank_id=user_eval_long_context_1776292414`
- `skip_retain=true`
- `queries=26`
- `summary`: `mean_recall=1.0`, `top1_hit_rate=1.0`, `evidence_hit_rate=1.0`
- `verbatim`: `mean_recall=1.0`, `top1_hit_rate=1.0`, `evidence_hit_rate=1.0`
- `fusion`: `mean_recall=1.0`, `top1_hit_rate=1.0`, `evidence_hit_rate=1.0`

Damit ist verifiziert:
- ingest/embedding kann separat laufen
- spaetere Runs koennen recall-only wiederverwendet werden
- derselbe Bank funktioniert ueber alle drei Routen

### Public-Benchmark-Adapter vorbereitet

Neu:
- `prepare_convomem_adapter.py`
- `prepare_memoryarena_adapter.py`

Beide Skripte konvertieren Benchmark-Eingaben in das gemeinsame lokale
`corpus + queries`-Schema, damit dieselben Eval-Runner fuer `hindsight`,
`mempalace` und `fusion` verwendet werden koennen.

## Persistenz (optional)

Ergebnisse in `agent.evals` mit `eval_type: memory_ab` — Schema siehe [`specs/execution/exec-18-unified-agent-schema.md`](../../../specs/execution/exec-18-unified-agent-schema.md) Abschnitt „Ergaenzung (Plan 2026-04)“.

## Aggregation / `memory_ab`

Wenn Hindsight- und MemPalace-Ergebnisse bereits als JSON vorliegen, kann
`aggregate_memory_ab.py` einen vergleichbaren Run bauen:

```bash
uv run python experiments/memory_eval/aggregate_memory_ab.py \
  hindsight.json mempalace.json --out result.json --persist
```

Das Script berechnet aktuell:
- `mean_recall`
- `mean_latency_ms`
- `total_token_cost`
- `error_rate`

Offen bleibt aktuell noch die echte Datensatz-Verdrahtung der neuen Adapter an
die jeweiligen Public-Benchmark-Downloads. Fuer den lokalen Shared-Corpus-Pfad
und die vorbereiteten Adapter ist die kanonische Ref-Angleichung jetzt
vorhanden.
