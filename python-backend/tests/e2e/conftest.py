"""Shared fixtures + skip-logic for integration tests.

Integration tests talk to a real Postgres + NATS JetStream + Go-appservice
+ Python-backend stack. Run-time environment decides whether they execute:

* ``pytest -m integration`` — explicit opt-in (CI integration stage).
* ``RUN_INTEGRATION=1 pytest`` — env-var opt-in (dev loop).
* Default: every ``integration``-marked test skips with a helpful reason.

Stack can be brought up via:

    podman-compose --profile scheduler up -d

See ``docker-compose.yml`` (scheduler profile).
"""

from __future__ import annotations

import os
import socket

import pytest


def _port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    opt_in = (
        os.environ.get("RUN_INTEGRATION", "").strip().lower() in {"1", "true", "yes"}
        or config.option.markexpr == "integration"
    )
    if opt_in:
        return
    skip = pytest.mark.skip(
        reason=(
            "integration test — set RUN_INTEGRATION=1 or pass -m integration "
            "(requires Postgres:5433 + NATS:4222 + go-appservice:9000)"
        )
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def postgres_url() -> str:
    url = os.environ.get("SCHEDULER_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
    if not url:
        pytest.skip("SCHEDULER_DB_URL / HINDSIGHT_DB_URL not set")
    return url


@pytest.fixture(scope="session")
def nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


@pytest.fixture(scope="session")
def go_appservice_url() -> str:
    return os.environ.get("GO_APPSERVICE_URL", "http://localhost:9000")


@pytest.fixture(scope="session", autouse=True)
def _require_stack(postgres_url, nats_url, go_appservice_url):
    """Quick TCP probe so every integration test fails fast with a clean
    message instead of a deep asyncpg/nats stack-trace when services are
    down.
    """
    from urllib.parse import urlparse

    probes = [
        ("postgres", urlparse(postgres_url).hostname or "localhost", urlparse(postgres_url).port or 5432),
        ("nats", urlparse(nats_url).hostname or "localhost", urlparse(nats_url).port or 4222),
        (
            "go-appservice",
            urlparse(go_appservice_url).hostname or "localhost",
            urlparse(go_appservice_url).port or 9000,
        ),
    ]
    missing = [name for name, host, port in probes if not _port_open(host, port)]
    if missing:
        pytest.skip(
            f"integration stack services unreachable: {', '.join(missing)} — "
            "run `podman-compose --profile scheduler up -d`"
        )
