import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import SessionLocal, init_db
from .routers import auth, guide, ingest, properties
from .scheduler import start_scheduler
from .seed_guide import seed_planning_stages

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RealEstateTinder API")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.frontend_origins.split(",") if o.strip()],
    allow_credentials=True,  # session cookie requires an explicit origin, not "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(guide.router)
app.include_router(ingest.router)


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        seed_planning_stages(db)
    finally:
        db.close()
    start_scheduler()


@app.get("/api/health")
def health():
    return {"status": "ok"}
