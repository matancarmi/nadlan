"""AI Investment Advisor: a chat interface loaded with the user's saved
property database and current market context (CMA, rental yield, mortgage/
cash-flow assumptions), so it can answer questions like "which of my saved
properties has the best cash flow?" or "is this Bat Yam deal priced well?".
"""
import logging

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import DecisionStatus, Property
from .finance import attach_finance_metrics, get_or_create_finance_settings
from .geo import get_or_create_settings as get_or_create_area_settings

logger = logging.getLogger(__name__)


def _build_context(db: Session) -> tuple[list[Property], list[dict]]:
    """Saved (liked) + bookmarked-for-later properties, enriched with finance
    metrics - the advisor's whole knowledge base is "your shortlist", not the
    full firehose of pending/passed listings."""
    properties = (
        db.query(Property)
        .filter(or_(Property.decision == DecisionStatus.LIKED, Property.saved_for_later.is_(True)))
        .order_by(Property.updated_at.desc())
        .all()
    )
    finance_settings = get_or_create_finance_settings(db)
    premium_cities = set(get_or_create_area_settings(db).premium_cities or [])

    rows = []
    for p in properties:
        metrics = attach_finance_metrics(p, finance_settings, premium_cities)
        rows.append(
            {
                "id": p.id,
                "title": p.title,
                "city": p.city,
                "street": p.street,
                "decision": p.decision.value,
                "saved_for_later": p.saved_for_later,
                "inventory_status": p.inventory_status.value,
                "asking_price": p.asking_price,
                "price_per_sqm": p.price_per_sqm,
                "cma_avg_price_per_sqm": p.cma_avg_price_per_sqm,
                "cma_discount_pct": p.cma_discount_pct,
                "is_high_value_deal": p.is_high_value_deal,
                "estimated_monthly_rent": p.estimated_monthly_rent,
                "gross_rental_yield_pct": p.gross_rental_yield_pct,
                "estimated_monthly_mortgage_payment": metrics["estimated_monthly_mortgage_payment"],
                "monthly_cash_flow": metrics["monthly_cash_flow"],
                "is_premium_area": metrics["is_premium_area"],
                "planning_status": p.planning_status,
                "notes": p.notes,
            }
        )
    return properties, rows


def generate_reply(db: Session, conversation: list[dict], user_message: str) -> str:
    """conversation: prior [{"role": "user"|"assistant", "content": str}, ...]"""
    _properties, rows = _build_context(db)
    settings = get_settings()

    if settings.anthropic_api_key:
        try:
            return _generate_with_claude(settings, rows, conversation, user_message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Claude chat advisor failed: %s", exc)

    return _generate_rule_based(rows, user_message)


def _generate_with_claude(settings, rows: list[dict], conversation: list[dict], user_message: str) -> str:
    import json

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    system_prompt = f"""You are an Israeli real-estate investment advisor embedded in a private
single-user app covering the Hadera-Gedera corridor. You have access to the user's saved/shortlisted
properties below, each with market comparables (CMA), estimated rental yield, and mortgage/cash-flow
figures computed from the user's own financing assumptions (equity, loan term, mortgage mix).

Answer the user's questions using ONLY this data - if something isn't covered by it, say so plainly
rather than inventing numbers. Be concise and concrete: name specific properties (by title/city) and
numbers when relevant. Respond in the same language the user writes in (Hebrew or English).

Saved properties (JSON):
{json.dumps(rows, ensure_ascii=False)}"""

    messages = [{"role": m["role"], "content": m["content"]} for m in conversation]
    messages.append({"role": "user", "content": user_message})

    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=800,
        system=system_prompt,
        messages=messages,
    )
    return message.content[0].text


def _generate_rule_based(rows: list[dict], user_message: str) -> str:
    """Deterministic fallback so the advisor still answers useful, directly
    computable questions when no ANTHROPIC_API_KEY is configured."""
    if not rows:
        return "אין עדיין נכסים שמורים או ל'המשך' - שמרו כמה נכסים ואחזור עם תובנות עליהם."

    lowered = user_message.lower()

    if any(k in lowered for k in ["cash flow", "תזרים", "cashflow"]):
        with_cf = [r for r in rows if r["monthly_cash_flow"] is not None]
        if not with_cf:
            return "אין מספיק נתונים (מחיר/שכירות מוערכת) כדי לחשב תזרים מזומנים כרגע."
        best = max(with_cf, key=lambda r: r["monthly_cash_flow"])
        return (
            f"התזרים החודשי הטוב ביותר בין הנכסים השמורים: {best['title']} ({best['city']}), "
            f"כ-{int(best['monthly_cash_flow'])} ₪/חודש "
            f"(שכירות מוערכת {int(best['estimated_monthly_rent'])} ₪ פחות החזר משכנתא מוערך "
            f"{int(best['estimated_monthly_mortgage_payment'])} ₪, לפי הגדרות המימון הנוכחיות)."
        )

    if any(k in lowered for k in ["yield", "תשואה"]):
        with_yield = [r for r in rows if r["gross_rental_yield_pct"] is not None]
        if not with_yield:
            return "אין מספיק נתונים כדי לחשב תשואת שכירות כרגע."
        best = max(with_yield, key=lambda r: r["gross_rental_yield_pct"])
        return f"תשואת השכירות הגולמית הגבוהה ביותר: {best['title']} ({best['city']}) - כ-{best['gross_rental_yield_pct']}%."

    if any(k in lowered for k in ["discount", "הנחה", "מתחת למחיר", "below market"]):
        with_discount = [r for r in rows if r["cma_discount_pct"] is not None]
        if not with_discount:
            return "אין מספיק נתוני עסקאות השוואה כדי לחשב הנחה מול השוק כרגע."
        best = max(with_discount, key=lambda r: r["cma_discount_pct"])
        return (
            f"הנכס עם ההנחה הגדולה ביותר מול השוק: {best['title']} ({best['city']}) - "
            f"כ-{best['cma_discount_pct']}% מתחת לממוצע האזורי."
        )

    # Generic fallback: summarize the shortlist so the answer is still useful.
    lines = []
    for r in rows[:8]:
        line = f"- {r['title']} ({r['city']}): מחיר {int(r['asking_price']) if r['asking_price'] else '?'} ₪"
        if r["gross_rental_yield_pct"]:
            line += f", תשואה {r['gross_rental_yield_pct']}%"
        if r["monthly_cash_flow"] is not None:
            line += f", תזרים {int(r['monthly_cash_flow'])} ₪/חודש"
        lines.append(line)
    return (
        "לא הוגדר מפתח Claude API (ANTHROPIC_API_KEY), אז אני יכול לענות רק על שאלות ישירות "
        "(תזרים, תשואה, הנחה מול השוק). הנה סיכום הנכסים השמורים:\n" + "\n".join(lines)
    )
