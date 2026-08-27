import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .config import get_settings
from .database import SessionLocal
from .services.ingestion import run_daily_ingestion

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _job():
    db = SessionLocal()
    try:
        result = run_daily_ingestion(db)
        logger.info("Daily ingestion complete: %s", result)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    settings = get_settings()
    _scheduler = BackgroundScheduler(timezone="Asia/Jerusalem")
    _scheduler.add_job(_job, "cron", hour=settings.ingestion_cron_hour, minute=0, id="daily_ingestion")
    _scheduler.start()
    logger.info("Scheduler started: daily ingestion at %02d:00 Asia/Jerusalem", settings.ingestion_cron_hour)
    return _scheduler
