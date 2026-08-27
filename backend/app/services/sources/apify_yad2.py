"""Yad2 for-sale listings via Apify (https://apify.com) - a paid third-party
scraping platform that runs its own scraping infrastructure and handles
Yad2's bot-protection question on its own terms, unlike the direct-request
attempt in yad2.py. Used automatically instead of the direct attempt whenever
APIFY_API_TOKEN is configured (see config.py); falls back to the exact same
mock data as the direct adapter if the run fails, times out, or an actor
isn't configured, so the pipeline never breaks.

Targets `swerve/yad2-scraper` by default - verified against a real live run
(see below), not a guess. Its `dealType` input is required and explicit
(`rent` / `buy` / `commercial`), which matters: an earlier actor tried here
(`amit123/YadScraper`) turned out to *only* scrape rental listings no matter
what URL/category was passed in (giveaway fields like `payments_in_year`,
`furnished`, `entrance_date`, and rent-magnitude prices like ₪4,900), which
is a fundamental mismatch for an app whose purpose is finding properties to
buy. swerve/yad2-scraper's `dealType: "buy"` avoids that ambiguity outright,
and its `city` input accepts the same Hebrew city names already used
throughout this app (config.target_cities, resolve_target_cities) - so no
city-id lookup table is needed either, unlike the old `_CITY_IDS` guesses.

Verified real output schema (via a live run against Gedera/Bat Yam/Hadera,
inspected directly through Railway rather than assumed): `url` (a genuine
per-listing https://www.yad2.co.il/item/<id> link), `streetName`,
`neighbourhood`, `address`, `city`/`cityHebrew`, `price` (a plain number,
already in ILS for dealType=buy), `rooms`, `areaSqm`, `floor`, `images`
(list), `coverImage`, `listingDescription`, `contactName`/`contactPhone`,
`propertyType`, `listingId`. `_parse_item` maps these directly; the
multi-key `_first()` fallback lookups are kept only as a defensive net in
case the actor's schema drifts or `APIFY_ACTOR_INPUT_JSON`/a different actor
is swapped in later.
"""
import json
import logging
from datetime import timedelta

from ...config import get_settings
from .base import RawListing, SourceAdapter
from .yad2 import Yad2Adapter

logger = logging.getLogger(__name__)

_ASSET_TYPE_KEYWORDS = [
    ("פינוי בינוי", "pinui_binui"),
    ("פינוי-בינוי", "pinui_binui"),
    ("פרויקט חדש", "new_project"),
    ("מקבלן", "new_project"),
    ("על הנייר", "new_project"),
    ("דירת גן", "garden_apartment"),
]


def _first(item: dict, keys: list[str]):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


class ApifyYad2Adapter(SourceAdapter):
    name = "yad2"

    def fetch_listings(self, cities: list[str], max_price: float) -> list[RawListing]:
        settings = get_settings()

        if not settings.apify_actor_id:
            logger.warning("APIFY_API_TOKEN is set but APIFY_ACTOR_ID isn't - falling back to direct/mock Yad2 adapter")
            return Yad2Adapter().fetch_listings(cities, max_price)

        try:
            from apify_client import ApifyClient
        except ImportError:
            logger.error("apify-client package not installed - falling back to direct/mock Yad2 adapter")
            return Yad2Adapter().fetch_listings(cities, max_price)

        try:
            client = ApifyClient(settings.apify_api_token)
            run_input = self._build_run_input(cities, max_price, settings)
            run_timeout = timedelta(seconds=settings.apify_run_timeout_seconds)
            run = client.actor(settings.apify_actor_id).call(
                run_input=run_input,
                run_timeout=run_timeout,
                timeout=run_timeout + timedelta(seconds=30),  # client-side wait budget, slightly above the run's own
                max_items=settings.apify_max_items,
            )
            # apify-client 3.x's actor().call() returns a typed `Run` Pydantic
            # model, not a dict - attribute access (snake_case), not .get()/[].
            dataset_id = run.default_dataset_id if run else None
            items = list(client.dataset(dataset_id).iterate_items()) if dataset_id else []
        except Exception as exc:  # noqa: BLE001 - any Apify failure -> fall back, never break the pipeline
            logger.error("Apify Yad2 run failed (%s) - falling back to mock data", exc)
            self.is_live = False
            return Yad2Adapter()._mock_listings(cities, max_price)

        listings = [parsed for item in items if (parsed := self._parse_item(item, cities)) is not None]
        self.is_live = bool(listings)
        if not listings:
            logger.info("Apify Yad2 run returned no usable listings - falling back to mock data")
            return Yad2Adapter()._mock_listings(cities, max_price)
        logger.info("Apify Yad2 run returned %d real listings", len(listings))
        return listings

    def _build_run_input(self, cities: list[str], max_price: float, settings) -> dict:
        """Default input matches swerve/yad2-scraper's schema: Hebrew/English
        city names (comma-separated) plus an explicit dealType=buy so it
        never silently returns rentals. Override entirely via
        APIFY_ACTOR_INPUT_JSON for a different actor's input shape."""
        if settings.apify_actor_input_json:
            try:
                return json.loads(settings.apify_actor_input_json)
            except json.JSONDecodeError:
                logger.warning("APIFY_ACTOR_INPUT_JSON is not valid JSON - using the default input instead")

        return {
            "city": ",".join(cities),
            "dealType": "buy",
            "maxPrice": int(max_price),
            "maxItems": settings.apify_max_items,
        }

    def _parse_item(self, item: dict, cities: list[str]) -> RawListing | None:
        try:
            # dealType=buy items may still include commercial/rental rows if
            # a differently-configured actor mixes categories (e.g. the
            # commercial section) - skip anything that isn't actually a sale.
            deal_type = _first(item, ["dealType", "deal_type"])
            if deal_type and deal_type not in ("buy", "sale", "forsale", "for_sale"):
                return None

            price = _first(item, ["price", "Price", "askingPrice", "priceNis"])
            if price is None:
                return None
            price = float(str(price).replace(",", "").replace("₪", "").strip())

            city = _first(item, ["cityHebrew", "city_hebrew", "city", "City"])
            street = _first(item, ["streetName", "street_name", "street", "Street", "address"])
            neighborhood = _first(item, ["neighbourhood", "neighborhood", "Neighbourhood"])
            if not city:
                text = f"{street or ''} {neighborhood or ''}"
                city = next((c for c in cities if c in text), None)
            if not city:
                return None  # can't file this under any city - skip rather than guess

            rooms = _first(item, ["rooms", "Rooms", "roomsCount", "numOfRooms"])
            size = _first(item, ["areaSqm", "area_sqm", "squareMeters", "square", "size", "area", "sqm"])
            images = _first(item, ["images", "Images", "photos", "imageUrls"])
            image_url = images[0] if isinstance(images, list) and images else _first(item, ["coverImage", "image"])
            url = _first(item, ["url", "Url", "link", "adUrl", "item_url"])
            contact_name = _first(item, ["contactName", "contact_name"])
            contact_phone = _first(item, ["contactPhone", "contact_phone", "phone", "phoneNumber"])
            contact = ", ".join(str(v) for v in (contact_name, contact_phone) if v) or None
            description = _first(item, ["listingDescription", "description", "Description"]) or ""
            property_type = _first(item, ["propertyType", "property_type"]) or ""

            rooms_f = float(rooms) if rooms else None
            title_bits = [b for b in (property_type, f"{rooms_f:g} חדרים" if rooms_f else None, street, city) if b]
            title = ", ".join(title_bits) or "נכס למכירה"

            text_blob = f"{title} {description} {property_type}"
            asset_type = "rooms_4" if rooms_f and 3.5 <= rooms_f <= 4.5 else "other"
            for keyword, mapped_type in _ASSET_TYPE_KEYWORDS:
                if keyword in text_blob:
                    asset_type = mapped_type
                    break

            return RawListing(
                source=self.name,
                external_id=str(_first(item, ["listingId", "listing_id", "id", "Id", "adNumber", "itemId"]) or url or f"{city}-{title}-{price}"),
                title=title,
                city=city,
                asset_type=asset_type,
                asking_price=price,
                size_sqm=float(size) if size else None,
                rooms=rooms_f,
                neighborhood=neighborhood,
                street=street,
                source_url=url,  # only a genuine per-listing link - never a generic search-page fallback
                contact_info=contact,
                image_url=image_url,  # only set if the actor genuinely returned one - no placeholder
                raw=item,
            )
        except Exception as exc:  # noqa: BLE001 - skip malformed individual item
            logger.debug("Skipping unparsable Apify item: %s", exc)
            return None
