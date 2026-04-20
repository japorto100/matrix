"""Tests for agent/titles/generator.py."""
from __future__ import annotations

import pytest

from agent.titles import generator as gen


def test_sanitize_strips_quotes_and_whitespace():
    assert gen._sanitize('  "Portfolio Briefing"  ', max_words=7) == "Portfolio Briefing"


def test_sanitize_caps_word_count():
    raw = "one two three four five six seven eight nine"
    assert gen._sanitize(raw, max_words=5) == "one two three four five"


def test_sanitize_drops_trailing_punct():
    assert gen._sanitize("Meeting Recap!", max_words=7) == "Meeting Recap"


def test_sanitize_takes_first_line():
    raw = "Portfolio Brief\nexplanatory aside about why"
    assert gen._sanitize(raw, max_words=7) == "Portfolio Brief"


def test_sanitize_empty_returns_empty():
    assert gen._sanitize("", max_words=7) == ""
    assert gen._sanitize("   ", max_words=7) == ""


@pytest.mark.asyncio
async def test_generate_title_skips_without_service_key(monkeypatch):
    # Ensure env-var is absent.
    monkeypatch.delenv("MATRIX_TITLE_GEN_KEY", raising=False)
    result = await gen.generate_title(
        user_message="hi", assistant_reply="hello"
    )
    assert result is None


@pytest.mark.asyncio
async def test_generate_title_skips_empty_input():
    result = await gen.generate_title(user_message="", assistant_reply="hello")
    assert result is None
    result = await gen.generate_title(user_message="hi", assistant_reply="")
    assert result is None


@pytest.mark.asyncio
async def test_generate_title_returns_sanitized_llm_output(monkeypatch):
    monkeypatch.setenv("MATRIX_TITLE_GEN_KEY", "test-key")
    monkeypatch.setenv("MATRIX_TITLE_GEN_MODEL", "claude-haiku-4-5-20251001")

    class _Choice:
        class message:  # noqa: N801
            content = ' "Weekly Portfolio Review".  '

    class _Resp:
        choices = [_Choice()]

    async def _fake_acompletion(**kwargs):
        assert kwargs["api_key"] == "test-key"
        return _Resp()

    # litellm is a deep import — patch it via monkeypatch through sys.modules.
    import types

    fake = types.SimpleNamespace(acompletion=_fake_acompletion)
    monkeypatch.setitem(__import__("sys").modules, "litellm", fake)

    result = await gen.generate_title(
        user_message="Give me a market summary", assistant_reply="Sure, ..."
    )
    assert result == "Weekly Portfolio Review"


@pytest.mark.asyncio
async def test_generate_title_fails_soft_on_llm_error(monkeypatch):
    monkeypatch.setenv("MATRIX_TITLE_GEN_KEY", "test-key")

    async def _raising_acompletion(**kwargs):
        raise RuntimeError("boom")

    import types

    fake = types.SimpleNamespace(acompletion=_raising_acompletion)
    monkeypatch.setitem(__import__("sys").modules, "litellm", fake)

    result = await gen.generate_title(
        user_message="hi", assistant_reply="hello"
    )
    assert result is None


@pytest.mark.asyncio
async def test_persist_fails_soft_on_empty_inputs():
    assert (await gen.persist_session_title("", "Title")) is False
    assert (await gen.persist_session_title("sid", "")) is False
