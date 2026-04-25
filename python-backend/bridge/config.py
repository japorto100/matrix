from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
_ENV_BASE = _ROOT / ".env"


def _load_env() -> None:
    """Lädt .env als baseline, dann .env.<APP_ENV> als override (analog GO_ENV).

    Shell-Env hat weiterhin Vorrang (nicht überschrieben). `.env.<APP_ENV>` override=True
    ersetzt nur zuvor aus Datei geladene Werte.
    """
    if _ENV_BASE.exists():
        load_dotenv(dotenv_path=_ENV_BASE, override=False)

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    env_specific = _ROOT / f".env.{app_env}"
    if env_specific.exists():
        load_dotenv(dotenv_path=env_specific, override=True)


def _csv(value: str | None) -> tuple[str, ...]:
    return tuple(part.strip() for part in str(value or "").split(",") if part.strip())


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
    nats_allowed_agents: tuple[str, ...] = ()

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
            nats_allowed_agents=_csv(os.getenv("NATS_ALLOWED_AGENTS")),
        )
