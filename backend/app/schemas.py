from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .models import AssetType, DecisionStatus, InventoryStatus


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str
    source_url: str | None
    contact_info: str | None
    image_url: str | None
    title: str
    city: str
    neighborhood: str | None
    street: str | None
    asset_type: AssetType
    rooms: float | None
    size_sqm: float | None
    asking_price: float | None
    price_per_sqm: float | None
    planning_status: str | None
    planning_status_key: str | None
    cma_avg_price_per_sqm: float | None
    cma_sample_size: int | None
    cma_discount_pct: float | None
    is_high_value_deal: bool
    ai_summary: str | None
    ai_pros: str | None
    ai_cons: str | None
    ai_verdict: str | None
    decision: DecisionStatus
    saved_for_later: bool
    inventory_status: InventoryStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # --- Rental yield (stored, computed at ingestion) ---
    estimated_monthly_rent: float | None = None
    gross_rental_yield_pct: float | None = None

    # --- Dynamic fields, computed at read-time from current Finance/Area
    # settings rather than stored - see services/finance.py ---
    estimated_monthly_mortgage_payment: float | None = None
    monthly_cash_flow: float | None = None
    loan_amount_used: float | None = None
    is_premium_area: bool = False


class DecisionUpdate(BaseModel):
    # Only a final decision - liked or passed. "Save for later" is a
    # bookmark, not a decision; see POST /{id}/save-for-later instead.
    decision: Literal[DecisionStatus.LIKED, DecisionStatus.PASSED]


class InventoryUpdate(BaseModel):
    inventory_status: InventoryStatus | None = None
    notes: str | None = None


class SaveForLaterUpdate(BaseModel):
    saved_for_later: bool = True


class IngestionResult(BaseModel):
    fetched: int
    created: int
    updated: int
    high_value_deals: int
    alerts_sent: int
    errors: list[str] = []


class PlanningStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    order: int
    title: str
    short_description: str
    long_description: str
    category: str


class LoginRequest(BaseModel):
    password: str


class SearchSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mode: str
    cities: list[str] | None
    address: str | None
    radius_km: float | None
    center_lat: float | None
    center_lon: float | None
    resolved_cities: list[str] | None
    premium_cities: list[str] | None


class SearchSettingsUpdate(BaseModel):
    mode: str  # "cities" | "radius"
    cities: list[str] | None = None
    address: str | None = None
    radius_km: float | None = None


class PremiumCitiesUpdate(BaseModel):
    premium_cities: list[str]


class AvailableCitiesOut(BaseModel):
    cities: list[str]


class MortgageTranche(BaseModel):
    name: str
    share_pct: float
    annual_rate_pct: float


class FinanceSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equity_nis: float
    loan_term_years: int
    mix: list[MortgageTranche]


class FinanceSettingsUpdate(BaseModel):
    equity_nis: float
    loan_term_years: int
    mix: list[MortgageTranche]


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ChatRequest(BaseModel):
    content: str


class IngestUrlRequest(BaseModel):
    url: str


class ManualPropertyCreate(BaseModel):
    title: str
    city: str
    street: str | None = None
    asset_type: AssetType = AssetType.OTHER
    rooms: float | None = None
    size_sqm: float | None = None
    asking_price: float
    source_url: str | None = None
    image_url: str | None = None
    contact_info: str | None = None
    notes: str | None = None


class IngestUrlResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: Literal["created", "needs_manual_input"]
    property: PropertyOut | None = None
    prefill: dict | None = None
    message: str | None = None
