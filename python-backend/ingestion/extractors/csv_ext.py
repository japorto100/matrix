"""CSV file extractor — convert to markdown table."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from ingestion.core.types import ExtractedTable
from ingestion.extractors.base import DocumentExtractor, ExtractedDocument


class CSVExtractor(DocumentExtractor):
    """Convert CSV to markdown table."""

    name = "csv"

    def is_available(self) -> bool:
        return True

    def extract(self, path: Path) -> ExtractedDocument:
        text = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if not rows:
            return ExtractedDocument(
                doc_id="",
                source_path=path,
                extractor=self.name,
                content_md="",
                content_json={"rows": []},
            )

        header, *body = rows
        md_lines: list[str] = []
        md_lines.append("| " + " | ".join(header) + " |")
        md_lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in body:
            row += [""] * (len(header) - len(row))
            md_lines.append("| " + " | ".join(row[: len(header)]) + " |")
        content_md = "\n".join(md_lines)

        table = ExtractedTable(
            id="table_01",
            page=0,
            content_md=content_md,
            content_csv=text,
        )

        return ExtractedDocument(
            doc_id="",
            source_path=path,
            extractor=self.name,
            content_md=content_md,
            content_json={"rows": rows, "header": header},
            tables=[table],
        )
