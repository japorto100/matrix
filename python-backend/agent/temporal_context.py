"""Temporal Context — zeitbasierter Agent-Kontext (exec-10 Phase 3.5).

Gibt dem Agent automatisch Kontext ueber:
- Letzte Agent-Interaktionen (aus Trajectory Logs)
- Zeitstempel-basierte Relevanz
- Portfolio-/Market-Events (Zukunft: aus externen Quellen)

Wird ins System-Prompt injiziert, aehnlich wie Skills.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

TRAJECTORIES_DIR = Path(__file__).parent / "skills" / ".trajectories"


def get_temporal_context(
    user_id: str,
    lookback_hours: int = 24,
    max_entries: int = 5,
) -> str:
    """Erstellt zeitbasierten Kontext aus den letzten Agent-Interaktionen.

    Args:
        user_id: User-ID fuer personalisierte History
        lookback_hours: Wie weit zurueckschauen (default: 24h)
        max_entries: Max Anzahl Eintraege (default: 5)

    Returns:
        Formatierter Kontext-String fuer System-Prompt Injection.
        Leerer String wenn keine History vorhanden.
    """
    if not TRAJECTORIES_DIR.exists():
        return ""

    cutoff = datetime.now() - timedelta(hours=lookback_hours)
    entries: list[dict] = []

    for path in sorted(TRAJECTORIES_DIR.glob(f"{user_id}_*.json"), reverse=True):
        if len(entries) >= max_entries:
            break
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ts = datetime.fromisoformat(data.get("timestamp", ""))
            if ts < cutoff:
                continue
            entries.append({
                "time": ts.strftime("%H:%M"),
                "success": data.get("success", True),
                "messages": data.get("messages_count", 0),
                "tools": data.get("tool_calls_count", 0),
                "summary": _summarize_trajectory(data),
            })
        except Exception:
            continue

    if not entries:
        return ""

    lines = [f"## Recent Activity (last {lookback_hours}h)\n"]
    for e in entries:
        status = "ok" if e["success"] else "FAILED"
        lines.append(f"- [{e['time']}] {e['summary']} ({e['messages']} msgs, {e['tools']} tools, {status})")

    return "\n".join(lines)


def _summarize_trajectory(data: dict) -> str:
    """Extrahiert eine kurze Zusammenfassung aus einer Trajectory."""
    messages = data.get("messages", [])
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            text = msg["content"][:80]
            return text.rstrip(".")
    return "Agent interaction"
