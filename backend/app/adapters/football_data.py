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
                # football-data free tier rejects any window over 10 days
                "dateTo": (today + timedelta(days=10)).isoformat(),
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


async def fetch_live(league_codes: list[str]) -> list[Item]:
    """Currently in-play matches (and half-time) for the chosen competitions,
    with the running score. Scores are delayed, not real-time (SOURCES.md).
    No date filter, so the 10-day window cap does not apply here."""
    if not FOOTBALL_DATA_TOKEN:
        raise KeyMissing("FOOTBALL_DATA_TOKEN not set. Register free at football-data.org and add the emailed token to backend/.env")
    if not league_codes:
        return []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{BASE}/matches",
            params={"competitions": ",".join(league_codes), "status": "IN_PLAY,PAUSED"},
            headers={"X-Auth-Token": FOOTBALL_DATA_TOKEN},
        )
        resp.raise_for_status()
        data = resp.json()

    items: list[Item] = []
    for match in data.get("matches", [])[:30]:
        home = (match.get("homeTeam") or {}).get("shortName") or (match.get("homeTeam") or {}).get("name") or "TBD"
        away = (match.get("awayTeam") or {}).get("shortName") or (match.get("awayTeam") or {}).get("name") or "TBD"
        comp = (match.get("competition") or {}).get("name", "")
        full = (match.get("score") or {}).get("fullTime") or {}
        sh = full.get("home") if full.get("home") is not None else 0
        sa = full.get("away") if full.get("away") is not None else 0
        minute = match.get("minute")
        clock = f"{minute}'" if minute else ("HT" if match.get("status") == "PAUSED" else "LIVE")
        items.append(item(
            source="football-data.org", domain="sports", kind="live",
            title=f"{home} {sh}-{sa} {away}",
            subtitle=f"{comp} · {clock}" if comp else clock,
            url="",
            ts=match.get("utcDate"),
            group=comp or None,
        ))
    return items
