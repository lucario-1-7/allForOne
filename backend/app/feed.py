"""Feed composition: turns a user's interests and follows into the per-domain
payload the frontend renders. All adapters run concurrently; each is isolated
behind run_adapter so a dead source degrades to an error card, never a 500."""

import asyncio

from .adapters import (anilist, apisports_tennis, balldontlie, cricapi, football_data,
                       hackernews, igdb, jolpica, rss, tmdb, tvmaze, vlrgg)
from .adapters.base import Item, run_adapter
from .db import Follow, Interest

# Cache TTLs tuned to each source's cadence and rate limit (SOURCES.md).
TTL = {
    "hackernews": 15 * 60,
    "rss": 15 * 60,
    "tmdb": 12 * 3600,
    "tvmaze": 6 * 3600,
    "anilist": 1 * 3600,       # 30 req/min limit: batch + cache
    "igdb": 12 * 3600,
    "football": 30 * 60,       # 10 req/min limit
    "balldontlie": 1 * 3600,   # 5 req/min limit
    "vlrgg": 5 * 60,
    "f1": 12 * 3600,           # schedule changes rarely
    "cricket": 1 * 3600,       # 100/day limit
    "tennis": 1 * 3600,        # 100/day limit, beta
    "football_live": 30,       # live scores: short TTL, polled only during matches
}

# Which adapter failures belong to which domain (for placing error cards).
SOURCE_DOMAIN = {
    "hackernews": "tech", "rss:tech": "tech",
    "tmdb": "screen", "tvmaze": "screen", "anilist": "screen", "rss:screen": "screen",
    "igdb": "games", "vlrgg": "games", "rss:games": "games",
    "football": "sports", "balldontlie": "sports", "rss:sports": "sports",
    "f1": "sports", "cricket": "sports", "tennis": "sports",
}


async def build_feed(interests: list[Interest], follows: list[Follow]) -> dict:
    domains = {i.domain: (i.config or {}) for i in interests}
    tv_follows = [{"external_id": f.external_id, "title": f.title} for f in follows if f.kind == "tv"]
    anime_follows = [{"external_id": f.external_id, "title": f.title} for f in follows if f.kind == "anime"]

    errors: dict[str, str] = {}
    tasks: dict[str, asyncio.Task] = {}

    async def gather_into(name: str, ttl_key: str, coro_factory):
        return await run_adapter(name, TTL[ttl_key], coro_factory, errors)

    async with asyncio.TaskGroup() as tg:
        if "tech" in domains:
            tasks["hn"] = tg.create_task(gather_into("hackernews", "hackernews", hackernews.fetch_top))
            tasks["rss_tech"] = tg.create_task(gather_into("rss:tech", "rss", lambda: rss.fetch_domain("tech")))
        if "screen" in domains:
            tasks["tmdb"] = tg.create_task(gather_into("tmdb", "tmdb", tmdb.fetch_upcoming))
            tasks["rss_screen"] = tg.create_task(gather_into("rss:screen", "rss", lambda: rss.fetch_domain("screen")))
            if tv_follows:
                key = "tvmaze:" + ",".join(f["external_id"] for f in tv_follows)
                tasks["tvmaze"] = tg.create_task(run_adapter(key, TTL["tvmaze"], lambda: tvmaze.fetch_next_episodes(tv_follows), errors))
            if anime_follows:
                key = "anilist:" + ",".join(f["external_id"] for f in anime_follows)
                tasks["anilist"] = tg.create_task(run_adapter(key, TTL["anilist"], lambda: anilist.fetch_airing(anime_follows), errors))
        if "games" in domains:
            tasks["igdb"] = tg.create_task(gather_into("igdb", "igdb", igdb.fetch_upcoming))
            tasks["rss_games"] = tg.create_task(gather_into("rss:games", "rss", lambda: rss.fetch_domain("games")))
            if domains["games"].get("esports") == "valorant":
                tasks["vlrgg"] = tg.create_task(gather_into("vlrgg", "vlrgg", vlrgg.fetch_upcoming))
        if "sports" in domains:
            cfg = domains["sports"]
            soccer = [code for code in cfg.get("leagues", []) if code != "NBA"]
            other = set(cfg.get("sports", []))
            if "NBA" in cfg.get("leagues", []):
                other.add("nba")  # back-compat: NBA used to live in leagues
            if soccer:
                key = "football:" + ",".join(sorted(soccer))
                tasks["football"] = tg.create_task(run_adapter(key, TTL["football"], lambda: football_data.fetch_fixtures(soccer), errors))
            if "nba" in other:
                tasks["bdl"] = tg.create_task(gather_into("balldontlie", "balldontlie", balldontlie.fetch_games))
            if "f1" in other:
                tasks["f1"] = tg.create_task(gather_into("f1", "f1", jolpica.fetch_races))
            if "cricket" in other:
                tasks["cricket"] = tg.create_task(gather_into("cricket", "cricket", cricapi.fetch_matches))
            if "tennis" in other:
                tasks["tennis"] = tg.create_task(gather_into("tennis", "tennis", apisports_tennis.fetch_games))
            tasks["rss_sports"] = tg.create_task(gather_into("rss:sports", "rss", lambda: rss.fetch_domain("sports")))

    def items_of(*names: str) -> list[Item]:
        out: list[Item] = []
        for name in names:
            task = tasks.get(name)
            if task is not None:
                out.extend(task.result())
        return out

    def sort_events(items: list[Item]) -> list[Item]:
        return sorted([i for i in items if i["ts"]], key=lambda i: i["ts"]) + [i for i in items if not i["ts"]]

    def sort_news(items: list[Item]) -> list[Item]:
        return sorted(items, key=lambda i: i["ts"] or "", reverse=True)

    payload: dict = {"domains": {}, "errors": []}

    if "tech" in domains:
        payload["domains"]["tech"] = {
            "events": [],  # tech is calendar-poor by design (roadmap IA)
            "news": sort_news(items_of("hn", "rss_tech")),
        }
    if "screen" in domains:
        news = items_of("rss_screen")
        payload["domains"]["screen"] = {
            "events": sort_events(items_of("tmdb", "tvmaze", "anilist")),
            "news": {
                "movies": sort_news([n for n in news if n["group"] == "movies"]),
                "tv": sort_news([n for n in news if n["group"] == "tv"]),
                "anime": sort_news([n for n in news if n["group"] == "anime"]),
            },
        }
    if "games" in domains:
        payload["domains"]["games"] = {
            "events": sort_events(items_of("igdb", "vlrgg")),
            "news": sort_news(items_of("rss_games")),
        }
    if "sports" in domains:
        payload["domains"]["sports"] = {
            "events": sort_events(items_of("football", "bdl", "f1", "cricket", "tennis")),
            "news": sort_news(items_of("rss_sports")),
        }

    for source, message in errors.items():
        base = source.split(":")[0]
        payload["errors"].append({
            "source": source,
            "domain": SOURCE_DOMAIN.get(source) or SOURCE_DOMAIN.get(base, "tech"),
            "message": message,
        })
    return payload


async def build_live(interests: list[Interest]) -> dict:
    """Live football scores for the user's soccer competitions. Football is the
    only source that gives (delayed) live scores on a free tier; the frontend
    polls this on a short interval only while the Sports tab is open."""
    domains = {i.domain: (i.config or {}) for i in interests}
    cfg = domains.get("sports", {})
    soccer = [code for code in cfg.get("leagues", []) if code != "NBA"]

    errors: dict[str, str] = {}
    matches: list[Item] = []
    if soccer:
        key = "football_live:" + ",".join(sorted(soccer))
        matches = await run_adapter(key, TTL["football_live"],
                                    lambda: football_data.fetch_live(soccer), errors)
    return {
        "matches": matches,
        "errors": [{"source": s, "message": m} for s, m in errors.items()],
    }
