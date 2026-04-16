# Auto-RAG-Optimizer

Autonomous RAG configuration optimizer inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch). Drop your documents in a folder, provide your API key, and let it run overnight to find the perfect RAG settings.

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                       │
│                                                      │
│  1. Read research_log.md (past experiments)          │
│  2. LLM Researcher proposes new config.json          │
│  3. Run RAG pipeline (index + answer questions)      │
│  4. Evaluate answers (Faithfulness + Relevance)      │
│  5. Log results → research_log.md                    │
│  6. Keep best config → best_config.json              │
│  7. Sleep → repeat                                   │
└─────────────────────────────────────────────────────┘
```

The LLM acts as an autonomous researcher — it reads the experiment history, identifies trends, and proposes new configurations to test. Good results are kept, bad ones are discarded. Over hours of running, it converges on the optimal RAG setup for your specific documents and questions.

## Project Structure

```
auto-rag-optimizer/
├── orchestrator.py       # Core autonomous loop engine
├── rag_pipeline.py       # Modular RAG: load docs, index, answer
├── evaluator.py          # RAGAS / LLM-as-judge scoring
├── config.json           # Current experiment configuration
├── research_log.md       # Full experiment history (LLM-readable)
├── test_questions.jsonl  # Your evaluation questions
├── docs/                 # Put your PDF/TXT/MD documents here
├── .env                  # API keys (create from .env.example)
├── requirements.txt      # Python dependencies
└── pyproject.toml        # Project metadata
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up your API key

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Add your documents

Place your `.pdf`, `.txt`, or `.md` files in the `docs/` folder.

### 4. Add your test questions

Edit `test_questions.jsonl` — one JSON object per line:

```jsonl
{"question": "What is the refund policy?", "ground_truth": "30-day money back guarantee"}
{"question": "How do I reset my password?", "ground_truth": ""}
```

The `ground_truth` field is optional. If provided, it enables reference-based metrics.

### 5. Run

```bash
# Run indefinitely (Ctrl+C to stop)
python orchestrator.py

# Run exactly 20 experiments
python orchestrator.py --max-runs 20

# Custom interval between experiments (seconds)
python orchestrator.py --interval 60
```

## What Gets Tuned

| Parameter | Range | Description |
|---|---|---|
| `chunk_size` | 128–2048 | Document chunk size in characters |
| `chunk_overlap` | 0–512 | Overlap between chunks |
| `top_k` | 1–20 | Number of retrieved chunks |
| `embedding_model` | 3 options | OpenAI embedding model |
| `llm_model` | 4 options | OpenAI chat model |
| `temperature` | 0.0–1.0 | LLM generation temperature |
| `search_type` | similarity, threshold | Retrieval strategy |
| `splitter` | recursive, character | Text splitting strategy |

## Output Files

- **`research_log.md`** — Full experiment history with all configs and scores
- **`best_config.json`** — The best configuration found so far
- **`orchestrator.log`** — Detailed runtime log

## Evaluation Metrics

- **Faithfulness** — Is the answer grounded in the retrieved context? (0–1)
- **Answer Relevance** — Does the answer address the question? (0–1)
- **Average Score** — Mean of the above two metrics

Uses [RAGAS](https://docs.ragas.io/) when available, with an automatic fallback to LLM-as-a-judge scoring.

## Running with GitHub Actions

Run the optimizer automatically in the cloud — no server needed. Each trigger runs one experiment, commits results back, and the next trigger picks up where it left off.

### Setup

1. **Push this project to a GitHub repo**

2. **Add your API key as a repository secret**
   - Go to **Settings → Secrets and variables → Actions**
   - Add `OPENAI_API_KEY` with your key

3. **Add documents to `docs/`** and commit them

4. **Enable the workflow**
   - The workflow at `.github/workflows/optimize.yml` runs every 10 minutes by default
   - You can also trigger manually from **Actions → Auto-RAG-Optimizer → Run workflow**

### How It Works

```
┌─ GitHub Actions (cron every 10 min) ──────────────┐
│  1. Checkout repo (research_log.md = state)        │
│  2. Install deps + restore FAISS index             │
│  3. python orchestrator.py --max-runs 1            │
│  4. Generate charts                                │
│  5. Commit results back to repo                    │
│  6. "[skip ci]" prevents infinite trigger loops     │
└────────────────────────────────────────────────────┘
```

- **State is the repo itself** — `research_log.md`, `best_config.json`, and `charts/` are committed after each run
- **FAISS index** is cached via GitHub Actions artifacts (avoids re-embedding every run)
- **Concurrency lock** prevents overlapping runs
- **`[skip ci]`** in commit message prevents the push from re-triggering the workflow

### Customizing the Schedule

Edit the cron in `.github/workflows/optimize.yml`:

```yaml
schedule:
  - cron: '*/10 * * * *'   # every 10 minutes (default)
  - cron: '*/30 * * * *'   # every 30 minutes
  - cron: '0 * * * *'      # every hour
```

### Running Multiple Experiments Per Trigger

Use manual dispatch with a custom count:
- Go to **Actions → Run workflow → Set `max_runs` to e.g. `5`**

Or change the default in the workflow file.

### Cost Estimate

Each experiment uses ~2–4 API calls (proposal + RAG + evaluation). With `gpt-4o-mini`:
- ~$0.01–0.03 per experiment
- 144 runs/day (every 10 min) ≈ **$1.50–4.50/day**

## Tips

- **More questions = better signal.** Add 10–20+ diverse questions for reliable scoring.
- **Include ground truths** when possible for more accurate evaluation.
- **Let it run overnight.** Each experiment takes 1–3 minutes. In 10 hours you get 200–600 experiments.
- **Check `research_log.md`** to see trends and understand what the optimizer is learning.
- **GitHub Actions free tier** gives 2,000 minutes/month — enough for ~200 experiments.

## License

MIT
