"""File-backed State Store (NLAH Paper Pattern, exec-10 Phase 6.2b).

Speichert Zwischen-Ergebnisse auf Disk fuer Crash-Recovery.
Pattern: agent/state/{thread_id}/{role}_output.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path(__file__).parent / "state"


class FileBackedState:
    """Persistiert Role-Outputs auf Disk fuer Recovery."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or DEFAULT_STATE_DIR

    def save(self, thread_id: str, role: str, data: dict) -> Path:
        thread_dir = self.base_dir / thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)
        path = thread_dir / f"{role}_output.json"
        path.write_text(
            json.dumps(
                {
                    "role": role,
                    "timestamp": datetime.now().isoformat(),
                    "data": data,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    def load(self, thread_id: str, role: str) -> dict | None:
        path = self.base_dir / thread_id / f"{role}_output.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("data")
        except Exception:
            return None

    def has_checkpoint(self, thread_id: str, role: str) -> bool:
        return (self.base_dir / thread_id / f"{role}_output.json").exists()
