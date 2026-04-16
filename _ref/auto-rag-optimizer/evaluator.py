"""
Evaluator module for Auto-RAG-Optimizer.
Scores RAG answers using RAGAS metrics (Faithfulness, Answer Relevance)
with a fallback to LLM-as-a-judge when RAGAS is unavailable.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.callbacks.manager import get_openai_callback
from openai import OpenAI

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
EVAL_LLM_MODEL = "qwen/qwen3.5-flash-02-23"

# OpenRouter client for LLM-as-judge
def get_openrouter_client():
    """Get OpenRouter client with proper API key loading."""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        timeout=60.0,
    )

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = BASE_DIR / "results.json"
SCORES_PATH = BASE_DIR / "scores.json"


def load_results() -> dict:
    """Load pipeline results from results.json."""
    with open(RESULTS_PATH, "r") as f:
        return json.load(f)


def evaluate_with_ragas(results: dict, config: dict) -> dict[str, float]:
    """
    Evaluate using the RAGAS library.
    Returns dict with faithfulness and answer_relevance scores.
    """
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy
        from ragas import EvaluationDataset, SingleTurnSample

        samples = []
        for i in range(len(results["questions"])):
            sample = SingleTurnSample(
                user_input=results["questions"][i],
                response=results["answers"][i],
                retrieved_contexts=results["contexts"][i],
            )
            if results["ground_truths"][i]:
                sample.reference = results["ground_truths"][i]
            samples.append(sample)

        eval_dataset = EvaluationDataset(samples=samples)

        llm = ChatOpenAI(
            model=EVAL_LLM_MODEL,
            temperature=0.0,
            openai_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            openai_api_base=OPENROUTER_BASE_URL,
            model_kwargs={"extra_body": {"reasoning": {"effort": "none"}}},
        )
        embeddings = OpenAIEmbeddings(
            model=config.get("embedding_model", "qwen/qwen3-embedding-8b"),
            openai_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            openai_api_base=OPENROUTER_BASE_URL,
        )

        score = evaluate(
            dataset=eval_dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=llm,
            embeddings=embeddings,
        )

        scores = {
            "faithfulness": round(float(score["faithfulness"]), 4),
            "answer_relevance": round(float(score["answer_relevancy"]), 4),
        }
        scores["avg_score"] = round(
            (scores["faithfulness"] + scores["answer_relevance"]) / 2, 4
        )

        logger.info(f"RAGAS scores: {scores}")
        return scores

    except Exception as e:
        logger.warning(f"RAGAS evaluation failed: {e}. Falling back to LLM-as-judge.")
        return evaluate_with_llm_judge(results, config)


def evaluate_with_llm_judge(results: dict, config: dict) -> dict[str, float]:
    """
    Fallback evaluator: uses an LLM to score faithfulness and relevance.
    Each QA pair is scored individually, then averaged.
    """
    faithfulness_scores = []
    relevance_scores = []

    for i in range(len(results["questions"])):
        question = results["questions"][i]
        answer = results["answers"][i]
        contexts = results["contexts"][i]
        context_str = "\n---\n".join(contexts) if contexts else "(no context retrieved)"

        # --- Faithfulness ---
        faith_prompt = (
            "You are an evaluation judge. Rate how faithful the answer is to the "
            "provided context. A faithful answer only contains information present "
            "in the context and does not hallucinate.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {question}\n"
            f"Answer: {answer}\n\n"
            "Score from 0.0 (completely unfaithful / hallucinated) to 1.0 "
            "(perfectly faithful). Reply with ONLY the numeric score, nothing else."
        )

        # --- Relevance ---
        rel_prompt = (
            "You are an evaluation judge. Rate how relevant and useful the answer "
            "is to the question asked. A relevant answer directly addresses the "
            "question with specific information.\n\n"
            f"Question: {question}\n"
            f"Answer: {answer}\n\n"
            "Score from 0.0 (completely irrelevant) to 1.0 (perfectly relevant). "
            "Reply with ONLY the numeric score, nothing else."
        )

        try:
            openrouter_client = get_openrouter_client()
            faith_resp = openrouter_client.chat.completions.create(
                model=EVAL_LLM_MODEL,
                messages=[{"role": "user", "content": faith_prompt}],
                temperature=0.0,
                extra_body={"reasoning": {"effort": "none"}},
            )
            faith_score = _parse_score(faith_resp.choices[0].message.content)
            faithfulness_scores.append(faith_score)
        except Exception as e:
            logger.warning(f"Faithfulness scoring failed for Q{i}: {e}")
            faithfulness_scores.append(0.0)

        try:
            openrouter_client = get_openrouter_client()
            rel_resp = openrouter_client.chat.completions.create(
                model=EVAL_LLM_MODEL,
                messages=[{"role": "user", "content": rel_prompt}],
                temperature=0.0,
                extra_body={"reasoning": {"effort": "none"}},
            )
            rel_score = _parse_score(rel_resp.choices[0].message.content)
            relevance_scores.append(rel_score)
        except Exception as e:
            logger.warning(f"Relevance scoring failed for Q{i}: {e}")
            relevance_scores.append(0.0)

    avg_faith = round(sum(faithfulness_scores) / max(len(faithfulness_scores), 1), 4)
    avg_rel = round(sum(relevance_scores) / max(len(relevance_scores), 1), 4)
    avg_score = round((avg_faith + avg_rel) / 2, 4)

    scores = {
        "faithfulness": avg_faith,
        "answer_relevance": avg_rel,
        "avg_score": avg_score,
    }

    logger.info(f"LLM-as-judge scores: {scores}")
    return scores


def _parse_score(text: str) -> float:
    """Extract a float score from LLM response text."""
    text = text.strip()
    # Try to parse the first float-like token
    for token in text.split():
        try:
            score = float(token.rstrip(".,;:"))
            return max(0.0, min(1.0, score))
        except ValueError:
            continue
    logger.warning(f"Could not parse score from: '{text}', defaulting to 0.0")
    return 0.0


def run_evaluation(config: dict | None = None) -> dict[str, float]:
    """
    Main evaluation entry point.
    Loads results.json, scores with RAGAS (or LLM fallback), saves scores.json.
    """
    if config is None:
        from rag_pipeline import load_config
        config = load_config()

    results = load_results()

    n_questions = len(results.get("questions", []))
    if n_questions == 0:
        logger.error("No results to evaluate.")
        return {"faithfulness": 0.0, "answer_relevance": 0.0, "avg_score": 0.0}

    logger.info(f"Evaluating {n_questions} QA pairs...")

    with get_openai_callback() as cb:
        scores = evaluate_with_ragas(results, config)

    eval_tokens = {
        "prompt_tokens": cb.prompt_tokens,
        "completion_tokens": cb.completion_tokens,
        "total_tokens": cb.total_tokens,
    }
    scores["_eval_tokens"] = eval_tokens
    logger.info(
        f"Eval token usage — prompt: {cb.prompt_tokens}, "
        f"completion: {cb.completion_tokens}, total: {cb.total_tokens}"
    )

    # Save scores
    with open(SCORES_PATH, "w") as f:
        json.dump(scores, f, indent=2)

    logger.info(f"Scores saved to {SCORES_PATH}")
    return scores


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    scores = run_evaluation()
    print(f"\nFinal Scores:")
    print(f"  Faithfulness:     {scores['faithfulness']}")
    print(f"  Answer Relevance: {scores['answer_relevance']}")
    print(f"  Average Score:    {scores['avg_score']}")
