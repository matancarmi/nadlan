from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DecisionStatus, InventoryStatus, Property
from ..schemas import DecisionUpdate, InventoryUpdate, PropertyOut, SaveForLaterUpdate
from ..security import require_session
from ..services.finance import attach_finance_metrics, get_or_create_finance_settings
from ..services.geo import get_or_create_settings as get_or_create_area_settings

router = APIRouter(prefix="/api/properties", tags=["properties"], dependencies=[Depends(require_session)])


def _enrich(properties: list[Property], db: Session) -> list[Property]:
    """Attach the dynamic, settings-dependent fields (mortgage payment, cash
    flow, premium-area flag) as plain instance attributes - not mapped
    columns, so this never touches the DB, just the response. Computed here
    (rather than stored) so changing Finance/Area settings applies
    immediately to every property on the very next fetch."""
    finance_settings = get_or_create_finance_settings(db)
    premium_cities = set(get_or_create_area_settings(db).premium_cities or [])
    for prop in properties:
        for key, value in attach_finance_metrics(prop, finance_settings, premium_cities).items():
            setattr(prop, key, value)
    return properties


@router.get("/feed", response_model=list[PropertyOut])
def get_feed(limit: int = 20, db: Session = Depends(get_db)):
    """Discovery feed: properties not yet swiped on, newest first."""
    properties = (
        db.query(Property)
        .filter(Property.decision == DecisionStatus.PENDING)
        .order_by(Property.is_high_value_deal.desc(), Property.created_at.desc())
        .limit(limit)
        .all()
    )
    return _enrich(properties, db)


@router.post("/{property_id}/decision", response_model=PropertyOut)
def set_decision(property_id: int, payload: DecisionUpdate, db: Session = Depends(get_db)):
    """Final swipe decision: like (save) or pass (discard/hide forever)."""
    prop = db.get(Property, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    prop.decision = payload.decision
    prop.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(prop)
    return _enrich([prop], db)[0]


@router.post("/{property_id}/save-for-later", response_model=PropertyOut)
def set_save_for_later(property_id: int, payload: SaveForLaterUpdate, db: Session = Depends(get_db)):
    """Bookmark (or un-bookmark) a property for later. This is NOT a final
    decision: `decision` is left untouched, so a bookmarked property stays
    PENDING and keeps showing up in the discovery feed until the user
    actually likes or passes it."""
    prop = db.get(Property, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    prop.saved_for_later = payload.saved_for_later
    db.commit()
    db.refresh(prop)
    return _enrich([prop], db)[0]


@router.get("/saved", response_model=list[PropertyOut])
def get_saved(
    status: InventoryStatus | None = None,
    include_archived: bool = True,
    db: Session = Depends(get_db),
):
    """Saved Inventory Hub: all liked properties, optionally filtered by status."""
    query = db.query(Property).filter(Property.decision == DecisionStatus.LIKED)
    if status is not None:
        query = query.filter(Property.inventory_status == status)
    elif not include_archived:
        query = query.filter(Property.inventory_status != InventoryStatus.ARCHIVED)
    return _enrich(query.order_by(Property.updated_at.desc()).all(), db)


@router.patch("/{property_id}/inventory", response_model=PropertyOut)
def update_inventory(property_id: int, payload: InventoryUpdate, db: Session = Depends(get_db)):
    prop = db.get(Property, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if payload.inventory_status is not None:
        prop.inventory_status = payload.inventory_status
    if payload.notes is not None:
        prop.notes = payload.notes
    db.commit()
    db.refresh(prop)
    return _enrich([prop], db)[0]


@router.get("/later", response_model=list[PropertyOut])
def get_later(db: Session = Depends(get_db)):
    """Properties bookmarked "save for later" that are still undecided -
    also still visible in the discovery feed; revisit here and finish
    deciding like/pass whenever ready. Liking or passing removes a property
    from this list automatically (its decision is no longer PENDING)."""
    properties = (
        db.query(Property)
        .filter(Property.saved_for_later.is_(True), Property.decision == DecisionStatus.PENDING)
        .order_by(Property.updated_at.desc())
        .all()
    )
    return _enrich(properties, db)


@router.get("/passed", response_model=list[PropertyOut])
def get_passed(db: Session = Depends(get_db)):
    """Hidden archive of discarded properties (kept so they never resurface, viewable on request)."""
    properties = (
        db.query(Property)
        .filter(Property.decision == DecisionStatus.PASSED)
        .order_by(Property.decided_at.desc())
        .all()
    )
    return _enrich(properties, db)
