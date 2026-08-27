"use client";

import { useState } from "react";
import { ASSET_TYPE_LABELS, FinanceSettings, Property } from "@/lib/types";
import { calculateMortgage } from "@/lib/finance";

function formatPrice(n: number | null) {
  if (n == null) return "לא צוין";
  return `₪${n.toLocaleString("he-IL")}`;
}

function formatMoney(n: number | null | undefined) {
  if (n == null) return "-";
  return `₪${Math.round(n).toLocaleString("he-IL")}`;
}

export default function PropertyCard({
  property,
  financeSettings,
  children,
}: {
  property: Property;
  financeSettings?: FinanceSettings | null;
  children?: React.ReactNode;
}) {
  const p = property;
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = !!p.image_url && !imageFailed;

  const [calcOpen, setCalcOpen] = useState(false);
  const [equity, setEquity] = useState<number>(financeSettings?.equity_nis ?? 500000);
  const [termYears, setTermYears] = useState<number>(financeSettings?.loan_term_years ?? 25);

  const canCalculate = !!(financeSettings && p.asking_price);
  const localCalc = canCalculate
    ? calculateMortgage(p.asking_price!, equity, termYears, financeSettings!.mix)
    : null;
  const localCashFlow =
    localCalc && p.estimated_monthly_rent != null ? Math.round(p.estimated_monthly_rent - localCalc.monthlyPayment) : null;

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="aspect-[16/10] w-full overflow-hidden bg-gray-100">
        {showImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={p.image_url!}
            alt={p.title}
            className="h-full w-full object-cover"
            loading="lazy"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <a
            href={p.source_url || undefined}
            target="_blank"
            rel="noreferrer"
            className="flex h-full w-full flex-col items-center justify-center gap-1 bg-gray-200 text-center text-gray-500"
          >
            <span className="text-2xl">🖼️</span>
            <span className="px-4 text-sm font-medium">בשביל תמונה אנא כנס לקישור</span>
          </a>
        )}
      </div>
      <div className="flex items-start justify-between gap-2 border-b border-gray-100 bg-gray-50 px-4 py-3">
        <div>
          <div className="flex items-center gap-1.5 text-lg font-semibold leading-tight">
            {p.is_premium_area && <span title="אזור צמיחה מועדף">⭐</span>}
            {p.title}
          </div>
          <div className="text-sm text-gray-500">
            {p.city}
            {p.street ? ` · ${p.street}` : ""}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          {p.is_high_value_deal && (
            <span className="whitespace-nowrap rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800">
              🔥 עסקה חמה
            </span>
          )}
          {p.saved_for_later && (
            <span className="whitespace-nowrap rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
              🔖 שמור להמשך
            </span>
          )}
        </div>
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

      {(p.gross_rental_yield_pct != null || p.monthly_cash_flow != null) && (
        <div className="grid grid-cols-3 gap-2 px-4 pb-3 text-xs">
          <div className="rounded-lg bg-gray-50 px-2 py-2 text-center">
            <div className="text-gray-400">שכ"ד מוערך</div>
            <div className="font-semibold">{formatMoney(p.estimated_monthly_rent)}</div>
          </div>
          <div className="rounded-lg bg-gray-50 px-2 py-2 text-center">
            <div className="text-gray-400">תשואה גולמית</div>
            <div className="font-semibold">{p.gross_rental_yield_pct != null ? `${p.gross_rental_yield_pct}%` : "-"}</div>
          </div>
          <div
            className={`rounded-lg px-2 py-2 text-center ${
              p.monthly_cash_flow != null && p.monthly_cash_flow >= 0 ? "bg-brand-50" : "bg-red-50"
            }`}
          >
            <div className="text-gray-400">תזרים חודשי</div>
            <div className={`font-semibold ${p.monthly_cash_flow != null && p.monthly_cash_flow < 0 ? "text-red-700" : ""}`}>
              {formatMoney(p.monthly_cash_flow)}
            </div>
          </div>
        </div>
      )}

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

      {canCalculate && (
        <div className="mx-4 mb-3 overflow-hidden rounded-lg border border-gray-200">
          <button
            onClick={() => setCalcOpen((v) => !v)}
            className="flex w-full items-center justify-between bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-600"
          >
            <span>💰 מחשבון מימון</span>
            <span>{calcOpen ? "−" : "+"}</span>
          </button>
          {calcOpen && (
            <div className="flex flex-col gap-2 px-3 py-3 text-xs">
              <div className="flex items-center justify-between gap-2">
                <label className="text-gray-500">הון עצמי</label>
                <input
                  type="number"
                  value={equity}
                  onChange={(e) => setEquity(Number(e.target.value) || 0)}
                  className="w-32 rounded-md border border-gray-200 px-2 py-1 text-left"
                />
              </div>
              <div className="flex items-center justify-between gap-2">
                <label className="text-gray-500">תקופת הלוואה (שנים)</label>
                <input
                  type="number"
                  value={termYears}
                  onChange={(e) => setTermYears(Number(e.target.value) || 1)}
                  className="w-32 rounded-md border border-gray-200 px-2 py-1 text-left"
                />
              </div>
              {localCalc && (
                <div className="mt-1 grid grid-cols-3 gap-2 border-t border-gray-100 pt-2 text-center">
                  <div>
                    <div className="text-gray-400">סכום הלוואה</div>
                    <div className="font-semibold">{formatMoney(localCalc.loanAmount)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400">החזר חודשי</div>
                    <div className="font-semibold">{formatMoney(localCalc.monthlyPayment)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400">תזרים חודשי</div>
                    <div className={`font-semibold ${localCashFlow != null && localCashFlow < 0 ? "text-red-700" : ""}`}>
                      {formatMoney(localCashFlow)}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
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
