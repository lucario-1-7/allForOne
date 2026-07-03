# AllForOne

A personal dashboard that pulls everything you follow (tech, sports, games, movies, TV,
anime, esports) into one place. FastAPI backend, vanilla JS frontend, Postgres storage.
**Live on Render, backed by Neon Postgres.**

## Run it locally

```
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8010
```

Open http://127.0.0.1:8010 — the backend serves the frontend directly.

## Configuration (backend/.env)

Copy `.env.example` to `.env`. Two core values plus a set of optional keys:

- `SECRET_KEY`: any long random string (signs session tokens).
- `DATABASE_URL`: Postgres is the project default:
  `postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/allforone`
  (create the db once with `createdb -U postgres allforone`). A SQLite URL also works
  for quick dev runs. In production this points at the Neon connection string.
- `REDIS_URL`: optional. Empty = in-process cache (fine for one instance). Set it to a
  Redis URL to share the cache across instances when scaling out.
- API keys: all optional. Modules whose key is missing show a card in the UI telling you
  exactly where to get it. Keyless modules (Hacker News, RSS, TVmaze, AniList, Jolpica-F1)
  work with no configuration.

## What works right now

- Accounts (register/sign in), onboarding (pick domains, refine sports/leagues/esports/
  subtopics, search and follow TV shows and anime), per-user persisted dashboards.
- **Live football scores** in the Sports tab (football-data), polled only while the tab is
  open, updating in place.
- Sports coverage: soccer incl. **World Cup & Euros** (football-data), NBA (balldontlie),
  Formula 1 (Jolpica, keyless), cricket (CricAPI), tennis (api-sports beta).
- Live modules with no key: tech headlines (Hacker News, Ars Technica, The Verge),
  screen news in Movies/TV/Anime sub-tabs (Variety, Anime News Network), gaming news
  (GameSpot), sports news (BBC Sport), next-episode tracking for followed TV (TVmaze)
  and anime (AniList, exact air timestamps), F1 race calendar.
- Key-gated modules, live once you add the key: upcoming movies (TMDB), game release
  calendar (IGDB via Twitch), soccer fixtures (football-data.org), NBA games (balldontlie),
  cricket (CricAPI), tennis (api-sports), Valorant esports (self-hosted vlrggapi).
- Failure isolation: a dead or unconfigured source degrades to an error card; the rest of
  the page always renders. Responses are cached per source with TTLs tuned to each API's
  rate limit.

## Architecture in one paragraph

Each source is an adapter (`backend/app/adapters/`) returning items in one normalized
shape; `app/feed.py` composes a user's feed from their interests and follows, running all
adapters concurrently behind a (pluggable) cache and per-source error isolation;
`app/api.py` exposes auth, profile, search/follow, feed, and live-scores routes; the
frontend (`frontend/`) renders the dashboard (unified agenda plus top headlines per domain)
and the four tabs (Sports, Games, Screen with Movies/TV/Anime news sub-tabs, Tech with no
calendar).

## Adding a new source

Thanks to the adapter interface, a new source is one file: write an adapter in
`backend/app/adapters/` that returns normalized items (gate it on its key with `KeyMissing`
if it needs one), add its key to `config.py`, and wire it in `feed.py`. Cricket and tennis
are already wired this way — supplying the key is all that's needed to activate them.

## Not done yet

- Capacitor mobile wrap.
- Live scores beyond football (blocked by free-tier limits).
- Esports requires self-hosting vlrggapi.
- v5 intelligence layer (ranking, digest, semantic filtering) is deliberately deferred
  until the ML skills exist to build it properly.
