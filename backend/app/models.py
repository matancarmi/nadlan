import enum
from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, DateTime, Enum, Float, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AssetType(str, enum.Enum):
    ROOMS_4 = "rooms_4"
    GARDEN_APARTMENT = "garden_apartment"
    NEW_PROJECT = "new_project"
    PINUI_BINUI = "pinui_binui"
    OTHER = "other"


class DecisionStatus(str, enum.Enum):
    PENDING = "pending"   # not yet swiped -> shows in discovery feed
    LIKED = "liked"       # saved -> shows in Saved Inventory
    PASSED = "passed"     # discarded -> hidden archive, never shown again
    MAYBE = "maybe"       # save for later -> leaves the feed, revisit on /later to decide


class InventoryStatus(str, enum.Enum):
    UNDER_REVIEW = "under_review"
    CONTACTED_AGENT = "contacted_agent"
    ARCHIVED = "archived"


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_source_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- Source / identity ---
    source: Mapped[str] = mapped_column(String(50), index=True)  # e.g. "yad2", "madlan", "winwin", "gov_pinui_binui"
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_info: Mapped[str | None] = mapped_column(String(300), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- Core listing data ---
    title: Mapped[str] = mapped_column(String(300))
    city: Mapped[str] = mapped_column(String(100), index=True)
    neighborhood: Mapped[str | None] = mapped_column(String(150), nullable=True)
    street: Mapped[str | None] = mapped_column(String(150), nullable=True)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), index=True)
    rooms: Mapped[float | None] = mapped_column(Float, nullable=True)
    size_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    asking_price: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Planning / project status (for pinui binui + presale) ---
    planning_status: Mapped[str | None] = mapped_column(String(200), nullable=True)
    planning_status_key: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # --- AI / CMA analysis ---
    cma_avg_price_per_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    cma_sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cma_discount_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # positive = below market
    is_high_value_deal: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # --- Rental yield (market-level estimate, independent of any one buyer's
    # financing choices, so computed once at ingestion and stored) ---
    estimated_monthly_rent: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_rental_yield_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_pros: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_cons: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_verdict: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- Raw payload for debugging / re-analysis ---
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- User workflow ---
    decision: Mapped[DecisionStatus] = mapped_column(Enum(DecisionStatus), default=DecisionStatus.PENDING, index=True)
    inventory_status: Mapped[InventoryStatus] = mapped_column(
        Enum(InventoryStatus), default=InventoryStatus.UNDER_REVIEW
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SearchSettings(Base):
    """Singleton row (id=1) holding the user's configured search area.

    mode="cities": use `cities` (a JSON list of city names) directly.
    mode="radius": geocode `address` once and keep all properties within
    `radius_km` of it, computed against a curated coordinate table
    (see services/geo.py) rather than per-property geocoding.
    """
    __tablename__ = "search_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mode: Mapped[str] = mapped_column(String(20), default="cities")  # "cities" | "radius"
    cities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    radius_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_cities: Mapped[list | None] = mapped_column(JSON, nullable=True)  # cache of last radius match
    # Cities flagged by the user as high-potential / rapidly developing ("growth
    # areas") - shown with a ⭐ badge on property cards regardless of search mode.
    premium_cities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FinanceSettings(Base):
    """Singleton row (id=1) holding the user's default financing assumptions,
    used to compute the estimated mortgage payment and cash flow shown on
    every property card. `mix` is a standard Israeli "תמהיל" - a JSON list of
    tranches, each {name, share_pct, annual_rate_pct}, whose share_pct sums
    to 100."""
    __tablename__ = "finance_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equity_nis: Mapped[float] = mapped_column(Float, default=500_000)
    loan_term_years: Mapped[int] = mapped_column(Integer, default=25)
    mix: Mapped[list] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    """Log of the AI Investment Advisor chat (single conversation - this is a
    single-user app). role is "user" or "assistant"."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class PlanningStage(Base):
    """Static reference content for the educational Planning Guide page."""
    __tablename__ = "planning_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200))
    short_description: Mapped[str] = mapped_column(Text)
    long_description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), default="general")  # general | pinui_binui | presale
