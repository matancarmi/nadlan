import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AssetType, DecisionStatus, Property
from ..schemas import IngestUrlRequest, IngestUrlResult, ManualPropertyCreate, PropertyOut
from ..security import require_session
from ..services.ai_analysis import enrich_with_cma, enrich_with_rental_yield, generate_ai_summary
from ..services.finance import enrich_properties_for_response
from ..services.manual_ingest import fetch_and_parse

router = APIRouter(prefix="/api/properties", tags=["properties"], dependencies=[Depends(require_session)])


def _create_property_from_fields(db: Session, source: str, external_id: str, fields: dict) -> Property:
    """Shared by both the URL-ingest success path and the manual-entry
    endpoint. Upserts on (source, external_id), same as the daily bulk
    ingestion - re-submitting the same URL updates the existing property
    rather than duplicating it."""
    existing = db.query(Property).filter(Property.source == source, Property.external_id == external_id).one_or_none()
    prop = existing or Property(source=source, external_id=external_id, decision=DecisionStatus.PENDING)

    prop.title = fields["title"]
    prop.city = fields["city"]
    prop.street = fields.get("street")
    try:
        prop.asset_type = AssetType(fields.get("asset_type") or "other")
    except ValueError:
        prop.asset_type = AssetType.OTHER
    prop.rooms = fields.get("rooms")
    prop.size_sqm = fields.get("size_sqm")
    prop.asking_price = fields["asking_price"]
    prop.source_url = fields.get("source_url")
    prop.image_url = fields.get("image_url")  # only ever a genuinely found/user-supplied image - no placeholder
    prop.contact_info = fields.get("contact_info")
    prop.notes = fields.get("notes")
    if existing is None:
        db.add(prop)
    db.flush()

    enrich_with_cma(prop)
    enrich_with_rental_yield(prop)
    generate_ai_summary(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.post("/ingest-url", response_model=IngestUrlResult)
def ingest_url(payload: IngestUrlRequest, db: Session = Depends(get_db)):
    """Add a single listing by pasting its URL: fetch + parse the page, run
    it through the same AI/CMA/rental pipeline as the daily ingestion, and
    drop it straight into the discovery feed. If not enough could be parsed
    automatically, returns what was found so the UI can offer a short manual
    form instead of getting stuck."""
    result = fetch_and_parse(payload.url)
    prefill = result["prefill"]

    if not result["ok"]:
        return IngestUrlResult(
            status="needs_manual_input",
            prefill=prefill,
            message="לא הצלחנו לשלוף אוטומטית את כל הפרטים מהקישור - השלימו את החסר.",
        )

    prop = _create_property_from_fields(db, source="manual_url", external_id=payload.url, fields=prefill)
    enriched = enrich_properties_for_response([prop], db)[0]
    return IngestUrlResult(status="created", property=PropertyOut.model_validate(enriched))


@router.post("/manual", response_model=PropertyOut)
def create_manual_property(payload: ManualPropertyCreate, db: Session = Depends(get_db)):
    """Fallback for when ingest-url couldn't parse enough automatically (or
    the user just wants to type up a listing directly, e.g. from a phone
    call or a site with no scrapable page at all)."""
    external_id = payload.source_url or f"manual-{uuid.uuid4().hex}"
    prop = _create_property_from_fields(
        db,
        source="manual_url" if payload.source_url else "manual",
        external_id=external_id,
        fields=payload.model_dump(),
    )
    return enrich_properties_for_response([prop], db)[0]
