from __future__ import annotations

import pytest

from bridge.agent_client import AgentClient
from bridge.config import Config


class _FakeResponse:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeHTTPClient:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.kwargs = {}

    def stream(self, *_args: object, **_kwargs: object) -> _FakeResponse:
        self.kwargs = _kwargs
        return _FakeResponse(self._lines)


def _client(lines: list[str]) -> tuple[AgentClient, _FakeHTTPClient]:
    client = AgentClient(
        Config(
            nats_url="nats://example.invalid:4222",
            agent_service_url="http://agent.invalid",
            agent_timeout_sec=5,
            agent_user_id="@agent-alice:matrix.local",
            host="127.0.0.1",
            port=8097,
        )
    )
    fake_http = _FakeHTTPClient(lines)
    client._client = fake_http  # type: ignore[assignment]
    return client, fake_http


@pytest.mark.asyncio
async def test_agent_client_reads_ai_sdk_v6_text_delta() -> None:
    client, fake_http = _client(
        [
            'data: {"type":"start","messageId":"m1"}',
            'data: {"type":"text-start","id":"t1"}',
            'data: {"type":"text-delta","id":"t1","delta":"Hallo "}',
            'data: {"type":"text-delta","id":"t1","delta":"Matrix"}',
            'data: {"type":"finish","finishReason":"stop"}',
        ]
    )

    text = await client.send_message(
        message="hi",
        room_id="!room:matrix.local",
        sender="@alice:matrix.local",
    )

    assert text == "Hallo Matrix"
    assert fake_http.kwargs["headers"] == {"x-auth-user": "@alice:matrix.local"}


@pytest.mark.asyncio
async def test_agent_client_keeps_legacy_text_delta() -> None:
    client, _fake_http = _client(
        [
            'data: {"type":"text_delta","text":"legacy"}',
            'data: {"type":"finish"}',
        ]
    )

    text = await client.send_message(
        message="hi",
        room_id="!room:matrix.local",
        sender="@alice:matrix.local",
    )

    assert text == "legacy"


@pytest.mark.asyncio
async def test_agent_client_includes_matrix_event_metadata_in_context() -> None:
    client, fake_http = _client(['data: {"type":"finish"}'])

    await client.send_message(
        message="hi",
        room_id="!room:matrix.local",
        sender="@alice:matrix.local",
        thread_id="$root",
        matrix_event_id="$event",
        target_agent="research",
        is_thread_reply=True,
    )

    payload = fake_http.kwargs["json"]
    assert payload["threadId"] == "$root"
    assert payload["context"] == (
        "matrix_room:!room:matrix.local sender:@alice:matrix.local "
        "event_id:$event target_agent:research is_thread_reply:true"
    )
