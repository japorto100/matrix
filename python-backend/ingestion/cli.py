"""CLI for manual ingestion debugging.

Usage:
    uv run python -m ingestion.cli ingest-note --text "hello world"
    uv run python -m ingestion.cli ingest-file --path /local/file.pdf
    uv run python -m ingestion.cli status
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

from ingestion.core.config import get_config
from ingestion.pipelines.base import PipelineContext
from ingestion.pipelines.document import DocumentPipeline
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
    """Local file → load → extract → ... pipeline.

    For local files we bypass SeaweedFS by writing the file metadata
    directly to the tracker (no Go gateway).
    """
    path = Path(args.path)
    if not path.is_file():
        logger.error("file not found: {}", path)
        return 1

    ctx = PipelineContext.from_config(get_config())

    # Build a Job from local file (no SeaweedFS)
    _ = uuid4()  # reserved for future SeaweedFS integration
    _ = DocumentPipeline(ctx)  # reserved for future SeaweedFS integration
    logger.warning(
        "CLI ingest-file requires SeaweedFS upload first — use the worker /ingest/document API"
    )
    logger.warning("(Local-only ingestion bypassing SeaweedFS is not implemented yet)")
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

    p_file = sub.add_parser("ingest-file", help="(stub) local file ingestion")
    p_file.add_argument("--path", required=True)

    sub.add_parser("status", help="show job status counts")

    args = parser.parse_args()

    if args.cmd == "ingest-note":
        return asyncio.run(cmd_ingest_note(args))
    if args.cmd == "ingest-file":
        return asyncio.run(cmd_ingest_file(args))
    if args.cmd == "status":
        return asyncio.run(cmd_status(args))
    return 1


if __name__ == "__main__":
    sys.exit(main())
