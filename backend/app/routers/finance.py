from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import FinanceSettingsOut, FinanceSettingsUpdate
from ..security import require_session
from ..services.finance import get_or_create_finance_settings

router = APIRouter(prefix="/api/settings/finance", tags=["finance"], dependencies=[Depends(require_session)])


@router.get("", response_model=FinanceSettingsOut)
def get_finance_settings(db: Session = Depends(get_db)):
    return get_or_create_finance_settings(db)


@router.put("", response_model=FinanceSettingsOut)
def update_finance_settings(payload: FinanceSettingsUpdate, db: Session = Depends(get_db)):
    row = get_or_create_finance_settings(db)
    row.equity_nis = payload.equity_nis
    row.loan_term_years = payload.loan_term_years
    row.mix = [t.model_dump() for t in payload.mix]
    db.commit()
    db.refresh(row)
    return row
