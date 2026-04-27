from __future__ import annotations

import argparse
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

DEFAULT_SCHEMAS = ("matrix", "agent", "ingestion", "public")

OWNER_FEATURES: dict[str, str] = {
    "agent.audit_events": "001/014",
    "ingestion.jobs": "002",
    "ingestion.chunk_hashes": "002/019/021",
    "ingestion.source_artifacts": "021",
    "agent.agent_role_overrides": "007/009",
    "agent.consent_overrides": "013",
    "agent.a2a_delegations": "009",
    "agent.skills_state": "015",
    "agent.user_llm_settings": "011",
    "agent.user_llm_api_keys": "011",
    "agent.agent_skills": "015",
    "agent.agent_skill_audit": "015",
    "agent.sessions": "007",
    "agent.traces": "014/016",
    "agent.spans": "014/016",
    "agent.tool_servers": "008",
    "agent.tool_server_credentials": "008/013",
    "agent.agent_components": "008/010",
    "agent.scheduler_jobs": "015",
    "agent.scheduler_runs": "015",
    "agent.agent_metrics": "014",
    "agent.agent_sync_failures": "006/007",
    "agent.agent_redaction_patterns": "013",
    "agent.agent_ab_experiments": "011/014",
    "agent.ab_experiments": "011/014",
    "agent.agent_surfaces": "010",
    "agent.mempalace_drawers": "012",
    "agent.kg_entities": "017",
    "agent.kg_claims": "017",
    "agent.kg_claim_evidence": "017/019",
    "agent.kg_claim_access_stats": "017/019",
    "agent.kg_projection_outbox": "017",
}


@dataclass(frozen=True)
class ColumnInfo:
    schema: str
    table: str
    name: str
    data_type: str
    nullable: bool
    default: str | None
    generated: str | None


@dataclass(frozen=True)
class IndexInfo:
    schema: str
    table: str
    name: str
    definition: str


@dataclass(frozen=True)
class ConstraintInfo:
    schema: str
    table: str
    name: str
    kind: str
    definition: str


@dataclass(frozen=True)
class SchemaInventory:
    alembic_revisions: tuple[str, ...]
    extensions: tuple[str, ...]
    columns: tuple[ColumnInfo, ...]
    indexes: tuple[IndexInfo, ...]
    constraints: tuple[ConstraintInfo, ...]


def _schema_filter(schemas: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(schema.strip() for schema in schemas if schema.strip()))


def _data_type(row: dict) -> str:
    udt_name = row.get("udt_name")
    data_type = row["data_type"]
    if data_type == "USER-DEFINED" and udt_name:
        return str(udt_name)
    if data_type == "ARRAY" and udt_name:
        return str(udt_name)
    return str(data_type)


def fetch_inventory(dsn: str, *, schemas: Iterable[str] = DEFAULT_SCHEMAS) -> SchemaInventory:
    selected_schemas = _schema_filter(schemas)
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Dynamic table names cannot be parameterized safely in SQL. Query
            # each selected alembic_version table through psycopg Identifier.
            revisions_list: list[str] = []
            for schema in selected_schemas:
                cur.execute(
                    """
                    SELECT to_regclass(%s) AS relation_name
                    """,
                    (f"{schema}.alembic_version",),
                )
                if cur.fetchone()["relation_name"] is None:
                    continue
                with conn.cursor(row_factory=dict_row) as version_cur:
                    version_cur.execute(
                        sql.SQL(
                            "SELECT version_num FROM {}.alembic_version ORDER BY version_num"
                        ).format(
                            sql.Identifier(schema)
                        )
                    )
                    revisions_list.extend(
                        f"{schema}:{row['version_num']}" for row in version_cur.fetchall()
                    )
            revisions = tuple(revisions_list)

            cur.execute(
                """
                SELECT extname
                FROM pg_extension
                WHERE extname NOT IN ('plpgsql')
                ORDER BY extname
                """
            )
            extensions = tuple(str(row["extname"]) for row in cur.fetchall())

            cur.execute(
                """
                SELECT
                    table_schema,
                    table_name,
                    column_name,
                    data_type,
                    udt_name,
                    is_nullable,
                    column_default,
                    is_generated
                FROM information_schema.columns
                WHERE table_schema = ANY(%s)
                ORDER BY table_schema, table_name, ordinal_position
                """,
                (list(selected_schemas),),
            )
            columns = tuple(
                ColumnInfo(
                    schema=str(row["table_schema"]),
                    table=str(row["table_name"]),
                    name=str(row["column_name"]),
                    data_type=_data_type(row),
                    nullable=row["is_nullable"] == "YES",
                    default=row["column_default"],
                    generated=row["is_generated"],
                )
                for row in cur.fetchall()
            )

            cur.execute(
                """
                SELECT schemaname, tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = ANY(%s)
                ORDER BY schemaname, tablename, indexname
                """,
                (list(selected_schemas),),
            )
            indexes = tuple(
                IndexInfo(
                    schema=str(row["schemaname"]),
                    table=str(row["tablename"]),
                    name=str(row["indexname"]),
                    definition=str(row["indexdef"]),
                )
                for row in cur.fetchall()
            )

            cur.execute(
                """
                SELECT
                    ns.nspname AS schema_name,
                    cls.relname AS table_name,
                    con.conname AS constraint_name,
                    con.contype AS constraint_type,
                    pg_get_constraintdef(con.oid) AS definition
                FROM pg_constraint con
                JOIN pg_class cls ON cls.oid = con.conrelid
                JOIN pg_namespace ns ON ns.oid = cls.relnamespace
                WHERE ns.nspname = ANY(%s)
                ORDER BY ns.nspname, cls.relname, con.conname
                """,
                (list(selected_schemas),),
            )
            constraints = tuple(
                ConstraintInfo(
                    schema=str(row["schema_name"]),
                    table=str(row["table_name"]),
                    name=str(row["constraint_name"]),
                    kind=str(row["constraint_type"]),
                    definition=str(row["definition"]),
                )
                for row in cur.fetchall()
            )

    return SchemaInventory(
        alembic_revisions=revisions,
        extensions=extensions,
        columns=columns,
        indexes=indexes,
        constraints=constraints,
    )


def _group_by_table(items: Iterable[ColumnInfo | IndexInfo | ConstraintInfo]) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for item in items:
        grouped.setdefault(f"{item.schema}.{item.table}", []).append(item)
    return grouped


def format_markdown(inventory: SchemaInventory, *, generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now(UTC)
    columns_by_table = _group_by_table(inventory.columns)
    indexes_by_table = _group_by_table(inventory.indexes)
    constraints_by_table = _group_by_table(inventory.constraints)

    lines = [
        "# Current Database Schema",
        "",
        "Generated by: `python-backend/scripts/schema_inventory.py`",
        "",
        f"Generated: `{generated_at.isoformat(timespec='seconds')}`",
        "",
        "Alembic remains the authoritative migration source. This inventory is a",
        "human-readable snapshot of the database after `alembic upgrade head`.",
        "",
        "Regenerate with:",
        "",
        "```bash",
        "cd python-backend",
        "uv run python scripts/schema_inventory.py --output ../docs/database/current-schema.md",
        "```",
        "",
        "## Alembic",
        "",
        f"- Current revisions: `{', '.join(inventory.alembic_revisions) or 'unknown'}`",
        "",
        "## Extensions",
        "",
    ]
    if inventory.extensions:
        lines.extend(f"- `{extension}`" for extension in inventory.extensions)
    else:
        lines.append("- none")

    lines.extend(["", "## Tables", ""])
    for table_key in sorted(columns_by_table):
        owner = OWNER_FEATURES.get(table_key, "unassigned")
        lines.extend([f"### `{table_key}`", "", f"Owner feature: `{owner}`", "", "| Column | Type | Null | Default | Generated |", "|---|---|---:|---|---|"])
        for column in columns_by_table[table_key]:
            default = (column.default or "").replace("\n", " ")
            generated = column.generated or ""
            null_value = "yes" if column.nullable else "no"
            lines.append(
                f"| `{column.name}` | `{column.data_type}` | {null_value} | `{default}` | `{generated}` |"
            )
        table_indexes = indexes_by_table.get(table_key, [])
        if table_indexes:
            lines.extend(["", "Indexes:"])
            lines.extend(f"- `{index.name}`: `{index.definition}`" for index in table_indexes)
        table_constraints = constraints_by_table.get(table_key, [])
        if table_constraints:
            lines.extend(["", "Constraints:"])
            lines.extend(
                f"- `{constraint.name}` ({constraint.kind}): `{constraint.definition}`"
                for constraint in table_constraints
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Matrix Postgres schema inventory.")
    parser.add_argument(
        "--dsn",
        default=os.getenv("SCHEMA_INVENTORY_DB_URL")
        or os.getenv("HINDSIGHT_DB_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://postgres@localhost:5433/hindsight_dev",
        help="Postgres DSN. Defaults to SCHEMA_INVENTORY_DB_URL/HINDSIGHT_DB_URL/DATABASE_URL.",
    )
    parser.add_argument(
        "--schema",
        action="append",
        dest="schemas",
        default=[],
        help="Schema to include. Repeatable. Defaults to matrix, agent and public.",
    )
    parser.add_argument("--output", type=Path, help="Write Markdown inventory to this path.")
    args = parser.parse_args()

    inventory = fetch_inventory(args.dsn, schemas=args.schemas or DEFAULT_SCHEMAS)
    markdown = format_markdown(inventory)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown)
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
