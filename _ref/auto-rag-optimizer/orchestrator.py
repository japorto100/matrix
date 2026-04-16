"""
Orchestrator - the core autonomous engine for Auto-RAG-Optimizer.
Reads research_log.md, asks an LLM to propose new configs, runs the RAG
pipeline + evaluation, logs results, and loops indefinitely.

Usage:
    python orchestrator.py                  # run with defaults
    python orchestrator.py --max-runs 50    # stop after 50 experiments
    python orchestrator.py --interval 60    # 60s pause between runs
"""

import json
import os
import sys
import time
import copy
import logging
import argparse
import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from rag_pipeline import load_config, run_pipeline, CONFIG_PATH, get_token_usage, estimate_cost
from evaluator import run_evaluation
from visualizer import generate_all_charts

load_dotenv()

logger = logging.getLogger(__name__)

# OpenRouter client for researcher LLM
OPENROUTER_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    timeout=60.0,
)

BASE_DIR = Path(__file__).resolve().parent
RESEARCH_LOG_PATH = BASE_DIR / "research_log.md"
CONFIG_PATH_ORC = BASE_DIR / "config.json"
BEST_CONFIG_PATH = BASE_DIR / "best_config.json"

PARAM_BOUNDS = {
    "chunk_size": {"min": 128, "max": 2048, "type": "int"},
    "chunk_overlap": {"min": 0, "max": 512, "type": "int"},
    "top_k": {"min": 1, "max": 20, "type": "int"},
    "temperature": {"min": 0.0, "max": 1.0, "type": "float"},
    "embedding_model": {
        "type": "enum",
        "values": [
            "qwen/qwen3-embedding-8b",
        ],
    },
    "llm_model": {
        "type": "enum",
        "values": [
            "qwen/qwen3.5-flash-02-23",
            "qwen/qwen3.5-122b-a10b",
            "nvidia/nemotron-3-nano-30b-a3b:free",
        ],
    },
    "search_type": {
        "type": "enum",
        "values": ["similarity", "similarity_score_threshold"],
    },
    "splitter": {
        "type": "enum",
        "values": ["recursive", "character"],
    },
}

RESEARCHER_SYSTEM_PROMPT = (
    "You are an expert RAG systems researcher. Your goal is to find the optimal "
    "RAG configuration that maximizes both Faithfulness and Answer Relevance.\n\n"
    "You are given the full experiment history below. Analyze the trends:\n"
    "- Which parameter changes improved scores?\n"
    "- Which hurt scores?\n"
    "- What hasn't been tried yet?\n\n"
    "Propose ONE new configuration as a JSON object. You MUST include ALL of these keys:\n"
    "  chunk_size, chunk_overlap, top_k, embedding_model, llm_model, temperature, "
    "search_type, splitter\n\n"
    "Parameter bounds:\n{bounds}\n\n"
    "RULES:\n"
    "1. Output ONLY valid JSON. No markdown, no explanation, no commentary.\n"
    "2. chunk_overlap must be strictly less than chunk_size.\n"
    "3. Vary at most 2-3 parameters from the current best to isolate effects.\n"
    "4. Be creative but systematic. If small changes plateau, try bigger shifts.\n"
    "5. Never repeat an exact configuration that has already been tested."
)


def read_research_log() -> str:
    if not RESEARCH_LOG_PATH.exists():
        return ""
    return RESEARCH_LOG_PATH.read_text()


def get_next_experiment_id(log_text: str) -> int:
    max_id = -1
    for line in log_text.splitlines():
        line = line.strip()
        if (
            line.startswith("|")
            and not line.startswith("| experiment_id")
            and not line.startswith("|---")
        ):
            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]
            if parts:
                try:
                    eid = int(parts[0])
                    max_id = max(max_id, eid)
                except ValueError:
                    pass
    return max_id + 1


def propose_new_config(log_text: str, current_config: dict) -> dict:
    bounds_str = json.dumps(PARAM_BOUNDS, indent=2)
    system_prompt = RESEARCHER_SYSTEM_PROMPT.format(bounds=bounds_str)

    user_msg = (
        "## Current Best Configuration\n"
        "```json\n"
        f"{json.dumps(current_config, indent=2)}\n"
        "```\n\n"
        "## Experiment History\n"
        f"{log_text}\n\n"
        "Propose the next experiment configuration as a JSON object."
    )

    response = OPENROUTER_CLIENT.chat.completions.create(
        model="qwen/qwen3.5-flash-02-23",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        extra_body={"reasoning": {"effort": "none"}},
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n", 1)
        raw = lines[1] if len(lines) > 1 else raw[3:]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    proposed = json.loads(raw)
    validated = validate_config(proposed, current_config)
    return validated


def validate_config(proposed: dict, fallback: dict) -> dict:
    validated = copy.deepcopy(fallback)

    for key, bounds in PARAM_BOUNDS.items():
        if key not in proposed:
            continue

        value = proposed[key]

        if bounds["type"] == "int":
            try:
                value = int(value)
                value = max(bounds["min"], min(bounds["max"], value))
            except (ValueError, TypeError):
                value = fallback.get(key)
        elif bounds["type"] == "float":
            try:
                value = float(value)
                value = max(bounds["min"], min(bounds["max"], value))
                value = round(value, 2)
            except (ValueError, TypeError):
                value = fallback.get(key)
        elif bounds["type"] == "enum":
            if value not in bounds["values"]:
                value = fallback.get(key)

        validated[key] = value

    if validated["chunk_overlap"] >= validated["chunk_size"]:
        validated["chunk_overlap"] = max(0, validated["chunk_size"] // 4)

    return validated


def save_config(config: dict) -> None:
    with open(CONFIG_PATH_ORC, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Config saved: {json.dumps(config)}")


def append_to_research_log(config: dict, scores: dict, status: str = "ok",
                          token_usage: dict | None = None,
                          cost: dict | None = None) -> None:
    total_tokens = 0
    if token_usage:
        total_tokens = sum(token_usage.values())
        eval_tokens = scores.get("_eval_tokens", {})
        total_tokens += eval_tokens.get("total_tokens", 0)
    cost_usd = cost.get("total_cost_usd", 0.0) if cost else 0.0

    row = (
        f"| {config.get('experiment_id', '?')} "
        f"| {config.get('chunk_size', '')} "
        f"| {config.get('chunk_overlap', '')} "
        f"| {config.get('top_k', '')} "
        f"| {config.get('embedding_model', '')} "
        f"| {config.get('llm_model', '')} "
        f"| {config.get('temperature', '')} "
        f"| {config.get('search_type', '')} "
        f"| {config.get('splitter', '')} "
        f"| {scores.get('faithfulness', 0.0)} "
        f"| {scores.get('answer_relevance', 0.0)} "
        f"| {scores.get('avg_score', 0.0)} "
        f"| {total_tokens} "
        f"| ${cost_usd:.4f} "
        f"| {status} |"
    )
    with open(RESEARCH_LOG_PATH, "a") as f:
        f.write(row + "\n")
    logger.info(
        f"Logged experiment {config.get('experiment_id')}: "
        f"avg_score={scores.get('avg_score')}, tokens={total_tokens}, cost=${cost_usd:.4f}"
    )


def update_best_config(config: dict, scores: dict) -> None:
    best = copy.deepcopy(config)
    best["_scores"] = scores
    best["_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(BEST_CONFIG_PATH, "w") as f:
        json.dump(best, f, indent=2)
    logger.info(f"New best config saved (avg_score={scores['avg_score']})")


def run_experiment(config: dict) -> dict[str, float]:
    save_config(config)
    logger.info(f"=== Experiment {config['experiment_id']} START ===")

    try:
        run_pipeline(config)
        scores = run_evaluation(config)
        scores["_pipeline_tokens"] = get_token_usage()
        return scores
    except Exception as e:
        logger.error(
            f"Experiment {config['experiment_id']} FAILED: {e}", exc_info=True
        )
        return {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "avg_score": 0.0,
            "_error": str(e),
        }


def orchestrate(max_runs: int = 0, interval: int = 30) -> None:
    best_avg_score = -1.0
    best_config = None
    run_count = 0

    logger.info("=" * 60)
    logger.info("Auto-RAG-Optimizer starting")
    logger.info(f"Max runs: {'unlimited' if max_runs == 0 else max_runs}")
    logger.info(f"Interval: {interval}s between experiments")
    logger.info("=" * 60)

    # --- Run 0: Baseline with default config ---
    log_text = read_research_log()
    config = load_config()
    next_id = get_next_experiment_id(log_text)

    if next_id == 0:
        logger.info("Running baseline experiment with default config...")
        config["experiment_id"] = 0
        scores = run_experiment(config)
        pipeline_tokens = scores.get("_pipeline_tokens", {})
        cost = estimate_cost(pipeline_tokens, config)
        scores["_cost"] = cost
        status = "crash" if "_error" in scores else "baseline"
        append_to_research_log(config, scores, status, pipeline_tokens, cost)
        best_avg_score = scores.get("avg_score", 0.0)
        best_config = copy.deepcopy(config)
        update_best_config(best_config, scores)
        run_count += 1
        logger.info(f"Baseline avg_score: {best_avg_score}")
    else:
        logger.info(f"Resuming from experiment {next_id}. Reading best so far...")
        if BEST_CONFIG_PATH.exists():
            with open(BEST_CONFIG_PATH, "r") as f:
                saved = json.load(f)
            best_avg_score = saved.get("_scores", {}).get("avg_score", 0.0)
            best_config = {
                k: v for k, v in saved.items() if not k.startswith("_")
            }
        else:
            best_config = copy.deepcopy(config)

    # --- Main experiment loop ---
    while True:
        if 0 < max_runs <= run_count:
            logger.info(f"Reached max_runs={max_runs}. Stopping.")
            break

        log_text = read_research_log()
        next_id = get_next_experiment_id(log_text)

        # Ask the LLM researcher for a new config
        logger.info("Asking LLM researcher for next config...")
        try:
            new_config = propose_new_config(log_text, best_config or config)
        except Exception as e:
            logger.error(f"Config proposal failed: {e}. Retrying after interval.")
            time.sleep(interval)
            continue

        new_config["experiment_id"] = next_id

        # Run the experiment
        scores = run_experiment(new_config)
        has_error = "_error" in scores

        pipeline_tokens = scores.get("_pipeline_tokens", {})
        cost = estimate_cost(pipeline_tokens, new_config)
        scores["_cost"] = cost

        if has_error:
            status = "crash"
            append_to_research_log(new_config, scores, status, pipeline_tokens, cost)
            logger.warning(
                f"Experiment {next_id} crashed: {scores.get('_error', 'unknown')}"
            )
        else:
            new_avg = scores.get("avg_score", 0.0)
            if new_avg > best_avg_score:
                status = "keep"
                best_avg_score = new_avg
                best_config = copy.deepcopy(new_config)
                update_best_config(best_config, scores)
                logger.info(
                    f"Experiment {next_id}: IMPROVEMENT! "
                    f"avg_score {new_avg:.4f} > previous best"
                )
            else:
                status = "discard"
                logger.info(
                    f"Experiment {next_id}: no improvement "
                    f"(avg_score={new_avg:.4f} <= best={best_avg_score:.4f})"
                )

            append_to_research_log(new_config, scores, status, pipeline_tokens, cost)

        run_count += 1
        logger.info(
            f"Completed {run_count} experiments. "
            f"Best avg_score: {best_avg_score:.4f}"
        )

        # Auto-generate charts after each experiment
        try:
            generate_all_charts(html=True)
        except Exception as e:
            logger.warning(f"Chart generation failed: {e}")

        logger.info(f"Sleeping {interval}s before next experiment...")
        time.sleep(interval)

    # Final summary
    logger.info("=" * 60)
    logger.info("AUTO-RAG-OPTIMIZER COMPLETE")
    logger.info(f"Total experiments: {run_count}")
    logger.info(f"Best avg_score: {best_avg_score:.4f}")
    if best_config:
        logger.info(f"Best config: {json.dumps(best_config, indent=2)}")
    logger.info(f"Full log: {RESEARCH_LOG_PATH}")
    logger.info(f"Best config file: {BEST_CONFIG_PATH}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Auto-RAG-Optimizer Orchestrator")
    parser.add_argument(
        "--max-runs",
        type=int,
        default=int(os.getenv("MAX_EXPERIMENTS", "0")),
        help="Max experiments to run (0 = unlimited)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("LOOP_INTERVAL", "30")),
        help="Seconds between experiments",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(BASE_DIR / "orchestrator.log"),
        ],
    )

    orchestrate(max_runs=args.max_runs, interval=args.interval)


if __name__ == "__main__":
    main()
