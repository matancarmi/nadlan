"""Manual "add by URL" ingestion: the user pastes a single listing link they
already found (Yad2 or any other site) and we try to fetch + parse it into a
property. This is a fundamentally different situation from the bulk Yad2
scraper: it's one request the user explicitly asked for, not an automated
sweep, so a plain fetch (following redirects, real browser headers, no
retry-hammering) is reasonable here even where bulk scraping is not.

If the page can't be fetched or not enough was found to make a useful
listing (at minimum a title and a price), this reports back what little it
did find (`needs_manual_input`) so the UI can fall back to a short manual
entry form instead of the workflow getting stuck.
"""
import logging
import re

import httpx
from bs4 import BeautifulSoup

from ..config import get_settings
from .geo import CITY_COORDS

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}

_PRICE_RE = re.compile(r"₪\s?([\d,]{5,10})|([\d,]{5,10})\s?₪|([\d,]{6,10})\s*ש\"ח")
_ROOMS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*חדרים")
_SIZE_RE = re.compile(r"(\d{2,4})\s*מ[\"']?ר")


def _extract_number(match: re.Match) -> float | None:
    for group in match.groups():
        if group:
            return float(group.replace(",", ""))
    return None


def _guess_city(text: str) -> str | None:
    for city in CITY_COORDS:
        if city in text:
            return city
    return None


def _guess_asset_type(text: str, rooms: float | None) -> str:
    if "פינוי בינוי" in text or "פינוי-בינוי" in text:
        return "pinui_binui"
    if "פרויקט חדש" in text or "מקבלן" in text or "על הנייר" in text:
        return "new_project"
    if "דירת גן" in text or ("גן" in text and "דירה" in text):
        return "garden_apartment"
    if rooms and 3.5 <= rooms <= 4.5:
        return "rooms_4"
    return "other"


def _try_ai_extraction(text: str) -> dict | None:
    """Best-effort structured extraction via Claude for whatever regex
    couldn't find - only attempted when ANTHROPIC_API_KEY is configured."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import json

        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = f"""Extract real-estate listing details from this page text (Hebrew or English).
Respond ONLY with compact JSON: {{"title": str|null, "city": str|null, "street": str|null,
"asking_price": number|null, "rooms": number|null, "size_sqm": number|null, "asset_type":
one of "rooms_4"|"garden_apartment"|"new_project"|"pinui_binui"|"other"|null}}.
If a field isn't findable in the text, use null - never invent a number.

Page text:
{text[:4000]}"""
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(raw[start : end + 1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI extraction failed for manual URL ingestion: %s", exc)
        return None


def fetch_and_parse(url: str) -> dict:
    """Returns a dict always containing at least `prefill` (whatever was
    found, however partial) and `ok` (True if there's enough - title + price
    - to create a listing outright without the user filling anything in)."""
    settings = get_settings()
    prefill: dict = {"source_url": url}

    try:
        with httpx.Client(headers=_HEADERS, timeout=settings.ingestion_request_timeout_seconds, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:  # noqa: BLE001
        logger.warning("Manual URL fetch failed for %s: %s", url, exc)
        return {"ok": False, "prefill": prefill, "error": str(exc)}

    soup = BeautifulSoup(html, "html.parser")

    def meta(name_or_prop: str) -> str | None:
        tag = soup.find("meta", attrs={"property": name_or_prop}) or soup.find("meta", attrs={"name": name_or_prop})
        return tag.get("content") if tag else None

    title = meta("og:title") or (soup.title.string.strip() if soup.title and soup.title.string else None)
    description = meta("og:description") or ""
    image_url = meta("og:image")
    body_text = soup.get_text(separator=" ", strip=True)
    combined_text = f"{title or ''} {description} {body_text}"

    price_match = _PRICE_RE.search(combined_text)
    rooms_match = _ROOMS_RE.search(combined_text)
    size_match = _SIZE_RE.search(combined_text)

    asking_price = _extract_number(price_match) if price_match else None
    rooms = _extract_number(rooms_match) if rooms_match else None
    size_sqm = _extract_number(size_match) if size_match else None
    city = _guess_city(combined_text)
    street = None
    asset_type_hint = None

    # If regex parsing came up short on the essentials, let AI have a shot at
    # the same raw text before giving up and asking the user to fill it in.
    if (asking_price is None or city is None) and settings.anthropic_api_key:
        ai_data = _try_ai_extraction(combined_text)
        if ai_data:
            title = title or ai_data.get("title")
            city = city or ai_data.get("city")
            asking_price = asking_price or ai_data.get("asking_price")
            rooms = rooms or ai_data.get("rooms")
            size_sqm = size_sqm or ai_data.get("size_sqm")
            street = ai_data.get("street")
            asset_type_hint = ai_data.get("asset_type")

    prefill.update(
        {
            "title": title,
            "image_url": image_url,
            "asking_price": asking_price,
            "rooms": rooms,
            "size_sqm": size_sqm,
            "city": city,
            "street": street,
            "asset_type": asset_type_hint or _guess_asset_type(combined_text, rooms),
        }
    )

    ok = bool(title and asking_price and city)
    return {"ok": ok, "prefill": prefill}
