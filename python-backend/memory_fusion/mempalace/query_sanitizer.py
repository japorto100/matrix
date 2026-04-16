"""Vendored from MemPalace: search-query contamination mitigation."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("memory_fusion.mempalace")

MAX_QUERY_LENGTH = 250
SAFE_QUERY_LENGTH = 200
MIN_QUERY_LENGTH = 10
QUOTE_CHARS = {"'", '"'}
_SENTENCE_SPLIT = re.compile(r"[.!?。！？\n]+")
_QUESTION_MARK = re.compile(r'[?？]\s*["\']?\s*$')


def sanitize_query(raw_query: str) -> dict:
    """Extract the likely search intent from a contaminated prompt+query string."""
    if not raw_query or not raw_query.strip():
        return {
            "clean_query": raw_query or "",
            "was_sanitized": False,
            "original_length": len(raw_query) if raw_query else 0,
            "clean_length": len(raw_query) if raw_query else 0,
            "method": "passthrough",
        }

    raw_query = raw_query.strip()
    original_length = len(raw_query)

    def _strip_wrapping_quotes(candidate: str) -> str:
        candidate = candidate.strip()
        while (
            len(candidate) >= 2
            and candidate[:1] in QUOTE_CHARS
            and candidate[:1] == candidate[-1:]
        ):
            candidate = candidate[1:-1].strip()
            if not candidate:
                return ""
        if candidate[:1] in QUOTE_CHARS:
            candidate = candidate[1:].strip()
        if candidate[-1:] in QUOTE_CHARS:
            candidate = candidate[:-1].strip()
        return candidate

    def _trim_candidate(candidate: str) -> str:
        candidate = _strip_wrapping_quotes(candidate)
        if len(candidate) <= MAX_QUERY_LENGTH:
            return candidate

        nested_fragments = [
            _strip_wrapping_quotes(frag)
            for frag in _SENTENCE_SPLIT.split(candidate)
            if frag.strip()
        ]
        for frag in reversed(nested_fragments):
            if MIN_QUERY_LENGTH <= len(frag) <= MAX_QUERY_LENGTH:
                return frag

        return candidate[-MAX_QUERY_LENGTH:].strip()

    if original_length <= SAFE_QUERY_LENGTH:
        return {
            "clean_query": raw_query,
            "was_sanitized": False,
            "original_length": original_length,
            "clean_length": original_length,
            "method": "passthrough",
        }

    all_segments = [segment.strip() for segment in raw_query.split("\n") if segment.strip()]
    question_sentences = [seg for seg in reversed(all_segments) if _QUESTION_MARK.search(seg)]

    if not question_sentences:
        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(raw_query) if s.strip()]
        for sent in reversed(sentences):
            if "?" in sent or "？" in sent:
                question_sentences.append(sent)

    if question_sentences:
        candidate = question_sentences[0].strip()
        if len(candidate) >= MIN_QUERY_LENGTH:
            if len(candidate) > MAX_QUERY_LENGTH:
                candidate = _trim_candidate(candidate)
            logger.warning(
                "Query sanitized: %d -> %d chars (question_extraction)",
                original_length,
                len(candidate),
            )
            return {
                "clean_query": candidate,
                "was_sanitized": True,
                "original_length": original_length,
                "clean_length": len(candidate),
                "method": "question_extraction",
            }

    for seg in reversed(all_segments):
        if len(seg) >= MIN_QUERY_LENGTH:
            candidate = _trim_candidate(seg)
            if len(candidate) < MIN_QUERY_LENGTH:
                continue
            logger.warning(
                "Query sanitized: %d -> %d chars (tail_sentence)",
                original_length,
                len(candidate),
            )
            return {
                "clean_query": candidate,
                "was_sanitized": True,
                "original_length": original_length,
                "clean_length": len(candidate),
                "method": "tail_sentence",
            }

    candidate = raw_query[-MAX_QUERY_LENGTH:].strip()
    logger.warning(
        "Query sanitized: %d -> %d chars (tail_truncation)",
        original_length,
        len(candidate),
    )
    return {
        "clean_query": candidate,
        "was_sanitized": True,
        "original_length": original_length,
        "clean_length": len(candidate),
        "method": "tail_truncation",
    }
