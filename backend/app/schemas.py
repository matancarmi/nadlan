from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .models import AssetType, DecisionStatus, InventoryStatus


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str
    source_url: str | None
    contact_info: str | None
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
    inventory_status: InventoryStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class DecisionUpdate(BaseModel):
    decision: DecisionStatus


class InventoryUpdate(BaseModel):
    inventory_status: InventoryStatus | None = None
    notes: str | None = None


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
