"""Section-aware markdown chunker.

Adopted from paperwatcher/paperwatcher/core/doc_extractor/chunking.py
with the addition of langchain RecursiveCharacterTextSplitter as a fallback
for non-markdown content.
"""

from __future__ import annotations

import re

from ingestion.chunkers.base import Chunker
from ingestion.core.types import ExtractedChunk, ExtractedDocument


class TokenChunker(Chunker):
    """Section-aware chunker.

    Default behavior matches paperwatcher: splits on markdown headings, then
    further splits oversized sections by paragraphs to stay under chunk_size words.

    For non-markdown content (no headings), falls back to langchain
    RecursiveCharacterTextSplitter with character-based splits.
    """

    name = "token"

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, doc: ExtractedDocument) -> list[ExtractedChunk]:
        text = doc.content_md or ""
        if not text.strip():
            return []

        if "#" in text:
            chunks = self._chunk_markdown(text, doc.doc_id)
        else:
            chunks = self._chunk_recursive(text, doc.doc_id)

        doc.chunks = chunks
        doc.chunk_count = len(chunks)
        return chunks

    def _chunk_markdown(self, md_text: str, doc_id: str) -> list[ExtractedChunk]:
        """Section-aware split on heading boundaries."""
        sections = re.split(r"(?=^#{1,4}\s+)", md_text, flags=re.MULTILINE)
        chunks: list[ExtractedChunk] = []
        idx = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            heading_match = re.match(r"^(#{1,4})\s+(.+)", section)
            section_title = heading_match.group(2).strip() if heading_match else ""

            words = section.split()
            if len(words) <= self.chunk_size:
                chunks.append(
                    ExtractedChunk(
                        id=f"chunk_{idx:03d}",
                        text=section,
                        section=section_title,
                        token_count=len(words),
                        chunk_type="text",
                    )
                )
                idx += 1
            else:
                paragraphs = section.split("\n\n")
                current: list[str] = []
                current_len = 0
                for para in paragraphs:
                    para_len = len(para.split())
                    if current_len + para_len > self.chunk_size and current:
                        chunks.append(
                            ExtractedChunk(
                                id=f"chunk_{idx:03d}",
                                text="\n\n".join(current),
                                section=section_title,
                                token_count=current_len,
                                chunk_type="text",
                            )
                        )
                        idx += 1
                        current = []
                        current_len = 0
                    current.append(para)
                    current_len += para_len
                if current:
                    chunks.append(
                        ExtractedChunk(
                            id=f"chunk_{idx:03d}",
                            text="\n\n".join(current),
                            section=section_title,
                            token_count=current_len,
                            chunk_type="text",
                        )
                    )
                    idx += 1

        return chunks

    def _chunk_recursive(self, text: str, doc_id: str) -> list[ExtractedChunk]:
        """Char-based fallback for non-markdown content."""
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            return self._chunk_naive(text)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size * 4,  # words → roughly chars
            chunk_overlap=self.chunk_overlap * 4,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        parts = splitter.split_text(text)
        return [
            ExtractedChunk(
                id=f"chunk_{i:03d}",
                text=part,
                token_count=len(part.split()),
                chunk_type="text",
            )
            for i, part in enumerate(parts)
        ]

    def _chunk_naive(self, text: str) -> list[ExtractedChunk]:
        """Last-resort word-based chunker (no langchain)."""
        words = text.split()
        chunks: list[ExtractedChunk] = []
        step = self.chunk_size - self.chunk_overlap
        for i in range(0, len(words), step):
            piece = " ".join(words[i : i + self.chunk_size])
            chunks.append(
                ExtractedChunk(
                    id=f"chunk_{len(chunks):03d}",
                    text=piece,
                    token_count=len(piece.split()),
                    chunk_type="text",
                )
            )
        return chunks
