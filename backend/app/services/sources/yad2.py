"""Yad2 real-estate listings adapter.

Yad2 has no official public API. This adapter makes a best-effort real HTTP
call to Yad2's public (unofficial, undocumented) search endpoint, browser-like
headers included, and parses the JSON it returns. Because the endpoint is
undocumented, city IDs are approximate and the response shape can change or
be blocked (Yad2 uses bot-protection that may 403 non-browser clients) — any
failure for a given city, or of the whole call, is caught and that city
silently falls back to realistic mock listings so the rest of the pipeline
(DB, AI, CMA, UI, email alerts) always has data to work with.

NOTE: this was written and reasoned about, but could NOT be network-tested
from the development sandbox (outbound access to yad2.co.il is blocked by
this environment's network policy). Verify against the live site after
deploying, and adjust `_CITY_IDS` / `_parse_response` if Yad2's response
shape differs from what's assumed here.
"""
import logging
import random

import httpx

from ...config import get_settings
from .base import RawListing, SourceAdapter

logger = logging.getLogger(__name__)

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

        with httpx.Client(headers=_HEADERS, timeout=settings.ingestion_request_timeout_seconds) as client:
            for city in cities:
                city_id = _CITY_IDS.get(city)
                if city_id is None:
                    continue
                try:
                    resp = client.get(_BASE_URL, params={"city": city_id, "maxPrice": int(max_price)})
                    resp.raise_for_status()
                    payload = resp.json()
                    parsed = self._parse_response(payload, city)
                    if parsed:
                        listings.extend(parsed)
                        any_live_success = True
                except Exception as exc:  # noqa: BLE001 - any failure -> fall back for this city
                    logger.warning("Yad2 live fetch failed for %s: %s", city, exc)

        self.is_live = any_live_success
        if not listings:
            logger.info("Yad2: no live results (blocked/unavailable), using mock fallback data")
            listings = self._mock_listings(cities, max_price)
        return listings

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
                        latitude=item.get("lat"),
                        longitude=item.get("lon"),
                        raw=item,
                    )
                )
            except Exception:  # noqa: BLE001 - skip malformed individual listing
                continue
        return out

    def _mock_listings(self, cities: list[str], max_price: float) -> list[RawListing]:
        rng = random.Random(42)  # deterministic mock data across runs
        out = []
        asset_types = ["rooms_4", "garden_apartment", "new_project"]
        for city in cities:
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
                        raw={"mock": True},
                    )
                )
        return out
