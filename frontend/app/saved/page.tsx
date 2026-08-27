"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { INVENTORY_STATUS_LABELS, InventoryStatus, Property } from "@/lib/types";
import PropertyCard from "@/components/PropertyCard";
import { useFinanceSettings } from "@/lib/useFinanceSettings";

const STATUSES: InventoryStatus[] = ["under_review", "contacted_agent", "archived"];

export default function SavedInventory() {
  const [items, setItems] = useState<Property[] | null>(null);
  const [filter, setFilter] = useState<InventoryStatus | "all">("all");
  const [error, setError] = useState<string | null>(null);
  const financeSettings = useFinanceSettings();

  async function load() {
    try {
      setItems(await api.getSaved());
    } catch (e: any) {
      setError(e.message || "שגיאה בטעינה");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function updateStatus(id: number, status: InventoryStatus) {
    await api.updateInventory(id, { inventory_status: status });
    load();
  }

  async function updateNotes(id: number, notes: string) {
    await api.updateInventory(id, { notes });
  }

  if (error) return <div className="mt-10 text-center text-red-600">{error}</div>;
  if (items === null) return <div className="mt-10 text-center text-gray-400">טוען...</div>;

  const filtered = filter === "all" ? items : items.filter((i) => i.inventory_status === filter);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setFilter("all")}
          className={`rounded-full px-3 py-1 text-xs font-medium ${filter === "all" ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-600"}`}
        >
          הכל ({items.length})
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${filter === s ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-600"}`}
          >
            {INVENTORY_STATUS_LABELS[s]} ({items.filter((i) => i.inventory_status === s).length})
          </button>
        ))}
      </div>

      {filtered.length === 0 && <div className="mt-10 text-center text-gray-400">אין נכסים תואמים</div>}

      {filtered.map((p) => (
        <PropertyCard key={p.id} property={p} financeSettings={financeSettings}>
          <div className="border-t border-gray-100 px-4 py-3">
            <label className="mb-1 block text-xs text-gray-400">סטטוס</label>
            <select
              value={p.inventory_status}
              onChange={(e) => updateStatus(p.id, e.target.value as InventoryStatus)}
              className="mb-2 w-full rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {INVENTORY_STATUS_LABELS[s]}
                </option>
              ))}
            </select>
            <label className="mb-1 block text-xs text-gray-400">הערות פרטיות</label>
            <textarea
              defaultValue={p.notes || ""}
              onBlur={(e) => updateNotes(p.id, e.target.value)}
              placeholder="הוסיפו הערה..."
              className="w-full rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
              rows={2}
            />
          </div>
        </PropertyCard>
      ))}
    </div>
  );
}
