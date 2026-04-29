from __future__ import annotations

from reports.contract import Citation, ReportManifest, build_report_artifacts


def _manifest() -> ReportManifest:
    return ReportManifest(
        report_id="report-1",
        title="RAG Summary",
        owner="matrix",
        input_sources=("artifact-a",),
        citations=(
            Citation(
                citation_id="S1",
                source_id="artifact-a",
                title="Artifact A",
                uri="doc://artifact-a",
            ),
        ),
    )


def test_list_report_artifacts_reads_manifest_outputs_and_validation(tmp_path):
    from agent.control.reports import _list_report_artifacts

    build_report_artifacts(
        source_markdown="# RAG Summary\nEvidence [S1]",
        manifest=_manifest(),
        output_dir=tmp_path,
    )

    payload = _list_report_artifacts(tmp_path)

    assert len(payload) == 1
    report = payload[0]
    assert report["report_id"] == "report-1"
    assert report["validation"]["passed"] is True
    assert report["status"] == "validated"
    assert report["matrix_publication"]["status"] == "not_published"
    assert {item["kind"] for item in report["output_files"]} >= {
        "manifest",
        "source",
        "html",
        "text",
    }


def test_list_report_artifacts_surfaces_invalid_manifest(tmp_path):
    from agent.control.reports import _list_report_artifacts

    report_dir = tmp_path / "bad-report"
    report_dir.mkdir()
    (report_dir / "manifest.json").write_text("{not-json", encoding="utf-8")

    payload = _list_report_artifacts(tmp_path)

    assert payload[0]["status"] == "failed"
    assert payload[0]["validation"]["failures"] == ["invalid-manifest-json"]


async def test_list_reports_endpoint_uses_configured_root(tmp_path, monkeypatch):
    from agent.control import reports

    build_report_artifacts(
        source_markdown="# RAG Summary\nEvidence [S1]",
        manifest=_manifest(),
        output_dir=tmp_path,
    )
    monkeypatch.setenv("MATRIX_REPORT_ARTIFACT_DIR", str(tmp_path))

    payload = await reports.list_reports()

    assert payload["total"] == 1
    assert payload["items"][0]["manifest_path"] == "report-1/manifest.json"
