export type AssetType = "rooms_4" | "garden_apartment" | "new_project" | "pinui_binui" | "other";
export type DecisionStatus = "pending" | "liked" | "passed";
export type InventoryStatus = "under_review" | "contacted_agent" | "archived";

export interface Property {
  id: number;
  source: string;
  external_id: string;
  source_url: string | null;
  contact_info: string | null;
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
