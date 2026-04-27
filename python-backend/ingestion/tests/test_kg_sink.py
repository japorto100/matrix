from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from ingestion.core.types import ExtractedChunk, ExtractedDocument, Job
from ingestion.sinks.kg_sink import KGSink


class FakeKGPipelineClient:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.calls: list[dict] = []

    async def propose(
        self,
        text: str,
        doc_id: str,
        *,
        source_uri: str | None = None,
        evidence_metadata_by_ref: dict[str, dict] | None = None,
        persist: bool = False,
    ) -> dict:
        self.calls.append(
            {
                "text": text,
                "doc_id": doc_id,
                "source_uri": source_uri,
                "evidence_metadata_by_ref": evidence_metadata_by_ref or {},
                "persist": persist,
            }
        )
        return {"proposal_count": 1, "proposals": [{"id": "proposal-1"}]}


def _doc() -> ExtractedDocument:
    return ExtractedDocument(
        doc_id="doc-1",
        source_path=Path("/tmp/source.md"),
        extractor="markdown",
        content_md="EU sanctions Russia.",
    )


def _job() -> Job:
    return Job(
        user_id="meta-harness",
        metadata={
            "chunk_metadata": {
                "chunk-1": {
                    "source_artifact_id": "artifact-1",
                    "source_uri": "file:///papers/sanctions.md",
                    "chunk_hash": "hash-1",
                    "citation_ref": "file:///papers/sanctions.md#chunk=chunk-1",
                    "parser_name": "markdown",
                    "parser_version": "2.0",
                    "chunker_name": "token",
                }
            }
        },
        started_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_kg_sink_emits_source_grounded_claim_proposals_without_persisting() -> None:
    client = FakeKGPipelineClient(enabled=True)
    sink = KGSink(client)  # type: ignore[arg-type]
    chunks = [ExtractedChunk(id="chunk-1", text="EU sanctions Russia.")]

    result = await sink.write_batch(_doc(), chunks, [[0.1, 0.2, 0.3]], _job())

    assert result.written == 1
    assert result.skipped == 0
    assert result.metadata == {"proposal_count": 1, "persisted": False}
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["doc_id"] == "chunk-1"
    assert call["source_uri"] == "file:///papers/sanctions.md"
    assert call["persist"] is False
    evidence_metadata = call["evidence_metadata_by_ref"]["chunk-1"]
    assert evidence_metadata["source_artifact_id"] == "artifact-1"
    assert evidence_metadata["chunk_hash"] == "hash-1"
    assert evidence_metadata["citation_ref"].endswith("#chunk=chunk-1")
    assert evidence_metadata["embedding_dim"] == 3
    assert evidence_metadata["embedding_reused_as_evidence_input"] is True
    assert evidence_metadata["kg_persist"] is False


@pytest.mark.asyncio
async def test_kg_sink_skips_when_pipeline_is_disabled() -> None:
    client = FakeKGPipelineClient(enabled=False)
    sink = KGSink(client)  # type: ignore[arg-type]
    chunks = [ExtractedChunk(id="chunk-1", text="EU sanctions Russia.")]

    result = await sink.write_batch(_doc(), chunks, [[0.1, 0.2, 0.3]], _job())

    assert result.written == 0
    assert result.skipped == 1
    assert result.metadata == {"reason": "kg_pipeline disabled"}
    assert client.calls == []
