from __future__ import annotations

from ingestion.detectors.base import DetectionResult
from ingestion.detectors.registry import DetectorRegistry


class PlainTextMagic:
    def detect(self, **_: object) -> DetectionResult:
        return DetectionResult(mime_type="text/plain", extension=".md")


def test_known_extension_overrides_generic_magic_result(tmp_path) -> None:
    source = tmp_path / "paper.md"
    source.write_text("# Title\n\nBody", encoding="utf-8")
    registry = DetectorRegistry()
    registry._magic = PlainTextMagic()  # noqa: SLF001

    result = registry.detect(path=source, data=source.read_bytes(), filename=source.name)

    assert result.mime_type == "text/markdown"
