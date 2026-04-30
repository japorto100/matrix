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

    provider_smoke = sub.add_parser(
        "provider-smoke",
        help="Gate configured provider metadata and optionally run one chat call",
    )
    provider_smoke.add_argument("--run-id", default="")
    provider_smoke.add_argument("--data-dir", type=Path, default=None)
    provider_smoke.add_argument("--model", default="")
    provider_smoke.add_argument(
        "--chat-call",
        action="store_true",
        help="Send one minimal chat completion through the configured gateway",
    )
    provider_smoke.add_argument(
        "--allow-deterministic-fake",
        action="store_true",
        help="Allow llm-mock/mock provider lanes for unit or contract tests",
    )

    mcp_policy = sub.add_parser(
        "mcp-catalog-policy",
        help="Run provider-free Feature 024 MCP catalog policy scenarios",
    )
    mcp_policy.add_argument("--run-id", default="")
    mcp_policy.add_argument("--data-dir", type=Path, default=None)

    widget_policy = sub.add_parser(
        "matrix-widget-policy",
        help="Run provider-free Feature 030 Matrix widget policy scenarios",
    )
    widget_policy.add_argument("--run-id", default="")
    widget_policy.add_argument("--data-dir", type=Path, default=None)

    report_grounding = sub.add_parser(
        "report-grounding",
        help="Run provider-free Feature 027 report citation/build scenarios",
    )
    report_grounding.add_argument("--run-id", default="")
    report_grounding.add_argument("--data-dir", type=Path, default=None)

    routing_contract = sub.add_parser(
        "routing-contract",
        help="Run provider-free Feature 020 route/delegation/loop-guard scenarios",
    )
    routing_contract.add_argument("--run-id", default="")
    routing_contract.add_argument("--data-dir", type=Path, default=None)

    prompt_cache_contract = sub.add_parser(
        "prompt-cache-contract",
        help="Run provider-free Feature 032 prompt-cache telemetry scenarios",
    )
    prompt_cache_contract.add_argument("--run-id", default="")
    prompt_cache_contract.add_argument("--data-dir", type=Path, default=None)

    skill_lifecycle_contract = sub.add_parser(
        "skill-lifecycle-contract",
        help="Run provider-free Feature 015 skill audit/lifecycle scenarios",
    )
    skill_lifecycle_contract.add_argument("--run-id", default="")
    skill_lifecycle_contract.add_argument("--data-dir", type=Path, default=None)

    domain_contract = sub.add_parser(
        "domain-contract",
        help="Run provider-free python-backend Meta-Harness domain scenarios",
    )
    domain_contract.add_argument("--run-id", default="")
    domain_contract.add_argument("--data-dir", type=Path, default=None)

    contract_suite = sub.add_parser(
        "contract-suite",
        help=(
            "Run provider-free cross-feature contract lanes for "
            "Features 012/015/016/017/019/020/022/023/024/025/027/030"
        ),
    )
    contract_suite.add_argument("--run-id", default="")
    contract_suite.add_argument("--data-dir", type=Path, default=None)

    knowledge_contract = sub.add_parser(
        "knowledge-contract",
        help="Run provider-free Memory/KG/RAG/Semantic boundary scenarios",
    )
    knowledge_contract.add_argument("--run-id", default="")
    knowledge_contract.add_argument("--data-dir", type=Path, default=None)

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

    pdf_sweep = sub.add_parser(
        "pdf-extraction-sweep",
        help="Run available Feature 021 parser candidates against Markdown truth",
    )
    pdf_sweep.add_argument("--run-id", default="")
    pdf_sweep.add_argument(
        "--extractors",
        default="",
        help="Comma-separated extractor registry names. Defaults to known profiles.",
    )
    pdf_sweep.add_argument(
        "--include-unavailable",
        action="store_true",
        help="Write failure artifacts for unavailable optional parser candidates.",
    )
    pdf_sweep.add_argument("--pdf-path", type=Path, default=None)
    pdf_sweep.add_argument("--truth-path", type=Path, default=None)
    pdf_sweep.add_argument("--data-dir", type=Path, default=None)

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
    decide.add_argument(
        "--decision", choices=("keep", "discard", "defer"), required=True
    )
    decide.add_argument("--rationale", required=True)
    decide.add_argument("--metrics-json", default="{}")
    decide.add_argument("--follow-up", default="")
    decide.add_argument("--data-dir", type=Path, default=None)

    sub.add_parser("pareto", help="Show Pareto frontier summary")

    experience = sub.add_parser(
        "experience-packet",
        help="Write a paper-aligned Meta-Harness outer-loop experience packet",
    )
    experience.add_argument("--run-id", default="")
    experience.add_argument("--data-dir", type=Path, default=None)
    experience.add_argument("--limit", type=int, default=40)
    experience.add_argument(
        "--no-write-manifests",
        action="store_true",
        help="Inspect candidates without writing candidate_manifest.json files",
    )

    pending_eval = sub.add_parser(
        "pending-eval",
        help="Write a frozen pending-evaluation envelope for one candidate",
    )
    pending_eval.add_argument("--run-id", required=True)
    pending_eval.add_argument("--candidate-id", required=True)
    pending_eval.add_argument("--candidate-type", required=True)
    pending_eval.add_argument("--domain-id", required=True)
    pending_eval.add_argument("--write-scope", action="append", default=[])
    pending_eval.add_argument("--evaluation", required=True)
    pending_eval.add_argument("--rollback-ref", default="")
    pending_eval.add_argument("--data-dir", type=Path, default=None)

    promotion_check = sub.add_parser(
        "promotion-check",
        help="Fail-closed preflight for candidate promotion",
    )
    promotion_check.add_argument("--run-id", required=True)
    promotion_check.add_argument("--candidate-id", required=True)
    promotion_check.add_argument("--data-dir", type=Path, default=None)

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
    if args.command == "provider-smoke":
        from meta_harness.provider_smoke import run_provider_smoke

        kwargs = {
            "run_id": args.run_id or None,
            "model": args.model or None,
            "chat_call": args.chat_call,
            "allow_deterministic_fake": args.allow_deterministic_fake,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return await run_provider_smoke(**kwargs)
    if args.command == "mcp-catalog-policy":
        from meta_harness.mcp_catalog_policy import run_mcp_catalog_policy_scenarios

        kwargs = {"run_id": args.run_id or "run-mcp-catalog-policy"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_mcp_catalog_policy_scenarios(**kwargs)
    if args.command == "matrix-widget-policy":
        from meta_harness.matrix_widget_policy import (
            run_matrix_widget_policy_scenarios,
        )

        kwargs = {"run_id": args.run_id or "run-matrix-widget-policy"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_matrix_widget_policy_scenarios(**kwargs)
    if args.command == "report-grounding":
        from meta_harness.report_grounding import run_report_grounding_scenarios

        kwargs = {"run_id": args.run_id or "run-report-grounding"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_report_grounding_scenarios(**kwargs)
    if args.command == "routing-contract":
        from meta_harness.routing_contract import run_routing_contract_scenarios

        kwargs = {"run_id": args.run_id or "run-routing-contract"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_routing_contract_scenarios(**kwargs)
    if args.command == "prompt-cache-contract":
        from meta_harness.prompt_cache_contract import (
            run_prompt_cache_contract_scenarios,
        )

        kwargs = {"run_id": args.run_id or "run-prompt-cache-contract"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_prompt_cache_contract_scenarios(**kwargs)
    if args.command == "skill-lifecycle-contract":
        from meta_harness.skill_lifecycle_contract import (
            run_skill_lifecycle_contract_scenarios,
        )

        kwargs = {"run_id": args.run_id or "run-skill-lifecycle-contract"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_skill_lifecycle_contract_scenarios(**kwargs)
    if args.command == "domain-contract":
        from meta_harness.domain_contract import run_domain_contract_scenarios

        kwargs = {"run_id": args.run_id or "run-domain-contract"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_domain_contract_scenarios(**kwargs)
    if args.command == "contract-suite":
        from meta_harness.contract_suite import run_contract_suite

        kwargs = {"run_id": args.run_id or "run-contract-suite"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_contract_suite(**kwargs)
    if args.command == "knowledge-contract":
        from meta_harness.knowledge_contract import run_knowledge_contract_scenarios

        kwargs = {"run_id": args.run_id or "run-knowledge-contract"}
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return run_knowledge_contract_scenarios(**kwargs)
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
    if args.command == "pdf-extraction-sweep":
        from meta_harness.extraction_benchmark import (
            DEFAULT_PDF_PATH,
            run_pdf_extraction_sweep,
        )

        pdf_path = args.pdf_path or DEFAULT_PDF_PATH
        truth_path = args.truth_path or pdf_path.with_suffix(".md")
        extractor_names = tuple(
            value.strip()
            for value in str(args.extractors or "").split(",")
            if value.strip()
        )
        kwargs = {
            "pdf_path": pdf_path,
            "truth_path": truth_path,
            "run_id": args.run_id or None,
            "extractor_names": extractor_names or None,
            "available_only": not args.include_unavailable,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return await run_pdf_extraction_sweep(**kwargs)
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
    if args.command == "experience-packet":
        from meta_harness.outer_loop import write_experience_packet

        kwargs = {
            "run_id": args.run_id or "run-outer-loop-experience",
            "limit": args.limit,
            "write_manifests": not args.no_write_manifests,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return write_experience_packet(**kwargs)
    if args.command == "pending-eval":
        from meta_harness.outer_loop import write_pending_eval

        kwargs = {
            "run_id": args.run_id,
            "candidate_id": args.candidate_id,
            "candidate_type": args.candidate_type,
            "domain_id": args.domain_id,
            "write_scope": args.write_scope,
            "evaluation": args.evaluation,
            "rollback_ref": args.rollback_ref,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return write_pending_eval(**kwargs)
    if args.command == "promotion-check":
        from meta_harness.outer_loop import promotion_gate

        kwargs = {
            "run_id": args.run_id,
            "candidate_id": args.candidate_id,
        }
        if args.data_dir is not None:
            kwargs["data_dir"] = args.data_dir
        return promotion_gate(**kwargs)
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
