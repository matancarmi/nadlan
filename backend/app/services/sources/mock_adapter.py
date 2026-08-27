"""Realistic mock adapter for sources without an official/scrapable API.

Madlan, WinWin and Facebook Marketplace/groups all block or have no public
API for automated access. Each is represented by an instance of this class so
the ingestion pipeline treats them identically to Yad2 — same RawListing
shape, same downstream AI/CMA/alerts. Swap in a real implementation later by
writing a SourceAdapter subclass with the same `fetch_listings` signature.
"""
import random

from .base import RawListing, SourceAdapter

_ASSET_TYPES = ["rooms_4", "garden_apartment", "new_project", "pinui_binui"]
_PLANNING_STATUSES = [
    ("tabah_valid", "תב\"ע בתוקף"),
    ("deposited", "תוכנית בהפקדה"),
    ("local_committee", "בדיון בוועדה המקומית"),
    ("district_committee", "בדיון בוועדה המחוזית"),
    ("permit_issued", "היתר בנייה הופק"),
]


class MockAdapter(SourceAdapter):
    def __init__(self, name: str, seed: int, presale_heavy: bool = False):
        self.name = name
        self._seed = seed
        self._presale_heavy = presale_heavy

    def fetch_listings(self, cities: list[str], max_price: float) -> list[RawListing]:
        rng = random.Random(self._seed)
        out = []
        for city in cities:
            for i in range(rng.randint(0, 2)):
                asset_type = (
                    rng.choice(["new_project", "pinui_binui"])
                    if self._presale_heavy
                    else rng.choice(_ASSET_TYPES)
                )
                size = rng.randint(70, 135)
                price = rng.randint(int(max_price * 0.5), int(max_price))
                planning_key, planning_label = rng.choice(_PLANNING_STATUSES)
                out.append(
                    RawListing(
                        source=self.name,
                        external_id=f"{self.name}-{city}-{i}",
                        title=f"{'פרויקט' if asset_type in ('new_project', 'pinui_binui') else 'דירה'} ב{city}",
                        city=city,
                        asset_type=asset_type,
                        asking_price=float(price),
                        size_sqm=float(size),
                        rooms=rng.choice([3, 3.5, 4, 4.5, 5]),
                        street=f"רחוב לדוגמה {i + 1}",
                        source_url=f"https://example-{self.name}.co.il/listing/{city}-{i}",
                        contact_info="050-0000000 (מוצג לדוגמה)",
                        planning_status=planning_label if asset_type in ("new_project", "pinui_binui") else None,
                        planning_status_key=planning_key if asset_type in ("new_project", "pinui_binui") else None,
                        raw={"mock": True},
                    )
                )
        return out
