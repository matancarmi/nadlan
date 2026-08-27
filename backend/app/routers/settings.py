from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AvailableCitiesOut, SearchSettingsOut, SearchSettingsUpdate
from ..security import require_session
from ..services.geo import CITY_COORDS, geocode_address, get_or_create_settings

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_session)])


@router.get("/areas", response_model=SearchSettingsOut)
def get_areas(db: Session = Depends(get_db)):
    return get_or_create_settings(db)


@router.get("/areas/available-cities", response_model=AvailableCitiesOut)
def available_cities():
    """Cities the app knows coordinates for (used both for the checklist UI
    in "cities" mode and as candidates for radius matching)."""
    return {"cities": sorted(CITY_COORDS.keys())}


@router.put("/areas", response_model=SearchSettingsOut)
def update_areas(payload: SearchSettingsUpdate, db: Session = Depends(get_db)):
    row = get_or_create_settings(db)
    row.mode = payload.mode

    if payload.mode == "cities":
        row.cities = payload.cities or []
        row.address = None
        row.radius_km = None
        row.center_lat = None
        row.center_lon = None
        row.resolved_cities = None
    else:  # radius
        row.address = payload.address
        row.radius_km = payload.radius_km
        # Re-geocode whenever the address changes so the map/city match stays accurate.
        center = geocode_address(payload.address) if payload.address else None
        row.center_lat, row.center_lon = center if center else (None, None)
        row.resolved_cities = None

    db.commit()
    db.refresh(row)
    return row
