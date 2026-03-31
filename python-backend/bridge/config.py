from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _load_env() -> None:
    """Lädt .env falls vorhanden. Shell-Env hat Vorrang."""
    load_dotenv(dotenv_path=_ENV_PATH, override=False)


@dataclass
class Config:
    # ── NATS (Go Appservice Koordination) ───────────────────────────────────
    nats_url: str

    # ── Agent Service (bestehender Python Agent) ─────────────────────────────
    agent_service_url: str
    agent_timeout_sec: float

    # ── Agent-Identität (für NATS ReplyMessage) ─────────────────────────────
    agent_user_id: str

    # ── Service ──────────────────────────────────────────────────────────────
    host: str
    port: int

    @classmethod
    def from_env(cls) -> Config:
        _load_env()
        return cls(
            nats_url=os.getenv("NATS_URL", "nats://localhost:4222"),
            agent_service_url=os.getenv("AGENT_SERVICE_URL", "http://localhost:8094"),
            agent_timeout_sec=float(os.getenv("AGENT_TIMEOUT_SEC", "120")),
            agent_user_id=os.getenv(
                "AGENT_USER_ID",
                os.getenv("MATRIX_BOT_USER_ID", "@agent-trading:matrix.local"),
            ),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8097")),
        )
