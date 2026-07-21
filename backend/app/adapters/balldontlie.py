"""balldontlie NBA games. Keyed: raw API key in the Authorization header, no
Bearer prefix. Free tier is 5 req/min and reaches games/teams/players only,
so one upcoming-games call and a long cache TTL (SOURCES.md)."""

from datetime import date, timedelta

import httpx

from ..config import BALLDONTLIE_KEY, HTTP_TIMEOUT
from .base import Item, KeyMissing, item

BASE = "https://api.balldontlie.io/v1"


async def fetch_games() -> list[Item]:
    if not BALLDONTLIE_KEY:
        raise KeyMissing("BALLDONTLIE_KEY not set. Create a free account at app.balldontlie.io and add the key to backend/.env")
    today = date.today()
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{BASE}/games",
            params={
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=14)).isoformat(),
                "per_page": 100,  # 2-week NBA window can be many games; 100 is the free-tier max
            },
            headers={"Authorization": BALLDONTLIE_KEY},
        )
        resp.raise_for_status()
        data = resp.json()

    items: list[Item] = []
    for game in data.get("data", []):
        home = (game.get("home_team") or {}).get("full_name", "")
        visitor = (game.get("visitor_team") or {}).get("full_name", "")
        game_date = game.get("date") or ""
        ts = f"{game_date}T00:00:00+00:00" if len(game_date) == 10 else game_date
        items.append(item(
            source="balldontlie", domain="sports", kind="event",
            title=f"{visitor} at {home}",
            subtitle="NBA",
            url="",
            ts=ts,
            group="NBA",
        ))
    return items
