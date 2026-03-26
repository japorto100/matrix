from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


def _load_env() -> None:
    """Lädt .env falls vorhanden. Shell-Env hat Vorrang."""
    load_dotenv(dotenv_path=".env", override=False)


@dataclass
class Config:
    # ── Matrix ───────────────────────────────────────────────────────────────
    homeserver_url: str
    bot_user_id: str
    bot_password: str
    bot_access_token: str | None  # nach erstem Login; spart Re-Login
    device_name: str
    store_path: str  # SQLite E2EE Key Store

    # ── Agent Service (bestehender Python Agent) ─────────────────────────────
    agent_service_url: (
        str  # z.B. http://localhost:8094 (Test) oder 11500 (Hauptprojekt)
    )
    agent_timeout_sec: float

    # ── NATS (optional — für Go Appservice Koordination) ─────────────────────
    nats_url: str | None

    # ── Service ──────────────────────────────────────────────────────────────
    host: str
    port: int

    # ── Bot-Verhalten ─────────────────────────────────────────────────────────
    # In Gruppen-Chats nur reagieren wenn Bot erwähnt wird
    mention_only_in_groups: bool = True
    # Nur User von diesen Homeservern akzeptieren (leer = alle)
    allowed_homeservers: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> Config:
        _load_env()
        return cls(
            homeserver_url=os.getenv("MATRIX_HOMESERVER_URL", "http://localhost:8448"),
            bot_user_id=os.getenv("MATRIX_BOT_USER_ID", "@trading-agent:matrix.local"),
            bot_password=_require("MATRIX_BOT_PASSWORD"),
            bot_access_token=os.getenv("MATRIX_BOT_ACCESS_TOKEN") or None,
            device_name=os.getenv("MATRIX_DEVICE_NAME", "TradingAgent-Bridge"),
            store_path=os.getenv("MATRIX_STORE_PATH", "./data/matrix_store"),
            agent_service_url=os.getenv("AGENT_SERVICE_URL", "http://localhost:8094"),
            agent_timeout_sec=float(os.getenv("AGENT_TIMEOUT_SEC", "120")),
            nats_url=os.getenv("NATS_URL") or None,
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8097")),
            mention_only_in_groups=os.getenv("MENTION_ONLY_IN_GROUPS", "true").lower()
            == "true",
            allowed_homeservers=[
                h.strip()
                for h in os.getenv("ALLOWED_HOMESERVERS", "matrix.local").split(",")
                if h.strip()
            ],
        )

    @property
    def bot_localpart(self) -> str:
        """Gibt den Localpart der Bot-User-ID zurück (@trading-agent:... → trading-agent)."""
        return self.bot_user_id.split(":")[0].lstrip("@")


def _require(key: str) -> str:
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"Required env var not set: {key}\nSee .env.example")
    return v
