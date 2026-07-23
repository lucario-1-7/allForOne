"""IGDB upcoming game releases. Keyed via Twitch OAuth: client-credentials
token, cached until near expiry, then POST with an Apicalypse text body, not
REST params (SOURCES.md). Chosen over RAWG to avoid the attribution-backlink
obligation."""

import time

import httpx

from ..config import HTTP_TIMEOUT, IGDB_CLIENT_ID, IGDB_CLIENT_SECRET
from .base import Item, KeyMissing, item

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
BASE = "https://api.igdb.com/v4"

_token: dict = {"value": "", "expires_at": 0.0}


async def _get_token(client: httpx.AsyncClient) -> str:
    if _token["value"] and time.time() < _token["expires_at"] - 60:
        return _token["value"]
    resp = await client.post(TOKEN_URL, params={
        "client_id": IGDB_CLIENT_ID,
        "client_secret": IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    })
    resp.raise_for_status()
    data = resp.json()
    _token["value"] = data["access_token"]
    _token["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token["value"]


async def fetch_upcoming() -> list[Item]:
    if not (IGDB_CLIENT_ID and IGDB_CLIENT_SECRET):
        raise KeyMissing("IGDB_CLIENT_ID / IGDB_CLIENT_SECRET not set. Create an app in the Twitch Dev Console (dev.twitch.tv) and add both to backend/.env")
    now = int(time.time())
    body = (
        "fields game.name, game.url, date, human, platform.abbreviation; "
        f"where date > {now} & game.hypes > 5; "
        "sort date asc; limit 25;"
    )
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        token = await _get_token(client)
        resp = await client.post(
            f"{BASE}/release_dates", content=body,
            headers={"Client-ID": IGDB_CLIENT_ID, "Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        releases = resp.json()

    items: list[Item] = []
    seen: set[str] = set()
    for release in releases:
        game = release.get("game") or {}
        name = game.get("name")
        if not name or name in seen:
            continue  # one game releases on many platforms; keep one entry
        seen.add(name)
        from datetime import datetime, timezone
        ts = datetime.fromtimestamp(release["date"], tz=timezone.utc).isoformat() if release.get("date") else None
        platform = (release.get("platform") or {}).get("abbreviation", "")
        items.append(item(
            source="IGDB", domain="games", kind="event",
            title=name,
            subtitle=f"Releases {release.get('human', '')}" + (f" ({platform})" if platform else ""),
            url=game.get("url", ""),
            ts=ts,
            group=None,
        ))
    return items
