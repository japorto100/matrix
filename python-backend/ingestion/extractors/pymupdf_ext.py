"""pymupdf4llm extraction backend (CPU, no ML model, fastest).

Adopted from paperwatcher/paperwatcher/core/doc_extractor/pymupdf_ext.py (1:1).
Only changes: import paths (`from .base` → `from ingestion.extractors.base`).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from ingestion.extractors.base import (
    DocumentExtractor,
    ExtractedDocument,
    ExtractedFigure,
    ExtractedFormula,
    ExtractedTable,
)

logger = logging.getLogger(__name__)


class PyMuPDF4LLMExtractor(DocumentExtractor):
    """Extraction backend using pymupdf4llm.

    Pure CPU, no model download needed. Provides markdown output,
    basic table detection, and optional image extraction.
    """

    name = "pymupdf4llm"
    requires_gpu = False
    requires_model_download = False
    model_size_mb = 0

    def is_available(self) -> bool:
        try:
            import pymupdf4llm  # noqa: F401

            return True
        except ImportError:
            return False

    def extract(self, path: Path) -> ExtractedDocument:
        import pymupdf4llm

        md_text = pymupdf4llm.to_markdown(str(path))

        # Get page count via pymupdf
        try:
            import pymupdf

            pdf_doc = pymupdf.open(str(path))
            page_count = len(pdf_doc)
            pdf_doc.close()
        except ImportError:
            page_count = 0

        tables = self._extract_tables(md_text)
        figures = self._extract_figures(md_text)
        formulas = self._extract_formulas(md_text)
        sections = self._count_sections(md_text)

        return ExtractedDocument(
            doc_id="",
            source_path=path,
            extractor=self.name,
            content_md=md_text,
            content_json={"markdown": md_text},
            tables=tables,
            figures=figures,
            formulas=formulas,
            page_count=page_count,
            section_count=sections,
        )

    def _extract_tables(self, md_text: str) -> list[ExtractedTable]:
        """Extract markdown tables from the converted text."""
        tables: list[ExtractedTable] = []
        table_pattern = re.compile(
            r"((?:^[|].*[|]\s*\n)+)",
            re.MULTILINE,
        )
        for idx, match in enumerate(table_pattern.finditer(md_text)):
            block = match.group(1).strip()
            lines = block.splitlines()
            if len(lines) < 2:
                continue

            # Try to find a caption above the table
            start = match.start()
            pre_text = md_text[:start].rstrip()
            caption = None
            if pre_text:
                last_line = pre_text.splitlines()[-1].strip()
                if re.match(r"(?i)table\s+\d+", last_line):
                    caption = last_line

            # Convert to CSV
            csv_lines: list[str] = []
            for line in lines:
                if re.match(r"^\|[\s\-:]+\|$", line):
                    continue  # Skip separator rows
                cells = [c.strip() for c in line.strip("|").split("|")]
                csv_lines.append(",".join(cells))
            content_csv = "\n".join(csv_lines)

            # Convert to HTML
            html_rows: list[str] = []
            is_header = True
            for line in lines:
                if re.match(r"^\|[\s\-:]+\|$", line):
                    is_header = False
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                tag = "th" if is_header else "td"
                row_html = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
                html_rows.append(f"<tr>{row_html}</tr>")
                if is_header:
                    is_header = False

            content_html = f"<table>{''.join(html_rows)}</table>"

            tables.append(
                ExtractedTable(
                    id=f"table_{idx + 1:02d}",
                    page=0,  # pymupdf4llm md doesn't preserve page info
                    caption=caption,
                    content_md=block,
                    content_csv=content_csv,
                    content_html=content_html,
                )
            )
        return tables

    def _extract_figures(self, md_text: str) -> list[ExtractedFigure]:
        """Extract figure references from markdown text."""
        figures: list[ExtractedFigure] = []
        fig_pattern = re.compile(
            r"(?i)\b(fig(?:ure)?\s*\d+[a-z]?)\b[:.\-]?\s*(.*)",
        )
        seen: set[str] = set()
        for match in fig_pattern.finditer(md_text):
            label = match.group(1).strip()
            if label.lower() in seen:
                continue
            seen.add(label.lower())
            caption = match.group(2).strip() or None
            figures.append(
                ExtractedFigure(
                    id=f"fig_{len(figures) + 1:02d}",
                    page=0,
                    caption=caption,
                    figure_type="other",
                )
            )
        return figures

    def _extract_formulas(self, md_text: str) -> list[ExtractedFormula]:
        """Extract LaTeX formulas from markdown (display and inline)."""
        formulas: list[ExtractedFormula] = []

        # Display math: $$ ... $$
        for match in re.finditer(r"\$\$(.+?)\$\$", md_text, re.DOTALL):
            latex = match.group(1).strip()
            if not latex:
                continue
            start = max(0, match.start() - 100)
            end = min(len(md_text), match.end() + 100)
            context = md_text[start:end].strip()
            formulas.append(
                ExtractedFormula(
                    id=f"formula_{len(formulas) + 1:02d}",
                    page=0,
                    latex=latex,
                    context=context,
                    display=True,
                )
            )

        # Inline math: $ ... $ (single dollar, not doubled)
        for match in re.finditer(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", md_text):
            latex = match.group(1).strip()
            if not latex or len(latex) < 3:
                continue
            start = max(0, match.start() - 80)
            end = min(len(md_text), match.end() + 80)
            context = md_text[start:end].strip()
            formulas.append(
                ExtractedFormula(
                    id=f"formula_{len(formulas) + 1:02d}",
                    page=0,
                    latex=latex,
                    context=context,
                    display=False,
                )
            )

        return formulas

    def _count_sections(self, md_text: str) -> int:
        """Count markdown heading sections."""
        return len(re.findall(r"^#{1,4}\s+", md_text, re.MULTILINE))


def create_extractor() -> PyMuPDF4LLMExtractor:
    """Factory function for the pymupdf4llm backend."""
    return PyMuPDF4LLMExtractor()
