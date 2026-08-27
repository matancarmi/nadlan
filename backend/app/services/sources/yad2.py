"""Yad2 real-estate listings adapter.

Yad2 has no official public API. This adapter makes a best-effort real HTTP
call to Yad2's public (unofficial, undocumented) search endpoint, browser-like
headers included, and parses the JSON it returns. Because the endpoint is
undocumented, city IDs are approximate and the response shape can change or
be blocked (Yad2 uses PerimeterX bot-protection, which redirects non-browser
clients to a CAPTCHA/validation page) — any failure for a given city, or of
the whole call, is caught and that city silently falls back to realistic
mock listings so the rest of the pipeline (DB, AI, CMA, UI, email alerts)
always has data to work with.

Deliberately NOT implemented here: CAPTCHA solving, browser-fingerprint
spoofing, or IP/residential-proxy rotation to defeat PerimeterX - that
crosses from "resilient scraping" into deliberately evading a site's active
anti-bot defenses, which this project stays away from. What IS implemented:
retries with backoff for transient failures, a clear distinction in the logs
between "blocked by anti-bot protection" and other errors, and an optional
pass-through proxy hook (`YAD2_PROXY_URL`) so you can legitimately route
through your own paid proxy or a commercial scraping API (e.g. Apify,
ScrapingBee - see the README) if you have one; this code never rotates or
manages that proxy itself.

NOTE: this was written and reasoned about, but could NOT be network-tested
from the development sandbox (outbound access to yad2.co.il is blocked by
this environment's network policy). Verify against the live site after
deploying, and adjust `_CITY_IDS` / `_parse_response` if Yad2's response
shape differs from what's assumed here.
"""
import logging
import random
import time

import httpx

from ...config import get_settings
from .base import RawListing, SourceAdapter

logger = logging.getLogger(__name__)

_BOT_PROTECTION_HOSTS = ("perfdrive.com", "shieldsquare.com", "px-cdn.net")

# Best-effort Yad2/CBS city IDs for the Hadera<->Gedera corridor. Unverified —
# if wrong, the API call for that city simply returns nothing and we fall
# back to mock data for it (see fetch_listings).
_CITY_IDS: dict[str, int] = {
    "חדרה": 2500,
    "נתניה": 7400,
    "כפר יונה": 2130,
    "טירת כרמל": 2800,
    "פרדס חנה-כרכור": 2530,
    "כפר סבא": 6900,
    "רעננה": 8700,
    "הרצליה": 6400,
    "פתח תקווה": 7900,
    "ראשון לציון": 8300,
    "רחובות": 8400,
    "יבנה": 1061,
    "גדרה": 1273,
}

_BASE_URL = "https://gw.yad2.co.il/realestate-feed/forsale/map"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
    "Referer": "https://www.yad2.co.il/realestate/forsale",
}

_ASSET_TYPE_MAP = {
    "garden": "garden_apartment",
    "4_rooms": "rooms_4",
    "new": "new_project",
}


class Yad2Adapter(SourceAdapter):
    name = "yad2"

    def fetch_listings(self, cities: list[str], max_price: float) -> list[RawListing]:
        settings = get_settings()
        listings: list[RawListing] = []
        any_live_success = False
        blocked_count = 0

        client_kwargs = {"headers": _HEADERS, "timeout": settings.ingestion_request_timeout_seconds}
        if settings.yad2_proxy_url:
            client_kwargs["proxy"] = settings.yad2_proxy_url

        with httpx.Client(**client_kwargs) as client:
            for city in cities:
                city_id = _CITY_IDS.get(city)
                if city_id is None:
                    continue
                result = self._fetch_city_with_retries(client, city, city_id, max_price, settings)
                if result == "blocked":
                    blocked_count += 1
                elif result:
                    listings.extend(result)
                    any_live_success = True

        self.is_live = any_live_success
        if blocked_count:
            logger.warning(
                "Yad2: %d/%d cities blocked by anti-bot protection (PerimeterX CAPTCHA redirect) - "
                "not retrying past that on purpose. Set YAD2_PROXY_URL to route through your own "
                "paid proxy/scraping API if you have one.",
                blocked_count,
                len(cities),
            )
        if not listings:
            logger.info("Yad2: no live results (blocked/unavailable), using mock fallback data")
            listings = self._mock_listings(cities, max_price)
        return listings

    def _fetch_city_with_retries(self, client, city, city_id, max_price, settings):
        """Returns a list of listings, "blocked" if PerimeterX intercepted the
        request, or None after exhausting retries on a transient error.
        Retries only genuinely transient failures (timeouts, connection
        errors, 5xx) - a bot-protection redirect is a deliberate wall, not a
        glitch, so it's reported once and not hammered with retries."""
        last_exc = None
        for attempt in range(1, settings.yad2_max_retries + 1):
            try:
                resp = client.get(_BASE_URL, params={"city": city_id, "maxPrice": int(max_price)})
                if resp.is_redirect and any(
                    host in resp.headers.get("location", "") for host in _BOT_PROTECTION_HOSTS
                ):
                    logger.info("Yad2 blocked by anti-bot protection for %s (attempt %d)", city, attempt)
                    return "blocked"
                resp.raise_for_status()
                payload = resp.json()
                return self._parse_response(payload, city)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    logger.warning("Yad2 live fetch failed for %s: %s", city, exc)
                    return None  # client error (403/404/...) - not transient, don't retry
                last_exc = exc
            except Exception as exc:  # noqa: BLE001 - network errors, timeouts, etc.
                last_exc = exc
            if attempt < settings.yad2_max_retries:
                time.sleep(settings.yad2_retry_backoff_seconds * attempt)
        logger.warning("Yad2 live fetch failed for %s after %d attempts: %s", city, settings.yad2_max_retries, last_exc)
        return None

    def _parse_response(self, payload: dict, city: str) -> list[RawListing]:
        items = payload.get("data", {}).get("markers") or payload.get("markers") or []
        out = []
        for item in items:
            try:
                price = item.get("price")
                if price is None or price > 0 and price == 0:
                    pass
                if price is None:
                    continue
                out.append(
                    RawListing(
                        source=self.name,
                        external_id=str(item.get("orderId") or item.get("id")),
                        title=item.get("title") or f"נכס למכירה ב{city}",
                        city=city,
                        asset_type=_ASSET_TYPE_MAP.get(item.get("propertyCondition"), "rooms_4"),
                        asking_price=float(price),
                        size_sqm=item.get("square") and float(item["square"]),
                        rooms=item.get("rooms") and float(item["rooms"]),
                        street=item.get("street"),
                        neighborhood=item.get("neighborhood"),
                        source_url=f"https://www.yad2.co.il/realestate/item/{item.get('id')}",
                        # Only a genuine image URL scraped from Yad2 itself - no
                        # placeholder. If Yad2 didn't provide one, image_url stays
                        # None and the UI shows "go to the link for a photo" instead.
                        image_url=item.get("image") or item.get("coverImage"),
                        latitude=item.get("lat"),
                        longitude=item.get("lon"),
                        raw=item,
                    )
                )
            except Exception:  # noqa: BLE001 - skip malformed individual listing
                continue
        return out

    def _mock_listings(self, cities: list[str], max_price: float) -> list[RawListing]:
        out = []
        asset_types = ["rooms_4", "garden_apartment", "new_project"]
        for city in cities:
            # Reseeded per city so listings/external_ids are stable regardless
            # of the cities list's iteration order - see MockAdapter for why.
            rng = random.Random(f"yad2:{city}")
            for i in range(rng.randint(1, 3)):
                size = rng.randint(75, 130)
                price = rng.randint(int(max_price * 0.55), int(max_price))
                out.append(
                    RawListing(
                        source=self.name,
                        external_id=f"mock-{city}-{i}",
                        title=f"דירה למכירה ב{city}, {size} מ\"ר",
                        city=city,
                        asset_type=rng.choice(asset_types),
                        asking_price=float(price),
                        size_sqm=float(size),
                        rooms=rng.choice([3, 3.5, 4, 4.5, 5]),
                        street=f"רחוב הדוגמה {i + 1}",
                        source_url="https://www.yad2.co.il/realestate/forsale",
                        contact_info="050-0000000 (מוצג לדוגמה)",
                        # No placeholder image for mock/fallback listings either -
                        # only a genuine scraped image counts.
                        raw={"mock": True},
                    )
                )
        return out
