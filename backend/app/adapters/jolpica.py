"""Formula 1 via Jolpica-F1, the maintained free successor to the dead Ergast
API (SOURCES.md). No key. Ergast-compatible JSON: one call gets the season's
race calendar; we keep the upcoming rounds."""

from datetime import date, datetime, timezone

import httpx

from ..config import HTTP_TIMEOUT
from .base import Item, item

BASE = "https://api.jolpi.ca/ergast/f1"


async def fetch_races() -> list[Item]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(f"{BASE}/current/races/", params={"format": "json"})
        resp.raise_for_status()
        data = resp.json()

    races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    today = date.today().isoformat()
    items: list[Item] = []
    for race in races:
        race_date = race.get("date")
        if not race_date or race_date < today:
            continue  # keep only upcoming rounds
        race_time = race.get("time", "")  # e.g. "13:00:00Z"
        ts = f"{race_date}T{race_time.replace('Z', '+00:00')}" if race_time else f"{race_date}T00:00:00+00:00"
        circuit = (race.get("Circuit") or {}).get("circuitName", "")
        items.append(item(
            source="Jolpica F1", domain="sports", kind="event",
            title=race.get("raceName", "Grand Prix"),
            subtitle=f"Round {race.get('round', '')}" + (f" - {circuit}" if circuit else ""),
            url=race.get("url", ""),
            ts=ts,
            group="Formula 1",
        ))
    return items
