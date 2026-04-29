from __future__ import annotations

from reports.contract import Citation, ReportManifest, build_report_artifacts


def _manifest() -> ReportManifest:
    return ReportManifest(
        report_id="report-1",
        title="RAG Summary",
        owner="@agent:example",
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


def test_widget_proposals_derive_pending_report_artifact_items(tmp_path):
    from agent.control.widgets import _list_widget_proposals, _widget_policy

    build_report_artifacts(
        source_markdown="# RAG Summary\nEvidence [S1]",
        manifest=_manifest(),
        output_dir=tmp_path,
    )

    payload = _list_widget_proposals(
        tmp_path,
        _widget_policy(),
        "https://widgets.example",
    )

    assert len(payload) == 1
    proposal = payload[0]
    assert proposal["proposal_id"] == "report-report-1"
    assert proposal["status"] == "pending"
    assert proposal["can_approve"] is True
    assert proposal["report_artifact"]["manifest_id"] == "report-1/manifest.json"
    assert proposal["report_artifact"]["renderer"] == "markdown-fallback"
    assert proposal["fallback_markdown"].startswith("[RAG Summary]")


def test_widget_proposals_block_unsafe_origin(tmp_path):
    from agent.control.widgets import _list_widget_proposals, _widget_policy

    build_report_artifacts(
        source_markdown="# RAG Summary\nEvidence [S1]",
        manifest=_manifest(),
        output_dir=tmp_path,
    )

    payload = _list_widget_proposals(
        tmp_path,
        _widget_policy(),
        "https://blocked.example",
    )

    assert payload[0]["status"] == "blocked"
    assert payload[0]["can_approve"] is False
    assert payload[0]["denial_reasons"] == ["widget-origin-not-allowed"]


async def test_list_widget_proposals_endpoint_uses_configured_root(tmp_path, monkeypatch):
    from agent.control import widgets

    build_report_artifacts(
        source_markdown="# RAG Summary\nEvidence [S1]",
        manifest=_manifest(),
        output_dir=tmp_path,
    )
    monkeypatch.setenv("MATRIX_REPORT_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("MATRIX_WIDGET_APP_BASE_URL", "https://widgets.example")

    payload = await widgets.list_widget_proposals()

    assert payload["contract"] == "matrix-widget-approval/v1"
    assert payload["total"] == 1
    assert payload["summary"]["pending"] == 1
