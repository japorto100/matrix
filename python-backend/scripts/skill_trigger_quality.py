"""CLI: aggregate per-skill trigger quality from `agent.audit_events`.

Usage:
  HINDSIGHT_DB_URL=... python scripts/skill_trigger_quality.py \
      [--days 30] [--min-n 5] [--json]

Reads skill_found / skill_refined / skill_used events, joins their
coverage_score metadata, and prints a quality verdict per skill:
  OK                    — healthy trigger
  BROAD_TRIGGER         — false_rate above threshold → description too broad
  LOW_AVG_COVERAGE      — avg coverage below 3 → weak match overall
  NO_COVERAGE_SCORES    — never refined with coverage gate on
  INSUFFICIENT_DATA     — below `--min-n`
"""

from __future__ import annotations

import argparse
import json
import sys

from agent.skills.trigger_quality import compute_trigger_quality


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30, help="look-back window (0 = all)")
    p.add_argument("--min-n", type=int, default=5, help="min events per skill")
    p.add_argument(
        "--false-threshold",
        type=float,
        default=2.5,
        help="coverage_score below this is a false trigger",
    )
    p.add_argument(
        "--false-rate",
        type=float,
        default=0.4,
        help="fraction of false triggers to flag as BROAD",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    stats = compute_trigger_quality(
        days=args.days,
        false_threshold=args.false_threshold,
        false_threshold_rate=args.false_rate,
        min_n=args.min_n,
    )

    if args.json:
        print(json.dumps([s.as_dict() for s in stats], indent=2))
        sys.exit(0)

    if not stats:
        print("(no skill events in window)")
        sys.exit(0)

    print(
        f"{'skill_id':<45} {'n_found':>8} {'n_cov':>6} {'avg_cov':>8} "
        f"{'false%':>7}  verdict"
    )
    print("-" * 95)
    for s in stats:
        print(
            f"{s.skill_id:<45} {s.n_found:>8} {s.n_with_score:>6} "
            f"{s.avg_coverage:>8.2f} {s.false_rate*100:>6.1f}%  {s.verdict}"
        )


if __name__ == "__main__":
    main()
