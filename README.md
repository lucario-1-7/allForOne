# extractorPie

A personal dashboard that pulls everything you follow (tech, sports, games, movies, TV,
anime, esports) into one place. FastAPI backend, vanilla JS frontend, Postgres storage.

- Plan and version history: `ROADMAP.md`
- Verified API reference for every source: `SOURCES.md`

## Run it

```
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8010
```

Open http://127.0.0.1:8010 - the backend serves the frontend directly.

## Configuration (backend/.env)

Copy `.env.example` to `.env`. Two required values and a set of optional keys:

- `SECRET_KEY`: any long random string (signs session tokens).
- `DATABASE_URL`: Postgres is the project default:
  `postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/extractorpie`
  (create the db once with `createdb -U postgres extractorpie`). A SQLite URL also works
  for quick dev runs.
- API keys: all optional. Modules whose key is missing show a card in the UI telling you
  exactly where to get it. See the keys checklist in `SOURCES.md`. Keyless modules
  (Hacker News, RSS, TVmaze, AniList) work with no configuration.

## What works right now

- Accounts (register/sign in), onboarding (pick domains, refine leagues/esports/subtopics,
  search and follow TV shows and anime), per-user persisted dashboards.
- Live modules with no key: tech headlines (Hacker News, Ars Technica, The Verge),
  screen news in Movies/TV/Anime sub-tabs (Variety, Anime News Network), gaming news
  (GameSpot), sports news (BBC Sport), next-episode tracking for followed TV (TVmaze)
  and anime (AniList, exact air timestamps).
- Key-gated modules, live once you add the key: upcoming movies (TMDB), game release
  calendar (IGDB via Twitch), soccer fixtures (football-data.org), NBA games (balldontlie),
  Valorant esports (self-hosted vlrggapi).
- Failure isolation: a dead or unconfigured source degrades to an error card; the rest of
  the page always renders. Responses are cached per source with TTLs tuned to each API's
  rate limit (see `SOURCES.md`).

## Architecture in one paragraph

Each source is an adapter (`backend/app/adapters/`) returning items in one normalized
shape; `app/feed.py` composes a user's feed from their interests and follows, running all
adapters concurrently behind a cache and per-source error isolation; `app/api.py` exposes
auth, profile, search/follow, and feed routes; the frontend (`frontend/`) renders the
dashboard (unified agenda plus top headlines per domain) and the four tabs (Sports, Games,
Screen with Movies/TV/Anime news sub-tabs, Tech with no calendar), per the information
architecture in `ROADMAP.md`.

## Not done yet

- Deployment (Render/Railway for the backend or a VPS; needs your account).
- Capacitor mobile wrap (v4 phase 4.5).
- Esports requires self-hosting vlrggapi (see `SOURCES.md`).
- v5 intelligence layer (ranking, digest, semantic filtering) is deliberately deferred
  until the ML skills exist to build it properly.
