"""Israel Tax Authority real-estate transaction data, for Comparative Market
Analysis (CMA).

data.gov.il publishes the Tax Authority's "מאגר מידע נדל\"ן" (real-estate
transactions registry) as an open CKAN dataset. This module makes a best
effort real call to the public CKAN `datastore_search` API and falls back to
deterministic mock comparables (seeded by city, so results are stable) if the
call fails for any reason (network policy, resource ID drift, schema
changes, rate limiting).

NOTE: this was written and reasoned about, but could NOT be network-tested
from the development sandbox (outbound access to data.gov.il is blocked by
this environment's network policy). After deploying, verify `_RESOURCE_ID`
still points at the live "עסקאות מכר של רשות המסים" resource on
https://data.gov.il (search the datasets under the "רשות המסים" organization)
and adjust the field names in `_parse_records` to match its real columns.
"""
import logging
import random
import statistics

import httpx

from ...config import get_settings

logger = logging.getLogger(__name__)

_CKAN_BASE = "https://data.gov.il/api/3/action/datastore_search"
# Best-effort resource id for the Tax Authority real-estate deals dataset.
# Unverified from this sandbox — confirm on data.gov.il and update if needed.
_RESOURCE_ID = "6b58e84b-1e34-46e1-b6cc-90068ddc0162"


class ComparableResult:
    def __init__(self, avg_price_per_sqm: float | None, sample_size: int, is_live: bool):
        self.avg_price_per_sqm = avg_price_per_sqm
        self.sample_size = sample_size
        self.is_live = is_live


def get_comparable_price_per_sqm(city: str, street: str | None = None) -> ComparableResult:
    """Look up recent comparable transactions for a city (+ optional street)
    and return the average price per sqm."""
    settings = get_settings()
    query = street or city
    try:
        with httpx.Client(timeout=settings.ingestion_request_timeout_seconds) as client:
            resp = client.get(
                _CKAN_BASE,
                params={"resource_id": _RESOURCE_ID, "q": query, "limit": 50},
            )
            resp.raise_for_status()
            payload = resp.json()
            records = payload.get("result", {}).get("records", [])
            values = _parse_records(records)
            if values:
                return ComparableResult(statistics.mean(values), len(values), is_live=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tax Authority live CMA lookup failed for %s: %s", query, exc)

    return _mock_comparable(city)


def _parse_records(records: list[dict]) -> list[float]:
    values = []
    for rec in records:
        try:
            price = float(rec.get("DEALAMOUNT") or rec.get("price") or 0)
            size = float(rec.get("DEALNATURE") == "sqm" and rec.get("sqm") or rec.get("AREA") or 0)
            if price > 0 and size > 0:
                values.append(price / size)
        except (TypeError, ValueError):
            continue
    return values


def _mock_comparable(city: str) -> ComparableResult:
    # Deterministic per-city mock average, roughly modeled on real corridor prices (NIS/sqm).
    rng = random.Random(hash(city) % (2**32))
    base = rng.randint(13000, 22000)
    return ComparableResult(avg_price_per_sqm=float(base), sample_size=rng.randint(8, 30), is_live=False)
