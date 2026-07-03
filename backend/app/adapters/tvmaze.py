"""TVmaze: keyless. Search powers the follow flow; the embedded nextepisode
link powers the countdown. nextepisode is absent for ended or between-season
shows, so its absence is handled, not assumed (SOURCES.md)."""

import asyncio

import httpx

from ..config import HTTP_TIMEOUT
from .base import Item, item

BASE = "https://api.tvmaze.com"


async def search_shows(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{BASE}/search/shows", params={"q": query})
        resp.raise_for_status()
    results = []
    for hit in resp.json()[:10]:
        show = hit.get("show", {})
        results.append({
            "external_id": str(show.get("id")),
            "title": show.get("name", ""),
            "subtitle": ", ".join(show.get("genres", [])[:3]) or (show.get("status") or ""),
            "kind": "tv",
        })
    return results


async def fetch_next_episodes(follows: list[dict]) -> list[Item]:
    """follows: [{external_id, title}] for kind == 'tv'."""
    if not follows:
        return []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:

        async def one(follow: dict):
            resp = await client.get(f"{BASE}/shows/{follow['external_id']}",
                                    params={"embed": "nextepisode"})
            resp.raise_for_status()
            show = resp.json()
            next_ep = (show.get("_embedded") or {}).get("nextepisode")
            if not next_ep:
                return None  # ended or between seasons: no countdown to show
            season, number = next_ep.get("season"), next_ep.get("number")
            return item(
                source="TVmaze", domain="screen", kind="event",
                title=f"{follow['title']} S{season:02d}E{number:02d}" if season and number else follow["title"],
                subtitle=next_ep.get("name") or "New episode",
                url=show.get("url", ""),
                ts=next_ep.get("airstamp"),
                group="tv",
            )

        results = await asyncio.gather(*(one(f) for f in follows), return_exceptions=True)

    return [r for r in results if isinstance(r, dict)]
