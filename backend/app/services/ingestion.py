"""Daily ingestion orchestration: fetch from all sources, normalize, dedupe,
run AI/CMA analysis, persist, and email-alert on new high-value deals.
"""
import logging

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AssetType, DecisionStatus, Property
from .ai_analysis import enrich_with_cma, generate_ai_summary
from .email_alerts import send_high_value_deal_alert
from .geo import resolve_target_cities
from .sources.base import RawListing, SourceAdapter
from .sources.mock_adapter import MockAdapter
from .sources.yad2 import Yad2Adapter

logger = logging.getLogger(__name__)


def get_all_adapters() -> list[SourceAdapter]:
    return [
        Yad2Adapter(),
        MockAdapter(name="madlan", seed=1),
        MockAdapter(name="winwin", seed=2),
        MockAdapter(name="facebook_groups", seed=3),
        MockAdapter(name="gov_pinui_binui", seed=4, presale_heavy=True),
    ]


def run_daily_ingestion(db: Session) -> dict:
    settings = get_settings()
    adapters = get_all_adapters()
    target_cities = resolve_target_cities(db)

    fetched, created, updated, errors = 0, 0, 0, []
    new_high_value_deals: list[Property] = []

    for adapter in adapters:
        try:
            listings = adapter.fetch_listings(target_cities, settings.max_budget_nis)
        except Exception as exc:  # noqa: BLE001 - one bad source should never kill the run
            logger.error("Adapter %s failed entirely: %s", adapter.name, exc)
            errors.append(f"{adapter.name}: {exc}")
            continue

        for raw in listings:
            fetched += 1
            try:
                is_new, prop = _upsert_property(db, raw)
                enrich_with_cma(prop)
                generate_ai_summary(prop)
                db.flush()
                if is_new:
                    created += 1
                else:
                    updated += 1
                if prop.is_high_value_deal and not prop.alert_sent:
                    new_high_value_deals.append(prop)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to process listing %s/%s: %s", raw.source, raw.external_id, exc)
                errors.append(f"{raw.source}/{raw.external_id}: {exc}")

    db.commit()

    alerts_sent = 0
    if new_high_value_deals:
        if send_high_value_deal_alert(new_high_value_deals):
            for p in new_high_value_deals:
                p.alert_sent = True
            db.commit()
            alerts_sent = len(new_high_value_deals)

    return {
        "fetched": fetched,
        "created": created,
        "updated": updated,
        "high_value_deals": len(new_high_value_deals),
        "alerts_sent": alerts_sent,
        "errors": errors,
    }


def _upsert_property(db: Session, raw: RawListing) -> tuple[bool, Property]:
    existing = (
        db.query(Property)
        .filter(Property.source == raw.source, Property.external_id == raw.external_id)
        .one_or_none()
    )
    is_new = existing is None
    prop = existing or Property(source=raw.source, external_id=raw.external_id, decision=DecisionStatus.PENDING)

    prop.title = raw.title
    prop.city = raw.city
    prop.neighborhood = raw.neighborhood
    prop.street = raw.street
    try:
        prop.asset_type = AssetType(raw.asset_type)
    except ValueError:
        prop.asset_type = AssetType.OTHER
    prop.rooms = raw.rooms
    prop.size_sqm = raw.size_sqm
    prop.asking_price = raw.asking_price
    prop.source_url = raw.source_url
    prop.contact_info = raw.contact_info
    prop.image_url = raw.image_url
    prop.planning_status = raw.planning_status
    prop.planning_status_key = raw.planning_status_key
    prop.latitude = raw.latitude
    prop.longitude = raw.longitude
    prop.raw_data = raw.raw

    if is_new:
        db.add(prop)
    return is_new, prop
