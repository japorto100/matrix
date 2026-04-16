# Memory Eval Stacks

Ziel: fuer Memory-Evals nur den Stack hochfahren, der wirklich noetig ist.
Der Python-Code bleibt **lokal auf dem Host**; nur stateful Infra laeuft in
Podman/Docker.

## 1. MemPalace-only Eval

Fuer isolierte MemPalace-Evals braucht es **keine Container**.

Voraussetzungen:
- lokaler Code in `python-backend/`
- `uv sync` fuer Python-Dependencies
- ein Palace oder ein `convo_dir`
- erster Chroma-Start laedt lokal einmal das Default-Embedding-Modell
  (`all-MiniLM-L6-v2`, grob ~80 MB)

Empfohlene Env:

```bash
export AGENT_MEMORY_ENGINE=mempalace
export MEMPALACE_PALACE_PATH="$PWD/python-backend/.tmp/mempalace_eval/dev-palace"
```

Beispiel:

```bash
cd python-backend
uv run python experiments/memory_eval/run_mempalace_eval.py \
  experiments/memory_eval/sample_mempalace_queries.json \
  --out mempalace.json --remine
```

## 2. Minimaler Hindsight Eval Stack

Fuer Recall-Only-Evals braucht Hindsight nur PostgreSQL mit pgvector.
NATS, Go-Appservice, SeaweedFS, Homeserver, Control-UI sind dafuer **nicht**
noetig.

Start:

```bash
podman compose -f docker-compose.memory-eval.yml up -d postgres
```

Host-Env fuer lokalen Python-Code:

```bash
export AGENT_MEMORY_ENGINE=hindsight
export HINDSIGHT_DB_URL=postgresql://postgres:postgres@127.0.0.1:5433/hindsight_dev
export HINDSIGHT_SYNC_TASKS=true
```

## 3. Hindsight Retain / Reflect Eval

Sobald Retain/Reflect mit LLM bewertet werden soll, kommt LiteLLM dazu:

```bash
podman compose -f docker-compose.memory-eval.yml --profile llm up -d
```

Zusatz-Env auf dem Host:

```bash
export LITELLM_BASE_URL=http://127.0.0.1:4000
```

## 4. Voller DevStack

Nur noetig fuer:
- Agent-Chat end-to-end
- exec-15 / exec-19 Verify-Gates
- Go/Python/UI Integration
- NATS-basierte Flows

Dann:
- `docker-compose.yml` verwenden
- Code weiter lokal lassen
- Infra in Podman laufen lassen

Fuer Memory-Themen ist die sinnvolle Staffelung:

1. MemPalace-only lokal
2. Hindsight + Postgres minimal
3. Hindsight + LiteLLM
4. erst dann voller DevStack

## 5. Empfehlung

Fuer die naechste Runde:
- MemPalace Eval lokal fahren
- Hindsight nur mit `postgres` daneben hochziehen
- `litellm` erst zuschalten, wenn wir Retain/Reflect oder echte Agent-Runs messen
- `nats`, `go-appservice`, `seaweedfs`, `tuwunel`, `control-ui` aus den Memory-Evals raushalten
