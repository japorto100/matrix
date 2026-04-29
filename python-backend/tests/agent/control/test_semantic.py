from __future__ import annotations


async def test_semantic_catalog_endpoint_validates_default_catalog():
    from agent.control.semantic import semantic_catalog

    payload = await semantic_catalog()

    assert payload["validation"]["passed"] is True
    assert payload["catalog"]["metrics"]


async def test_semantic_lookup_endpoint_returns_metric():
    from agent.control.semantic import semantic_lookup

    payload = await semantic_lookup("tool success rate")

    assert payload["matched"] is True
    assert payload["matches"][0]["type"] == "metric"


async def test_semantic_metric_plan_endpoint_respects_tenant_scope():
    from agent.control.semantic import semantic_metric_plan

    denied = await semantic_metric_plan("agent_tool_success_rate")
    allowed = await semantic_metric_plan(
        "agent_tool_success_rate",
        user_id="alice",
        tenant_id="tenant-a",
    )

    assert denied["allowed"] is False
    assert allowed["allowed"] is True
    assert allowed["raw_sql_allowed"] is False
