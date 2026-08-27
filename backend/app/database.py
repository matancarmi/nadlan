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
    _sync_postgres_enum_types()


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
        "properties": [
            ("image_url", "VARCHAR(500)"),
            ("estimated_monthly_rent", "FLOAT"),
            ("gross_rental_yield_pct", "FLOAT"),
        ],
        "search_settings": [
            ("premium_cities", "JSON"),
        ],
    }
    for table, columns in additions.items():
        if table not in existing_tables:
            continue  # brand-new table, create_all() already made it with every column
        existing_columns = {c["name"] for c in inspector.get_columns(table)}
        for column_name, column_type in columns:
            if column_name not in existing_columns:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))


def _sync_postgres_enum_types():
    """Add any new Python enum members to their matching Postgres native ENUM
    type. SQLAlchemy's Enum() creates a real Postgres ENUM type from whatever
    members existed at table-creation time — adding a value to the Python
    enum later (e.g. DecisionStatus.MAYBE) does NOT expand that Postgres
    type, so writing the new value would fail with "invalid input value for
    enum" until this runs. No-op on SQLite, which stores enums as plain text.

    Important: SQLAlchemy's default Enum() stores each member's NAME
    ("PENDING") as the Postgres label, not its `.value` ("pending") — even
    though this project's enums subclass `str` and their members compare
    equal to their lowercase value. Verified directly against a real
    Postgres 16 instance before relying on it here.
    """
    import logging

    import sqlalchemy as sa
    from sqlalchemy import text

    logger = logging.getLogger(__name__)
    if engine.dialect.name != "postgresql":
        return

    for table in Base.metadata.tables.values():
        for column in table.columns:
            col_type = column.type
            if not (isinstance(col_type, sa.Enum) and col_type.enum_class):
                continue
            pg_type_name = col_type.name
            try:
                with engine.begin() as conn:
                    existing_labels = {
                        row[0]
                        for row in conn.execute(
                            text(
                                "SELECT enumlabel FROM pg_enum "
                                "WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = :name)"
                            ),
                            {"name": pg_type_name},
                        )
                    }
                    for member in col_type.enum_class:
                        if member.name not in existing_labels:
                            # ALTER TYPE ... ADD VALUE takes no bind params; these
                            # values come from our own code's enum definitions, not
                            # user input, so inlining is safe.
                            conn.execute(text(f"ALTER TYPE \"{pg_type_name}\" ADD VALUE IF NOT EXISTS '{member.name}'"))
            except Exception as exc:  # noqa: BLE001 - never block startup over this
                logger.warning("Could not sync Postgres enum type %r: %s", pg_type_name, exc)
