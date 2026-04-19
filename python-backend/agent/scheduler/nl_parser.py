"""Natural-language scheduling parser (Phase-1 rules-based).

Maps common German + English phrases to cron expressions or absolute
timestamps. Returns a draft that the agent echoes back for user
confirmation — intentional two-step UX so "morgen 9" (which 9?) or
ambiguous "jeden Mittag" don't silently commit wrong schedules.

Phase-1 covers ~80% of expected user inputs via regex; Phase-2 adds
an LLM-fallback for the rest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


@dataclass
class ParseResult:
    """Draft produced by parse(). ``kind``/``cron_expr``/``scheduled_at_ms``
    form the trigger shape for the scheduled_tasks row.
    """

    kind: str  # recurring | one_shot | reminder
    cron_expr: str | None = None
    scheduled_at_ms: int | None = None
    tz: str = "UTC"
    prompt: str = ""
    confidence: str = "high"  # high | medium | low
    notes: list[str] = field(default_factory=list)


WEEKDAY_MAP = {
    "mon": 1,
    "monday": 1,
    "montag": 1,
    "mo": 1,
    "tue": 2,
    "tuesday": 2,
    "dienstag": 2,
    "di": 2,
    "wed": 3,
    "wednesday": 3,
    "mittwoch": 3,
    "mi": 3,
    "thu": 4,
    "thursday": 4,
    "donnerstag": 4,
    "do": 4,
    "fri": 5,
    "friday": 5,
    "freitag": 5,
    "fr": 5,
    "sat": 6,
    "saturday": 6,
    "samstag": 6,
    "sa": 6,
    "sun": 0,
    "sunday": 0,
    "sonntag": 0,
    "so": 0,
}


def _extract_time(text: str) -> tuple[int, int] | None:
    """Return (hour, minute) from expressions like ``9:30``, ``17h``, ``9 uhr``.
    Returns None when no explicit time is found.
    """
    # HH:MM
    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # HH uhr  / HH h
    m = re.search(r"\b(\d{1,2})\s*(?:uhr|h)\b", text, re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return hour, 0
    # English "at 9"
    m = re.search(r"\bat\s+(\d{1,2})\b", text, re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return hour, 0
    return None


def _extract_weekday(text: str) -> int | None:
    lower = text.lower()
    for key, val in WEEKDAY_MAP.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            return val
    return None


def _extract_prompt(text: str) -> str:
    """Strip scheduling phrases from the raw input to leave the intent.

    We don't try to be clever here — the caller uses both the whole input
    and the extracted prompt; the LLM seeing the full user message is fine.
    """
    return text.strip()


def _to_utc_ms(local: datetime, tz_name: str) -> int:
    if ZoneInfo is None:
        return int(local.timestamp() * 1000)
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = UTC
    aware = local.replace(tzinfo=tz)
    return int(aware.timestamp() * 1000)


def parse(
    text: str,
    *,
    user_tz: str = "UTC",
    now: datetime | None = None,
) -> ParseResult:
    """Parse a natural-language scheduling request.

    ``user_tz`` is the IANA timezone the user speaks in (e.g.
    ``Europe/Zurich``); times in the phrase are interpreted against this.
    ``now`` injectable for tests.
    """
    raw = text.strip()
    lower = raw.lower()
    if now is None:
        now = datetime.now(UTC)

    # ── one-shot relative: "in 6 monaten" / "in 2 weeks" / "in 3 days"
    m = re.search(r"\bin\s+(\d+)\s*(minute|minuten|minutes|hour|stunde|stunden|hours|day|tag|tage|days|week|woche|wochen|weeks|month|monat|monate|months)\b", lower)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        delta = _relative_delta(amount, unit)
        if delta is not None:
            scheduled = now + delta
            return ParseResult(
                kind="reminder",
                scheduled_at_ms=int(scheduled.timestamp() * 1000),
                tz="UTC",
                prompt=_extract_prompt(raw),
            )

    # ── recurring weekly: "jeden Montag 9 Uhr" / "every monday at 9"
    weekday = _extract_weekday(lower)
    time_spec = _extract_time(lower)
    if weekday is not None and (
        "jeden" in lower or "every" in lower or "wöchentlich" in lower
    ):
        hour, minute = time_spec if time_spec else (9, 0)
        cron = f"{minute} {hour} * * {weekday}"
        return ParseResult(
            kind="recurring",
            cron_expr=cron,
            tz=user_tz,
            prompt=_extract_prompt(raw),
        )

    # ── recurring every N hours: "alle 2 Stunden"
    m = re.search(r"alle\s+(\d+)\s*stunden", lower)
    if m:
        hours = int(m.group(1))
        if 1 <= hours <= 23:
            return ParseResult(
                kind="recurring",
                cron_expr=f"0 */{hours} * * *",
                tz=user_tz,
                prompt=_extract_prompt(raw),
            )

    # ── recurring weekdays + time: "werktags 17 Uhr" / "weekdays at 17"
    if time_spec and ("werktag" in lower or "weekday" in lower):
        hour, minute = time_spec
        return ParseResult(
            kind="recurring",
            cron_expr=f"{minute} {hour} * * 1-5",
            tz=user_tz,
            prompt=_extract_prompt(raw),
        )

    # ── recurring daily: "jeden Tag 8 Uhr" / "daily at 8"
    if (("jeden tag" in lower) or ("täglich" in lower) or ("daily" in lower)) and time_spec:
        hour, minute = time_spec
        return ParseResult(
            kind="recurring",
            cron_expr=f"{minute} {hour} * * *",
            tz=user_tz,
            prompt=_extract_prompt(raw),
        )

    # ── one-shot tomorrow at time: "morgen 8" / "tomorrow at 9"
    if ("morgen" in lower or "tomorrow" in lower) and time_spec:
        hour, minute = time_spec
        tomorrow = (now + timedelta(days=1)).date()
        local = datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute)
        return ParseResult(
            kind="one_shot",
            scheduled_at_ms=_to_utc_ms(local, user_tz),
            tz=user_tz,
            prompt=_extract_prompt(raw),
        )

    # ── one-shot today at time: "heute 18 Uhr"
    if ("heute" in lower or "today" in lower) and time_spec:
        hour, minute = time_spec
        today = now.date()
        local = datetime(today.year, today.month, today.day, hour, minute)
        return ParseResult(
            kind="one_shot",
            scheduled_at_ms=_to_utc_ms(local, user_tz),
            tz=user_tz,
            prompt=_extract_prompt(raw),
        )

    # Low-confidence fallback: surface the raw text with a note so the agent
    # asks the user for a concrete schedule instead of guessing.
    return ParseResult(
        kind="recurring",
        confidence="low",
        tz=user_tz,
        prompt=_extract_prompt(raw),
        notes=[
            "could not parse schedule from natural-language input",
            "expected patterns: 'jeden Montag 9 Uhr', 'morgen 8', "
            "'alle 2 Stunden', 'in 6 Monaten', 'werktags 17 Uhr'",
        ],
    )


def _relative_delta(amount: int, unit: str) -> timedelta | None:
    unit = unit.lower()
    if unit.startswith(("minute", "minuten")):
        return timedelta(minutes=amount)
    if unit.startswith(("hour", "stunde")):
        return timedelta(hours=amount)
    if unit.startswith(("day", "tag")):
        return timedelta(days=amount)
    if unit.startswith(("week", "woche")):
        return timedelta(weeks=amount)
    if unit.startswith(("month", "monat")):
        return timedelta(days=30 * amount)  # approximation OK for reminders
    return None


def draft_to_dict(draft: ParseResult) -> dict[str, Any]:
    """JSON-serialisable dict for tool return values."""
    return {
        "kind": draft.kind,
        "cron_expr": draft.cron_expr,
        "scheduled_at_ms": draft.scheduled_at_ms,
        "tz": draft.tz,
        "prompt": draft.prompt,
        "confidence": draft.confidence,
        "notes": draft.notes,
    }
