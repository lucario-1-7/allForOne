"""In-process TTL cache.

Free-tier rate limits make caching load-bearing (AniList 30/min, balldontlie
5/min, API-Football 100/day), so every adapter call goes through here. One
process, one dict; swap for Redis only if the app ever runs multiple workers.
"""

import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}


def get(key: str) -> Any | None:
    entry = _store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        del _store[key]
        return None
    return value


def put(key: str, value: Any, ttl_seconds: float) -> None:
    _store[key] = (time.time() + ttl_seconds, value)
