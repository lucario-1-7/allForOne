"""TMDB upcoming movies. Keyed: needs the v4 Read Access Token as a Bearer
header. Region-sensitive, so we pass one (SOURCES.md). Attribution note: a
public deployment must show the TMDB logo and disclaimer."""

import httpx

from ..config import HTTP_TIMEOUT, TMDB_TOKEN
from .base import Item, KeyMissing, item

BASE = "https://api.themoviedb.org/3"
REGION = "US"


async def fetch_upcoming() -> list[Item]:
    if not TMDB_TOKEN:
        raise KeyMissing("TMDB_TOKEN not set. Get a v4 Read Access Token at themoviedb.org (Settings > API) and add it to backend/.env")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{BASE}/movie/upcoming",
            params={"region": REGION, "page": 1},
            headers={"Authorization": f"Bearer {TMDB_TOKEN}"},
        )
        resp.raise_for_status()
        data = resp.json()

    items: list[Item] = []
    for movie in data.get("results", [])[:15]:
        release = movie.get("release_date") or None
        items.append(item(
            source="TMDB", domain="screen", kind="event",
            title=movie.get("title", ""),
            subtitle="In theaters",
            url=f"https://www.themoviedb.org/movie/{movie.get('id')}",
            ts=f"{release}T00:00:00+00:00" if release else None,
            group="movies",
        ))
    return items
