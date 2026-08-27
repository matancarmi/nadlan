"""Central configuration, loaded from environment variables (.env in dev)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    # Defaults to a local SQLite file for zero-config local dev.
    # On Railway, set DATABASE_URL to the provisioned Postgres connection string.
    database_url: str = "sqlite:///./nadlan.db"

    # --- Auth (simple single-user password gate) ---
    app_password: str = "changeme"
    session_secret: str = "dev-secret-change-me"
    # Frontend and backend are typically deployed on different subdomains, so
    # the session cookie needs SameSite=None + Secure over HTTPS in production.
    # Set to false only for local http:// dev (same-site localhost ports).
    session_cookie_secure: bool = True

    # --- AI (Claude) ---
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # --- Email alerts (SMTP) ---
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    alert_email_to: str = "matancarmi.mc@gmail.com"
    alert_email_from: str | None = None

    # --- Search criteria (defaults per product spec) ---
    max_budget_nis: int = 2_500_000
    target_cities: list[str] = [
        "חדרה", "נתניה", "כפר יונה", "טירת כרמל", "פרדס חנה-כרכור",
        "כפר סבא", "רעננה", "הרצליה", "פתח תקווה", "ראשון לציון",
        "רחובות", "יבנה", "גדרה",
    ]
    high_value_discount_threshold_pct: float = 15.0

    # --- Scheduler ---
    ingestion_cron_hour: int = 6  # daily run time (server local time), 24h format

    # --- CORS ---
    # Comma-separated list of allowed frontend origins (cookies require an exact
    # origin, not "*"). Set to your deployed frontend URL(s) in production.
    frontend_origins: str = "http://localhost:3000"

    # --- Ingestion network behavior ---
    # Real scrapers/gov API calls are attempted; on any failure (network policy,
    # site changes, rate limiting) each adapter falls back to labeled mock data
    # so the rest of the pipeline (AI analysis, alerts, UI) keeps working.
    ingestion_request_timeout_seconds: int = 20

    # --- Yad2 adapter resilience ---
    # Retries with backoff for transient failures (timeouts, 5xx). Does NOT
    # retry through PerimeterX bot-protection blocks - those are a deliberate
    # wall, not a transient error, and are logged distinctly instead.
    yad2_max_retries: int = 3
    yad2_retry_backoff_seconds: float = 1.5
    # Optional: route Yad2 requests through your own proxy or a commercial
    # scraping API (e.g. https://user:pass@proxy.scraperapi.com:8001) if you
    # have one. This is a pass-through hook only - nothing here manages,
    # rotates, or picks proxies on your behalf.
    yad2_proxy_url: str | None = None

    # --- Apify (real Yad2 listings via a third-party scraping platform) ---
    # When APIFY_API_TOKEN is set, the daily ingestion and POST /api/ingest/run
    # fetch Yad2 through Apify (which runs its own compliant scraping
    # infrastructure) instead of the direct-request attempt in yad2.py. Falls
    # back to the same mock data as the direct adapter if the Apify run fails
    # or an actor isn't configured.
    apify_api_token: str | None = None
    # Apify actor id, "username/actor-name" (see README for how to pick one -
    # there's no single official Yad2 actor, this must be chosen and verified
    # against your own Apify account).
    apify_actor_id: str | None = None
    # Optional raw JSON overriding the actor input this integration builds by
    # default (a list of Yad2 search-result startUrls + maxItems) - set this
    # if your chosen actor expects a different input shape.
    apify_actor_input_json: str | None = None
    apify_max_items: int = 200
    apify_run_timeout_seconds: int = 180


@lru_cache
def get_settings() -> Settings:
    return Settings()
