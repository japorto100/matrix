from __future__ import annotations

import json

from reports.contract import (
    Citation,
    ReportManifest,
    build_report_artifacts,
    compute_checksum,
    fallback_markdown_to_html,
    validate_report_manifest,
)


def _manifest(checksum: str = "") -> ReportManifest:
    return ReportManifest(
        report_id="report-1",
        title="Risk Brief",
        owner="matrix",
        input_sources=("source-a",),
        citations=(
            Citation(
                citation_id="S1",
                source_id="source-a",
                title="Source A",
                uri="https://example.invalid/source-a",
                excerpt="evidence",
            ),
        ),
        checksum=checksum,
    )


def test_report_manifest_validation_requires_citations_and_usage():
    manifest = _manifest()

    result = validate_report_manifest(manifest, source_markdown="# Brief\nNo citation")

    assert result["passed"] is False
    assert "citation-not-used:S1" in result["failures"]


def test_report_manifest_checksum_validation():
    source = "# Brief\nEvidence [S1]"
    manifest = _manifest(checksum=compute_checksum(source))

    result = validate_report_manifest(manifest, source_markdown=source)

    assert result["passed"] is True


def test_fallback_renderer_escapes_html():
    html = fallback_markdown_to_html("# <script>alert(1)</script>")

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_build_report_artifacts_writes_manifest_and_outputs(tmp_path):
    source = "# Risk Brief\nEvidence [S1]"
    result = build_report_artifacts(
        source_markdown=source,
        manifest=_manifest(),
        output_dir=tmp_path,
    )

    assert result["passed"] is True
    artifacts = result["artifacts"]
    manifest = json.loads((tmp_path / "report-1" / "manifest.json").read_text())
    assert artifacts["checksum"] == compute_checksum(source)
    assert manifest["checksum"] == compute_checksum(source)
    assert manifest["output_files"] == ["source.md", "report.html", "report.txt"]
    assert (tmp_path / "report-1" / "report.html").exists()
