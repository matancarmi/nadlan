"""Mortgage payment and cash-flow calculations, and the finance-settings
singleton (default equity, loan term, and mortgage mix / "תמהיל").

The mortgage math (standard fixed-payment amortization per tranche) is
mirrored in the frontend (lib/finance.ts) so a property card's mortgage
widget can recompute instantly as the user tweaks equity/term, without a
round trip - both implementations must stay in sync.
"""
from sqlalchemy.orm import Session

from ..models import FinanceSettings, Property

# A standard Israeli mortgage mix ("תמהיל ממוצע"): roughly a third prime-rate
# (variable, tracks Bank of Israel base rate), a third fixed unlinked, a
# third fixed CPI-linked ("קל\"צ"). Rates are illustrative averages, not a
# live feed - clearly a planning estimate, editable in Finance Settings.
DEFAULT_MIX = [
    {"name": "פריים", "share_pct": 33.34, "annual_rate_pct": 6.0},
    {"name": "קבועה לא צמודה", "share_pct": 33.33, "annual_rate_pct": 5.3},
    {"name": 'קל"צ (קבועה צמודה)', "share_pct": 33.33, "annual_rate_pct": 4.2},
]


def get_or_create_finance_settings(db: Session) -> FinanceSettings:
    row = db.get(FinanceSettings, 1)
    if row is None:
        row = FinanceSettings(id=1, equity_nis=500_000, loan_term_years=25, mix=DEFAULT_MIX)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def monthly_payment_for_tranche(principal: float, annual_rate_pct: float, term_years: int) -> float:
    """Standard fixed-payment ("שפיצר") amortization formula."""
    if principal <= 0:
        return 0.0
    monthly_rate = (annual_rate_pct / 100) / 12
    n = term_years * 12
    if monthly_rate == 0:
        return principal / n
    return principal * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)


def calculate_mortgage(asking_price: float, equity_nis: float, loan_term_years: int, mix: list[dict]) -> dict:
    loan_amount = max(asking_price - equity_nis, 0.0)
    total_monthly_payment = 0.0
    for tranche in mix:
        tranche_principal = loan_amount * (tranche["share_pct"] / 100)
        total_monthly_payment += monthly_payment_for_tranche(
            tranche_principal, tranche["annual_rate_pct"], loan_term_years
        )
    return {
        "loan_amount": round(loan_amount, 0),
        "equity_used": round(min(equity_nis, asking_price), 0),
        "monthly_payment": round(total_monthly_payment, 0),
    }


def attach_finance_metrics(prop: Property, finance_settings: FinanceSettings, premium_cities: set[str]) -> dict:
    """Compute the dynamic, settings-dependent fields for one property: these
    are never stored on the row (financing assumptions can change at any
    time and should apply retroactively to every property on the very next
    fetch), unlike the rental-yield fields which are market-level estimates
    computed once at ingestion."""
    metrics = {"estimated_monthly_mortgage_payment": None, "monthly_cash_flow": None, "loan_amount_used": None}
    if prop.asking_price:
        calc = calculate_mortgage(prop.asking_price, finance_settings.equity_nis, finance_settings.loan_term_years, finance_settings.mix)
        metrics["estimated_monthly_mortgage_payment"] = calc["monthly_payment"]
        metrics["loan_amount_used"] = calc["loan_amount"]
        if prop.estimated_monthly_rent is not None:
            metrics["monthly_cash_flow"] = round(prop.estimated_monthly_rent - calc["monthly_payment"], 0)
    metrics["is_premium_area"] = prop.city in premium_cities
    return metrics
