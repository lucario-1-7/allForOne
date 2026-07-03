"""Generic RSS adapter. One fetch function parameterized by feed config, used
for every news lane that has no dedicated API (SOURCES.md: RSS is the robust
keyless option). feedparser is synchronous, so parsing runs in a thread."""

import asyncio
from datetime import datetime, timezone

import feedparser
import httpx

from ..config import HTTP_TIMEOUT
from .base import Item, item

# domain news lanes -> feeds. group is the sub-tab label where a tab has them.
FEEDS: dict[str, list[dict]] = {
    "tech": [
        {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "group": None},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "group": None},
    ],
    "games": [
        {"name": "GameSpot", "url": "https://www.gamespot.com/feeds/game-news/", "group": None},
    ],
    "sports": [
        {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "group": None},
    ],
    "screen": [
        {"name": "Variety Film", "url": "https://variety.com/v/film/feed/", "group": "movies"},
        {"name": "Variety TV", "url": "https://variety.com/v/tv/feed/", "group": "tv"},
        {"name": "Anime News Network", "url": "https://www.animenewsnetwork.com/newsroom/rss.xml", "group": "anime"},
    ],
}

ITEMS_PER_FEED = 10


def _entry_ts(entry) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()


async def fetch_domain(domain: str) -> list[Item]:
    feeds = FEEDS.get(domain, [])
    items: list[Item] = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True,
                                 headers={"User-Agent": "AllForOne/0.1 (personal dashboard)"}) as client:

        async def one(feed: dict):
            resp = await client.get(feed["url"])
            resp.raise_for_status()
            parsed = await asyncio.to_thread(feedparser.parse, resp.content)
            out = []
            for entry in parsed.entries[:ITEMS_PER_FEED]:
                out.append(item(
                    source=feed["name"], domain=domain, kind="news",
                    title=entry.get("title", ""),
                    subtitle=feed["name"],
                    url=entry.get("link", ""),
                    ts=_entry_ts(entry),
                    group=feed["group"],
                ))
            return out

        results = await asyncio.gather(*(one(f) for f in feeds), return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            items.extend(result)
    if not items and results:
        # every feed in the lane failed; surface it as an adapter failure
        first_error = next((r for r in results if isinstance(r, Exception)), None)
        if first_error:
            raise first_error
    items.sort(key=lambda i: i["ts"] or "", reverse=True)
    return items
