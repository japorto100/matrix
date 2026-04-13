"""Alembic Environment — Matrix Project eigene Tabellen.

Nutzt "agent" Schema (getrennt von Hindsight's "public" Schema).
DB URL aus HINDSIGHT_DB_URL ENV var (gleiche PostgreSQL Instanz).
"""

import os
from logging.config import fileConfig

from sqlalchemy import create_engine, text

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DB URL: aus ENV (überschreibt alembic.ini)
db_url = os.environ.get("HINDSIGHT_DB_URL") or os.environ.get("AUDIT_DB_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

SCHEMA = "agent"


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=None, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    engine = create_engine(url)

    with engine.connect() as connection:
        # Schema erstellen wenn nicht vorhanden
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=None,
            version_table_schema=SCHEMA,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
