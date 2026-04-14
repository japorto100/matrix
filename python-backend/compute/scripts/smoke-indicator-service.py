from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys

from fastapi.testclient import TestClient


def make_candle(index: int, base: float) -> dict[str, float | int]:
    dt = datetime.now(timezone.utc) - timedelta(days=120 - index)
    drift = (index % 17 - 8) * 0.22
    open_price = base + drift
    close_price = open_price + ((index % 5) - 2) * 0.35
    high_price = max(open_price, close_price) + 0.8
    low_price = min(open_price, close_price) - 0.8
    volume = 950000 + (index % 11) * 18000
    return {
        "time": int(dt.timestamp()),
        "open": round(open_price, 4),
        "high": round(high_price, 4),
        "low": round(low_price, 4),
        "close": round(close_price, 4),
        "volume": float(volume),
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    service_dir = repo_root / "python-backend" / "services" / "indicator-service"
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))

    from app import app  # noqa: PLC0415

    client = TestClient(app)
    candles = [make_candle(i, 150.0 + i * 0.03) for i in range(140)]
    payload = {"ohlcv": candles}

    checks: dict[str, int] = {}
    routes = {
        "composite": ("/api/v1/signals/composite", payload),
        "candlestick": ("/api/v1/patterns/candlestick", payload),
        "harmonic": ("/api/v1/patterns/harmonic", payload),
        "timing": ("/api/v1/patterns/timing", payload),
        "price": ("/api/v1/patterns/price", payload),
        "elliott": ("/api/v1/patterns/elliott-wave", payload),
        "fibonacci": ("/api/v1/fibonacci/levels", payload),
        "exotic_ma": ("/api/v1/indicators/exotic-ma", {**payload, "maType": "kama", "period": 20}),
        "ks_collection": ("/api/v1/indicators/ks-collection", payload),
        "chart_transform": (
            "/api/v1/charting/transform",
            {**payload, "transformType": "heikin_ashi"},
        ),
        "evaluate_strategy": (
            "/api/v1/evaluate/strategy",
            {
                "trades": [
                    {"entry": 100, "exit": 105, "quantity": 10, "side": "long", "fee": 1.2},
                    {"entry": 112, "exit": 107, "quantity": 8, "side": "long", "fee": 1.0},
                    {"entry": 95, "exit": 91, "quantity": 6, "side": "short", "fee": 0.8},
                ]
            },
        ),
    }

    for key, (route, body) in routes.items():
        response = client.post(route, json=body)
        response.raise_for_status()
        checks[key] = response.status_code

    print(json.dumps(checks, indent=2))
    if checks["composite"] != 200:
        raise SystemExit("Smoke failed: composite endpoint did not return 200")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
