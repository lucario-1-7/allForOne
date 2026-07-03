# extractorPie - Source and API Reference

Verified against current official documentation on **2026-07-03**. Where a provider blocked
automated fetch, the values were corroborated across multiple sources and are flagged inline.

Re-check before launch: **AniList's rate limit** (officially "temporarily" 30/min, may be back
to 90/min) and anything marked with a flag below.

---

## Source map

| Interest | Shape | Source (chosen) | Auth | Free-tier limit | Load-bearing note |
|----------|-------|-----------------|------|-----------------|-------------------|
| Tech news | Stream | Hacker News API | None | No documented limit | Returns ID arrays; fan out `/item/{id}` |
| Tech news (alt) | Stream | Site RSS (Ars, Verge) | None | Unlimited | No SLA, can change anytime |
| Upcoming movies | Stream / calendar | TMDB (v3 data, v4 token) | Bearer token | ~50 req/s per IP | Attribution required; pass `region` |
| TV shows | Follow | TVmaze | None | ~20 calls / 10s | `nextepisode` absent if none scheduled |
| Anime | Follow | AniList (GraphQL) | None for public data | 30/min (degraded from 90) | `nextAiringEpisode` gives exact countdown |
| Anime (fallback) | Follow | Jikan (MAL) | None | 3/s, 60/min | Cached scrape; no exact next-episode |
| Game releases | Stream / calendar | IGDB (default) | Twitch OAuth | 4 req/s, 8 open | Apicalypse POST body; refresh token |
| Game releases (alt) | Stream / calendar | RAWG | API key (`?key=`) | 20,000 / month | Requires attribution + active backlink |
| Esports: Valorant | Stream | vlrggapi (self-hosted) | None (self-host) | self-imposed ~600/min | Unofficial scraper, fragile, best-effort |
| Esports: CS2 | Stream | HLTV | n/a | n/a | ToS forbids scraping; avoid |
| Soccer | Stream + follow | football-data.org | API key (`X-Auth-Token`) | 10/min, 12 comps | Delayed scores, no player stats on free |
| NBA | Stream + follow | balldontlie | API key (`Authorization` raw) | 5/min | Games/players/teams only; standings paid |
| Formula 1 | Stream | Jolpica-F1 | None | 4/s, 500/hr | Ergast successor (Ergast is dead); clean schedule/results |
| Cricket | Stream | CricketData.org (CricAPI) | API key (`?apikey=`) | 100 / day | Only permanent free cricket option; no rankings endpoint |
| Tennis | Stream | api-sports.io (beta) | API key (`x-apisports-key`) | 100 / day | Beta, thin data, endpoint paths inferred; best-effort |
| Multi-sport (alt) | Stream + follow | API-Football | API key (`x-apisports-key`) | 100 / day | Broad + live, but tight daily cap |

---

## Per-domain decisions

- **Movies -> TMDB.** No real alternative needed. Use the v4 bearer token.
- **TV -> TVmaze.** Keyless and stable. The only one for this job.
- **Anime -> AniList primary, Jikan fallback.** AniList gives an exact next-episode timestamp
  in one query; Jikan only gives broadcast day, so it is redundancy, not the default.
- **Game releases -> IGDB by default.** No attribution/backlink obligation and no user/pageview
  caps, unlike RAWG. Trade-off: IGDB's Twitch OAuth + Apicalypse POST syntax is more setup than
  RAWG's plain `?key=` GET. If you want the fastest possible wiring and do not mind adding a
  RAWG backlink, RAWG is the easier start. Default to IGDB.
- **Esports -> treat as fragile, best-effort, and add it late.** vlrggapi is maintained and
  self-hostable but is an unofficial scraper with no SLA and a dead public instance. CS2/HLTV is
  worse (ToS-prohibited, Cloudflare-protected). Never let esports become load-bearing.
- **Soccer -> football-data.org for v1.** The 12 free competitions cover the major European
  leagues plus World Cup and Euros, and 10/min beats API-Football's 100/day for polling. Move to
  API-Football only if you need MLS, lower divisions, live in-play scores, or player stats.
- **NBA -> balldontlie**, accepting that standings and live box scores need a paid tier; free
  gives you schedules and results.
- **Formula 1 -> Jolpica-F1**, free and keyless. The old Ergast API is dead as of 2025; Jolpica
  is its maintained, API-compatible successor. Best F1 option by far.
- **Cricket -> CricketData.org (CricAPI)**, the only genuinely permanent free cricket API
  (100 hits/day). Budget calls around live polling.
- **Tennis -> api-sports.io tennis (beta), best-effort.** Free tennis is weak across the board;
  this is the least reliable module. It is beta, its exact endpoint paths are not firmly
  documented, and the adapter parses defensively. If it errors, the fix is likely the endpoint
  path or field names in `apisports_tennis.py`, check your api-sports.io dashboard.

---

## API reference (detail)

### Hacker News (tech) - no key
- **Auth:** none. **Cost:** free, no documented rate limit.
- **Base URL:** `https://hacker-news.firebaseio.com/v0/`
- **Endpoints:** `/topstories.json` and `/newstories.json` return arrays of up to 500 IDs;
  `/item/{id}.json` fetches one story. You must fan out one request per story.
- **Alternative for search/filtering:** Algolia HN Search `http://hn.algolia.com/api/v1/`.
- **Docs:** https://github.com/HackerNews/API

### TMDB (movies) - bearer token
- **Auth:** register at TMDB, Settings > API, copy the **v4 Read Access Token**. Send as
  `Authorization: Bearer <token>`. (A legacy v3 `?api_key=` string also exists; prefer the token.)
- **Cost:** free for personal/non-commercial. **Rate:** effectively unlimited (CDN guard around
  ~50 req/s per IP).
- **Base URL:** `https://api.themoviedb.org/3`
- **Endpoints:** `GET /movie/upcoming` (pass `region=US` or the user's country for meaningful
  dates); `GET /movie/{id}?append_to_response=release_dates,videos`.
- **Gotchas:** upcoming is region-sensitive. **Attribution required:** show the TMDB logo and
  "This product uses the TMDB API but is not endorsed or certified by TMDB." All catalog data is
  on v3; v4 is only auth + user lists.
- **Docs:** https://developer.themoviedb.org/reference/movie-upcoming-list

### TVmaze (TV) - no key
- **Auth:** none for the public API. **Cost:** free. **Rate:** ~20 calls / 10s per IP (429 if over).
- **Base URL:** `https://api.tvmaze.com`
- **Endpoints:** `GET /search/shows?q={query}` (many results); `GET /singlesearch/shows?q={query}&embed=episodes`
  (best match + episodes in one call); show objects expose `_links.nextepisode`, or fetch with
  `?embed[]=nextepisode`.
- **Gotchas:** `nextepisode` only exists when a show has a scheduled upcoming episode, so the
  countdown UI must handle its absence. **License CC BY-SA:** attribute (a link to the show's
  TVmaze page) and note ShareAlike if you ever redistribute the data.
- **Docs:** https://www.tvmaze.com/api

### AniList (anime, primary) - no key for public data
- **Auth:** none for search/media/airing queries. OAuth2 only to act on a logged-in AniList
  user's private lists (not needed; use a local follow-list instead).
- **Cost:** free. **Rate:** **30 req/min currently** (official docs still show this "temporary"
  degradation from 90/min; re-check at build time). Plus a burst limiter. Handle 429 with the
  `Retry-After` header.
- **Base URL:** `https://graphql.anilist.co` - single endpoint, always `POST` with a JSON body
  (`query` + `variables`). No REST paths.
- **Queries:** search via `Media(search: $q, type: ANIME)` or `Page.media(...)`; next episode via
  `Media { nextAiringEpisode { airingAt timeUntilAiring episode } }` (null for non-airing anime).
- **Docs:** https://docs.anilist.co/ (rate limits: https://docs.anilist.co/guide/rate-limiting)

### Jikan (anime, fallback) - no key
- **Auth:** none, read-only. **Cost:** free. **Rate:** 3 req/s and 60 req/min on the public
  instance; responses cached ~24h server-side (data can lag MAL).
- **Base URL:** `https://api.jikan.moe/v4`
- **Endpoints:** `GET /anime?q={query}`; `GET /seasons/now` and `/seasons/upcoming`;
  `GET /schedules?filter={weekday}`.
- **Gotchas:** unofficial scrape/cache of MyAnimeList; no precise next-episode timestamp (only
  broadcast day/time), so you would compute an approximate countdown. Best-effort uptime.
- **Docs:** https://docs.api.jikan.moe/

### IGDB (game releases, default) - Twitch OAuth
- **Auth:** create an app in the **Twitch Dev Console** for a **Client ID + Client Secret**, then
  `POST https://id.twitch.tv/oauth2/token?client_id=...&client_secret=...&grant_type=client_credentials`
  for an app access token. Send `Client-ID: <id>` and `Authorization: Bearer <token>` on every
  request. Tokens expire (`expires_in`), so cache and refresh.
- **Cost:** free (needs a free Twitch dev account). **Rate:** 4 req/s, max 8 open requests (429 over).
- **Base URL:** `https://api.igdb.com/v4`
- **Endpoints:** `POST /release_dates` or `POST /games` with an Apicalypse text body, e.g.
  `fields game.name, date, human, platform.name; where date > <unix_now>; sort date asc; limit 50;`
  (`release_dates` is cleaner for a "what's coming out" feed).
- **Gotchas:** everything is POST with a text body (not REST GET params); dates are Unix
  timestamps. Ignore any tutorial using v3 or a bare `user-key`. *(Flag: IGDB's docs host blocks
  automated fetch; auth flow, 4 req/s + 8 open, and base URL corroborated via Twitch's own docs.)*
- **Docs:** https://api-docs.igdb.com/ ; auth: https://dev.twitch.tv/docs/authentication/

### RAWG (game releases, alternative) - API key
- **Auth:** sign up at rawg.io, fill the short dev form, copy the key. Pass as `?key=YOUR_KEY`.
- **Cost:** free, **20,000 requests/month**. **Personal use is free only with attribution plus an
  active hyperlink to RAWG on every page showing their data** (load-bearing condition). Commercial
  is free under 100k MAU or 500k pageviews/month, else contact them.
- **Base URL:** `https://api.rawg.io/api`
- **Endpoint:** `GET /games?dates=2026-07-01,2026-12-31&ordering=-added&key=...` (a future date
  range plus `ordering=-added` surfaces anticipated releases).
- **Docs:** https://rawg.io/apidocs ; ToS: https://rawg.io/tos_api

### vlrggapi (Valorant esports) - self-host, fragile
- **Auth:** none (self-hosted). **Cost:** free, open-source (MIT, by axsddlr, FastAPI/Python).
  **Actively maintained** (last push 2026-07-01).
- **Rate:** self-imposed ~600/min with per-endpoint TTL caching (live ~30s, results ~60s,
  upcoming ~5min, rankings ~1h). Real ceiling is vlr.gg's tolerance.
- **Base URL:** self-hosted (e.g. `http://localhost:8000`). **The public instance
  `vlrggapi.vercel.app` is DOWN** (exceeded free-tier limits) - you must self-host.
- **Endpoints:** `GET /match?q=upcoming` | `results` | `live_score`; `GET /rankings?region=<na|eu|ap|kr|br|...>`;
  prefer the `/v2/*` variants going forward.
- **Gotchas:** unofficial HTML scraper - breaks when vlr.gg changes markup, one maintainer, no
  SLA, scraping is a ToS grey area. Keep volume low, honor caching, self-host, treat as best-effort.
- **Repo:** https://github.com/axsddlr/vlrggapi
- **CS2 note:** HLTV has no API and its **ToS explicitly prohibits scraping** (behind Cloudflare).
  Higher-risk than Valorant; likely not worth including.

### football-data.org (soccer) - API key
- **Auth:** free account at football-data.org/client/register, key emailed instantly. Header
  `X-Auth-Token: <key>` (not a query param).
- **Cost:** free. **Rate:** 10 req/min. Free tier = **12 competitions** (Champions League, PL, La
  Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, Primeira Liga, Championship, Brasileirao, World
  Cup, Euros). No player stats, scores are **delayed not live**.
- **Base URL:** `https://api.football-data.org/v4/`
- **Endpoints:** `/competitions/{id}/matches` (fixtures/results); `/competitions/{id}/standings`
  (table); `/matches` (across competitions, filter by date).
- **Docs:** https://docs.football-data.org/general/v4/

### balldontlie (NBA) - API key
- **Auth:** free account at app.balldontlie.io. Header `Authorization: YOUR_API_KEY` (**raw, no
  `Bearer` prefix**).
- **Cost:** free tier exists (paid tiers $9.99+/mo). **Rate:** 5 req/min free.
- **Base URL:** `https://api.balldontlie.io/v1/`
- **Endpoints:** `GET /games` (filter by date/season/team); `GET /games/{id}`; `GET /standings` (paid).
- **Gotchas:** **free tier only reaches Teams, Players, and Games** - standings, box scores, and
  stats need a paid tier. So free gives schedules/results but not live box scores or standings.
- **Docs:** https://docs.balldontlie.io

### API-Football (multi-sport alternative) - API key
- **Auth:** direct via `x-apisports-key: <key>` (base `https://v3.football.api-sports.io/`), OR via
  RapidAPI with different headers and host. Pick one; not interchangeable.
- **Cost:** free = **100 requests/day** (resets 00:00 UTC, no rollover). GET-only.
- **Endpoints:** `/fixtures` (filter by league/season/date, `?live=all` for in-play); `/standings`;
  `/leagues` (discover IDs/seasons).
- **Gotchas:** far broader than football-data.org (MLS, lower divisions, live), but the 100/day cap
  is tight - cache hard. *(Flag: official pages 403 to automated fetch; base URL, header, and
  100/day corroborated across sources.)*
- **Docs:** https://www.api-football.com/documentation-v3

### Tech/news beyond Hacker News
- **Best free option: site RSS** (`https://feeds.arstechnica.com/arstechnica/index`,
  `https://www.theverge.com/rss/index.xml`, or Google News RSS). No key, unlimited, but no SLA.
- **JSON alternatives:** GNews (free 100/day, 1 req/s, **non-commercial**, past-week only);
  NewsAPI.org (free 100/day, localhost-only CORS, 24h-delayed, **non-commercial**). Fine for a
  personal dashboard, not for a shipped client-side app.

---

## Keys to obtain before v1

Register these once and store them as environment variables (never in code):

- [ ] **TMDB** account -> v4 Read Access Token
- [ ] **IGDB** path: Twitch Dev Console app -> Client ID + Client Secret  *(or, if using RAWG instead: a RAWG API key)*
- [ ] **football-data.org** account -> API token  *(only if soccer is in scope for the version you are building)*
- [ ] **balldontlie** account -> API key  *(only if NBA is in scope)*
- [ ] **CricketData.org** account -> API key  *(only if cricket is in scope)*
- [ ] **api-sports.io** account -> API key  *(only if tennis is in scope; separate service from football-data.org)*

No key needed: Hacker News, TVmaze, AniList (public data), Jikan, site RSS, **Jolpica-F1 (Formula 1)**.
Not a key but infrastructure: **vlrggapi** must be self-hosted (Docker) - defer until esports is actually being built.

---

## Licensing and attribution (matters if this ever goes public / on your resume)

Several free tiers carry obligations. For a private personal dashboard most are moot, but if you
publish it (the standalone-website-for-resume path), you must honor:

- **TMDB:** display the TMDB logo + the exact non-endorsement disclaimer.
- **TVmaze:** attribute (link back to the TVmaze page); CC BY-SA ShareAlike on redistributed data.
- **RAWG:** attribution + an active backlink on every page showing RAWG data (if you use RAWG).
- **GNews / NewsAPI:** free tiers are non-commercial only.
- **Esports scrapers (vlrggapi, any HLTV tool):** legal/ToS grey area; a public product raises the
  risk. Keep them out of anything you put your name on publicly, or keep volume minimal and framed
  as personal use.

---

## Rate-limit design note

Some limits are tight: **AniList 30/min, balldontlie 5/min, API-Football 100/day**. This means the
caching layer (roadmap v2, Phase 2.4) is **not optional** - it is required for the app to function
without hitting 429s. Design each source's cache TTL to its cadence: tech every ~15 min, movies and
release calendars once or twice a day, sports scores every few minutes, airing schedules a few times
a day. Cache first, call the API only on a cache miss.
