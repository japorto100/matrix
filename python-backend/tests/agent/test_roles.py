from __future__ import annotations

from agent.roles import (
    TRADING_ROLE_CONTRACTS,
    TRADING_ROLE_MEMORY,
    TRADING_ROLE_PROMPTS,
    TRADING_ROLE_TOOLS,
    TradingRole,
)


def test_trading_roles_have_complete_runtime_contracts():
    roles = set(TradingRole)

    assert len(roles) == 6
    assert set(TRADING_ROLE_PROMPTS) == roles
    assert set(TRADING_ROLE_TOOLS) == roles
    assert set(TRADING_ROLE_MEMORY) == roles

    for role in roles:
        assert TRADING_ROLE_PROMPTS[role].strip()
        assert TRADING_ROLE_TOOLS[role]
        assert "save_memory" in TRADING_ROLE_TOOLS[role] or role is TradingRole.RISK_MANAGER
        assert "load_memory" in TRADING_ROLE_TOOLS[role]
        assert "memory_write" in TRADING_ROLE_MEMORY[role]
        assert "memory_recall_tags" in TRADING_ROLE_MEMORY[role]


def test_trading_role_decision_contracts_cover_sequential_roles():
    assert {
        TradingRole.RESEARCHER,
        TradingRole.TRADER,
        TradingRole.RISK_MANAGER,
    } <= set(TRADING_ROLE_CONTRACTS)

    assert any("bull" in item.lower() for item in TRADING_ROLE_CONTRACTS[TradingRole.RESEARCHER])
    assert any("bear" in item.lower() for item in TRADING_ROLE_CONTRACTS[TradingRole.RESEARCHER])
    assert any("entry" in item.lower() for item in TRADING_ROLE_CONTRACTS[TradingRole.TRADER])
    assert any("stop loss" in item.lower() for item in TRADING_ROLE_CONTRACTS[TradingRole.TRADER])
    assert any("approval" in item.lower() for item in TRADING_ROLE_CONTRACTS[TradingRole.RISK_MANAGER])
    assert any("risk score" in item.lower() for item in TRADING_ROLE_CONTRACTS[TradingRole.RISK_MANAGER])
