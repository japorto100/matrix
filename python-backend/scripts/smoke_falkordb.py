from __future__ import annotations

import os
import sys
from pathlib import Path

PYTHON_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_BACKEND_ROOT) not in sys.path:
    sys.path.append(str(PYTHON_BACKEND_ROOT))

from memory_engine.kg_store import create_kg_store  # noqa: E402


def main() -> int:
    os.environ["KG_PROVIDER"] = "falkor"
    store = create_kg_store()
    status = store.status()
    print({"provider": "falkor", "status": status})
    return 0 if status == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
