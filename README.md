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
| Yad2 | **Real attempt + mock fallback** | `services/sources/yad2.py` calls Yad2's public (unofficial, undocumented) search endpoint with browser-like headers. Any failure (blocking, schema drift, wrong city IDs) falls back to mock listings for that city automatically. |
| Madlan / WinWin / Facebook groups | Mock (realistic, same schema) | `services/sources/mock_adapter.py`. Swap in a real adapter later by implementing `SourceAdapter.fetch_listings` the same way `Yad2Adapter` does. |
| Israel Tax Authority transactions (CMA) | **Real attempt + mock fallback** | `services/gov_data/tax_authority.py` calls the public `data.gov.il` CKAN `datastore_search` API. Falls back to deterministic per-city mock comparables on failure. |
| Pinui Binui / presale planning status | Mock (realistic) | Generated alongside new_project/pinui_binui mock listings; wire up a real `gov_data` adapter the same way later. |

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
   [App Password](https://myaccount.google.com/apppasswords)). Leave `DATABASE_URL` as
   Railway's provided Postgres URL and `SESSION_COOKIE_SECURE` unset (defaults to `true`).
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

- `/` — **Discovery feed** ("Tinder mode"): swipe/tap ❤️ save or ❌ pass on one property
  at a time. Passed properties are hidden forever; liked ones move to Saved Inventory.
- `/saved` — **Saved Inventory Hub**: all liked properties, filterable by status
  (Under Review / Contacted Agent / Archived), with private notes per property.
- `/guide` — **Planning Stages Guide**: plain-Hebrew explanations of תב"ע, הפקדה,
  הוועדה המקומית/המחוזית, היתר בנייה, and the 4 stages of פינוי בינוי.

## Filtering criteria (defaults, in `backend/app/config.py`)

- Geography: Hadera↔Gedera corridor cities (`target_cities`)
- Asset types: 4-room apartments, garden apartments, new projects (presale), Pinui Binui
- Budget: up to ₪2,500,000
- "High-Value Deal" flag: ≥15% below the Tax-Authority comparable price/sqm, or a
  presale/Pinui Binui project with an advanced planning status (תב"ע בתוקף / היתר בנייה)
