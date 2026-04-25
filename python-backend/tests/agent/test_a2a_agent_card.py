from __future__ import annotations

from agent.a2a.agent_card import TRADING_AGENT_CARDS


def test_trading_agent_cards_cover_six_roles_and_serialize() -> None:
    assert set(TRADING_AGENT_CARDS) == {
        "fundamentals",
        "sentiment",
        "technical",
        "researcher",
        "trader",
        "risk_manager",
    }

    for card in TRADING_AGENT_CARDS.values():
        payload = card.to_dict()
        assert payload["name"]
        assert payload["description"]
        assert payload["version"]
        assert payload["default_input_modes"] == ["text/plain"]
        assert payload["default_output_modes"] == ["text/plain"]
        assert payload["capabilities"]["streaming"] is True
        assert payload["skills"]
        assert payload["skills"][0]["id"]
