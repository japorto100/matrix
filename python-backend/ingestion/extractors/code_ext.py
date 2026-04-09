"""Source code extractor — wraps file in markdown code fence."""

from __future__ import annotations

from pathlib import Path

from ingestion.extractors.base import DocumentExtractor, ExtractedDocument

# Map common extensions to language hints for fenced code blocks
_LANG_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".rb": "ruby",
    ".php": "php",
    ".sh": "bash",
    ".zsh": "bash",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
}


class CodeExtractor(DocumentExtractor):
    """Wrap source code in a markdown fenced code block with language hint."""

    name = "code"

    def is_available(self) -> bool:
        return True

    def extract(self, path: Path) -> ExtractedDocument:
        text = path.read_text(encoding="utf-8", errors="replace")
        lang = _LANG_MAP.get(path.suffix.lower(), "")
        content_md = f"```{lang}\n{text}\n```"
        return ExtractedDocument(
            doc_id="",
            source_path=path,
            extractor=self.name,
            content_md=content_md,
            content_json={"language": lang, "source": text},
        )
