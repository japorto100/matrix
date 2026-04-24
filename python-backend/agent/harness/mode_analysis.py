"""Post-hoc mode-labeling of agent.audit_events — exec-a2fm Phase 2.a (L1).

Derives A²FM-style mode labels (``instant`` / ``reasoning`` / ``agentic``)
from the existing audit trail without training a classifier. The goal is
to answer "what's matrix's real mode distribution?" BEFORE committing to
any ML-router work — exec-a2fm's Phase-2 spec asks this question, and
this script is the cheapest way to answer it.

**Labeling rules** (match the A2FM paper conceptually, adapted to
matrix's audit-event vocabulary):

* ``agentic`` — the thread has at least one ``tool_call`` audit event.
  Any turn that invoked a tool is by definition tool-aware.
* ``reasoning`` — no ``tool_call`` events AND the LLM iteration counter
  reached at least 2 (multi-turn deliberation without tools).
* ``instant`` — no ``tool_call`` events AND a single LLM iteration AND
  the LLM response is short (under ``INSTANT_MAX_CHARS``). Fallback
  bucket; captures the "trivial factual query" class.
* ``unknown`` — no LLM events at all (crashed session, tool-only, etc.).

The script emits a markdown report plus a CSV for ad-hoc spreadsheet
analysis. No schema changes; read-only query.

Usage (requires ``HINDSIGHT_DB_URL``)::

    uv run python -m agent.harness.mode_analysis
    # or with a narrower time window:
    uv run python -m agent.harness.mode_analysis --days 30 --limit 5000

References:

* ``docs/superpowers/findings/2026-04-23-a2fm-paper-research-phase2.md``
* ``specs/execution/exec-a2fm-adaptive-routing.md`` Phase 2.a (L1)
* ADR-001 G1-G4 + P1 (smart-routing rollout gate)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Heuristic threshold: LLM responses shorter than this + single-iteration
# + no tools → "instant". Tunable via env.
INSTANT_MAX_CHARS = int(os.environ.get("MODE_ANALYSIS_INSTANT_MAX_CHARS", "400"))


@dataclass
class ThreadStats:
    thread_id: str
    user_id: str | None = None
    action_counts: Counter[str] = field(default_factory=Counter)
    max_iteration: int = 0
    llm_response_durations_ms: list[float] = field(default_factory=list)
    llm_response_total_tokens: int = 0
    llm_response_char_lengths: list[int] = field(default_factory=list)
    model_used: str = ""

    @property
    def has_tool_calls(self) -> bool:
        return self.action_counts.get("tool_call", 0) > 0

    @property
    def llm_response_count(self) -> int:
        return self.action_counts.get("llm_response", 0)

    @property
    def avg_response_len(self) -> float:
        if not self.llm_response_char_lengths:
            return 0.0
        return sum(self.llm_response_char_lengths) / len(self.llm_response_char_lengths)

    def label_mode(self) -> str:
        if self.llm_response_count == 0:
            return "unknown"
        if self.has_tool_calls:
            return "agentic"
        if self.max_iteration >= 2 or self.llm_response_count >= 2:
            return "reasoning"
        if self.avg_response_len <= INSTANT_MAX_CHARS:
            return "instant"
        return "reasoning"  # long single-turn response = implicit reasoning


async def _fetch_events(
    dsn: str, *, days: int, limit: int
) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    since_clause = ""
    if days > 0:
        since_clause = f"AND timestamp > now() - interval '{int(days)} days'"

    sql = f"""
        SELECT thread_id, user_id, action, iteration, metadata, duration_ms, output
        FROM agent.audit_events
        WHERE thread_id IS NOT NULL AND thread_id <> ''
          {since_clause}
        ORDER BY thread_id, id
        LIMIT %(limit)s
    """
    async with await psycopg.AsyncConnection.connect(dsn, row_factory=dict_row) as conn:
        rows = await (await conn.execute(sql, {"limit": limit})).fetchall()
    return list(rows)


def _aggregate(events: list[dict[str, Any]]) -> dict[str, ThreadStats]:
    threads: dict[str, ThreadStats] = {}
    for row in events:
        tid = row.get("thread_id") or ""
        if not tid:
            continue
        stats = threads.setdefault(tid, ThreadStats(thread_id=tid))
        stats.user_id = stats.user_id or row.get("user_id")
        action = row.get("action") or ""
        stats.action_counts[action] += 1

        itr = row.get("iteration")
        if isinstance(itr, int) and itr > stats.max_iteration:
            stats.max_iteration = itr

        if action == "llm_response":
            dur = row.get("duration_ms")
            if isinstance(dur, (int, float)):
                stats.llm_response_durations_ms.append(float(dur))

            meta = row.get("metadata")
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:  # noqa: BLE001
                    meta = {}
            if isinstance(meta, dict):
                stats.llm_response_total_tokens += int(meta.get("token_usage") or 0)
                if not stats.model_used:
                    stats.model_used = str(meta.get("model") or "")

            out = row.get("output")
            if isinstance(out, str):
                try:
                    parsed = json.loads(out)
                    stats.llm_response_char_lengths.append(len(str(parsed)))
                except Exception:  # noqa: BLE001
                    stats.llm_response_char_lengths.append(len(out))
            elif out is not None:
                stats.llm_response_char_lengths.append(len(str(out)))
    return threads


def _render_report(threads: dict[str, ThreadStats], *, days: int) -> str:
    total = len(threads)
    if total == 0:
        return (
            "# Harness Mode Analysis\n\n"
            f"Generated: {datetime.now(UTC).isoformat()}\n\n"
            "No threads with audit events found. Either the DB is empty "
            "or the time filter excluded all sessions.\n"
        )

    mode_buckets: dict[str, list[ThreadStats]] = defaultdict(list)
    for stats in threads.values():
        mode_buckets[stats.label_mode()].append(stats)

    lines: list[str] = [
        "# Harness Mode Analysis — L1 post-hoc labeling",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Window: last {days} days" if days > 0 else "Window: all time",
        f"Total threads analyzed: **{total}**",
        f"Instant-max-chars threshold: {INSTANT_MAX_CHARS}",
        "",
        "## Mode distribution",
        "",
        "| Mode | Threads | % | Avg LLM turns | Avg tokens | Avg duration (ms) | Avg response chars |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    order = ["instant", "reasoning", "agentic", "unknown"]
    for mode in order:
        bucket = mode_buckets.get(mode, [])
        n = len(bucket)
        if n == 0:
            lines.append(f"| {mode} | 0 | 0.0% | — | — | — | — |")
            continue
        pct = 100.0 * n / total
        avg_turns = sum(s.llm_response_count for s in bucket) / n
        avg_tokens = sum(s.llm_response_total_tokens for s in bucket) / n
        avg_dur = (
            sum(sum(s.llm_response_durations_ms) for s in bucket) / n
            if bucket
            else 0.0
        )
        avg_chars = sum(s.avg_response_len for s in bucket) / n
        lines.append(
            f"| {mode} | {n} | {pct:.1f}% | {avg_turns:.1f} | {avg_tokens:.0f} "
            f"| {avg_dur:.0f} | {avg_chars:.0f} |"
        )

    lines.extend([
        "",
        "## Notes",
        "",
        "- **Labeling rules:** any `tool_call` → agentic. Else max_iteration ≥ 2 or ≥2 LLM responses → reasoning. Else short single response → instant. No LLM events → unknown.",
        "- **What this doesn't tell you:** whether routing the instant-bucket to a cheap model would have preserved quality. That's L2 (adaptive-reward loop using `harness_fitness_score`).",
        "- **Caveat:** the `instant` bucket is identified by response-length, not user intent. Short factual replies and short confused replies both land here. L2's fitness-delta check disambiguates.",
        "- **Re-run:** `uv run python -m agent.harness.mode_analysis` (optionally `--days N --limit M`).",
        "",
        "## Actionable",
        "",
        "1. If >90% of threads are `instant`, Phase-2 ML-classifier is moot — just optimize the cheap-route threshold for that bucket.",
        "2. If `agentic` is a meaningful chunk (>20%), L3 classifier has potential value (routing in/out of tool-use is the high-cost decision).",
        "3. If `unknown` is >10%, investigate audit gaps — likely crashed sessions or tool-only threads. Fix before trusting downstream analysis.",
        "",
    ])
    return "\n".join(lines)


def _render_csv(threads: dict[str, ThreadStats]) -> str:
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "thread_id",
        "user_id",
        "mode",
        "llm_turns",
        "has_tool_calls",
        "max_iteration",
        "total_tokens",
        "avg_response_chars",
        "total_duration_ms",
        "model_used",
    ])
    for stats in sorted(threads.values(), key=lambda s: s.thread_id):
        w.writerow([
            stats.thread_id,
            stats.user_id or "",
            stats.label_mode(),
            stats.llm_response_count,
            int(stats.has_tool_calls),
            stats.max_iteration,
            stats.llm_response_total_tokens,
            f"{stats.avg_response_len:.1f}",
            f"{sum(stats.llm_response_durations_ms):.0f}",
            stats.model_used,
        ])
    return buf.getvalue()


async def analyze_modes(
    *,
    dsn: str | None = None,
    days: int = 0,
    limit: int = 10000,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Main analysis entry point.

    Returns ``{"threads": int, "modes": {...}, "report_path": Path,
    "csv_path": Path}``. Non-fatal on empty DB — returns zeros.
    """
    dsn = dsn or os.environ.get("HINDSIGHT_DB_URL") or ""
    if not dsn:
        return {"error": "HINDSIGHT_DB_URL not set"}

    events = await _fetch_events(dsn, days=days, limit=limit)
    threads = _aggregate(events)
    report_md = _render_report(threads, days=days)
    csv_body = _render_csv(threads)

    # Repo-relative default so the script is portable (CI, Docker, other
    # machines). __file__ is python-backend/agent/harness/mode_analysis.py
    # → parents[3] is the repo root.
    out_dir = out_dir or (
        Path(__file__).resolve().parents[3] / "docs" / "superpowers" / "findings"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    report_path = out_dir / f"{stamp}-harness-mode-analysis.md"
    csv_path = out_dir / f"{stamp}-harness-mode-analysis.csv"
    report_path.write_text(report_md, encoding="utf-8")
    csv_path.write_text(csv_body, encoding="utf-8")

    modes = Counter(s.label_mode() for s in threads.values())
    return {
        "threads": len(threads),
        "events_read": len(events),
        "modes": dict(modes),
        "report_path": str(report_path),
        "csv_path": str(csv_path),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Post-hoc mode labeling of agent.audit_events")
    p.add_argument("--days", type=int, default=0, help="Restrict to last N days (0 = all)")
    p.add_argument("--limit", type=int, default=10000, help="Max audit rows to fetch")
    p.add_argument("--out-dir", type=Path, default=None, help="Override output directory")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = asyncio.run(
            analyze_modes(days=args.days, limit=args.limit, out_dir=args.out_dir)
        )
    except Exception as exc:  # noqa: BLE001
        print(f"mode-analysis failed: {exc}", file=sys.stderr)
        return 1

    if "error" in result:
        print(f"mode-analysis error: {result['error']}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
