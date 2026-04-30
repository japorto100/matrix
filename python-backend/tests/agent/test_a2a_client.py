from __future__ import annotations

import httpx
import pytest

from agent.a2a.client import A2AClient


@pytest.mark.asyncio
async def test_send_message_collects_ai_sdk_text_delta_field() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/agent/chat"
        assert request.read()
        return httpx.Response(
            200,
            text=(
                'data: {"type":"text-start","id":"t1"}\n\n'
                'data: {"type":"text-delta","id":"t1","delta":"hello"}\n\n'
                'data: {"type":"text-delta","id":"t1","delta":" world"}\n\n'
                'data: {"type":"text-end","id":"t1"}\n\n'
            ),
            headers={"content-type": "text/event-stream"},
        )

    client = A2AClient()
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    try:
        task = await client.send_message(
            "http://agent.local",
            "analyze AAPL",
            task_id="11111111-1111-1111-1111-111111111111",
        )
    finally:
        await client.close()

    assert task.state == "completed"
    assert task.task_id == "11111111-1111-1111-1111-111111111111"
    assert task.result == "hello world"


@pytest.mark.asyncio
async def test_send_message_keeps_legacy_text_field_fallback() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text='data: {"type":"text_delta","text":"legacy"}\n\n',
            headers={"content-type": "text/event-stream"},
        )

    client = A2AClient()
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    try:
        task = await client.send_message("http://agent.local", "ping")
    finally:
        await client.close()

    assert task.state == "completed"
    assert task.result == "legacy"


@pytest.mark.asyncio
async def test_send_message_reports_timeout_state(monkeypatch) -> None:
    client = A2AClient()

    async def raise_timeout(*_args, **_kwargs):
        raise httpx.TimeoutException("slow child")

    monkeypatch.setattr(client._client, "post", raise_timeout)
    try:
        task = await client.send_message("http://agent.local", "ping")
    finally:
        await client.close()

    assert task.state == "timeout"
    assert task.error == "timeout"
