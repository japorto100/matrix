from __future__ import annotations

import os
import sys
from pathlib import Path

PYTHON_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_BACKEND_ROOT) not in sys.path:
    sys.path.append(str(PYTHON_BACKEND_ROOT))

from memory_engine.vector_store import VectorStore  # noqa: E402


def main() -> int:
    provider = os.getenv("VECTOR_STORE_PROVIDER", "pgvector")
    if provider.strip().lower() != "pgvector":
        os.environ["VECTOR_STORE_PROVIDER"] = "pgvector"

    store = VectorStore(provider="pgvector", mock=True)
    status = store.status()
    print(status)
    return 0 if status.get("status") == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
