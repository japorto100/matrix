from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from experiments.memory_eval.run_long_context_smoke import build_long_context_fixture
from memory_fusion.fusion_engine import FusionMemoryEngine


@dataclass
class _FakeFact:
    text: str
    metadata: dict[str, str]
    fact_type: str = "experience"
    document_id: str | None = None
    chunk_id: str | None = None


class _FakeEngine:
    def __init__(self, *, recall_results=None, retain_return=None, banks=None, memory_units=None, documents=None, document=None):
        self.recall_results = recall_results or []
        self.retain_return = retain_return or [["id-1"]]
        self.banks = banks or []
        self.memory_units = memory_units or {"items": [], "total": 0}
        self.documents = documents or {"items": [], "total": 0}
        self.document = document
        self.calls: list[tuple[str, tuple, dict]] = []

    async def recall_async(self, *args, **kwargs):
        self.calls.append(("recall_async", args, kwargs))
        return SimpleNamespace(results=self.recall_results, entities={}, chunks={})

    async def retain_batch_async(self, *args, **kwargs):
        self.calls.append(("retain_batch_async", args, kwargs))
        return self.retain_return

    async def list_banks(self, *args, **kwargs):
        self.calls.append(("list_banks", args, kwargs))
        return self.banks

    async def list_memory_units(self, *args, **kwargs):
        self.calls.append(("list_memory_units", args, kwargs))
        return self.memory_units

    async def list_documents(self, *args, **kwargs):
        self.calls.append(("list_documents", args, kwargs))
        return self.documents

    async def get_document(self, *args, **kwargs):
        self.calls.append(("get_document", args, kwargs))
        return self.document

    async def health_check(self):
        return {"ok": True}


@pytest.mark.asyncio
async def test_recall_sanitizes_query_and_merges_summary_verbatim() -> None:
    summary_engine = _FakeEngine(
        recall_results=[
            _FakeFact(
                text="Summary answer",
                metadata={"source_ref": "session-001.jsonl#0", "fact_type": "experience"},
            )
        ]
    )
    verbatim_engine = _FakeEngine(
        recall_results=[
            _FakeFact(
                text="The archive token was raven-001-abcdef.",
                metadata={
                    "source_ref": "session-001.jsonl#0",
                    "fact_type": "experience",
                    "chunk_id": "0",
                    "document_id": "session-001.jsonl#0",
                },
                document_id="session-001.jsonl#0",
                chunk_id="0",
            )
        ]
    )
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=verbatim_engine,
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )
    contaminated_query = (
        "System prompt with a lot of extra context that should not become the retrieval query. " * 4
        + "\nUser context with more instructions that should also be ignored. "
        + "\nWhat archive token was mentioned in session 1?"
    )

    fused = await engine.recall(
        bank_id="user_1",
        query=contaminated_query,
        request_context=object(),
        route="fusion",
    )

    assert len(fused) == 1
    assert fused[0].providers == ["summary", "verbatim"]
    assert fused[0].metadata["summary_text"] == "Summary answer"
    assert fused[0].metadata["verbatim_text"] == "The archive token was raven-001-abcdef."

    summary_call = summary_engine.calls[0]
    verbatim_call = verbatim_engine.calls[0]
    assert summary_call[1][1] == "What archive token was mentioned in session 1?"
    assert verbatim_call[1][1] == "What archive token was mentioned in session 1?"


@pytest.mark.asyncio
async def test_retain_batch_adds_route_tags_and_provenance() -> None:
    summary_engine = _FakeEngine(retain_return=[["summary-id"]])
    verbatim_engine = _FakeEngine(retain_return=[["verbatim-id"]])
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=verbatim_engine,
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    result = await engine.retain_batch_async(
        bank_id="user_1",
        contents=[
            {
                "content": "Session note",
                "tags": ["alpha"],
                "metadata": {
                    "source_file": "session-001.jsonl",
                    "chunk_index": "0",
                    "wing": "user_1",
                    "room": "experience",
                },
            }
        ],
        request_context=object(),
        document_tags=["bench"],
    )

    assert result == [["summary-id", "verbatim-id"]]

    summary_call = summary_engine.calls[0]
    verbatim_call = verbatim_engine.calls[0]
    summary_item = summary_call[2]["contents"][0]
    verbatim_item = verbatim_call[2]["contents"][0]

    assert summary_item["metadata"]["source_ref"] == "session-001.jsonl#0"
    assert verbatim_item["metadata"]["provenance_ref"] == "session-001.jsonl#0"
    assert "wing:user-1" in summary_item["tags"]
    assert "room:experience" in verbatim_item["tags"]
    assert summary_item["metadata"]["hall"] == "events"
    assert summary_item["metadata"]["closet_id"] == "closet_user-1_experience_events"
    assert verbatim_item["metadata"]["drawer_id"] == "drawer_user-1_experience_session-001-jsonl-0"
    assert "hall:events" in summary_item["tags"]
    assert "closet:closet_user-1_experience_events" in summary_item["tags"]
    assert "drawer:drawer_user-1_experience_session-001-jsonl-0" in verbatim_item["tags"]
    assert summary_call[2]["document_tags"] == ["bench", "fusion:summary"]
    assert verbatim_call[2]["document_tags"] == ["bench", "fusion:verbatim"]
    assert summary_item["metadata"]["memory_layer"] == "personal_raw"
    assert summary_item["metadata"]["source_type"] == "user_input"
    assert summary_item["metadata"]["artifact_type"] == "chat_turn"
    assert summary_item["metadata"]["evidence_kind"] == "primary"


@pytest.mark.asyncio
async def test_list_banks_merges_route_banks() -> None:
    summary_engine = _FakeEngine(
        banks=[
            {
                "bank_id": "user_1__summary",
                "name": "User 1",
                "mission": "summary mission",
            }
        ]
    )
    verbatim_engine = _FakeEngine(
        banks=[
            {
                "bank_id": "user_1__verbatim",
                "name": "User 1 verbatim",
            }
        ]
    )
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=verbatim_engine,
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    banks = await engine.list_banks(request_context=object())

    assert banks == [
        {
            "bank_id": "user_1",
            "route_bank_ids": {
                "summary": "user_1__summary",
                "verbatim": "user_1__verbatim",
            },
            "routes_present": ["summary", "verbatim"],
            "name": "User 1",
            "mission": "summary mission",
        }
    ]


@pytest.mark.asyncio
async def test_recall_async_passes_wing_room_as_tags() -> None:
    summary_engine = _FakeEngine(
        recall_results=[
            _FakeFact(text="Summary", metadata={"source_ref": "room-a.jsonl#0", "fact_type": "experience"})
        ]
    )
    verbatim_engine = _FakeEngine()
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=verbatim_engine,
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    await engine.recall_async(
        bank_id="user_1",
        query="What happened?",
        request_context=object(),
        route="summary",
        wing="user_1",
        room="experience",
    )

    call = summary_engine.calls[0]
    assert call[2]["tags"] == ["wing:user_1", "room:experience"]


@pytest.mark.asyncio
async def test_recall_async_passes_full_loci_filters_as_tags() -> None:
    verbatim_engine = _FakeEngine(
        recall_results=[
            _FakeFact(text="Verbatim", metadata={"source_ref": "room-a.jsonl#0", "fact_type": "experience"})
        ]
    )
    engine = FusionMemoryEngine(
        summary_engine=_FakeEngine(),
        verbatim_engine=verbatim_engine,
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    await engine.recall_async(
        bank_id="user_1",
        query="What happened?",
        request_context=object(),
        route="verbatim",
        wing="user_1",
        room="experience",
        hall="events",
        closet="closet_user-1_experience_events",
        drawer="drawer_user-1_experience_session-001-jsonl-0",
    )

    call = verbatim_engine.calls[0]
    assert call[2]["tags"] == [
        "wing:user_1",
        "room:experience",
        "hall:events",
        "closet:closet_user-1_experience_events",
        "drawer:drawer_user-1_experience_session-001-jsonl-0",
    ]


@pytest.mark.asyncio
async def test_retain_batch_sets_semantics_for_raw_and_derived() -> None:
    summary_engine = _FakeEngine(retain_return=[["summary-raw"], ["summary-derived"]])
    verbatim_engine = _FakeEngine(retain_return=[["verbatim-raw"], ["verbatim-derived"]])
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=verbatim_engine,
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    await engine.retain_batch_async(
        bank_id="user_1",
        contents=[
            {
                "content": "The user said they prefer calmer execution.",
                "metadata": {
                    "source_file": "session-raw.jsonl",
                    "chunk_index": "0",
                },
            },
            {
                "content": "Observed preference: the user prefers calm breakout execution.",
                "artifact_type": "preference",
                "metadata": {
                    "source_file": "session-derived.jsonl",
                    "source_ref": "session-derived.jsonl#0",
                    "chunk_id": "0",
                },
            },
        ],
        request_context=object(),
    )

    summary_contents = summary_engine.calls[0][2]["contents"]
    raw_item = summary_contents[0]
    derived_item = summary_contents[1]

    assert raw_item["metadata"]["memory_layer"] == "personal_raw"
    assert raw_item["metadata"]["source_type"] == "user_input"
    assert raw_item["metadata"]["artifact_type"] == "chat_turn"
    assert raw_item["fact_type"] == "experience"

    assert derived_item["metadata"]["memory_layer"] == "personal_derived"
    assert derived_item["metadata"]["artifact_type"] == "preference"
    assert derived_item["metadata"]["source_type"] == "system_observation"
    assert derived_item["metadata"]["requires_evidence_backlinks"] == "true"
    assert derived_item["metadata"]["evidence_backlinks_present"] == "true"
    assert derived_item["fact_type"] == "opinion"


@pytest.mark.asyncio
async def test_explicit_preference_beats_world_like_tag_hints() -> None:
    summary_engine = _FakeEngine(retain_return=[["summary-derived"]])
    verbatim_engine = _FakeEngine(retain_return=[["verbatim-derived"]])
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=verbatim_engine,
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    await engine.retain_batch_async(
        bank_id="user_1",
        contents=[
            {
                "content": "Observed preference with an unfortunate tag collision.",
                "artifact_type": "preference",
                "tags": ["world-claim"],
                "metadata": {
                    "source_file": "session-derived.jsonl",
                    "source_ref": "session-derived.jsonl#0",
                },
            }
        ],
        request_context=object(),
    )

    summary_item = summary_engine.calls[0][2]["contents"][0]
    assert summary_item["metadata"]["memory_layer"] == "personal_derived"
    assert summary_item["metadata"]["artifact_type"] == "preference"


@pytest.mark.asyncio
async def test_retain_batch_rejects_derived_without_evidence_backlinks() -> None:
    engine = FusionMemoryEngine(
        summary_engine=_FakeEngine(),
        verbatim_engine=_FakeEngine(),
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    with pytest.raises(ValueError, match="Derived memory items require evidence backlinks"):
        await engine.retain_batch_async(
            bank_id="user_1",
            contents=[
                {
                    "content": "Observed preference without any provenance.",
                    "artifact_type": "preference",
                    "metadata": {},
                }
            ],
            request_context=object(),
        )


@pytest.mark.asyncio
async def test_recall_async_prefers_verbatim_text_for_evidence_queries() -> None:
    summary_engine = _FakeEngine(
        recall_results=[
            _FakeFact(
                text="Condensed preference summary",
                metadata={
                    "source_ref": "session-001.jsonl#0",
                    "fact_type": "experience",
                    "document_id": "session-001.jsonl#0",
                    "chunk_id": "0",
                },
                document_id="session-001.jsonl#0",
                chunk_id="0",
            )
        ]
    )
    verbatim_engine = _FakeEngine(
        recall_results=[
            _FakeFact(
                text="Exact quote: The archive token was raven-001-abcdef.",
                metadata={
                    "source_ref": "session-001.jsonl#0",
                    "fact_type": "experience",
                    "document_id": "session-001.jsonl#0",
                    "chunk_id": "0",
                },
                document_id="session-001.jsonl#0",
                chunk_id="0",
            )
        ]
    )
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=verbatim_engine,
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    result = await engine.recall_async(
        bank_id="user_1",
        query="What is the exact quote for the archive token?",
        request_context=object(),
        include_chunks=True,
    )

    assert result.results[0].text == "Exact quote: The archive token was raven-001-abcdef."
    assert result.results[0].metadata["memory_layer"] == "personal_raw"
    assert result.results[0].metadata["provenance_ref"] == "session-001.jsonl#0"
    assert result.results[0].metadata["grounding_status"] == "not_applicable"


@pytest.mark.asyncio
async def test_route_specific_recall_async_filters_ungrounded_derived() -> None:
    summary_engine = _FakeEngine(
        recall_results=[
            _FakeFact(text="Ungrounded preference", metadata={}, fact_type="opinion"),
            _FakeFact(
                text="Grounded evidence",
                metadata={"source_ref": "session-001.jsonl#0", "fact_type": "experience"},
                fact_type="experience",
            ),
        ]
    )
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=_FakeEngine(),
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    result = await engine.recall_async(
        bank_id="user_1",
        query="What do we know?",
        request_context=object(),
        route="summary",
    )

    assert len(result.results) == 1
    assert result.results[0].text == "Grounded evidence"
    assert result.results[0].metadata["fusion_route"] == "summary"


@pytest.mark.asyncio
async def test_list_memory_units_filters_ungrounded_derived_items() -> None:
    summary_engine = _FakeEngine(
        memory_units={
            "items": [
                {
                    "id": "derived-1",
                    "text": "Ungrounded derived item",
                    "fact_type": "opinion",
                    "metadata": {"artifact_type": "preference"},
                },
                {
                    "id": "raw-1",
                    "text": "Grounded raw item",
                    "fact_type": "experience",
                    "metadata": {"source_ref": "session-001.jsonl#0"},
                },
            ],
            "total": 2,
        }
    )
    engine = FusionMemoryEngine(
        summary_engine=summary_engine,
        verbatim_engine=_FakeEngine(),
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    result = await engine.list_memory_units(
        bank_id="user_1",
        request_context=object(),
        route="summary",
    )

    assert [item["id"] for item in result["items"]] == ["raw-1"]
    assert result["total"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "expected_fragment"),
    [
        (
            {
                "content": "Saved PDF about market structure.",
                "artifact_type": "pdf",
                "metadata": {"source_file": "market-structure.pdf", "source_ref": "market-structure.pdf#0"},
            },
            "bridge_personal_kb",
        ),
        (
            {
                "content": "Macro claim from external feed.",
                "fact_type": "world",
                "metadata": {"source_file": "macro.jsonl", "source_ref": "macro.jsonl#0"},
            },
            "bridge_world",
        ),
    ],
)
async def test_retain_batch_rejects_kb_and_world_inputs(content: dict[str, str], expected_fragment: str) -> None:
    engine = FusionMemoryEngine(
        summary_engine=_FakeEngine(),
        verbatim_engine=_FakeEngine(),
        summary_llm_provider="openrouter",
        verbatim_llm_provider="openrouter",
        summary_extraction_mode="concise",
        verbatim_extraction_mode="verbatim",
    )

    with pytest.raises(ValueError, match=expected_fragment):
        await engine.retain_batch_async(
            bank_id="user_1",
            contents=[content],
            request_context=object(),
        )


def test_long_context_fixture_uses_new_personal_memory_taxonomy() -> None:
    fixture = build_long_context_fixture(session_count=8)

    profile_items = [item for item in fixture["items"] if str(item["source_ref"]).startswith("profile-")]
    assert profile_items
    assert all(item["fact_type"] != "world" for item in profile_items)
    assert all(item["artifact_type"] == "preference" for item in profile_items)

    categories = {query["category"] for query in fixture["queries"]}
    assert categories == {"verbatim", "derived", "cross_session", "forgetting"}
