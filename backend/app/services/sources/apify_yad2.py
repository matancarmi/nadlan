"""Yad2 listings via Apify (https://apify.com) - a paid third-party scraping
platform that runs its own scraping infrastructure and handles Yad2's
bot-protection question on its own terms, unlike the direct-request attempt
in yad2.py. Used automatically instead of the direct attempt whenever
APIFY_API_TOKEN is configured (see config.py); falls back to the exact same
mock data as the direct adapter if the run fails, times out, or an actor
isn't configured, so the pipeline never breaks.

Important - there is no single "official" Yad2 actor on Apify, and this
integration's `actor.call()` / `dataset.iterate_items()` usage was verified
against the real apify-client 3.1.3 API (installed and introspected
directly - its method signatures changed across major versions, so this
matters), but the actual actor run could NOT be tested end-to-end: this
project's dev sandbox blocks outbound calls to api.apify.com the same way it
blocks yad2.co.il. You must pick a working actor yourself (see README) and
should verify the mapping in `_parse_item` against a sample of its real
output - the multi-key-name lookups in `_first()` are a best-effort guess at
common field names, not a verified schema.
"""
import json
import logging
from datetime import timedelta

from ...config import get_settings
from .base import RawListing, SourceAdapter
from .yad2 import _CITY_IDS, Yad2Adapter

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
        """Default input: a Yad2 search-results URL per target city, most
        generic Yad2 actors accept a list of start URLs to crawl. Override
        entirely via APIFY_ACTOR_INPUT_JSON if your actor expects something
        else (e.g. a structured `search` object instead of URLs)."""
        if settings.apify_actor_input_json:
            try:
                return json.loads(settings.apify_actor_input_json)
            except json.JSONDecodeError:
                logger.warning("APIFY_ACTOR_INPUT_JSON is not valid JSON - using the default input instead")

        start_urls = []
        for city in cities:
            city_id = _CITY_IDS.get(city)
            city_param = f"city={city_id}" if city_id else f"city={city}"
            start_urls.append({"url": f"https://www.yad2.co.il/realestate/forsale?{city_param}&maxPrice={int(max_price)}"})
        return {"startUrls": start_urls, "maxItems": settings.apify_max_items}

    def _parse_item(self, item: dict, cities: list[str]) -> RawListing | None:
        try:
            price = _first(item, ["price", "Price", "askingPrice", "priceNis"])
            if price is None:
                return None
            price = float(str(price).replace(",", "").replace("₪", "").strip())

            title = _first(item, ["title", "Title", "adTitle"]) or "נכס למכירה"
            city = _first(item, ["city", "City", "address_city", "cityName"])
            if not city:
                # Best effort: the actor's own city field is missing/named
                # differently - match against whichever target city name
                # appears in the title/address text instead of guessing wrong.
                text = f"{title} {_first(item, ['address', 'Address']) or ''}"
                city = next((c for c in cities if c in text), None)
            if not city:
                return None  # can't file this under any city - skip rather than guess

            rooms = _first(item, ["rooms", "Rooms", "roomsCount", "numOfRooms"])
            size = _first(item, ["squareMeters", "square", "size", "area", "sqm"])
            images = _first(item, ["images", "Images", "photos", "imageUrls"])
            image_url = images[0] if isinstance(images, list) and images else _first(item, ["image", "coverImage"])
            url = _first(item, ["url", "Url", "link", "adUrl"])
            contact = _first(item, ["contactName", "phone", "contact", "phoneNumber"])
            description = _first(item, ["description", "Description"]) or ""

            text_blob = f"{title} {description}"
            rooms_f = float(rooms) if rooms else None
            asset_type = "rooms_4" if rooms_f and 3.5 <= rooms_f <= 4.5 else "other"
            for keyword, mapped_type in _ASSET_TYPE_KEYWORDS:
                if keyword in text_blob:
                    asset_type = mapped_type
                    break

            return RawListing(
                source=self.name,
                external_id=str(_first(item, ["id", "Id", "adNumber", "itemId"]) or url or f"{city}-{title}-{price}"),
                title=title,
                city=city,
                asset_type=asset_type,
                asking_price=price,
                size_sqm=float(size) if size else None,
                rooms=rooms_f,
                street=_first(item, ["street", "Street", "address_street"]),
                source_url=url or "https://www.yad2.co.il/realestate/forsale",
                contact_info=str(contact) if contact else None,
                image_url=image_url,  # only set if the actor genuinely returned one - no placeholder
                raw=item,
            )
        except Exception as exc:  # noqa: BLE001 - skip malformed individual item
            logger.debug("Skipping unparsable Apify item: %s", exc)
            return None
