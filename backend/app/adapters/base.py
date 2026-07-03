"""The adapter contract.

Every source implements an async fetch function returning a list of normalized
items. run_adapter wraps a fetch with caching and per-source failure isolation
so one dead API never takes down the feed (roadmap phase 2.5).

Normalized item shape (the contract the frontend depends on):
    {
        "source":   "hackernews",          # where it came from
        "domain":   "tech",                # tech | sports | games | screen
        "kind":     "news" | "event",      # feed item vs dated calendar item
        "title":    str,
        "subtitle": str,                   # secondary line (site, score, ep no)
        "url":      str,
        "ts":       str | None,            # ISO 8601; events must have one
        "group":    str | None,            # sub-grouping (movies/tv/anime, league)
    }
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .. import cache

log = logging.getLogger("adapters")

Item = dict[str, Any]


def item(source: str, domain: str, kind: str, title: str, url: str = "",
         subtitle: str = "", ts: str | None = None, group: str | None = None) -> Item:
    return {"source": source, "domain": domain, "kind": kind, "title": title,
            "subtitle": subtitle, "url": url, "ts": ts, "group": group}


async def run_adapter(name: str, ttl: float, fetch: Callable[[], Awaitable[list[Item]]],
                      errors: dict[str, str]) -> list[Item]:
    """Cache-first execution with failure isolation.

    On error the adapter contributes an entry to `errors` and an empty list,
    never an exception, so the rest of the page still renders.
    """
    cached = await cache.get(name)
    if cached is not None:
        return cached
    try:
        items = await asyncio.wait_for(fetch(), timeout=20)
        await cache.put(name, items, ttl)
        return items
    except Exception as exc:  # noqa: BLE001 - isolation is the point
        log.warning("adapter %s failed: %s", name, exc)
        errors[name] = str(exc)
        return []


class KeyMissing(Exception):
    """Raised by keyed adapters when their credential is not configured."""
