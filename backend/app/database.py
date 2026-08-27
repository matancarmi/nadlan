from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401 ensure models are registered
    Base.metadata.create_all(bind=engine)  # creates brand-new tables only
    _run_lightweight_migrations()


def _run_lightweight_migrations():
    """Add columns to already-existing tables. `create_all()` never alters an
    existing table, so a column added to a model after the table was first
    created needs an explicit, idempotent ALTER TABLE here. There's no
    Alembic in this project (deliberately, for a single-user app) — extend
    this list whenever a new column is added to an existing model.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    additions = {
        "properties": [("image_url", "VARCHAR(500)")],
    }
    for table, columns in additions.items():
        if table not in existing_tables:
            continue  # brand-new table, create_all() already made it with every column
        existing_columns = {c["name"] for c in inspector.get_columns(table)}
        for column_name, column_type in columns:
            if column_name not in existing_columns:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))
