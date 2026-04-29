"""CLI for Feature 016 Meta-Harness scenario runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from meta_harness.proposer import ENABLE_EXTERNAL_LLM_ENV
from meta_harness.scenario_runner import run_runner_parity_file, run_scenario_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="matrix-meta-harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a scenario JSON file")
    run.add_argument("path", type=Path)
    run.add_argument("--max-scenarios", type=int, default=0)
    run.add_argument("--run-id", default="")
    run.add_argument("--candidate-id", default="baseline")
    run.add_argument("--user-id", default="anonymous")
    run.add_argument("--model", default="")
    run.add_argument("--system-prompt-override", default="")
    run.add_argument(
        "--agent-url",
        default="",
        help="Run through a live agent service, e.g. http://127.0.0.1:8094",
    )
    run.add_argument(
        "--runner-variant",
        choices=("dispatcher", "langgraph", "simple"),
        default="",
        help="In-process runner variant. Live service runs through its app dispatcher.",
    )
    run.add_argument("--data-dir", type=Path, default=None)

    parity = sub.add_parser("parity", help="Run a scenario file across runner variants")
    parity.add_argument("path", type=Path)
    parity.add_argument("--max-scenarios", type=int, default=0)
    parity.add_argument("--run-id", default="")
    parity.add_argument("--candidate-id-prefix", default="runner-parity")
    parity.add_argument("--user-id", default="anonymous")
    parity.add_argument("--model", default="")
    parity.add_argument("--system-prompt-override", default="")
    parity.add_argument(
        "--variants",
        default="dispatcher,langgraph,simple",
        help="Comma-separated runner variants to compare.",
    )
    parity.add_argument("--data-dir", type=Path, default=None)

    evaluate = sub.add_parser("evaluate", help="Evaluate the search or holdout set")
    evaluate.add_argument("--max-queries", type=int, default=5)
    evaluate.add_argument("--concurrency", type=int, default=4)
    evaluate.add_argument("--no-cache", action="store_true")
    evaluate.add_argument("--split", choices=("search", "holdout"), default="search")
    evaluate.add_argument("--allow-holdout", action="store_true")
    evaluate.add_argument("--eval-id", default="")
    evaluate.add_argument("--system-prompt-override", default="")
    evaluate.add_argument(
        "--runner-variant",
        choices=("dispatcher", "langgraph", "simple"),
        default="dispatcher",
    )

    rag_benchmark = sub.add_parser(
        "rag-benchmark",
        help="Run Feature 022 retrieval candidates and write Meta-Harness artifacts",
    )
    rag_benchmark.add_argument("--run-id", default="")
    rag_benchmark.add_argument("--data-dir", type=Path, default=None)
    rag_benchmark.add_argument("--k", type=int, default=5)
    rag_benchmark.add_argument("--token-budget", type=int, default=1600)
    rag_benchmark.add_argument("--max-hits", type=int, default=8)

    pdf_benchmark = sub.add_parser(
        "pdf-extraction-benchmark",
        help="Run Feature 021 PDF extraction against Markdown ground truth",
    )
    pdf_benchmark.add_argument("--run-id", default="")
    pdf_benchmark.add_argument("--candidate-id", default="pymupdf4llm-pdf-extraction")
    pdf_benchmark.add_argument(
        "--extractor",
        default="pymupdf4llm",
        help="Extractor registry name, e.g. pymupdf4llm or markitdown",
    )
    pdf_benchmark.add_argument(
        "--pdf-path",
        type=Path,
        default=None,
        help="PDF fixture path; defaults to ResearchWatcher small PDF",
    )
    pdf_benchmark.add_argument(
        "--truth-path",
        type=Path,
        default=None,
        help="Ground-truth Markdown path; defaults to PDF path with .md suffix",
    )
    pdf_benchmark.add_argument("--data-dir", type=Path, default=None)

    memory_smoke = sub.add_parser(
        "memory-smoke",
        help="Run deterministic Feature 023 memory/context smoke without provider calls",
    )
    memory_smoke.add_argument("--run-id", default="run-memory-context-smoke")
    memory_smoke.add_argument("--candidate-id", default="memory-context-deterministic")
    memory_smoke.add_argument("--data-dir", type=Path, default=None)

    inner_loop = sub.add_parser(
        "inner-loop",
        help="Run Feature 023 deterministic inner-loop candidate sweep",
    )
    inner_loop.add_argument(
        "--kind",
        choices=("rag",),
        default="rag",
        help="Inner-loop search space to run.",
    )
    inner_loop.add_argument("--run-id", default="")
    inner_loop.add_argument("--data-dir", type=Path, default=None)
    inner_loop.add_argument("--k", type=int, default=5)
    inner_loop.add_argument("--token-budget", type=int, default=1600)
    inner_loop.add_argument("--max-hits", type=int, default=8)
    inner_loop.add_argument(
        "--provider-calls-budget",
        type=int,
        default=0,
        help="Requested live-provider calls. Non-zero values require explicit quota env.",
    )

    propose = sub.add_parser("propose", help="Run proposer guard or external proposer")
    propose.add_argument("--sessions", type=int, default=10)
    propose.add_argument("--model", default="")
    propose.add_argument(
        "--enable-external-llm",
        action="store_true",
        help=f"Set {ENABLE_EXTERNAL_LLM_ENV}=true for this proposer call",
    )

    loop = sub.add_parser("loop", help="Run proposer iterations")
    loop.add_argument("--iterations", type=int, default=1)
    loop.add_argument("--candidates", type=int, default=1)
    loop.add_argument("--sessions", type=int, default=10)
    loop.add_argument("--model", default="")
    loop.add_argument("--eval-max-queries", type=int, default=0)
    loop.add_argument("--eval-concurrency", type=int, default=2)
    loop.add_argument(
        "--enable-external-llm",
        action="store_true",
        help=f"Set {ENABLE_EXTERNAL_LLM_ENV}=true for this proposer loop",
    )

    decide = sub.add_parser("decide", help="Record keep/discard/defer decision")
    decide.add_argument("--run-id", required=True)
    decide.add_argument("--candidate-id", required=True)
    decide.add_argument("--decision", choices=("keep", "discard", "defer"), required=True)
    decide.add_argument("--rationale", required=True)
    decide.add_argument("--metrics-json", default="{}")
    decide.add_argument("--follow-up", default="")
    decide.add_argument("--data-dir", type=Path, default=None)

    sub.add_parser("pareto", help="Show Pareto frontier summary")

    history = sub.add_parser("history", help="Show recent candidate decisions")
    history.add_argument("--limit", type=int, default=50)
    history.add_argument("--data-dir", type=Path, default=None)
    return parser


async def _main_async(args: argparse.Namespace) -> dict:
    _load_env_files()
    if args.command == "run":
        kwargs = {
            "max_scenarios": args.max_scenarios,
            "run_id": args.run_id or None,
            "candidate_id": args.candidate_id,
            "user_id": args.user_id,
            "model": args.model,
            "system_prompt_override": args.system_prompt_override,
            "agent_url": args.agent_url,
            "runner_variant": args.runner_variant,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return await run_scenario_file(args.path, **kwargs)
    if args.command == "parity":
        variants = tuple(
            value.strip() for value in str(args.variants).split(",") if value.strip()
        )
        kwargs = {
            "max_scenarios": args.max_scenarios,
            "run_id": args.run_id or None,
            "candidate_id_prefix": args.candidate_id_prefix,
            "user_id": args.user_id,
            "model": args.model,
            "system_prompt_override": args.system_prompt_override,
            "variants": variants,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return await run_runner_parity_file(args.path, **kwargs)
    if args.command == "evaluate":
        from meta_harness.evaluator import evaluate_search_set

        return await evaluate_search_set(
            system_prompt_override=args.system_prompt_override,
            max_queries=args.max_queries,
            eval_id=args.eval_id or None,
            concurrency=args.concurrency,
            use_cache=not args.no_cache,
            split=args.split,
            allow_holdout=args.allow_holdout,
            runner_variant=args.runner_variant,
        )
    if args.command == "rag-benchmark":
        from meta_harness.retrieval_benchmark import run_retrieval_benchmark

        kwargs = {
            "run_id": args.run_id or None,
            "k": args.k,
            "token_budget": args.token_budget,
            "max_hits": args.max_hits,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return await run_retrieval_benchmark(**kwargs)
    if args.command == "pdf-extraction-benchmark":
        from meta_harness.extraction_benchmark import (
            DEFAULT_PDF_PATH,
            run_pdf_extraction_benchmark,
        )

        pdf_path = args.pdf_path or DEFAULT_PDF_PATH
        truth_path = args.truth_path or pdf_path.with_suffix(".md")
        kwargs = {
            "pdf_path": pdf_path,
            "truth_path": truth_path,
            "run_id": args.run_id or None,
            "candidate_id": args.candidate_id,
            "extractor_name": args.extractor,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return await run_pdf_extraction_benchmark(**kwargs)
    if args.command == "memory-smoke":
        from meta_harness.memory_context_smoke import run_memory_context_smoke

        kwargs = {
            "run_id": args.run_id,
            "candidate_id": args.candidate_id,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_memory_context_smoke(**kwargs)
    if args.command == "inner-loop":
        from meta_harness.inner_loop import run_deterministic_rag_inner_loop

        kwargs = {
            "run_id": args.run_id or None,
            "k": args.k,
            "token_budget": args.token_budget,
            "max_hits": args.max_hits,
            "provider_calls_budget": args.provider_calls_budget,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return await run_deterministic_rag_inner_loop(**kwargs)
    if args.command == "propose":
        from meta_harness.proposer import propose

        if args.enable_external_llm:
            os.environ[ENABLE_EXTERNAL_LLM_ENV] = "true"
        return await propose(model=args.model, last_n_sessions=args.sessions)
    if args.command == "loop":
        from meta_harness.proposer import propose_loop

        if args.enable_external_llm:
            os.environ[ENABLE_EXTERNAL_LLM_ENV] = "true"
        results = await propose_loop(
            iterations=args.iterations,
            candidates_per_iter=args.candidates,
            model=args.model,
            last_n_sessions=args.sessions,
            eval_max_queries=args.eval_max_queries,
            eval_concurrency=args.eval_concurrency,
        )
        return {"iterations": len(results), "proposals": results}
    if args.command == "decide":
        from meta_harness.decisions import record_candidate_decision

        metrics = json.loads(args.metrics_json or "{}")
        if not isinstance(metrics, dict):
            raise ValueError("--metrics-json must decode to an object")
        kwargs = {
            "run_id": args.run_id,
            "candidate_id": args.candidate_id,
            "decision": args.decision,
            "rationale": args.rationale,
            "metrics": metrics,
            "follow_up": args.follow_up,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return record_candidate_decision(**kwargs).as_dict()
    if args.command == "pareto":
        from meta_harness.pareto import get_frontier_summary

        return get_frontier_summary()
    if args.command == "history":
        from meta_harness.decisions import load_candidate_decisions

        kwargs = {"limit": args.limit}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        decisions = load_candidate_decisions(**kwargs)
        return {"decisions": decisions, "total": len(decisions)}
    raise SystemExit(f"unknown command: {args.command}")


def _load_env_files() -> None:
    """Mirror service env loading for standalone harness CLI commands."""
    try:
        from dotenv import load_dotenv
    except Exception:  # noqa: BLE001
        return
    explicit_env = dict(os.environ)
    cwd = Path.cwd()
    load_dotenv(cwd / ".env", override=False)
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    load_dotenv(cwd / f".env.{app_env}", override=True)
    # CLI-supplied environment must win over repo env files so harness runs can
    # intentionally test provider, memory, timeout and runner variants.
    os.environ.update(explicit_env)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = asyncio.run(_main_async(args))
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
