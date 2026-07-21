"""Tennis via api-sports.io (beta). Keyed: x-apisports-key header. Honestly the
weakest source here: the tennis API is beta, its exact endpoint paths are not
publicly documented (SOURCES.md), and the free tier is 100/day. Parsing is
defensive so an unexpected shape degrades to few/no items rather than crashing.

If tennis shows an error card, the likely fix is the endpoint path or the
response field names below - check your api-sports.io dashboard docs and adjust.
"""

from datetime import date, datetime, timezone

import httpx

from ..config import API_SPORTS_KEY, HTTP_TIMEOUT
from .base import Item, KeyMissing, item

BASE = "https://v1.tennis.api-sports.io"


def _first(d: dict, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k):
            return d[k]
    return None


async def fetch_games() -> list[Item]:
    if not API_SPORTS_KEY:
        raise KeyMissing("API_SPORTS_KEY not set. Register at api-sports.io (free 100/day) for the tennis beta and add the key to backend/.env")
    today = date.today().isoformat()
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{BASE}/games", params={"date": today},
                                headers={"x-apisports-key": API_SPORTS_KEY})
        resp.raise_for_status()
        data = resp.json()

    items: list[Item] = []
    for game in (data.get("response") or [])[:20]:
        # defensive: the beta's shape is not firmly documented
        players = game.get("players") or game.get("teams") or {}
        home = _first(players.get("home", {}) if isinstance(players, dict) else {}, "name") or "TBD"
        away = _first(players.get("away", {}) if isinstance(players, dict) else {}, "name") or "TBD"
        ts = None
        raw = _first(game, "date", "timestamp", "time")
        if isinstance(raw, (int, float)):
            ts = datetime.fromtimestamp(raw, tz=timezone.utc).isoformat()
        elif isinstance(raw, str):
            ts = raw
        league = _first(game.get("league", {}) if isinstance(game.get("league"), dict) else {}, "name") or "Tennis"
        items.append(item(
            source="api-sports", domain="sports", kind="event",
            title=f"{home} vs {away}",
            subtitle=league,
            url="",
            ts=ts,
            group="Tennis",
        ))
    return items
