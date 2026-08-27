from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PlanningStage
from ..schemas import PlanningStageOut
from ..security import require_session

router = APIRouter(prefix="/api/guide", tags=["guide"], dependencies=[Depends(require_session)])


@router.get("/stages", response_model=list[PlanningStageOut])
def get_stages(db: Session = Depends(get_db)):
    return db.query(PlanningStage).order_by(PlanningStage.order).all()
