# RealEstateTinder

A private, single-user, mobile-first web app for discovering and filtering real-estate
investment opportunities in the Hadera↔Gedera corridor: a swipe-style discovery feed,
a saved-inventory tracker, AI-powered CMA/deal analysis, daily automated ingestion, and
an educational guide to Israeli planning-process terminology.

## Architecture

- **Backend**: FastAPI + SQLAlchemy (`backend/`). SQLite locally, Postgres in production.
  A daily APScheduler job (default 06:00 Asia/Jerusalem) runs the ingestion pipeline.
- **Frontend**: Next.js (App Router) + Tailwind CSS (`frontend/`), RTL Hebrew UI.
- **Auth**: a single shared password gate (no per-user accounts) — appropriate for a
  private single-user tool. A signed, HttpOnly session cookie protects every API route.

## Data sourcing — what's real vs. mock, and why

None of Yad2, Madlan, WinWin or Facebook groups expose an official public API, and none
can be reliably scraped long-term (bot protection, ToS, frequent markup changes). So the
ingestion pipeline is built around a `SourceAdapter` interface (`backend/app/services/sources/base.py`)
that every source implements identically — the rest of the app (DB, AI/CMA analysis, UI,
email alerts) never knows or cares whether a listing came from a live call or from
realistic mock data.

| Source | Status | Notes |
|---|---|---|
| Yad2 | **Real via Apify (optional) → real direct attempt → mock fallback** | If `APIFY_API_TOKEN` + `APIFY_ACTOR_ID` are set, `services/sources/apify_yad2.py` fetches real listings through Apify (see "Apify setup" below). Otherwise `services/sources/yad2.py` calls Yad2's public (unofficial, undocumented) search endpoint directly with browser-like headers - blocked by PerimeterX in practice (see below). Either way, any failure falls back to mock listings automatically. |
| Madlan / WinWin / Facebook groups | Mock (realistic, same schema) | `services/sources/mock_adapter.py`. Swap in a real adapter later by implementing `SourceAdapter.fetch_listings` the same way `Yad2Adapter` does. |
| Israel Tax Authority transactions (CMA) | **Real attempt + mock fallback** | `services/gov_data/tax_authority.py` calls the public `data.gov.il` CKAN `datastore_search` API. Falls back to deterministic per-city mock comparables on failure. |
| Pinui Binui / presale planning status | Mock (realistic) | Generated alongside new_project/pinui_binui mock listings; wire up a real `gov_data` adapter the same way later. |

### Apify setup (real Yad2 listings)

The direct Yad2 attempt above is reliably blocked by PerimeterX (see below), so the
realistic path to real listings is [Apify](https://apify.com) - a paid scraping platform
that runs the actual scraping on its own infrastructure and handles that compliance
question itself, rather than this app attempting to evade Yad2's anti-bot defenses (which
it deliberately doesn't do).

**There is no single "official" Yad2 actor** - you pick one from the
[Apify Store](https://apify.com/store) (search "yad2") and verify it works with your own
account before relying on it. To wire one up:

1. Create an Apify account and get an API token from your
   [Apify Console → Settings → Integrations](https://console.apify.com/account/integrations).
2. Pick a Yad2 scraper actor from the Apify Store, note its id (`username/actor-name`,
   e.g. `someone/yad2-scraper` - shown on the actor's page).
3. On Railway, set on the **backend** service: `APIFY_API_TOKEN` (your token) and
   `APIFY_ACTOR_ID` (the actor id from step 2).
4. Trigger `POST /api/ingest/run` and check the logs for `Apify Yad2 run returned N real
   listings` vs. a fallback warning. If it falls back, the actor's input or output shape
   likely differs from what this integration assumes by default:
   - **Input**: by default, this sends `{"startUrls": [...Yad2 search-result URLs per
     target city...], "maxItems": ...}` - the most common shape generic Yad2 actors accept.
     If your actor expects something else (e.g. a structured `search` object), set
     `APIFY_ACTOR_INPUT_JSON` to override the input entirely.
   - **Output mapping**: `_parse_item()` in `apify_yad2.py` tries several common field-name
     variants (`price`/`Price`/`askingPrice`, `rooms`/`Rooms`/`roomsCount`, etc.) - this is
     a best-effort guess, not a verified schema for any specific actor. Pull a sample run's
     dataset (Apify Console → your run → Dataset → Export) and adjust the key lists in
     `_first()` calls to match what your actor actually returns.
5. Growth-area cities (marked ⭐ on `/areas`) are always included in the Apify search
   alongside your main search area, even if outside it - so e.g. flagging Bat Yam as a
   growth area gets it searched regardless of your selected corridor.

**Verified vs. not**: this sandbox blocks outbound calls to `api.apify.com` the same way
it blocks `yad2.co.il`, so the actual scraping run could not be tested end-to-end. What
*was* verified: the `apify-client` API calls used here (`actor().call()`,
`dataset().iterate_items()`) match the real installed client's method signatures exactly
(introspected directly against `apify-client==3.1.3`), the item-parsing logic was
unit-tested against several synthetic realistic dataset shapes, and a real (failing, since
the sandbox blocks it) network call was made to confirm the whole path falls back to mock
data cleanly rather than crashing. The actor choice, its real input schema, and its real
output field names are yours to verify against a live run.

**Important — verify after deploying:** this project was built in a sandboxed dev
environment whose network policy blocks outbound calls to `yad2.co.il` and
`data.gov.il` entirely, so the "real attempt" code paths above could not be
network-tested here. The code is written defensively (any failure silently
falls back to mock data rather than crashing the pipeline), but once deployed
somewhere with normal internet access you should:

1. Trigger `POST /api/ingest/run` and check the response / logs for whether Yad2 and the
   Tax Authority calls actually returned live data (`Yad2Adapter.is_live`) or fell back.
2. If they fell back, inspect `_CITY_IDS` in `yad2.py` and `_RESOURCE_ID` in
   `tax_authority.py` — these were my best-effort guesses and may need correcting against
   the live site / dataset.

**On Yad2's anti-bot protection specifically:** live testing (from Railway, which has
normal internet access unlike the dev sandbox) shows Yad2's PerimeterX protection
actively redirects these requests to a CAPTCHA/validation page — so right now every
"Yad2" listing in the database is really the mock fallback. The adapter retries
transient failures (timeouts, 5xx) with backoff and reports blocked-vs-broken separately
in the logs, and supports an optional `YAD2_PROXY_URL` env var to route through your own
paid proxy or a commercial scraping API (Apify, ScrapingBee — see below) if you have one.
Deliberately NOT implemented: CAPTCHA solving or fingerprint/IP spoofing to defeat
PerimeterX — that crosses from resilient scraping into actively evading a site's anti-bot
defenses, which this project stays away from. If real Yad2 listings matter to you, a paid
scraping API is the realistic path (it handles that compliance question itself).

**Image policy:** a property only ever shows a photo it actually scraped from its source
(currently: none, since Yad2 is blocked as above). No placeholder/stock photo is ever
substituted — a listing without a genuine image shows a blank tile with a link to the
original listing instead ("בשביל תמונה אנא כנס לקישור").

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit APP_PASSWORD at minimum; SESSION_COOKIE_SECURE=false for http
uvicorn app.main:app --reload
```

Runs on `http://localhost:8000`, using a local `nadlan.db` SQLite file. Interactive API
docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Runs on `http://localhost:3000`.

## Deploying to Railway

1. Create a Railway project, add a **Postgres** plugin — it provides `DATABASE_URL`
   automatically.
2. Deploy `backend/` as a service (it has a `Dockerfile`). Set service variables:
   `APP_PASSWORD`, `SESSION_SECRET`, `FRONTEND_ORIGINS` (your deployed frontend URL),
   `ANTHROPIC_API_KEY` (for AI analysis), `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD`/
   `ALERT_EMAIL_TO` (for deal-alert emails — e.g. a Gmail address + an
   [App Password](https://myaccount.google.com/apppasswords)), and optionally
   `APIFY_API_TOKEN` + `APIFY_ACTOR_ID` (for real Yad2 listings — see "Apify setup"
   above). Leave `DATABASE_URL` as Railway's provided Postgres URL and
   `SESSION_COOKIE_SECURE` unset (defaults to `true`).
3. Deploy `frontend/` as a second Railway service (Nixpacks auto-detects Next.js). Set
   `BACKEND_URL` (server-side only, no `NEXT_PUBLIC_` prefix) to the backend service's
   URL — `next.config.js` proxies all `/api/*` browser requests to it. This keeps every
   request same-origin from the browser's point of view, which matters because the
   frontend and backend live on different Railway subdomains: without the proxy the
   session cookie would be a cross-site (third-party) cookie, which modern Chrome/Safari
   block by default and login would silently fail to persist.
4. The daily ingestion runs automatically via the in-process scheduler once the backend
   service is up — no separate cron service needed. Adjust the time with
   `INGESTION_CRON_HOUR`.

## Product pages

- `/` — **Discovery feed** ("Tinder mode"): swipe/tap ❤️ save, ❌ pass, or 🔖 push-to-back
  on one property at a time. Passed properties are hidden forever; liked ones move to Saved
  Inventory. 🔖 is a bookmark, not a final decision — it moves the card to the end of the
  current queue (you keep cycling through everything else, then see it again) and also
  appears on `/later`, until you actually decide ❤️/❌ on it from either place. An
  **➕ הוספת נכס לפי קישור** button opens a modal to paste a listing URL (Yad2 or any other
  site) - it's fetched, parsed, and dropped straight into the feed; if too little could be
  parsed automatically, the modal falls back to a short manual-entry form (pre-filled with
  whatever partial data - title, image, price - was found) so the workflow never gets stuck.
- `/saved` — **Saved Inventory Hub**: all liked properties, filterable by status
  (Under Review / Contacted Agent / Archived), with private notes per property.
- `/later` — everything bookmarked for later that's still undecided; rate ❤️/❌ from here,
  or remove the bookmark to leave it in the regular feed only.
- `/guide` — **Planning Stages Guide**: plain-Hebrew explanations of תב"ע, הפקדה,
  הוועדה המקומית/המחוזית, היתר בנייה, and the 4 stages of פינוי בינוי.
- `/areas` — configure the search area (pick specific cities, or an address + radius in km,
  resolved against a curated coordinate table) and mark "growth area" cities (⭐, e.g. בת ים)
  that get a badge on every matching property card.
- `/finance` — default equity, loan term, and mortgage mix ("תמהיל") used to compute the
  estimated monthly mortgage payment and cash flow shown on every property card.
- `/chat` — **AI Investment Advisor**: a chat loaded with your saved/for-later properties
  (CMA, rental yield, mortgage/cash-flow figures) - ask things like "which saved property has
  the best cash flow?" or "is this Bat Yam deal priced well?". Falls back to a few directly-
  computable answers (best cash flow / yield / discount) when no `ANTHROPIC_API_KEY` is set.

Every property card also shows its **estimated monthly rent and gross rental yield**
(`services/rental_estimates.py` - a curated rent-per-sqm table by city, since there's no
public rental-transaction registry like there is for sales) and an inline mortgage
calculator widget that recomputes instantly (client-side, mirroring the backend formula)
as you tweak equity/loan term for that one property.

## Filtering criteria (defaults, in `backend/app/config.py`)

- Geography: Hadera↔Gedera corridor cities (`target_cities`)
- Asset types: 4-room apartments, garden apartments, new projects (presale), Pinui Binui
- Budget: up to ₪2,500,000
- "High-Value Deal" flag: ≥15% below the Tax-Authority comparable price/sqm, or a
  presale/Pinui Binui project with an advanced planning status (תב"ע בתוקף / היתר בנייה)
