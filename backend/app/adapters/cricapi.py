"""Cricket via CricketData.org (CricAPI). Keyed: apikey as a query param. Free
tier is 100 hits/day (SOURCES.md), so cache hard. currentMatches covers live
and imminent internationals and franchise cricket."""

import httpx

from ..config import CRICAPI_KEY, HTTP_TIMEOUT
from .base import Item, KeyMissing, item

BASE = "https://api.cricapi.com/v1"


async def fetch_matches() -> list[Item]:
    if not CRICAPI_KEY:
        raise KeyMissing("CRICAPI_KEY not set. Sign up free at cricketdata.org (100 hits/day) and add the key to backend/.env")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{BASE}/currentMatches", params={"apikey": CRICAPI_KEY, "offset": 0})
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "success":
        raise RuntimeError(data.get("status", "CricAPI returned an error"))

    items: list[Item] = []
    for match in data.get("data", [])[:20]:
        items.append(item(
            source="CricketData", domain="sports", kind="event",
            title=match.get("name", "Cricket match"),
            subtitle=match.get("matchType", "").upper() or match.get("status", ""),
            url="",
            ts=match.get("dateTimeGMT"),
            group="Cricket",
        ))
    return items
