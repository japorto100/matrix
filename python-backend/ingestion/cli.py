"""CLI for manual ingestion debugging.

Usage:
    uv run python -m ingestion.cli ingest-note --text "hello world"
    uv run python -m ingestion.cli ingest-file --path /local/file.pdf
    uv run python -m ingestion.cli ingest-url --url https://arxiv.org/pdf/2604.09666
    uv run python -m ingestion.cli status
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from ingestion.core.config import get_config
from ingestion.core.exceptions import DedupSkipError
from ingestion.pipelines.base import PipelineContext
from ingestion.pipelines.document import DocumentPipeline
from ingestion.pipelines.link import LinkPipeline
from ingestion.pipelines.note import NotePipeline
from loguru import logger


async def cmd_ingest_note(args: argparse.Namespace) -> int:
    ctx = PipelineContext.from_config(get_config())
    pipeline = NotePipeline(ctx)
    text = args.text or sys.stdin.read()
    try:
        job = await pipeline.run(text=text, user_id=args.user, tags=args.tags or [])
        logger.info("note ingested: job_id={} status={}", job.id, job.status.value)
        return 0
    except Exception as e:  # noqa: BLE001
        logger.error("ingest_note failed: {}", e)
        return 1


async def cmd_ingest_file(args: argparse.Namespace) -> int:
    """Local file → load → extract → chunk → embed → sinks."""
    path = Path(args.path)
    if not path.is_file():
        logger.error("file not found: {}", path)
        return 1

    ctx = PipelineContext.from_config(get_config())
    pipeline = DocumentPipeline(ctx)
    try:
        job = await pipeline.run_local_path(
            path=path,
            user_id=args.user,
            tags=args.tags or [],
            sinks_active=args.sinks,
        )
        logger.info("file ingested: job_id={} status={}", job.id, job.status.value)
        return 0
    except DedupSkipError as e:
        logger.info("file skipped as duplicate: {}", e)
        return 0
    except Exception as e:  # noqa: BLE001
        logger.error("ingest_file failed: {}", e)
        return 1


async def cmd_ingest_url(args: argparse.Namespace) -> int:
    """URL → fetch → extract → chunk → embed → sinks."""
    ctx = PipelineContext.from_config(get_config())
    pipeline = LinkPipeline(ctx)
    try:
        job = await pipeline.run(
            url=args.url,
            user_id=args.user,
            tags=args.tags or [],
            title=args.title,
            sinks_active=args.sinks,
        )
        logger.info("url ingested: job_id={} status={}", job.id, job.status.value)
        return 0
    except DedupSkipError as e:
        logger.info("url skipped as duplicate: {}", e)
        return 0
    except Exception as e:  # noqa: BLE001
        logger.error("ingest_url failed: {}", e)
        return 1


async def cmd_status(args: argparse.Namespace) -> int:
    ctx = PipelineContext.from_config(get_config())
    counts = ctx.tracker.status_counts()
    print("Ingestion job counts:")
    for status, count in sorted(counts.items()):
        print(f"  {status:20s} {count}")
    print(f"Total: {sum(counts.values())}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ingestion-cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_note = sub.add_parser("ingest-note", help="ingest raw text as a note")
    p_note.add_argument("--text", help="note text (default: stdin)")
    p_note.add_argument("--user", default="local")
    p_note.add_argument("--tags", nargs="*")

    p_file = sub.add_parser("ingest-file", help="ingest a local file")
    p_file.add_argument("--path", required=True)
    p_file.add_argument("--user", default="local")
    p_file.add_argument("--tags", nargs="*")
    p_file.add_argument(
        "--sinks",
        nargs="*",
        help="sink names to run (default: hindsight; examples: hindsight kg)",
    )

    p_url = sub.add_parser("ingest-url", help="ingest a URL or paper link")
    p_url.add_argument("--url", required=True)
    p_url.add_argument("--title")
    p_url.add_argument("--user", default="local")
    p_url.add_argument("--tags", nargs="*")
    p_url.add_argument(
        "--sinks",
        nargs="*",
        help="sink names to run (default: hindsight; examples: hindsight kg)",
    )

    sub.add_parser("status", help="show job status counts")

    args = parser.parse_args()

    if args.cmd == "ingest-note":
        return asyncio.run(cmd_ingest_note(args))
    if args.cmd == "ingest-file":
        return asyncio.run(cmd_ingest_file(args))
    if args.cmd == "ingest-url":
        return asyncio.run(cmd_ingest_url(args))
    if args.cmd == "status":
        return asyncio.run(cmd_status(args))
    return 1


if __name__ == "__main__":
    sys.exit(main())
