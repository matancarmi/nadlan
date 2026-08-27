"""Geography helpers for the search-area settings: a curated table of
localities along the Hadera<->Gedera corridor (and the coastal-plain cities
around it) with approximate coordinates, a haversine distance function, and
best-effort address geocoding via OpenStreetMap's free Nominatim API.

Radius search works against this curated table rather than per-property
geocoding: cheap, deterministic, and good enough for "which cities are near
this address" — precise property-level geocoding can be added later per
source if a source ever supplies real coordinates.
"""
import logging
import math

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings

logger = logging.getLogger(__name__)

# name -> (lat, lon), approximate city-center coordinates.
CITY_COORDS: dict[str, tuple[float, float]] = {
    "חדרה": (32.4340, 34.9196),
    "אור עקיבא": (32.5045, 34.9174),
    "בנימינה-גבעת עדה": (32.5195, 34.9502),
    "זכרון יעקב": (32.5714, 34.9522),
    "פרדס חנה-כרכור": (32.4736, 34.9709),
    "קטיף-חריש": (32.4667, 35.0500),
    "חריש": (32.4667, 35.0500),
    "כפר יונה": (32.3167, 34.9333),
    "נתניה": (32.3215, 34.8532),
    "אבן יהודה": (32.2712, 34.8862),
    "כפר סבא": (32.1858, 34.9077),
    "הוד השרון": (32.1500, 34.8886),
    "רעננה": (32.1848, 34.8706),
    "הרצליה": (32.1624, 34.8447),
    "רמת השרון": (32.1467, 34.8397),
    "תל אביב-יפו": (32.0853, 34.7818),
    "פתח תקווה": (32.0917, 34.8872),
    "ראש העין": (32.0956, 34.9558),
    "בני ברק": (32.0807, 34.8338),
    "גבעתיים": (32.0700, 34.8125),
    "רמת גן": (32.0684, 34.8248),
    "חולון": (32.0114, 34.7736),
    "בת ים": (32.0234, 34.7503),
    "אור יהודה": (32.0333, 34.8500),
    "יהוד-מונוסון": (32.0333, 34.8833),
    "ראשון לציון": (31.9730, 34.7925),
    "נס ציונה": (31.9295, 34.7969),
    "רחובות": (31.8947, 34.8093),
    "באר יעקב": (31.9436, 34.8339),
    "יבנה": (31.8791, 34.7392),
    "גדרה": (31.8177, 34.7775),
    "קרית עקרון": (31.8667, 34.8167),
    "טירת כרמל": (32.7627, 34.9718),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cities_within_radius(lat: float, lon: float, radius_km: float) -> list[str]:
    return [city for city, (clat, clon) in CITY_COORDS.items() if haversine_km(lat, lon, clat, clon) <= radius_km]


def geocode_address(address: str) -> tuple[float, float] | None:
    """Best-effort geocoding via OpenStreetMap Nominatim (free, no API key).

    Returns None on any failure (network policy, no results, rate limiting) —
    callers should fall back gracefully (e.g. keep the previously resolved
    center, or fall back to the default city list).
    """
    settings = get_settings()
    try:
        with httpx.Client(timeout=settings.ingestion_request_timeout_seconds) as client:
            resp = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1, "countrycodes": "il"},
                # Nominatim's usage policy requires a descriptive User-Agent.
                headers={"User-Agent": "RealEstateTinder/1.0 (private single-user app)"},
            )
            resp.raise_for_status()
            results = resp.json()
            if not results:
                return None
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Geocoding failed for %r: %s", address, exc)
        return None


def get_or_create_settings(db: Session):
    from ..models import SearchSettings  # local import to avoid a circular import

    settings_row = db.get(SearchSettings, 1)
    if settings_row is None:
        default_settings = get_settings()
        settings_row = SearchSettings(id=1, mode="cities", cities=list(default_settings.target_cities))
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


def resolve_target_cities(db: Session) -> list[str]:
    """Return the city list the ingestion pipeline should search this run,
    based on the user's configured search-area settings (falls back to the
    app-wide default city list if nothing is configured yet)."""
    default_settings = get_settings()
    row = get_or_create_settings(db)

    if row.mode == "radius" and row.address:
        center = (row.center_lat, row.center_lon) if row.center_lat and row.center_lon else None
        if center is None:
            center = geocode_address(row.address)
            if center:
                row.center_lat, row.center_lon = center
        if center and row.radius_km:
            cities = cities_within_radius(center[0], center[1], row.radius_km)
            row.resolved_cities = cities
            db.commit()
            if cities:
                return cities
        logger.warning("Radius search could not be resolved for %r; falling back to default cities", row.address)
        return list(default_settings.target_cities)

    if row.mode == "cities" and row.cities:
        return row.cities

    return list(default_settings.target_cities)
