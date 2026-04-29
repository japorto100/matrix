"""Semantic layer lookup tool for metric/term-sensitive agent answers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from agent.tools.base import TradingTool
from semantic_layer.catalog import (
    DEFAULT_SEMANTIC_CATALOG,
    PermissionContext,
    lookup_phrase,
    plan_metric_query,
)

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class SemanticLookupInput(BaseModel):
    phrase: str = Field(
        min_length=1,
        description="Metric, business term, KG concept, or RAG concept phrase to resolve.",
    )
    tenant_id: str = Field(
        default="",
        description="Optional tenant id for permission-scoped metric contracts.",
    )
    include_metric_plan: bool = Field(
        default=True,
        description="Include the permission-filtered semantic metric contract when applicable.",
    )


class SemanticLookupTool(TradingTool):
    """Resolve semantic terms/metrics before answering metric-sensitive questions."""

    input_model = SemanticLookupInput

    @property
    def name(self) -> str:
        return "semantic_lookup"

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Resolve an authoritative Matrix semantic term or metric before answering "
                "questions about metrics, KG concepts, RAG concepts, definitions, freshness, "
                "or provenance. Use this instead of guessing definitions or writing raw SQL. "
                "If the phrase is unknown or ambiguous, return the refusal guidance instead "
                "of inventing a metric."
            ),
            "input_schema": SemanticLookupInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict[str, Any], ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = SemanticLookupInput(**tool_input)
        lookup = lookup_phrase(DEFAULT_SEMANTIC_CATALOG, params.phrase)
        result: dict[str, Any] = {
            "ok": True,
            "phrase": params.phrase,
            "matched": lookup["matched"],
            "ambiguous": lookup["ambiguous"],
            "authoritative": lookup["matched"],
            "matches": lookup["matches"],
            "raw_sql_allowed": False,
        }

        if lookup["ambiguous"]:
            result.update(
                {
                    "status": "ambiguous",
                    "refusal_reason": "ambiguous-semantic-definition",
                    "answer_template": (
                        "I found multiple authoritative semantic definitions for this phrase. "
                        "Ask the user to choose one before giving a metric answer."
                    ),
                }
            )
            return result

        if not lookup["matched"]:
            result.update(
                {
                    "status": "not_found",
                    "refusal_reason": "no-authoritative-definition",
                    "answer_template": (
                        "I do not have an authoritative Matrix semantic definition for this "
                        "phrase, so I should not invent a metric or SQL query."
                    ),
                }
            )
            return result

        match = lookup["matches"][0]
        item = match["item"]
        if match["type"] == "term":
            result.update(
                {
                    "status": "matched_term",
                    "answer_template": {
                        "definition": item.get("description", ""),
                        "provenance": item.get("source_refs", []),
                        "freshness": "definition-versioned",
                    },
                }
            )
            return result

        metric_plan: dict[str, Any] | None = None
        if params.include_metric_plan:
            metric_plan = plan_metric_query(
                DEFAULT_SEMANTIC_CATALOG,
                str(item["metric_id"]),
                PermissionContext(
                    user_id=ctx.user_id,
                    tenant_id=params.tenant_id,
                    roles=(ctx.user_role,) if ctx.user_role else (),
                ),
            )
        allowed = bool(metric_plan and metric_plan.get("allowed"))
        result.update(
            {
                "status": "matched_metric" if allowed else "metric_permission_denied",
                "metric_plan": metric_plan,
                "authoritative": allowed,
                "refusal_reason": None if allowed else (metric_plan or {}).get("reason"),
                "answer_template": {
                    "definition": item.get("measure", ""),
                    "value": "Only answer with a computed value supplied by an approved data path.",
                    "provenance": item.get("source_refs", []),
                    "freshness": item.get("freshness_sla", ""),
                },
            }
        )
        return result

    def to_model_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """Keep semantic lookup compact in the model context."""

        payload = {
            "status": result.get("status"),
            "phrase": result.get("phrase"),
            "authoritative": result.get("authoritative"),
            "ambiguous": result.get("ambiguous"),
            "refusal_reason": result.get("refusal_reason"),
            "answer_template": result.get("answer_template"),
            "raw_sql_allowed": False,
        }
        metric_plan = result.get("metric_plan")
        if isinstance(metric_plan, dict):
            payload["metric_plan"] = {
                "allowed": metric_plan.get("allowed"),
                "reason": metric_plan.get("reason"),
                "semantic_contract": metric_plan.get("semantic_contract"),
                "freshness_sla": metric_plan.get("freshness_sla"),
                "raw_sql_allowed": metric_plan.get("raw_sql_allowed", False),
            }
        return payload
