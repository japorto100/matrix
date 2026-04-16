"""Shared Method-of-Loci helpers for the Postgres-based fusion path."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _slug(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return fallback
    text = _NON_ALNUM_RE.sub("-", text).strip("-")
    return text or fallback


def _infer_hall(item: dict[str, Any], metadata: dict[str, str]) -> str:
    explicit = str(metadata.get("hall") or "").strip()
    if explicit:
        return explicit

    tags = {str(tag).strip().lower() for tag in list(item.get("tags") or [])}
    artifact_type = str(metadata.get("artifact_type") or item.get("artifact_type") or "").strip().lower()
    source_type = str(metadata.get("source_type") or item.get("source_type") or "").strip().lower()
    memory_layer = str(metadata.get("memory_layer") or "").strip().lower()

    if "preference" in tags or "preferences" in tags:
        return "preferences"
    if "advice" in tags:
        return "advice"
    if artifact_type in {"preference", "mental_model"}:
        return "preferences"
    if memory_layer == "bridge_world":
        return "facts"
    if memory_layer == "personal_derived" or artifact_type == "observation":
        return "discoveries"
    if source_type == "tool_output":
        return "artifacts"
    if memory_layer == "bridge_personal_kb":
        return "references"
    if memory_layer == "personal_raw":
        return "events"
    return "misc"


def derive_loci_metadata(
    item: dict[str, Any],
    metadata: dict[str, str],
    *,
    bank_id: str | None,
) -> dict[str, str]:
    source_file = str(metadata.get("source_file") or "")
    chunk_part = str(metadata.get("chunk_id") or metadata.get("chunk_index") or "0")
    source_ref = str(metadata.get("source_ref") or (f"{Path(source_file).name}#{chunk_part}" if source_file else ""))

    base_bank = str(bank_id or metadata.get("bank_id") or metadata.get("user_id") or "default").strip()
    wing = str(
        metadata.get("wing")
        or metadata.get("user_id")
        or metadata.get("thread_id")
        or base_bank
        or "general"
    ).strip()
    room = str(
        metadata.get("room")
        or metadata.get("topic")
        or metadata.get("agent_role")
        or (Path(source_file).stem if source_file else "")
        or str(item.get("fact_type") or metadata.get("fact_type") or "general")
    ).strip()
    hall = _infer_hall(item, metadata)

    wing_slug = _slug(wing, fallback="general")
    room_slug = _slug(room, fallback="general")
    hall_slug = _slug(hall, fallback="misc")
    source_slug = _slug(source_ref or metadata.get("document_id") or chunk_part, fallback="entry")

    closet_id = str(metadata.get("closet_id") or f"closet_{wing_slug}_{room_slug}_{hall_slug}")
    drawer_id = str(metadata.get("drawer_id") or f"drawer_{wing_slug}_{room_slug}_{source_slug}")
    loci_path = f"{wing_slug}/{room_slug}/{hall_slug}"

    return {
        "source_ref": source_ref,
        "provenance_ref": source_ref,
        "wing": wing_slug,
        "room": room_slug,
        "hall": hall_slug,
        "closet_id": closet_id,
        "drawer_id": drawer_id,
        "loci_path": loci_path,
    }


def loci_tags(item: dict[str, Any], loci: dict[str, str]) -> list[str]:
    tags = [str(tag).strip() for tag in list(item.get("tags") or []) if str(tag).strip()]
    tags.extend(
        [
            f"wing:{loci['wing']}",
            f"room:{loci['room']}",
            f"hall:{loci['hall']}",
            f"closet:{loci['closet_id']}",
            f"drawer:{loci['drawer_id']}",
            f"source_ref:{loci['source_ref']}",
        ]
    )

    out: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out
