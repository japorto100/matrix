"""KG Pipeline CLI (Phase 2 STUB)."""

from __future__ import annotations

import sys


def main() -> int:
    print("kg_pipeline lightweight extractor is available.")
    print("Start with: uv run uvicorn kg_pipeline.server:app --port 8099")
    return 0


if __name__ == "__main__":
    sys.exit(main())
