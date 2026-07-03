"""football-data.org fixtures for the user's chosen competitions. Keyed via
X-Auth-Token header; free tier is 10 req/min across 12 competitions, so we use
the cross-competition /matches endpoint (one call) rather than per-league calls
(SOURCES.md)."""

from datetime import date, timedelta

import httpx

from ..config import FOOTBALL_DATA_TOKEN, HTTP_TIMEOUT
from .base import Item, KeyMissing, item

BASE = "https://api.football-data.org/v4"

# The free-tier competitions offered at onboarding (code -> label).
# Full free tier is 12 comps; WC + EC are international and only have fixtures
# during tournament windows, but belong here so they surface when they're on.
FREE_COMPETITIONS = {
    "WC": "FIFA World Cup",
    "EC": "European Championship",
    "CL": "Champions League",
    "PL": "Premier League",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "DED": "Eredivisie",
    "PPL": "Primeira Liga",
    "ELC": "Championship",
    "BSA": "Brasileirao",
}


async def fetch_fixtures(league_codes: list[str]) -> list[Item]:
    if not FOOTBALL_DATA_TOKEN:
        raise KeyMissing("FOOTBALL_DATA_TOKEN not set. Register free at football-data.org and add the emailed token to backend/.env")
    if not league_codes:
        return []
    today = date.today()
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{BASE}/matches",
            params={
                "competitions": ",".join(league_codes),
                "dateFrom": today.isoformat(),
                "dateTo": (today + timedelta(days=14)).isoformat(),
            },
            headers={"X-Auth-Token": FOOTBALL_DATA_TOKEN},
        )
        resp.raise_for_status()
        data = resp.json()

    items: list[Item] = []
    for match in data.get("matches", [])[:50]:
        home = (match.get("homeTeam") or {}).get("shortName") or (match.get("homeTeam") or {}).get("name") or "TBD"
        away = (match.get("awayTeam") or {}).get("shortName") or (match.get("awayTeam") or {}).get("name") or "TBD"
        comp = (match.get("competition") or {}).get("name", "")
        items.append(item(
            source="football-data.org", domain="sports", kind="event",
            title=f"{home} vs {away}",
            subtitle=comp,
            url="",
            ts=match.get("utcDate"),
            group=comp or None,
        ))
    return items
