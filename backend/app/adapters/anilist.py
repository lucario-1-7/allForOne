"""AniList GraphQL: keyless for public data. nextAiringEpisode gives an exact
next-episode timestamp in one query, which is why it beats Jikan as the primary
anime source. Currently rate-limited to 30 req/min, so batching all followed
anime into ONE query matters (SOURCES.md)."""

from datetime import datetime, timezone

import httpx

from ..config import HTTP_TIMEOUT
from .base import Item, item

ENDPOINT = "https://graphql.anilist.co"

SEARCH_QUERY = """
query ($q: String) {
  Page(perPage: 10) {
    media(search: $q, type: ANIME) {
      id
      title { romaji english }
      status
      format
    }
  }
}
"""

AIRING_QUERY = """
query ($ids: [Int]) {
  Page(perPage: 50) {
    media(id_in: $ids, type: ANIME) {
      id
      title { romaji english }
      siteUrl
      nextAiringEpisode { airingAt episode }
    }
  }
}
"""


async def _gql(query: str, variables: dict) -> dict:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(ENDPOINT, json={"query": query, "variables": variables})
        resp.raise_for_status()
        return resp.json()["data"]


async def search_anime(query: str) -> list[dict]:
    data = await _gql(SEARCH_QUERY, {"q": query})
    results = []
    for media in data["Page"]["media"]:
        title = media["title"].get("english") or media["title"].get("romaji") or ""
        results.append({
            "external_id": str(media["id"]),
            "title": title,
            "subtitle": " / ".join(filter(None, [media.get("format"), media.get("status")])),
            "kind": "anime",
        })
    return results


async def fetch_airing(follows: list[dict]) -> list[Item]:
    """follows: [{external_id, title}] for kind == 'anime'. One batched query."""
    if not follows:
        return []
    ids = [int(f["external_id"]) for f in follows]
    data = await _gql(AIRING_QUERY, {"ids": ids})

    items: list[Item] = []
    for media in data["Page"]["media"]:
        next_ep = media.get("nextAiringEpisode")
        if not next_ep:
            continue  # finished or not currently airing
        title = media["title"].get("english") or media["title"].get("romaji") or ""
        ts = datetime.fromtimestamp(next_ep["airingAt"], tz=timezone.utc).isoformat()
        items.append(item(
            source="AniList", domain="screen", kind="event",
            title=f"{title} EP {next_ep['episode']}",
            subtitle="Airs",
            url=media.get("siteUrl", ""),
            ts=ts,
            group="anime",
        ))
    return items
