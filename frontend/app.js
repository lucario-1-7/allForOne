/* AllForOne frontend: vanilla JS single page app.
   Views: auth -> onboarding -> main (dashboard + domain tabs).
   The dashboard is always a subset of what the tabs hold: one unified agenda
   plus the top two headlines per domain. Full feeds live in the tabs. */

const API = "/api";

const state = {
  token: localStorage.getItem("xp_token") || "",
  me: null,          // {email, domains, follows, leagues}
  feed: null,        // /api/feed payload
  tab: "dashboard",
  screenSub: "movies",
  authMode: "login",
  // onboarding scratch
  obDomains: {},     // domain -> config
  searchResults: { tv: [], anime: [] },
  liveTimer: null,   // interval id for live-score polling (Sports tab only)
};

const app = document.getElementById("app");

const DOMAIN_META = {
  sports: { name: "Sports", desc: "Fixtures and sports news" },
  games: { name: "Games", desc: "Releases, gaming news, esports" },
  screen: { name: "Screen", desc: "Movies, TV shows, anime" },
  tech: { name: "Tech", desc: "Tech headlines" },
};
const TAB_ORDER = ["sports", "games", "screen", "tech"];
const TECH_TOPICS = ["ai", "hardware", "software", "mobile", "startups"];
// non-soccer sports: key -> label. Soccer leagues come from the backend.
const OTHER_SPORTS = { nba: "NBA (basketball)", f1: "Formula 1", cricket: "Cricket", tennis: "Tennis" };

/* ---------- api helper ---------- */

async function call(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const resp = await fetch(API + path, { ...options, headers });
  if (resp.status === 401 && state.token) { signOut(); throw new Error("Signed out"); }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || `Request failed (${resp.status})`);
  return data;
}

function signOut() {
  stopLive();
  state.token = "";
  localStorage.removeItem("xp_token");
  state.me = null;
  state.feed = null;
  renderAuth();
}

/* ---------- utilities ---------- */

function esc(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function dayLabel(iso) {
  const date = new Date(iso);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const same = (a, b) => a.toDateString() === b.toDateString();
  if (same(date, today)) return "Today";
  if (same(date, tomorrow)) return "Tomorrow";
  return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function timeLabel(iso) {
  const date = new Date(iso);
  if (date.getUTCHours() === 0 && date.getUTCMinutes() === 0) return "All day";
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function agoLabel(iso) {
  if (!iso) return "";
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return `${mins}m ago`;
  if (mins < 60 * 24) return `${Math.round(mins / 60)}h ago`;
  return `${Math.round(mins / 1440)}d ago`;
}

/* ---------- auth view ---------- */

function renderAuth() {
  const login = state.authMode === "login";
  app.innerHTML = `
    <div class="center-card">
      <h1>AllForOne</h1>
      <p class="sub">Everything you follow, in one place.</p>
      <div class="field"><label>Email</label><input id="email" type="email" autocomplete="email"></div>
      <div class="field"><label>Password${login ? "" : " (at least 8 characters)"}</label>
        <input id="password" type="password" autocomplete="${login ? "current-password" : "new-password"}"></div>
      <div class="btn-row">
        <button class="btn" id="submit">${login ? "Sign in" : "Create account"}</button>
        <span class="switch-link" id="switch">${login ? "New here? Create an account" : "Have an account? Sign in"}</span>
      </div>
      <div class="form-error" id="err"></div>
    </div>`;

  document.getElementById("switch").onclick = () => {
    state.authMode = login ? "register" : "login";
    renderAuth();
  };
  const submit = async () => {
    const err = document.getElementById("err");
    err.textContent = "";
    try {
      const body = JSON.stringify({
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
      });
      const data = await call(`/auth/${login ? "login" : "register"}`, { method: "POST", body });
      state.token = data.token;
      localStorage.setItem("xp_token", data.token);
      await loadMe();
      if (data.onboarded) await loadMain(); else startOnboarding();
    } catch (e) { err.textContent = e.message; }
  };
  document.getElementById("submit").onclick = submit;
  document.getElementById("password").addEventListener("keydown", e => { if (e.key === "Enter") submit(); });
}

/* ---------- onboarding ---------- */

function startOnboarding() {
  state.obDomains = {};
  for (const [domain, config] of Object.entries(state.me?.domains || {})) {
    state.obDomains[domain] = { ...config };
  }
  renderOnboarding();
}

function renderOnboarding() {
  const on = d => d in state.obDomains;
  const leagues = state.me?.leagues || {};
  const sportsCfg = state.obDomains.sports || {};
  const gamesCfg = state.obDomains.games || {};
  const techCfg = state.obDomains.tech || {};
  const follows = state.me?.follows || [];

  const domainCards = TAB_ORDER.map(d => `
    <div class="domain-card ${on(d) ? "on" : ""}" data-domain="${d}">
      <div class="name">${DOMAIN_META[d].name}</div>
      <div class="desc">${DOMAIN_META[d].desc}</div>
    </div>`).join("");

  let refine = "";
  if (on("sports")) {
    const chosenLeagues = sportsCfg.leagues || [];
    const chosenSports = sportsCfg.sports || [];
    const sportChips = Object.entries(OTHER_SPORTS).map(([key, label]) =>
      `<span class="chip ${chosenSports.includes(key) ? "on" : ""}" data-sport="${key}">${esc(label)}</span>`).join("");
    const leagueChips = Object.entries(leagues).map(([code, label]) =>
      `<span class="chip ${chosenLeagues.includes(code) ? "on" : ""}" data-league="${code}">${esc(label)}</span>`).join("");
    refine += `<div class="ob-section"><h3>Sports</h3>
      <p class="hint">Pick your sports. F1 works with no key; NBA, cricket, and tennis each need their own free key (see SOURCES.md).</p>
      <div class="chip-row" id="sport-row">${sportChips}</div>
      <p class="hint">Soccer competitions (needs a football-data.org key):</p>
      <div class="chip-row" id="league-row">${leagueChips}</div></div>`;
  }
  if (on("games")) {
    refine += `<div class="ob-section"><h3>Games</h3>
      <p class="hint">Game releases come automatically. Esports is optional and needs a self-hosted vlrggapi.</p>
      <div class="chip-row"><span class="chip ${gamesCfg.esports === "valorant" ? "on" : ""}" id="chip-valo">Valorant esports</span></div></div>`;
  }
  if (on("tech")) {
    const chosen = techCfg.subtopics || [];
    refine += `<div class="ob-section"><h3>Tech</h3>
      <p class="hint">Optional sub-topics, used to group and rank your tech feed.</p>
      <div class="chip-row" id="tech-row">${TECH_TOPICS.map(t =>
        `<span class="chip ${chosen.includes(t) ? "on" : ""}" data-topic="${t}">${t}</span>`).join("")}</div></div>`;
  }
  if (on("screen")) {
    const pills = follows.map(f =>
      `<span class="follow-pill">${esc(f.title)} <button data-unfollow="${f.id}" title="Unfollow">x</button></span>`).join("");
    refine += `<div class="ob-section"><h3>Screen</h3>
      <p class="hint">Follow the TV shows and anime you watch; the calendar tracks their next episodes. Movies come automatically.</p>
      <div class="search-row">
        <input id="tv-q" placeholder="Search TV shows...">
        <button class="btn small secondary" id="tv-go">Search</button>
      </div>
      <div class="search-results" id="tv-results">${hitList("tv")}</div>
      <div class="search-row">
        <input id="anime-q" placeholder="Search anime...">
        <button class="btn small secondary" id="anime-go">Search</button>
      </div>
      <div class="search-results" id="anime-results">${hitList("anime")}</div>
      <div class="follow-list">${pills || '<span class="empty">Nothing followed yet.</span>'}</div>
    </div>`;
  }

  app.innerHTML = `
    <div class="center-card wide">
      <h1>What are you into?</h1>
      <p class="sub">Pick your domains, then refine each one. You can change this any time.</p>
      <div class="domain-grid">${domainCards}</div>
      ${refine}
      <div class="btn-row">
        <button class="btn" id="save" ${Object.keys(state.obDomains).length ? "" : "disabled"}>Save and continue</button>
      </div>
      <div class="form-error" id="err"></div>
    </div>`;

  wireOnboarding();
}

function hitList(kind) {
  return (state.searchResults[kind] || []).map(hit => `
    <div class="search-hit">
      <span>${esc(hit.title)} <span class="meta">${esc(hit.subtitle)}</span></span>
      <button class="btn small" data-follow="${kind}" data-id="${esc(hit.external_id)}" data-title="${esc(hit.title)}">Follow</button>
    </div>`).join("");
}

function wireOnboarding() {
  document.querySelectorAll(".domain-card").forEach(card => {
    card.onclick = () => {
      const domain = card.dataset.domain;
      if (domain in state.obDomains) delete state.obDomains[domain];
      else state.obDomains[domain] = {};
      renderOnboarding();
    };
  });

  document.querySelectorAll("#sport-row .chip").forEach(chip => {
    chip.onclick = () => {
      const cfg = state.obDomains.sports;
      cfg.sports = cfg.sports || [];
      const key = chip.dataset.sport;
      cfg.sports = cfg.sports.includes(key) ? cfg.sports.filter(s => s !== key) : [...cfg.sports, key];
      renderOnboarding();
    };
  });

  document.querySelectorAll("#league-row .chip").forEach(chip => {
    chip.onclick = () => {
      const cfg = state.obDomains.sports;
      cfg.leagues = cfg.leagues || [];
      const code = chip.dataset.league;
      cfg.leagues = cfg.leagues.includes(code) ? cfg.leagues.filter(c => c !== code) : [...cfg.leagues, code];
      renderOnboarding();
    };
  });

  const valo = document.getElementById("chip-valo");
  if (valo) valo.onclick = () => {
    const cfg = state.obDomains.games;
    cfg.esports = cfg.esports === "valorant" ? null : "valorant";
    renderOnboarding();
  };

  document.querySelectorAll("#tech-row .chip").forEach(chip => {
    chip.onclick = () => {
      const cfg = state.obDomains.tech;
      cfg.subtopics = cfg.subtopics || [];
      const topic = chip.dataset.topic;
      cfg.subtopics = cfg.subtopics.includes(topic) ? cfg.subtopics.filter(t => t !== topic) : [...cfg.subtopics, topic];
      renderOnboarding();
    };
  });

  for (const kind of ["tv", "anime"]) {
    const go = document.getElementById(`${kind}-go`);
    const input = document.getElementById(`${kind}-q`);
    if (!go) continue;
    const run = async () => {
      if (!input.value.trim()) return;
      go.disabled = true;
      try {
        const data = await call(`/search?kind=${kind}&q=${encodeURIComponent(input.value)}`);
        state.searchResults[kind] = data.results;
        renderOnboarding();
        document.getElementById(`${kind}-q`).value = input.value;
      } catch (e) {
        document.getElementById("err").textContent = e.message;
      } finally { go.disabled = false; }
    };
    go.onclick = run;
    input.addEventListener("keydown", e => { if (e.key === "Enter") run(); });
  }

  document.querySelectorAll("[data-follow]").forEach(btn => {
    btn.onclick = async () => {
      btn.disabled = true;
      try {
        await call("/me/follows", { method: "POST", body: JSON.stringify({
          kind: btn.dataset.follow, external_id: btn.dataset.id, title: btn.dataset.title }) });
        await loadMe();
        renderOnboarding();
      } catch (e) { document.getElementById("err").textContent = e.message; }
    };
  });

  document.querySelectorAll("[data-unfollow]").forEach(btn => {
    btn.onclick = async () => {
      await call(`/me/follows/${btn.dataset.unfollow}`, { method: "DELETE" });
      await loadMe();
      renderOnboarding();
    };
  });

  document.getElementById("save").onclick = async () => {
    const err = document.getElementById("err");
    err.textContent = "";
    try {
      const domains = {};
      for (const [domain, config] of Object.entries(state.obDomains)) domains[domain] = config;
      await call("/me/interests", { method: "PUT", body: JSON.stringify({ domains }) });
      await loadMe();
      await loadMain();
    } catch (e) { err.textContent = e.message; }
  };
}

/* ---------- main app ---------- */

async function loadMe() {
  state.me = await call("/me");
}

async function loadMain() {
  app.innerHTML = `<div class="loading">Fetching your feed...</div>`;
  try {
    state.feed = await call("/feed");
  } catch (e) {
    app.innerHTML = `<div class="loading">Could not load the feed: ${esc(e.message)}</div>`;
    return;
  }
  state.tab = "dashboard";
  renderMain();
}

function renderMain() {
  const picked = TAB_ORDER.filter(d => state.feed.domains[d]);
  const tabs = ["dashboard", ...picked];
  app.innerHTML = `
    <header class="top">
      <span class="brand">AllForOne</span>
      <nav class="tabs">${tabs.map(t => `
        <button class="${state.tab === t ? "on" : ""}" data-tab="${t}">
          ${t === "dashboard" ? "Dashboard" : DOMAIN_META[t].name}
        </button>`).join("")}
      </nav>
      <span class="user">${esc(state.me.email)}
        <a id="edit">Edit interests</a><a id="signout">Sign out</a></span>
    </header>
    <main class="content" id="content"></main>`;

  document.querySelectorAll("nav.tabs button").forEach(btn => {
    btn.onclick = () => { state.tab = btn.dataset.tab; renderMain(); };
  });
  document.getElementById("edit").onclick = () => { startOnboarding(); };
  document.getElementById("signout").onclick = signOut;

  const content = document.getElementById("content");
  content.innerHTML = state.tab === "dashboard" ? renderDashboard() : renderDomain(state.tab);
  wireSubtabs();

  // Live scores poll only while the Sports tab is open (client-driven, self-limiting).
  stopLive();
  if (state.tab === "sports") startLive();
}

/* ---------- live scores ---------- */

function stopLive() {
  if (state.liveTimer) { clearInterval(state.liveTimer); state.liveTimer = null; }
}

async function startLive() {
  await refreshLive();
  state.liveTimer = setInterval(refreshLive, 45000);
}

async function refreshLive() {
  const strip = document.getElementById("live-strip");
  if (!strip) { stopLive(); return; }  // navigated away
  try {
    const data = await call("/live");
    renderLiveStrip(strip, data.matches || []);
  } catch { /* best-effort: never let a live hiccup disrupt the page */ }
}

function renderLiveStrip(strip, matches) {
  if (!matches.length) { strip.innerHTML = ""; return; }
  strip.innerHTML =
    `<div class="section-title live-title"><span class="live-dot"></span>Live now</div>
     <div class="live-strip">` +
    matches.map(m => `
      <div class="live-match">
        <span class="live-score">${esc(m.title)}</span>
        <span class="live-sub">${esc(m.subtitle)}</span>
      </div>`).join("") +
    `</div>`;
}

function errorCards(domain) {
  const errors = (state.feed.errors || []).filter(e => e.domain === domain);
  return errors.map(e =>
    `<div class="error-card"><b>${esc(e.source.split(":")[0])}</b>: ${esc(e.message)}</div>`).join("");
}

function agendaHtml(events, limit = 40) {
  if (!events.length) return `<div class="empty">Nothing scheduled right now.</div>`;
  const upcoming = events.filter(e => !e.ts || new Date(e.ts) > new Date(Date.now() - 12 * 3600 * 1000));
  let html = `<div class="agenda">`;
  let lastDay = "";
  for (const event of upcoming.slice(0, limit)) {
    const day = event.ts ? dayLabel(event.ts) : "Scheduled";
    if (day !== lastDay) { html += `<div class="day">${day}</div>`; lastDay = day; }
    html += `
      <div class="event">
        <span class="time">${event.ts ? timeLabel(event.ts) : ""}</span>
        <span class="etitle">${event.url ? `<a href="${esc(event.url)}" target="_blank" rel="noopener">${esc(event.title)}</a>` : esc(event.title)}</span>
        <span class="esub">${esc(event.subtitle)}${event.group ? ` &middot; ${esc(cap(event.group))}` : ""}</span>
      </div>`;
  }
  return html + `</div>`;
}

function newsHtml(items, limit = 30) {
  if (!items.length) return `<div class="empty">No headlines right now.</div>`;
  return `<div class="news-list">` + items.slice(0, limit).map(n => `
    <div class="news-item">
      <a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title)}</a>
      <div class="nmeta"><span class="src">${esc(n.source)}</span> &middot; ${agoLabel(n.ts)}</div>
    </div>`).join("") + `</div>`;
}

function cap(text) { return text ? text[0].toUpperCase() + text.slice(1) : ""; }

function domainNews(domain) {
  const data = state.feed.domains[domain];
  if (!data) return [];
  if (domain === "screen") return [...data.news.movies, ...data.news.tv, ...data.news.anime]
    .sort((a, b) => (b.ts || "").localeCompare(a.ts || ""));
  return data.news;
}

function renderDashboard() {
  const domains = Object.keys(state.feed.domains);
  const allEvents = domains.flatMap(d => state.feed.domains[d].events)
    .filter(e => e.ts)
    .sort((a, b) => a.ts.localeCompare(b.ts));

  const highlights = domains.map(domain => {
    const top = domainNews(domain).slice(0, 2);
    if (!top.length) return "";
    return `<div class="dash-domain">
      <div class="dname">${DOMAIN_META[domain].name}</div>
      ${newsHtml(top, 2)}
    </div>`;
  }).join("");

  const allErrors = (state.feed.errors || []).map(e =>
    `<div class="error-card"><b>${esc(e.source.split(":")[0])}</b>: ${esc(e.message)}</div>`).join("");

  return `
    ${allErrors}
    <div class="section-title">Coming up across everything</div>
    ${agendaHtml(allEvents, 14)}
    <div class="section-title">Key headlines</div>
    ${highlights || '<div class="empty">Pick some interests to see headlines.</div>'}`;
}

function renderDomain(domain) {
  const data = state.feed.domains[domain];
  if (!data) return `<div class="empty">Not enabled.</div>`;

  let html = errorCards(domain);

  // Live scores strip (football only); filled and refreshed by the poller.
  if (domain === "sports") html += `<div id="live-strip"></div>`;

  // Calendar zone: only for domains rich in dated events (IA rule: tech gets none)
  if (domain !== "tech") {
    html += `<div class="section-title">Coming up</div>` + agendaHtml(data.events);
  }

  if (domain === "screen") {
    const sub = state.screenSub;
    html += `<div class="section-title">News</div>
      <div class="subtabs">
        ${["movies", "tv", "anime"].map(s =>
          `<button class="${sub === s ? "on" : ""}" data-sub="${s}">${s === "tv" ? "TV" : cap(s)}</button>`).join("")}
      </div>
      ${newsHtml(data.news[sub])}`;
  } else {
    html += `<div class="section-title">News</div>` + newsHtml(data.news);
  }
  return html;
}

function wireSubtabs() {
  document.querySelectorAll(".subtabs button").forEach(btn => {
    btn.onclick = () => {
      state.screenSub = btn.dataset.sub;
      document.getElementById("content").innerHTML = renderDomain("screen");
      wireSubtabs();
    };
  });
}

/* ---------- boot ---------- */

(async function boot() {
  if (!state.token) { renderAuth(); return; }
  try {
    await loadMe();
    if (Object.keys(state.me.domains).length) await loadMain();
    else startOnboarding();
  } catch {
    renderAuth();
  }
})();
