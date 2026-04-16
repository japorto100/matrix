# Benchmark Coverage

Ziel: klar trennen zwischen
- bereits vorhandenen Upstream-Benchmarks
- fehlenden Benchmarks je System
- dem gemeinsamen Matrix-/Fusion-Harness in diesem Repo

## Native Upstream Coverage

| Benchmark | MemPalace | Hindsight | Anmerkung |
|---|---|---|---|
| LongMemEval | `native` | `native` | beide haben eigene Runner |
| LoCoMo | `native` | `native` | beide haben eigene Runner |
| ConvoMem | `native` | `fehlt lokal` | fuer Hindsight hier noch kein lokaler Runner |
| MemBench | `native` | `AMB / extern` | Hindsight nennt es im AMB, aber nicht als lokalen Runner im Submodul |
| LifeBench | `fehlt lokal` | `AMB / extern` | eher Hindsight-/AMB-Seite |
| PersonaMem | `fehlt lokal` | `AMB / extern` | eher Hindsight-/AMB-Seite |
| MemoryArena | `fehlt lokal` | `fehlt lokal` | agentischer Top-Level Benchmark, gemeinsamer Harness noetig |

## Was dieses Repo jetzt ergaenzt

1. `sample_shared_corpus.json`
   Ein gemeinsamer Mini-Korpus fuer beide Systeme.

2. `load_benchmark_corpus.py`
   Laedt denselben Korpus in Hindsight und/oder MemPalace.

3. `run_hindsight_eval.py`
   Unterstuetzt jetzt `expected_refs` / `retrieved_refs`.

4. `run_mempalace_eval.py`
   Arbeitet bereits mit kanonischen `source_file#chunk`-Referenzen.

5. `run_fusion_eval.py`
   Benchmark fuer den kombinierten Read-Pfad (`memory_fusion/`).

6. `aggregate_memory_suite.py`
   Vergleicht mehrere Runs (`hindsight`, `mempalace`, `fusion`) zusammen.

7. `lokaler smoke`
   Der Shared-Corpus wurde einmal komplett gegen `hindsight`, `mempalace` und
   `fusion` durchlaufen; die aktuelle Aggregation liegt in `.tmp/suite-shared.json`.

8. `long-context smoke`
   `run_long_context_smoke.py` erzeugt ~100k+ Kontext und misst getrennt:
   - `summary` route
   - `verbatim` route
   - `fusion` route

   Der Lauf zeigt nicht nur Ref-Recall, sondern auch `evidence_hit_rate`.
   Bei lokalem `summary_llm_provider=none` laufen Summary und Verbatim aktuell
   beide chunk-/verbatim-nah und erreichen daher dieselben Metriken. Mit echtem
   LLM-backed Summary-Pfad kann derselbe Harness spaeter die erwarteten
   Unterschiede wieder sichtbar machen.

   Neu dazu:
   - `--skip-retain` / `--bank-id` fuer Recall-only-Reuse
   - `--session-count`, `--max-queries`, `--routes` fuer schnellere Teil-Smokes

9. `public benchmark adapter prep`
   - `prepare_convomem_adapter.py`
   - `prepare_memoryarena_adapter.py`

   Beide bereiten externe Benchmark-Daten auf das gemeinsame lokale
   `corpus + queries`-Schema vor.

## Empfehlung fuer die Reihenfolge

1. `native sanity`
   - MemPalace: kleiner LongMemEval/LoCoMo-Run
   - Hindsight: kleiner LongMemEval/LoCoMo-Run

2. `shared matrix corpus`
   - derselbe Korpus
   - dieselben Queries
   - `hindsight` vs `mempalace` vs `fusion`

3. `long-context smoke`
   - ~100k+ Kontext
   - Quote vs Gist
   - `summary` vs `verbatim` vs `fusion`

4. `missing public benchmark adapters`
   - echte Datensatz-Verdrahtung fuer `ConvoMem`
   - echte Datensatz-Verdrahtung fuer `MemoryArena`

5. `agentic mode`
   - fixes LLM ueber LiteLLM/OpenRouter
   - gleiches Modell fuer alle Systeme

## Wichtig

`MemoryArena` ist der beste Endtest fuer `fusion`, aber nicht der erste.
Vorher muss der gemeinsame Read-/Ground-Truth-Pfad auf einem identischen Korpus
stehen, sonst misst man Agent-Stack-Unterschiede statt Memory-Systeme.
