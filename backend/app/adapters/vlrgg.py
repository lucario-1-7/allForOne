"""Valorant esports via a self-hosted vlrggapi instance. Deliberately fragile
and best-effort: unofficial scraper, public instance is down, must be
self-hosted (SOURCES.md). Never load-bearing; absent unless VLRGG_BASE_URL is
configured."""

import httpx

from ..config import HTTP_TIMEOUT, VLRGG_BASE_URL
from .base import Item, KeyMissing, item


async def fetch_upcoming() -> list[Item]:
    if not VLRGG_BASE_URL:
        raise KeyMissing("VLRGG_BASE_URL not set. Esports needs a self-hosted vlrggapi instance (github.com/axsddlr/vlrggapi); set its URL in backend/.env")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{VLRGG_BASE_URL.rstrip('/')}/match", params={"q": "upcoming"})
        resp.raise_for_status()
        data = resp.json()

    segments = (((data or {}).get("data") or {}).get("segments")) or []
    items: list[Item] = []
    for match in segments[:15]:
        items.append(item(
            source="vlr.gg", domain="games", kind="event",
            title=f"{match.get('team1', '?')} vs {match.get('team2', '?')}",
            subtitle=match.get("match_event", "Valorant"),
            url=match.get("match_page", ""),
            ts=None,  # vlrggapi returns relative times; shown as-is in subtitle
            group="Valorant",
        ))
        if match.get("time_until_match"):
            items[-1]["subtitle"] += f" - {match['time_until_match']}"
    return items
