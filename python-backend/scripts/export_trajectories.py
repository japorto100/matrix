#!/usr/bin/env python3
"""CLI — Export agent session trajectories in ShareGPT JSONL (exec-hermes §3.6).

Reads exec-18 ``agent.sessions`` × ``agent.traces`` × ``agent.spans`` from the
project Postgres and emits one ShareGPT conversation per session to STDOUT
(default) or a file (``--out``).

Usage::

    python scripts/export_trajectories.py --out trajectories.jsonl
    python scripts/export_trajectories.py --since 7 --user alice@matrix.local

ENV:
    HINDSIGHT_DB_URL  — Postgres connection string (same default as
                        agent/sessions.py: postgresql://postgres@localhost:5433/hindsight_dev).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from agent.trajectory.exporter import (
    build_sharegpt_conversation,
    iter_sessions_with_spans,
    serialize_jsonl,
)

logger = logging.getLogger("export_trajectories")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=None, help="Output JSONL file (default: stdout).")
    p.add_argument("--since", type=int, default=None, help="Days to look back (default: all).")
    p.add_argument("--user", type=str, default=None, help="Filter to one user_id.")
    p.add_argument("--db-url", type=str, default=None, help="Override HINDSIGHT_DB_URL.")
    p.add_argument(
        "--dry-run", action="store_true", help="Count candidates without writing."
    )
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    since_ms = None
    if args.since is not None:
        since_ms = int((time.time() - args.since * 86400) * 1000)
        logger.info("Filter: since_ms=%s (last %s days)", since_ms, args.since)
    if args.user:
        logger.info("Filter: user_id=%s", args.user)

    stats = {"sessions": 0, "skipped_empty": 0, "exported": 0}
    out_f = None
    if not args.dry_run and args.out is not None:
        out_f = args.out.open("w", encoding="utf-8")

    try:
        for session, spans in iter_sessions_with_spans(
            since_ms=since_ms, user_id=args.user, db_url=args.db_url
        ):
            stats["sessions"] += 1
            conv = build_sharegpt_conversation(session, spans)
            if conv is None:
                stats["skipped_empty"] += 1
                continue
            stats["exported"] += 1
            if args.dry_run:
                continue
            line = serialize_jsonl([conv])
            if out_f is not None:
                out_f.write(line)
            else:
                sys.stdout.write(line)
    finally:
        if out_f is not None:
            out_f.close()

    logger.info(
        "Done — sessions scanned=%d, exported=%d, skipped_empty=%d",
        stats["sessions"], stats["exported"], stats["skipped_empty"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
