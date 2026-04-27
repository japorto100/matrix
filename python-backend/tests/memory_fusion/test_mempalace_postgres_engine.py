from __future__ import annotations

import os
import uuid

import pytest

from memory_fusion.embeddings import DeterministicEmbedder
from memory_fusion.mempalace_engine import MempalaceMemoryEngine

pytestmark = pytest.mark.asyncio


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
    finally:
        banks = await engine.list_memory_units(bank_id=bank_id, limit=100)
        for item in banks["items"]:
            await engine.delete_memory_unit(unit_id=str(item["id"]))
