from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys

from fastapi.testclient import TestClient


def make_article(i: int, title: str, source: str, summary: str) -> dict[str, str]:
    ts = (datetime.now(timezone.utc) - timedelta(minutes=i * 9)).isoformat()
    return {
        "title": title,
        "url": f"https://example.com/article-{i}",
        "publishedAt": ts,
        "source": source,
        "summary": summary,
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    service_dir = repo_root / "python-backend" / "services" / "geopolitical-soft-signals"
    if str(service_dir) not in sys.path:
        sys.path.insert(0, str(service_dir))

    from app import app  # noqa: PLC0415

    client = TestClient(app)

    articles = [
        make_article(1, "OFAC announces new sanctions package on exports", "Reuters", "sanction embargo export control"),
        make_article(2, "ECB officials discuss inflation and policy rate path", "Bloomberg", "ecb central bank rate inflation"),
        make_article(3, "Border conflict raises military alert level", "AP", "missile strike conflict troop movement"),
        make_article(4, "Energy pipeline outage tightens LNG supply", "FT", "pipeline oil gas lng supply shock"),
        make_article(5, "Social media trending: urgent flash update from region", "X.com", "trending viral breaking urgent"),
        make_article(6, "Narrative in markets shifts toward sanctions language", "WSJ", "narrative shift sanctions market"),
        make_article(7, "Another sanctions headline amplifies discussion", "CNBC", "sanction package latest update"),
        make_article(8, "Breaking urgent flash reports dominate social chatter", "Reddit", "flash urgent latest trending"),
    ]

    payload = {
        "adapterId": "smoke",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "maxCandidates": 6,
        "articles": articles,
    }

    results: dict[str, int] = {}
    for route in ("cluster-headlines", "social-surge", "narrative-shift"):
        response = client.post(f"/api/v1/{route}", json=payload)
        response.raise_for_status()
        body = response.json()
        count = len(body.get("candidates", []))
        results[route] = count

    game_theory_payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "limit": 6,
        "events": [
            {
                "id": "ev-1",
                "eventDate": datetime.now(timezone.utc).date().isoformat(),
                "country": "Ukraine",
                "region": "Europe",
                "eventType": "Battles",
                "subEventType": "Armed clash",
                "fatalities": 12,
                "source": "acled",
                "notes": "border escalation and retaliation",
            },
            {
                "id": "ev-2",
                "eventDate": datetime.now(timezone.utc).date().isoformat(),
                "country": "Israel",
                "region": "Middle East",
                "eventType": "Explosions/Remote violence",
                "subEventType": "Air strike",
                "fatalities": 4,
                "source": "acled",
                "notes": "air strike and de-escalation talks",
            },
        ],
    }
    game_theory_response = client.post("/api/v1/game-theory/impact", json=game_theory_payload)
    game_theory_response.raise_for_status()
    game_theory_body = game_theory_response.json()
    results["game-theory-impact"] = len(game_theory_body.get("items", []))

    print(json.dumps(results, indent=2))
    if results["cluster-headlines"] <= 0:
        raise SystemExit("Smoke failed: cluster-headlines returned no candidates")
    if results["game-theory-impact"] <= 0:
        raise SystemExit("Smoke failed: game-theory-impact returned no items")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
