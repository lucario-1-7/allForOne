"""Hacker News: official Firebase API, no key. Returns ID arrays, so we fan out
one /item request per story (SOURCES.md)."""

import asyncio
from datetime import datetime, timezone

import httpx

from ..config import HTTP_TIMEOUT
from .base import Item, item

BASE = "https://hacker-news.firebaseio.com/v0"
STORY_COUNT = 15


async def fetch_top() -> list[Item]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{BASE}/topstories.json")
        resp.raise_for_status()
        ids = resp.json()[:STORY_COUNT]

        async def one(story_id: int):
            r = await client.get(f"{BASE}/item/{story_id}.json")
            r.raise_for_status()
            return r.json()

        stories = await asyncio.gather(*(one(i) for i in ids), return_exceptions=True)

    items: list[Item] = []
    for story in stories:
        if not isinstance(story, dict) or story.get("type") != "story":
            continue
        ts = datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc).isoformat()
        items.append(item(
            source="Hacker News", domain="tech", kind="news",
            title=story.get("title", ""),
            subtitle=f"{story.get('score', 0)} points",
            url=story.get("url") or f"https://news.ycombinator.com/item?id={story['id']}",
            ts=ts,
        ))
    return items
