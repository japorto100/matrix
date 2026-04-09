"""HTML file extractor — BeautifulSoup → text + headings → markdown."""

from __future__ import annotations

from pathlib import Path

from ingestion.core.exceptions import ExtractionError
from ingestion.extractors.base import DocumentExtractor, ExtractedDocument


class HTMLExtractor(DocumentExtractor):
    """Extract text + headings from HTML."""

    name = "html"

    def is_available(self) -> bool:
        try:
            import bs4  # noqa: F401

            return True
        except ImportError:
            return False

    def extract(self, path: Path) -> ExtractedDocument:
        try:
            from bs4 import BeautifulSoup
        except ImportError as e:
            raise ExtractionError("beautifulsoup4 is required for HTML extraction") from e

        html = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        # Strip script/style/nav/footer
        for tag in soup(["script", "style", "nav", "footer", "noscript", "iframe"]):
            tag.decompose()

        # Convert to markdown-ish
        lines: list[str] = []
        section_count = 0
        for el in soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code"]
        ):
            text = el.get_text(strip=True)
            if not text:
                continue
            tag = el.name
            if tag.startswith("h") and len(tag) == 2:
                level = int(tag[1])
                lines.append(f"{'#' * level} {text}")
                section_count += 1
            elif tag == "li":
                lines.append(f"- {text}")
            elif tag == "pre" or tag == "code":
                lines.append(f"```\n{text}\n```")
            else:
                lines.append(text)

        content_md = "\n\n".join(lines)
        return ExtractedDocument(
            doc_id="",
            source_path=path,
            extractor=self.name,
            content_md=content_md,
            content_json={"markdown": content_md},
            section_count=section_count,
        )
