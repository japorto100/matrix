"""Persistence helpers for `agent.evals` (exec-18 / exec-memory)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def save_eval_run(
    *,
    eval_type: str,
    eval_input: dict[str, Any],
    eval_data: dict[str, Any],
    name: str | None = None,
    agent_id: str | None = None,
    model_id: str | None = None,
    model_provider: str | None = None,
    component_id: str | None = None,
    component_version: int | None = None,
    evaluated_component_name: str | None = None,
    run_id: str | None = None,
) -> str:
    """Insert one row into `agent.evals` and return run_id."""
    rid = run_id or f"eval-{uuid.uuid4().hex[:16]}"
    now = int(datetime.now(UTC).timestamp())
    with psycopg.connect(_db_url(), autocommit=True) as conn:
        conn.execute(
            """
            INSERT INTO agent.evals (
                run_id, eval_type, eval_data, eval_input, name, agent_id,
                model_id, model_provider, component_id, component_version,
                evaluated_component_name, created_at, updated_at
            ) VALUES (
                %s, %s, %s::jsonb, %s::jsonb, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            """,
            (
                rid,
                eval_type,
                json.dumps(eval_data),
                json.dumps(eval_input),
                name,
                agent_id,
                model_id,
                model_provider,
                component_id,
                component_version,
                evaluated_component_name,
                now,
                now,
            ),
        )
    return rid


def save_memory_ab_eval(
    *,
    corpus_id: str,
    queries: list[str],
    hindsight_metrics: dict[str, Any],
    mempalace_metrics: dict[str, Any],
    name: str | None = None,
) -> str:
    """Persist a MemPalace vs Hindsight comparison into `agent.evals`."""
    return save_eval_run(
        eval_type="memory_ab",
        eval_input={
            "corpus_id": corpus_id,
            "queries": queries,
            "pipelines": ["hindsight", "mempalace"],
        },
        eval_data={
            "hindsight": hindsight_metrics,
            "mempalace": mempalace_metrics,
        },
        name=name or f"memory_ab:{corpus_id}",
        evaluated_component_name="memory_ab",
    )
