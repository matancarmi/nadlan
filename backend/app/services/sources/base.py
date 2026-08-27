"""Common interface every listing-source adapter implements.

Design: each adapter exposes `fetch_listings()` returning a list of
`RawListing`. The ingestion pipeline doesn't care whether the data came from
a real scrape/API call or from realistic mock data — that lets the whole
system (DB, AI analysis, CMA, UI, alerts) work end-to-end today, and lets any
adapter be swapped for a fully real integration later without touching
anything else.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawListing:
    source: str
    external_id: str
    title: str
    city: str
    asset_type: str  # matches models.AssetType value
    asking_price: float | None = None
    size_sqm: float | None = None
    rooms: float | None = None
    neighborhood: str | None = None
    street: str | None = None
    source_url: str | None = None
    contact_info: str | None = None
    planning_status: str | None = None
    planning_status_key: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    raw: dict = field(default_factory=dict)


class SourceAdapter(ABC):
    name: str = "unknown"

    @abstractmethod
    def fetch_listings(self, cities: list[str], max_price: float) -> list[RawListing]:
        """Return listings for the given cities, at or below max_price.

        Implementations should be resilient: catch their own network/parsing
        errors internally and return an empty list (or partial results)
        rather than raising, so one broken source never blocks the daily run
        for the others. Use `is_live` to report whether this call actually
        reached the real source or fell back to mock data.
        """

    is_live: bool = False  # set True by an adapter once it confirms a real network call succeeded
