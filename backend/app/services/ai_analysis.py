"""AI evaluation: CMA-based discount calculation + Claude-generated summary."""
import json
import logging

from ..config import get_settings
from ..models import Property
from .gov_data.tax_authority import get_comparable_price_per_sqm
from .rental_estimates import estimate_monthly_rent, gross_rental_yield_pct

logger = logging.getLogger(__name__)


def enrich_with_cma(prop: Property) -> None:
    """Compute price/sqm, comparable market price/sqm, and discount %."""
    if prop.asking_price and prop.size_sqm:
        prop.price_per_sqm = round(prop.asking_price / prop.size_sqm, 0)

    comp = get_comparable_price_per_sqm(prop.city, prop.street)
    prop.cma_avg_price_per_sqm = comp.avg_price_per_sqm
    prop.cma_sample_size = comp.sample_size

    if prop.price_per_sqm and comp.avg_price_per_sqm:
        discount = (comp.avg_price_per_sqm - prop.price_per_sqm) / comp.avg_price_per_sqm * 100
        prop.cma_discount_pct = round(discount, 1)

    settings = get_settings()
    is_discount_deal = bool(
        prop.cma_discount_pct and prop.cma_discount_pct >= settings.high_value_discount_threshold_pct
    )
    is_hot_presale = prop.asset_type.value in ("new_project", "pinui_binui") and bool(
        prop.planning_status_key in ("tabah_valid", "permit_issued")
    )
    prop.is_high_value_deal = is_discount_deal or is_hot_presale


def enrich_with_rental_yield(prop: Property) -> None:
    """Estimate monthly rent and gross rental yield for the property."""
    prop.estimated_monthly_rent = estimate_monthly_rent(prop.city, prop.size_sqm, prop.asset_type.value)
    prop.gross_rental_yield_pct = gross_rental_yield_pct(prop.asking_price, prop.estimated_monthly_rent)


def generate_ai_summary(prop: Property) -> None:
    """Populate ai_summary / ai_pros / ai_cons / ai_verdict.

    Uses Claude when ANTHROPIC_API_KEY is configured; otherwise falls back to
    a deterministic rule-based summary so the app works out of the box.
    """
    settings = get_settings()
    if settings.anthropic_api_key:
        try:
            _generate_with_claude(prop, settings)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Claude analysis failed for property %s: %s", prop.external_id, exc)

    _generate_rule_based(prop)


def _generate_with_claude(prop: Property, settings) -> None:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""You are a real-estate investment analyst for the Israeli market (Hadera-Gedera corridor).
Analyze this listing and respond ONLY with compact JSON: {{"summary": str, "pros": [str], "cons": [str], "verdict": str}}.
verdict must be one of: "High-Value Deal", "Worth Reviewing", "Fairly Priced", "Overpriced".

Listing:
- Title: {prop.title}
- City: {prop.city}, street: {prop.street or "N/A"}
- Asset type: {prop.asset_type.value}
- Asking price: {prop.asking_price} NIS
- Size: {prop.size_sqm} sqm, price/sqm: {prop.price_per_sqm}
- Comparable market avg price/sqm (Tax Authority data): {prop.cma_avg_price_per_sqm} (n={prop.cma_sample_size})
- Discount vs market: {prop.cma_discount_pct}%
- Planning/project status: {prop.planning_status or "N/A"}
- Estimated monthly rent: {prop.estimated_monthly_rent} NIS, gross rental yield: {prop.gross_rental_yield_pct}%

Write summary/pros/cons in Hebrew, 1-3 short bullet points each."""

    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    data = json.loads(_extract_json(text))
    prop.ai_summary = data.get("summary")
    prop.ai_pros = "\n".join(data.get("pros", []))
    prop.ai_cons = "\n".join(data.get("cons", []))
    prop.ai_verdict = data.get("verdict")


def _extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    return text[start : end + 1]


def _generate_rule_based(prop: Property) -> None:
    pros, cons = [], []
    if prop.cma_discount_pct and prop.cma_discount_pct > 0:
        pros.append(f"מחיר נמוך בכ-{prop.cma_discount_pct}% מהממוצע באזור")
    elif prop.cma_discount_pct:
        cons.append(f"מחיר גבוה בכ-{abs(prop.cma_discount_pct)}% מהממוצע באזור")
    if prop.gross_rental_yield_pct and prop.gross_rental_yield_pct >= 4.0:
        pros.append(f"תשואת שכירות גולמית טובה: כ-{prop.gross_rental_yield_pct}%")
    elif prop.gross_rental_yield_pct:
        cons.append(f"תשואת שכירות גולמית נמוכה יחסית: כ-{prop.gross_rental_yield_pct}%")
    if prop.asset_type.value in ("new_project", "pinui_binui"):
        pros.append("פרויקט חדש/התחדשות עירונית - פוטנציאל השבחה")
        if prop.planning_status:
            pros.append(f"סטטוס תכנוני: {prop.planning_status}")
        else:
            cons.append("סטטוס תכנוני לא ידוע - יש לבדוק מול הוועדה המקומית")
    if not pros:
        pros.append("נתונים בסיסיים תואמים את קריטריוני החיפוש")
    if not cons:
        cons.append("יש לבצע בדיקה פרטנית נוספת מול המקור")

    prop.ai_pros = "\n".join(pros)
    prop.ai_cons = "\n".join(cons)
    prop.ai_verdict = "High-Value Deal" if prop.is_high_value_deal else "Worth Reviewing"
    prop.ai_summary = (
        f"{prop.title} ב{prop.city}: מחיר {int(prop.asking_price) if prop.asking_price else 'לא ידוע'} ₪ "
        f"({int(prop.price_per_sqm) if prop.price_per_sqm else '?'} ₪/מ\"ר). "
        f"{'זוהתה עסקה בעלת פוטנציאל גבוה.' if prop.is_high_value_deal else 'נכס סביר לבדיקה נוספת.'}"
    )
