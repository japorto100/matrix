from __future__ import annotations

from agent.control.audit import (
    MCP_POLICY_AUDIT_ACTIONS,
    _append_mcp_policy_audit_clause,
    _audit_where,
)


def test_mcp_policy_audit_clause_filters_actions_tools_and_metadata() -> None:
    clauses: list[str] = ["user_id = %s"]
    params: list[object] = ["alice"]

    _append_mcp_policy_audit_clause(clauses, params)

    where = _audit_where(clauses)
    assert "action IN" in where
    assert "tool_name LIKE" in where
    assert "metadata::text ILIKE" in where
    assert params[0] == "alice"
    assert "MCP_TOOL_DENIED" in params
    assert "mcp_%" in params
    assert "%mcp%" in params
    assert len([value for value in params if value in MCP_POLICY_AUDIT_ACTIONS]) == len(
        MCP_POLICY_AUDIT_ACTIONS
    )
