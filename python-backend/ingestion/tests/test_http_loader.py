from __future__ import annotations

from ingestion.loaders.http import _filename_from_url


def test_filename_from_url_uses_content_type_when_url_has_no_extension() -> None:
    assert (
        _filename_from_url("https://arxiv.org/pdf/2604.09666", "application/pdf")
        == "2604.09666.pdf"
    )
    assert (
        _filename_from_url("https://example.test/article", "text/html; charset=utf-8")
        == "article.html"
    )


def test_filename_from_url_preserves_existing_extension() -> None:
    assert (
        _filename_from_url("https://example.test/report.markdown", "text/html")
        == "report.markdown"
    )
