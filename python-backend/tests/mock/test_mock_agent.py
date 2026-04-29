from __future__ import annotations

from fastapi.testclient import TestClient

from mock.mock_agent import app


def test_mock_agent_openai_chat_completions_shape():
    client = TestClient(app)

    response = client.post(
        "/chat/completions",
        json={
            "model": "mock/local",
            "messages": [
                {"role": "system", "content": "test"},
                {"role": "user", "content": "Reply with runner parity smoke."},
            ],
            "max_tokens": 64,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "mock/local"
    assert body["choices"][0]["message"] == {
        "role": "assistant",
        "content": "runner parity smoke.",
    }
    assert body["usage"]["completion_tokens"] == 3


def test_mock_agent_openai_v1_alias():
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock/local",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Mock LLM response."
