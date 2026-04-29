from __future__ import annotations

import os
import uuid

import pytest

from memory_fusion.embeddings import DeterministicEmbedder
from memory_fusion.mempalace_engine import MempalaceMemoryEngine

pytestmark = pytest.mark.asyncio


class _FailingEmbedder(DeterministicEmbedder):
    model = "deterministic-test-8d"

    async def embed(self, texts):
        raise RuntimeError("embedding provider down")


async def test_mempalace_engine_stores_verbatim_loci_in_postgres() -> None:
    db_url = os.environ.get("MEMPALACE_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        pytest.skip("requires HINDSIGHT_DB_URL or MEMPALACE_DB_URL")

    bank_id = f"test_bank_{uuid.uuid4().hex}"
    engine = MempalaceMemoryEngine(
        db_url=db_url,
        embedder=DeterministicEmbedder(),
    )
    await engine.initialize()

    try:
        stored = await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[
                {
                    "content": "The Matrix strategy agent should preserve verbatim tool outputs before compaction.",
                    "fact_type": "experience",
                    "metadata": {
                        "room": "memory-fusion",
                        "hall": "events",
                        "thread_id": "thread-1",
                        "session_id": "session-1",
                        "source_ref": "session.jsonl#1",
                    },
                    "tags": ["tool_output"],
                    "document_id": "doc-1",
                },
                {
                    "content": "A separate Matrix session stores a different durable memory.",
                    "fact_type": "experience",
                    "metadata": {
                        "room": "memory-fusion",
                        "hall": "events",
                        "thread_id": "thread-2",
                        "session_id": "session-2",
                        "source_ref": "session.jsonl#2",
                    },
                    "tags": ["tool_output"],
                    "document_id": "doc-2",
                }
            ],
        )

        drawer_id = stored[0][0]
        other_drawer_id = stored[1][0]
        unit = await engine.get_memory_unit(unit_id=drawer_id)
        assert unit is not None
        assert unit["metadata"]["wing"] == bank_id.replace("_", "-")
        assert unit["metadata"]["room"] == "memory-fusion"
        assert unit["metadata"]["hall"] == "events"
        assert unit["metadata"]["thread_id"] == "thread-1"
        assert unit["metadata"]["session_id"] == "session-1"
        assert "drawer:" + drawer_id in unit["tags"]

        listed = await engine.list_memory_units(bank_id=bank_id, room="memory-fusion")
        assert listed["total"] == 2
        assert {item["id"] for item in listed["items"]} == {drawer_id, other_drawer_id}

        thread_scoped = await engine.list_memory_units(
            bank_id=bank_id,
            room="memory-fusion",
            thread_id="thread-1",
        )
        assert thread_scoped["total"] == 1
        assert thread_scoped["items"][0]["id"] == drawer_id
        assert thread_scoped["items"][0]["content"].startswith("The Matrix strategy agent")

        session_scoped = await engine.list_memory_units(
            bank_id=bank_id,
            room="memory-fusion",
            session_id="session-1",
        )
        assert session_scoped["total"] == 1
        assert session_scoped["items"][0]["id"] == drawer_id

        recalled = await engine.recall_async(
            bank_id=bank_id,
            query="preserve verbatim tool outputs",
            room="memory-fusion",
        )
        assert recalled.results
        assert any(result.id == drawer_id for result in recalled.results)

        status = await engine.status()
        assert status["provider"] == "mempalace-postgres"
        assert status["storage"] == "postgres-pgvector"

        with pytest.raises(ValueError, match="unscoped"):
            await engine.delete_memory_units_by_scope(bank_id=bank_id)

        deleted = await engine.delete_memory_units_by_scope(
            bank_id=bank_id,
            room="memory-fusion",
            thread_id="thread-1",
            session_id="session-1",
        )
        assert deleted == {"deleted": 1, "bank_id": bank_id}
        assert await engine.get_memory_unit(unit_id=drawer_id) is None
        assert await engine.get_memory_unit(unit_id=other_drawer_id) is not None

        remaining = await engine.list_memory_units(bank_id=bank_id, room="memory-fusion")
        assert remaining["total"] == 1
        assert remaining["items"][0]["id"] == other_drawer_id

        archived = await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[
                {
                    "content": "Pre-save archive captures the full visible context before compaction.",
                    "fact_type": "experience",
                    "metadata": {
                        "room": "memory-fusion",
                        "hall": "archives",
                        "thread_id": "thread-archive",
                        "session_id": "session-archive",
                        "source_ref": "session.jsonl#pre-save",
                    },
                    "tags": ["pre_compress", "verbatim_archive"],
                    "document_id": "doc-archive",
                }
            ],
            defer_embedding=True,
        )
        archive_id = archived[0][0]
        archive_unit = await engine.get_memory_unit(unit_id=archive_id)
        assert archive_unit is not None
        assert archive_unit["metadata"]["embedding_status"] == "pending"
        assert archive_unit["metadata"]["embedding_deferred"] is True

        hydrated = await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[
                {
                    "content": "Pre-save archive captures the full visible context before compaction.",
                    "fact_type": "experience",
                    "metadata": {
                        "room": "memory-fusion",
                        "hall": "archives",
                        "thread_id": "thread-archive",
                        "session_id": "session-archive",
                        "source_ref": "session.jsonl#pre-save",
                    },
                    "tags": ["pre_compress", "verbatim_archive"],
                    "document_id": "doc-archive",
                }
            ],
        )
        assert hydrated[0][0] == archive_id
        archive_unit = await engine.get_memory_unit(unit_id=archive_id)
        assert archive_unit is not None
        assert archive_unit["metadata"]["embedding_status"] == "ready"
        assert archive_unit["metadata"]["embedding_deferred"] is False
    finally:
        banks = await engine.list_memory_units(bank_id=bank_id, limit=100)
        for item in banks["items"]:
            await engine.delete_memory_unit(unit_id=str(item["id"]))


async def test_mempalace_hydrates_pending_embeddings_and_marks_failures() -> None:
    db_url = os.environ.get("MEMPALACE_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        pytest.skip("requires HINDSIGHT_DB_URL or MEMPALACE_DB_URL")

    bank_id = f"test_bank_hydrate_{uuid.uuid4().hex}"
    engine = MempalaceMemoryEngine(
        db_url=db_url,
        embedder=DeterministicEmbedder(),
    )
    await engine.initialize()

    try:
        pending = await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[
                {
                    "content": "Hydration worker should attach embeddings after a fast verbatim pre-save.",
                    "fact_type": "experience",
                    "metadata": {
                        "room": "memory-fusion",
                        "hall": "archives",
                        "thread_id": "thread-hydrate",
                        "session_id": "session-hydrate",
                        "source_ref": "session.jsonl#hydrate",
                    },
                    "tags": ["pre_compress", "verbatim_archive"],
                    "document_id": "doc-hydrate",
                }
            ],
            defer_embedding=True,
        )
        drawer_id = pending[0][0]
        before = await engine.get_memory_unit(unit_id=drawer_id)
        assert before is not None
        assert before["metadata"]["embedding_status"] == "pending"

        result = await engine.hydrate_pending_embeddings(bank_id=bank_id, limit=10)

        assert result["scanned"] == 1
        assert result["hydrated"] == [drawer_id]
        assert result["failed"] == []
        after = await engine.get_memory_unit(unit_id=drawer_id)
        assert after is not None
        assert after["metadata"]["embedding_status"] == "ready"
        assert after["metadata"]["embedding_deferred"] is False
        assert after["metadata"]["embedding_hydrated_at"]

        failed = await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[
                {
                    "content": "Hydration worker should mark provider failures without losing verbatim content.",
                    "fact_type": "experience",
                    "metadata": {
                        "room": "memory-fusion",
                        "hall": "archives",
                        "thread_id": "thread-fail",
                        "session_id": "session-fail",
                        "source_ref": "session.jsonl#fail",
                    },
                    "document_id": "doc-fail",
                }
            ],
            defer_embedding=True,
        )
        failed_id = failed[0][0]
        failing_engine = MempalaceMemoryEngine(
            db_url=db_url,
            embedder=_FailingEmbedder(),
        )
        await failing_engine.initialize()

        failed_result = await failing_engine.hydrate_pending_embeddings(
            bank_id=bank_id,
            limit=10,
        )

        assert failed_result["scanned"] == 1
        assert failed_result["hydrated"] == []
        assert failed_result["failed"][0]["drawer_id"] == failed_id
        failed_unit = await engine.get_memory_unit(unit_id=failed_id)
        assert failed_unit is not None
        assert failed_unit["metadata"]["embedding_status"] == "failed"
        assert "embedding provider down" in failed_unit["metadata"]["embedding_failed_reason"]
        status = await engine.status()
        assert status["embedding_failed"] >= 1
    finally:
        banks = await engine.list_memory_units(bank_id=bank_id, limit=100)
        for item in banks["items"]:
            await engine.delete_memory_unit(unit_id=str(item["id"]))
