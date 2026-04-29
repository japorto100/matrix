"""Provider-agnostic report publishing contract."""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

RendererName = Literal["quarkdown", "markdown-fallback"]


@dataclass(frozen=True)
class Citation:
    citation_id: str
    source_id: str
    title: str
    uri: str = ""
    excerpt: str = ""
    source_type: str = "document"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReportManifest:
    report_id: str
    title: str
    owner: str
    input_sources: tuple[str, ...]
    citations: tuple[Citation, ...]
    renderer: RendererName = "markdown-fallback"
    renderer_version: str = "builtin"
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    checksum: str = ""
    output_files: tuple[str, ...] = ()
    feature_id: str = "027"

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["citations"] = [citation.as_dict() for citation in self.citations]
        return payload


def validate_report_manifest(
    manifest: ReportManifest,
    *,
    source_markdown: str = "",
) -> dict[str, Any]:
    failures: list[str] = []
    if not manifest.report_id:
        failures.append("missing-report-id")
    if not manifest.title:
        failures.append("missing-title")
    if not manifest.owner:
        failures.append("missing-owner")
    if not manifest.input_sources:
        failures.append("missing-input-sources")
    if not manifest.citations:
        failures.append("missing-citations")
    citation_ids = {citation.citation_id for citation in manifest.citations}
    if len(citation_ids) != len(manifest.citations):
        failures.append("duplicate-citation-id")
    for citation in manifest.citations:
        if not citation.source_id:
            failures.append(f"missing-citation-source:{citation.citation_id}")
        marker = f"[{citation.citation_id}]"
        if source_markdown and marker not in source_markdown:
            failures.append(f"citation-not-used:{citation.citation_id}")
    if manifest.checksum and source_markdown:
        expected = compute_checksum(source_markdown)
        if manifest.checksum != expected:
            failures.append("checksum-mismatch")
    return {"passed": not failures, "failures": failures}


def build_report_artifacts(
    *,
    source_markdown: str,
    manifest: ReportManifest,
    output_dir: Path,
) -> dict[str, Any]:
    """Write reproducible report artifacts without invoking external tools."""

    validation = validate_report_manifest(manifest, source_markdown=source_markdown)
    if not validation["passed"]:
        return {"passed": False, "validation": validation, "artifacts": {}}

    report_dir = output_dir / manifest.report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    checksum = compute_checksum(source_markdown)
    source_path = report_dir / "source.md"
    html_path = report_dir / "report.html"
    text_path = report_dir / "report.txt"
    manifest_path = report_dir / "manifest.json"
    source_path.write_text(source_markdown, encoding="utf-8")
    html_path.write_text(fallback_markdown_to_html(source_markdown), encoding="utf-8")
    text_path.write_text(source_markdown, encoding="utf-8")
    materialized = ReportManifest(
        **{
            **manifest.as_dict(),
            "citations": manifest.citations,
            "checksum": checksum,
            "output_files": ("source.md", "report.html", "report.txt"),
        }
    )
    manifest_path.write_text(
        json.dumps(materialized.as_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "passed": True,
        "validation": validation,
        "artifacts": {
            "report_dir": str(report_dir),
            "source": str(source_path),
            "html": str(html_path),
            "text": str(text_path),
            "manifest": str(manifest_path),
            "checksum": checksum,
        },
    }


def fallback_markdown_to_html(source_markdown: str) -> str:
    """Tiny fallback renderer for deterministic tests and safe previews."""

    body_lines = []
    for raw_line in source_markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("# "):
            body_lines.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            body_lines.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line:
            body_lines.append(f"<p>{html.escape(line)}</p>")
    body = "\n".join(body_lines)
    return (
        "<!doctype html>\n"
        '<html><head><meta charset="utf-8"><title>Matrix Report</title></head>'
        f"<body>{body}</body></html>\n"
    )


def compute_checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
