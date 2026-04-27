from __future__ import annotations

import types

import pytest
from ingestion.core.exceptions import ExtractionError
from ingestion.extractors.markitdown_ext import MarkItDownExtractor
from ingestion.extractors.registry import ExtractorRegistry


def test_registry_exposes_markitdown_as_optional_extractor() -> None:
    registry = ExtractorRegistry()

    extractor = registry.get("markitdown")

    assert isinstance(extractor, MarkItDownExtractor)


def test_markitdown_extractor_reports_unavailable_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)

    assert MarkItDownExtractor().is_available() is False


def test_markitdown_extractor_uses_text_content_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    source = tmp_path / "sample.docx"
    source.write_text("unused", encoding="utf-8")

    class DummyMarkItDown:
        def convert(self, path: str) -> object:
            assert path == str(source)
            return types.SimpleNamespace(text_content="# Title\n\nBody")

    monkeypatch.setitem(
        __import__("sys").modules,
        "markitdown",
        types.SimpleNamespace(MarkItDown=DummyMarkItDown),
    )

    doc = MarkItDownExtractor().extract(source)

    assert doc.extractor == "markitdown"
    assert doc.content_md == "# Title\n\nBody"
    assert doc.content_json["converter"] == "microsoft-markitdown"
    assert doc.section_count == 1


def test_markitdown_extractor_fails_on_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    source = tmp_path / "empty.pdf"
    source.write_bytes(b"%PDF")

    class DummyMarkItDown:
        def convert(self, path: str) -> object:
            return types.SimpleNamespace(text_content="")

    monkeypatch.setitem(
        __import__("sys").modules,
        "markitdown",
        types.SimpleNamespace(MarkItDown=DummyMarkItDown),
    )

    with pytest.raises(ExtractionError, match="empty markdown"):
        MarkItDownExtractor().extract(source)
