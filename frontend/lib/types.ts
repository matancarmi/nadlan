export type AssetType = "rooms_4" | "garden_apartment" | "new_project" | "pinui_binui" | "other";
export type DecisionStatus = "pending" | "liked" | "passed" | "maybe";
export type InventoryStatus = "under_review" | "contacted_agent" | "archived";

export interface Property {
  id: number;
  source: string;
  external_id: string;
  source_url: string | null;
  contact_info: string | null;
  image_url: string | null;
  title: string;
  city: string;
  neighborhood: string | null;
  street: string | null;
  asset_type: AssetType;
  rooms: number | null;
  size_sqm: number | null;
  asking_price: number | null;
  price_per_sqm: number | null;
  planning_status: string | null;
  planning_status_key: string | null;
  cma_avg_price_per_sqm: number | null;
  cma_sample_size: number | null;
  cma_discount_pct: number | null;
  is_high_value_deal: boolean;
  ai_summary: string | null;
  ai_pros: string | null;
  ai_cons: string | null;
  ai_verdict: string | null;
  decision: DecisionStatus;
  inventory_status: InventoryStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;

  estimated_monthly_rent: number | null;
  gross_rental_yield_pct: number | null;
  estimated_monthly_mortgage_payment: number | null;
  monthly_cash_flow: number | null;
  loan_amount_used: number | null;
  is_premium_area: boolean;
}

export interface PlanningStage {
  key: string;
  order: number;
  title: string;
  short_description: string;
  long_description: string;
  category: string;
}

export const ASSET_TYPE_LABELS: Record<AssetType, string> = {
  rooms_4: "דירת 4 חדרים",
  garden_apartment: "דירת גן",
  new_project: "פרויקט חדש",
  pinui_binui: "פינוי בינוי",
  other: "אחר",
};

export const INVENTORY_STATUS_LABELS: Record<InventoryStatus, string> = {
  under_review: "בבדיקה",
  contacted_agent: "יצרתי קשר עם המתווך",
  archived: "בארכיון",
};

export type AreaMode = "cities" | "radius";

export interface SearchAreaSettings {
  mode: AreaMode;
  cities: string[] | null;
  address: string | null;
  radius_km: number | null;
  center_lat: number | null;
  center_lon: number | null;
  resolved_cities: string[] | null;
  premium_cities: string[] | null;
}

export interface MortgageTranche {
  name: string;
  share_pct: number;
  annual_rate_pct: number;
}

export interface FinanceSettings {
  equity_nis: number;
  loan_term_years: number;
  mix: MortgageTranche[];
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}
