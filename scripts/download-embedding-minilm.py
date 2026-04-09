"""Download the default lightweight embedding model used in ingestion (CPU).

Opt-in only. This script should NEVER be executed automatically at runtime.

Usage:
  python3 scripts/download-embedding-minilm.py

Env:
  HF_HOME         Optional HF cache dir (default: ~/.cache/huggingface)
  EMBEDDER_MODEL  Optional override (default: sentence-transformers/all-MiniLM-L6-v2)
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    cache_dir = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    model_id = os.environ.get(
        "EMBEDDER_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    ).strip()

    print(f"HF cache dir: {cache_dir}")
    print(f"Model: {model_id}")

    try:
        from sentence_transformers import SentenceTransformer

        m = SentenceTransformer(model_id, device="cpu")
        dim = m.get_sentence_embedding_dimension()
        _ = m.encode(["hello world"], convert_to_numpy=True, show_progress_bar=False)
        print(f"OK: model loaded (dim={dim})")
        return 0
    except Exception as e:
        print(f"FAILED: {e}")
        print("Hint: ensure sentence-transformers is installed in the active environment.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

