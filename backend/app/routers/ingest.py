from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import IngestionResult
from ..security import require_session
from ..services.ingestion import run_daily_ingestion

router = APIRouter(prefix="/api/ingest", tags=["ingest"], dependencies=[Depends(require_session)])


@router.post("/run", response_model=IngestionResult)
def trigger_ingestion(db: Session = Depends(get_db)):
    """Manually trigger the daily ingestion pipeline (also runs automatically once a day)."""
    return run_daily_ingestion(db)
