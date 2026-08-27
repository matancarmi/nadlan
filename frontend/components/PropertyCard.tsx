"use client";

import { ASSET_TYPE_LABELS, Property } from "@/lib/types";

function formatPrice(n: number | null) {
  if (n == null) return "לא צוין";
  return `₪${n.toLocaleString("he-IL")}`;
}

export default function PropertyCard({
  property,
  children,
}: {
  property: Property;
  children?: React.ReactNode;
}) {
  const p = property;
  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="flex items-start justify-between gap-2 border-b border-gray-100 bg-gray-50 px-4 py-3">
        <div>
          <div className="text-lg font-semibold leading-tight">{p.title}</div>
          <div className="text-sm text-gray-500">
            {p.city}
            {p.street ? ` · ${p.street}` : ""}
          </div>
        </div>
        {p.is_high_value_deal && (
          <span className="whitespace-nowrap rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800">
            🔥 עסקה חמה
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 px-4 py-3 text-sm">
        <div>
          <div className="text-gray-400">מחיר מבוקש</div>
          <div className="font-semibold">{formatPrice(p.asking_price)}</div>
        </div>
        <div>
          <div className="text-gray-400">מחיר למ"ר</div>
          <div className="font-semibold">{p.price_per_sqm ? `₪${Math.round(p.price_per_sqm).toLocaleString("he-IL")}` : "-"}</div>
        </div>
        <div>
          <div className="text-gray-400">חדרים / גודל</div>
          <div className="font-semibold">
            {p.rooms ?? "-"} חד' · {p.size_sqm ?? "-"} מ"ר
          </div>
        </div>
        <div>
          <div className="text-gray-400">סוג נכס</div>
          <div className="font-semibold">{ASSET_TYPE_LABELS[p.asset_type]}</div>
        </div>
      </div>

      {p.planning_status && (
        <div className="mx-4 mb-2 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-800">
          🏗️ סטטוס תכנוני: {p.planning_status}
        </div>
      )}

      {p.cma_discount_pct != null && (
        <div
          className={`mx-4 mb-2 rounded-lg px-3 py-2 text-xs ${
            p.cma_discount_pct > 0 ? "bg-brand-50 text-brand-700" : "bg-red-50 text-red-700"
          }`}
        >
          📊 {p.cma_discount_pct > 0 ? "נמוך" : "גבוה"} ב-{Math.abs(p.cma_discount_pct)}% מהממוצע באזור
          {p.cma_sample_size ? ` (על בסיס ${p.cma_sample_size} עסקאות)` : ""}
        </div>
      )}

      {p.ai_summary && (
        <div className="mx-4 mb-3 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-700">
          <div className="mb-1 font-semibold text-gray-500">🤖 סיכום AI {p.ai_verdict ? `· ${p.ai_verdict}` : ""}</div>
          {p.ai_summary}
        </div>
      )}

      {p.source_url && (
        <div className="px-4 pb-3">
          <a
            href={p.source_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs font-medium text-brand-600 underline"
          >
            למקור המודעה ({p.source}) ↗
          </a>
        </div>
      )}

      {children}
    </div>
  );
}
