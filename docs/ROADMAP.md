# extractorPie - Build Roadmap

A personal dashboard that pulls everything you follow across your interests (tech, sports,
esports, gaming, TV, anime, movies) into one place, shaped to you. Working name; rename later.

This roadmap is versioned. Each version is independently shippable, has phases, and has a
strict **Done when** bar. Do not start a version until the previous one's bar is met. The
whole discipline of this project is resisting the urge to build v4 before v1 exists.

> **Status (2026-07-03):** v1 through v3 are built and verified locally, plus most of v4
> (adapters for every domain, widget types, the tab and dashboard IA, per-source failure
> isolation, caching). Sports now covers soccer (football-data), NBA (balldontlie),
> Formula 1 (Jolpica, keyless, verified live), cricket (CricAPI), and tennis (api-sports
> beta, best-effort). Onboarding lets you pick sports plus soccer leagues.
> Outstanding: deployment (needs your hosting account), the Capacitor wrap (phase 4.5),
> keyed modules need their keys in backend/.env (checklist in SOURCES.md), and the Postgres
> URL needs your password in backend/.env (runs on SQLite until then). v5 deferred until the
> ML skills exist.

---

## What it is (and is not)

- **Is:** an aggregator. It pulls from several purpose-built sources and unifies them into
  one page tailored to your chosen interests.
- **Is not:** a news app. Your interests are not all "news", some are structured, time-based
  data (fixtures, release dates, next-episode countdowns), each with its own best source.

---

## Core concept: interests come in two shapes

This is the backbone of the entire product. Every interest is one of two shapes, and they
behave differently.

**1. Topic streams (subscribe to a firehose).** The catalog is manageable, so you pull the
whole stream. You pick the topic, maybe a sub-topic, and see everything in that lane.
- Examples: tech, a specific esport title, a sports league.

**2. Followed items (track specific things).** The catalog is enormous, so subscribing to
"all of it" is nonsense. The user follows specific items and you track only those.
- Examples: TV shows, anime, favourite teams.

Consequences that ripple through every version:
- Streams need a **sub-topic choice** (esports -> which game). Follows need the user to
  **seed some follows** (search and add the shows they watch).
- Onboarding is therefore not one uniform question. It is: pick domain, then refine per the
  domain's shape.

---

## Information architecture (decided 2026-07-03)

The layout is the streams-vs-follows split made visible. One principle holds it together:
**the dashboard is the aggregated overview; each tab is the filtered deep-dive.** Same data,
two zoom levels. The dashboard never has content of its own, it is always a ranked subset of
what the tabs hold.

**Four big tabs:**
- **Sports**
- **Games** (gaming + esports, since esports is game-specific)
- **Screen** (movies + TV + anime, all "things I watch")
- **Tech**

**Inside a tab, two zones:**
- **Top: a calendar / agenda** of that domain's dated things (fixtures, releases, episodes).
  **Conditional:** only domains rich in dated events get a calendar. Tech is calendar-poor,
  so the Tech tab is mostly feed (at most a small "upcoming launches" strip). An empty
  calendar looks broken; do not force one.
- **Below: the news feed** for that domain.

**Screen tab special case:** one shared calendar for all watch-things, but the news zone is
split into **three sub-tabs: Movies / TV / Anime**, since their news audiences barely overlap.

**Dashboard (main page):**
- One **unified calendar**: the union of upcoming events across all the user's interests.
- **Key headlines only**: roughly the top 2 per picked interest. Explicitly NOT all the news;
  full feeds live in the tabs. The dashboard's job is the glance, the tab's job is the depth.

**Differentiating news inside a tab** (in order of value):
1. **Label by source** (trivial): every item shows its outlet; optional source filter.
2. **Group by sub-topic / followed entity** (the real one): reuse the onboarding choices.
   Sports news groups under the followed leagues/teams; tech under picked sub-topics (AI,
   hardware); news mentioning a followed entity floats up. Comes free from onboarding data.
3. **By type (news vs opinion vs announcement): skipped.** Needs text classification; it is
   a v5 nicety, not structure worth building early.

---

## Source map (interest to API)

| Interest | Shape | Source(s) | Key needed |
|----------|-------|-----------|------------|
| Tech | Stream | Hacker News API, plus RSS (The Verge, Ars Technica) | No |
| Upcoming movies | Stream / calendar | TMDB API | Free key |
| Gaming releases | Stream / calendar | RAWG or IGDB | Free key |
| Esports (per game) | Stream | Valorant: vlr.gg (vlrggapi); CS2: HLTV; others per title | Mostly no |
| Sports (per league/team) | Stream + follow | football-data.org (soccer, free tier); balldontlie (NBA) | Free tier |
| TV shows | Follow | TVmaze | No |
| Anime | Follow | AniList (GraphQL) or Jikan (MyAnimeList) | No |

All free or free-tier. Fitness was dropped: a news source adds little there, and that
interest is better served later by the separate research-feed project.

> Full, verified API details (auth method, how to get each key, free-tier limits, rate limits,
> exact endpoints, and gotchas) live in **`SOURCES.md`**, checked 2026-07-03. That file is the
> source of truth; this table is just the quick view.

---

## Tech stack and why

- **Backend: Python (FastAPI).** It fetches from each source, normalizes to one item shape,
  caches, and serves your app a clean feed. Building this in Python doubles as real practice
  for the language you are learning anyway.
- **Why a backend at all** (instead of the frontend calling APIs directly): three real
  reasons, and understanding them is part of the learning. It hides your API keys (never ship
  keys in frontend code), it caches so you do not blow through rate limits, and it normalizes
  many different data shapes into one before the frontend ever sees them.
- **Frontend:** start with plain HTML/JS or a small React app. One page, cards per module.
- **Storage: Postgres from the start.** You already use it across projects, so making it the
  default keeps your stack consistent and skips a later SQLite-to-Postgres migration. Run it
  locally (or in Docker) for development, and use a free-tier managed Postgres (Neon, Supabase,
  or the host's own) in production.
- **Deploy:** backend on Render/Railway/Fly free tier, frontend on Vercel/Netlify.
- **Later:** wrap the frontend as a mobile app with Capacitor (already familiar to you).

---

## What the versions mean

- **v1** proves the pipeline works, end to end, deployed. Interests hard-coded. No accounts.
- **v2** makes interests real data and cleanly pluggable. Still single-user.
- **v3** adds accounts and the onboarding + topic-vs-follow logic.
- **v4** expands breadth and polishes the widgets, then ships as an app.
- **v5** adds the intelligence layer (ranking, digest, semantic filtering). Optional, later.

---

# Version 1 - Prove the pipeline

**Goal:** two or three hard-coded interest modules on one page, deployed, openable on your
phone. No login, no database, interests hard-coded. This exists to prove the fetch, normalize,
serve, render, deploy loop works before any structure is added.

### Phase 1.1 - Skeleton and one live source
- Set up the FastAPI project and a single endpoint.
- Fetch the top stories from the **Hacker News API** and return them raw.
- Confirm you get live data over HTTP.

### Phase 1.2 - The normalized item shape
- Define one common shape every source will map to, for example:
  `{ source, type, title, subtitle, url, timestamp, image }`.
- Map the Hacker News response into a list of these. This shape is the contract the frontend
  depends on, so pin it down now.

### Phase 1.3 - Two more modules, deliberately different
- Add **upcoming movies** (TMDB, a calendar-shaped source) and **a couple of followed TV shows**
  (TVmaze, hard-code the show IDs for now). Pick sources whose data looks different on purpose:
  a headline stream, a release calendar, and a followed-item countdown, so the normalized shape
  gets tested against all three content types early.
- Each becomes its own endpoint or a section of one combined feed.
- **Esports is deliberately not in v1.** The research flagged it as fragile: vlr.gg has no
  official API, the community `vlrggapi` scraper's public instance is down, and it must be
  self-hosted. That is the wrong risk to carry while proving the pipeline. Esports comes in a
  later version once the pipeline is solid and you are ready to self-host it. See `SOURCES.md`.

### Phase 1.4 - Minimal frontend
- One page. Fetch your backend, render a titled card block per module.
- No styling ambition yet, just readable, correct, and grouped by module.

### Phase 1.5 - Deploy
- Backend to a free host, frontend to a free static host, wire the frontend to the deployed
  backend URL. Open it on your phone.

**Done when:** tech headlines, upcoming movies, and next-episode info for a couple of hard-coded
TV shows all show on one deployed page you can open on your phone. Interests are hard-coded.
There is no login and no database.

---

# Version 2 - Interests as data, sources as plugins

**Goal:** stop hard-coding. Interests become configuration, sources become interchangeable
plugins, and responses are cached. Still single-user, still no accounts.

### Phase 2.1 - The source adapter interface
- Define one interface every source implements: given its config, `fetch()` returns a list of
  normalized items. Refactor the three v1 modules to it.
- Payoff: adding a new source becomes "write one adapter", nothing else changes.

### Phase 2.2 - Interests as config
- Move the interest list out of code into data (a config file or DB rows): which sources are
  active, and each source's parameters (for esports, which game).
- The app now renders from this list, not from hard-coded modules.

### Phase 2.3 - Persistence
- Stand up Postgres (local or Docker for dev). Define the schema for interests and their
  settings, store them, and read them on startup. Use a migration tool from day one
  (Alembic if the backend is FastAPI/SQLAlchemy) so schema changes are tracked cleanly.

### Phase 2.4 - Caching and rate-limit safety
- Cache each source's response with a time-to-live (say tech every 15 min, movies once a day).
- Serve from cache when fresh. This protects free-tier rate limits and makes the app fast.

### Phase 2.5 - Graceful per-source failure
- If one source errors or times out, the rest of the page must still render. One dead API
  never takes down the dashboard. Return a per-module error state instead.

**Done when:** interests live in data, adding a new source is writing a single adapter,
responses are cached with sensible TTLs, and a failing source degrades to an error card
instead of breaking the page.

---

# Version 3 - Accounts, onboarding, and the two shapes

**Goal:** multiple users, each with their own dashboard, built through a first-login flow that
respects the stream-vs-follow distinction.

### Phase 3.1 - Accounts and per-user profiles
- Add simple authentication and a per-user record. Keep it minimal; the point is a saved
  profile per person, not a full identity system.

### Phase 3.2 - Onboarding step one: pick domains
- First login shows the domain choices (tech, sports, esports, gaming, TV, anime, movies).
- Save the selection to the user's profile.

### Phase 3.3 - Onboarding step two: refine per shape
- For **stream** domains, ask the sub-topic: esports -> which game; sports -> which leagues.
- For **follow** domains, let the user search and follow specific items: TV shows via TVmaze,
  anime via AniList. Store the followed IDs.

### Phase 3.4 - Search and follow mechanism
- Build the search-and-follow flow used by follow-shaped interests: query the source, show
  results, let the user follow, persist the follow list.

### Phase 3.5 - Personal dashboard render
- The dashboard now builds entirely from the logged-in user's saved domains, sub-topics, and
  follows. Two different users see two different pages.

**Done when:** a new user logs in, picks domains, refines them (game for esports, shows for
TV/anime, leagues/teams for sports), and sees a tailored dashboard that persists across
sessions.

---

# Version 4 - Breadth and content-appropriate widgets

**Goal:** cover all your target domains, and render each content type with a widget that fits
it, then ship as an installable app.

### Phase 4.1 - Add remaining domains
- Fill in the rest of the source map: more sports, gaming releases, anime, extra tech sources.
- Each is just another adapter thanks to v2's interface.

### Phase 4.2 - Widget types
- Build distinct card types instead of one generic list:
  - **Headline list** for tech, gaming and sports news.
  - **Release calendar** for upcoming movies, game releases, seasonal anime.
  - **Next-episode countdown** for followed TV shows and anime.
  - **Fixtures, scores, standings** for followed sports.

### Phase 4.3 - The tab + dashboard layout
- Implement the information architecture (see section above): the four tabs (Sports, Games,
  Screen, Tech), calendar-plus-feed zones inside each tab (calendar only where the domain has
  dated events), the Movies/TV/Anime news sub-tabs inside Screen, and the dashboard as unified
  calendar plus top ~2 headlines per interest.
- News inside each tab: source labels plus grouping by the sub-topics and followed entities
  chosen at onboarding.

### Phase 4.4 - UX polish
- Loading skeletons, empty states, and clear per-module error states. Make it feel finished.

### Phase 4.5 - Ship as an app
- Wrap the frontend with Capacitor, test on a device, produce an installable build.

**Done when:** every target domain is covered with a content-appropriate widget, the app
handles loading, empty, and error states cleanly, and it runs as an installable mobile app.

---

# Version 5 - The intelligence layer (optional, later)

**Goal:** make the dashboard smart. This is where the embedding and ML skills from your deep
learning plan plug in. Do not start this until you have those skills; it is a Stage 2 project.

### Phase 5.1 - Track engagement
- Log what the user opens and clicks. This implicit feedback is the training signal for
  everything below.

### Phase 5.2 - Ranking
- Order items by learned relevance. Start simple (recency plus engagement weighting), then
  move to embedding-based similarity to what the user actually engages with.

### Phase 5.3 - Daily digest
- Generate one plain-language cross-interest summary of the day using an LLM: "here is what
  happened across your stuff today."

### Phase 5.4 - Semantic filtering and dedupe
- Use embeddings to surface items similar to what you like within noisy streams, and to
  collapse near-duplicate stories into one.

**Done when:** the dashboard ranks and filters based on your behavior and produces a daily
cross-interest digest, with the ranking demonstrably better than plain reverse-chronological.

---

## Principles to keep

- **Ship each version before starting the next.** An unfinished v4 is worth less than a
  finished v1.
- **Narrow beats broad in v1.** One esport, a couple of followed shows, two or three modules.
  Hard-code your own interests if it gets you to deployed faster.
- **The normalized item shape and the adapter interface are the spine.** Get them right and
  every new source is cheap. Get them wrong and every source is a fight.
- **One dead source must never break the page.** Build for partial failure from v2 onward.
- **v1 to v4 are a web/full-stack project, not ML.** File them under "shipped a real app."
  The ML resume line only starts at v5.
