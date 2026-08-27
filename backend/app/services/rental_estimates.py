"""Estimated monthly rent, for Gross Rental Yield calculations.

There's no free, reliable public API for actual rental listings/transactions
in Israel (unlike sale transactions, the Tax Authority registry doesn't cover
rentals). This estimates rent from a curated table of approximate average
rent-per-sqm by city (general market knowledge of the Hadera<->Gedera coastal
corridor, NIS/month/sqm), scaled by the property's size — deterministic and
transparent, not a live feed. Swap in a real source (e.g. a licensed data
provider) by replacing `estimate_monthly_rent` while keeping its signature.
"""

# Approximate average residential rent, NIS per sqm per month. Rough figures
# based on general market knowledge as of 2025/26 - meant as a reasonable
# planning estimate, not a precise appraisal.
_RENT_PER_SQM: dict[str, float] = {
    "חדרה": 42, "אור עקיבא": 36, "בנימינה-גבעת עדה": 45, "זכרון יעקב": 50,
    "פרדס חנה-כרכור": 44, "חריש": 46, "כפר יונה": 48, "נתניה": 52,
    "אבן יהודה": 50, "כפר סבא": 62, "הוד השרון": 60, "רעננה": 65,
    "הרצליה": 72, "רמת השרון": 68, "תל אביב-יפו": 85, "פתח תקווה": 55,
    "ראש העין": 52, "בני ברק": 58, "גבעתיים": 75, "רמת גן": 70,
    "חולון": 55, "בת ים": 58, "אור יהודה": 50, "יהוד-מונוסון": 54,
    "ראשון לציון": 56, "נס ציונה": 54, "רחובות": 52, "באר יעקב": 48,
    "יבנה": 50, "גדרה": 46, "קרית עקרון": 42, "טירת כרמל": 44,
}
_DEFAULT_RENT_PER_SQM = 48.0


def estimate_monthly_rent(city: str, size_sqm: float | None, asset_type: str) -> float | None:
    if not size_sqm:
        return None
    rate = _RENT_PER_SQM.get(city, _DEFAULT_RENT_PER_SQM)
    rent = rate * size_sqm
    if asset_type == "garden_apartment":
        rent *= 1.08  # garden apartments typically command a modest premium
    return round(rent, -1)  # round to nearest 10 NIS


def gross_rental_yield_pct(asking_price: float | None, monthly_rent: float | None) -> float | None:
    if not asking_price or not monthly_rent:
        return None
    return round((monthly_rent * 12 / asking_price) * 100, 2)
