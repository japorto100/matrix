"""Control Surface - read-only report artifact index."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from reports.contract import (
    Citation,
    ReportDataArtifact,
    ReportManifest,
    validate_report_manifest,
)

router = APIRouter(tags=["control", "reports"])


def _report_root() -> Path:
    return Path(os.environ.get("MATRIX_REPORT_ARTIFACT_DIR", "data/reports"))


@router.get("/reports")
async def list_reports() -> dict[str, Any]:
    items = _list_report_artifacts(_report_root())
    return {"items": items, "total": len(items)}


def _list_report_artifacts(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    manifests = sorted(root.rglob("manifest.json"))
    items = [_load_report_artifact(path, root) for path in manifests]
    return sorted(
        (item for item in items if item is not None),
        key=lambda item: str(item.get("generated_at") or ""),
        reverse=True,
    )


def _load_report_artifact(manifest_path: Path, root: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = _manifest_from_raw(raw)
    except Exception:  # noqa: BLE001
        return _invalid_manifest_artifact(manifest_path, root)

    source_path = manifest_path.parent / "source.md"
    source_markdown = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    validation = validate_report_manifest(manifest, source_markdown=source_markdown)
    output_files = _output_files(raw.get("output_files") or (), manifest_path, root)
    return {
        "report_id": manifest.report_id,
        "title": manifest.title,
        "owner": manifest.owner,
        "status": _status(validation, raw),
        "renderer": manifest.renderer,
        "renderer_version": manifest.renderer_version,
        "generated_at": manifest.generated_at,
        "checksum": manifest.checksum,
        "manifest_path": _relative(manifest_path, root),
        "input_sources": list(manifest.input_sources),
        "citations": [citation.as_dict() for citation in manifest.citations],
        "data_artifacts": [item.as_dict() for item in manifest.data_artifacts],
        "output_files": output_files,
        "validation": validation,
        "matrix_publication": raw.get("matrix_publication") or {"status": "not_published"},
    }


def _manifest_from_raw(raw: dict[str, Any]) -> ReportManifest:
    citations = tuple(
        Citation(
            citation_id=str(item.get("citation_id") or ""),
            source_id=str(item.get("source_id") or ""),
            title=str(item.get("title") or ""),
            uri=str(item.get("uri") or ""),
            excerpt=str(item.get("excerpt") or ""),
            source_type=str(item.get("source_type") or "document"),
        )
        for item in raw.get("citations") or ()
        if isinstance(item, dict)
    )
    data_artifacts = tuple(
        ReportDataArtifact(
            artifact_id=str(item.get("artifact_id") or ""),
            kind="chart" if item.get("kind") == "chart" else "table",
            title=str(item.get("title") or ""),
            source_id=str(item.get("source_id") or ""),
            columns=tuple(str(column) for column in item.get("columns") or ()),
            rows=tuple(dict(row) for row in item.get("rows") or () if isinstance(row, dict)),
            chart_type=str(item.get("chart_type") or ""),
            unit=str(item.get("unit") or ""),
        )
        for item in raw.get("data_artifacts") or ()
        if isinstance(item, dict)
    )
    renderer = raw.get("renderer")
    return ReportManifest(
        report_id=str(raw.get("report_id") or ""),
        title=str(raw.get("title") or ""),
        owner=str(raw.get("owner") or ""),
        input_sources=tuple(str(item) for item in raw.get("input_sources") or ()),
        citations=citations,
        data_artifacts=data_artifacts,
        renderer="quarkdown" if renderer == "quarkdown" else "markdown-fallback",
        renderer_version=str(raw.get("renderer_version") or "unknown"),
        generated_at=str(raw.get("generated_at") or ""),
        checksum=str(raw.get("checksum") or ""),
        output_files=tuple(str(item) for item in raw.get("output_files") or ()),
        feature_id=str(raw.get("feature_id") or "027"),
    )


def _output_files(raw_output_files: Any, manifest_path: Path, root: Path) -> list[dict[str, Any]]:
    paths = [str(item) for item in raw_output_files if item]
    if "manifest.json" not in paths:
        paths.insert(0, "manifest.json")
    out: list[dict[str, Any]] = []
    for value in paths:
        path = manifest_path.parent / value
        out.append(
            {
                "kind": _output_kind(value),
                "path": _relative(path, root),
                "mime_type": _mime_type(value),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
        )
    return out


def _invalid_manifest_artifact(manifest_path: Path, root: Path) -> dict[str, Any]:
    report_id = manifest_path.parent.name or "unknown-report"
    return {
        "report_id": report_id,
        "title": report_id,
        "owner": "unknown",
        "status": "failed",
        "renderer": "markdown-fallback",
        "renderer_version": "unknown",
        "generated_at": "",
        "checksum": "",
        "manifest_path": _relative(manifest_path, root),
        "input_sources": [],
        "citations": [],
        "data_artifacts": [],
        "output_files": [
            {
                "kind": "manifest",
                "path": _relative(manifest_path, root),
                "mime_type": "application/json",
                "size_bytes": manifest_path.stat().st_size if manifest_path.exists() else None,
            }
        ],
        "validation": {"passed": False, "failures": ["invalid-manifest-json"]},
        "matrix_publication": {"status": "blocked"},
    }


def _status(validation: dict[str, Any], raw: dict[str, Any]) -> str:
    if not validation.get("passed"):
        return "failed"
    publication = raw.get("matrix_publication") or {}
    if publication.get("status") == "published":
        return "published"
    return "validated"


def _output_kind(path: str) -> str:
    name = Path(path).name.lower()
    suffix = Path(path).suffix.lower()
    if name == "manifest.json":
        return "manifest"
    if suffix in {".md", ".qd"}:
        return "source"
    if suffix == ".html":
        return "html"
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".pptx", ".slides"}:
        return "slides"
    if suffix == ".json":
        return "data"
    return "text"


def _mime_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".json": "application/json",
        ".md": "text/markdown",
        ".qd": "text/markdown",
        ".html": "text/html",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
    }.get(suffix, "application/octet-stream")


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
