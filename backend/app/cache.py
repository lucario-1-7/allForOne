"""Pluggable TTL cache.

Two backends, one interface:

- **Default (in-process dict):** perfect for a single instance, which is exactly
  the free-tier setup. Zero dependencies, zero latency. Downside: it is wiped on
  restart and not shared across instances.
- **Redis (set REDIS_URL):** a shared cache that survives restarts and is shared
  across every worker/instance. This is the one change that lets the app scale
  horizontally (see ROADMAP scalability notes). Flip it on by setting REDIS_URL;
  nothing else changes.

The adapter layer (base.py:run_adapter) awaits get/put and does not care which
backend is active.
"""

import json
import time
from typing import Any

from .config import REDIS_URL

# In-process fallback store: key -> (expires_at, value)
_store: dict[str, tuple[float, Any]] = {}

# Lazily created async Redis client; only imported when REDIS_URL is set, so the
# free/in-process path has no hard dependency on the redis package at runtime.
_redis = None
if REDIS_URL:
    import redis.asyncio as aioredis

    _redis = aioredis.from_url(REDIS_URL, decode_responses=True)


async def get(key: str) -> Any | None:
    if _redis is not None:
        raw = await _redis.get(key)
        return json.loads(raw) if raw is not None else None

    entry = _store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        del _store[key]
        return None
    return value


async def put(key: str, value: Any, ttl_seconds: float) -> None:
    if _redis is not None:
        await _redis.set(key, json.dumps(value), ex=max(1, int(ttl_seconds)))
        return
    _store[key] = (time.time() + ttl_seconds, value)
