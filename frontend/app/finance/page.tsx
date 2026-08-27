"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { FinanceSettings, MortgageTranche } from "@/lib/types";
import { invalidateFinanceSettingsCache } from "@/lib/useFinanceSettings";

export default function FinanceSettingsPage() {
  const [equity, setEquity] = useState(500000);
  const [termYears, setTermYears] = useState(25);
  const [mix, setMix] = useState<MortgageTranche[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getFinanceSettings()
      .then((s: FinanceSettings) => {
        setEquity(s.equity_nis);
        setTermYears(s.loan_term_years);
        setMix(s.mix);
      })
      .catch((e) => setError(e.message || "שגיאה בטעינה"))
      .finally(() => setLoading(false));
  }, []);

  const totalShare = mix.reduce((sum, t) => sum + t.share_pct, 0);

  function updateTranche(i: number, patch: Partial<MortgageTranche>) {
    setMix((prev) => prev.map((t, idx) => (idx === i ? { ...t, ...patch } : t)));
  }

  async function save() {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      await api.updateFinanceSettings({ equity_nis: equity, loan_term_years: termYears, mix });
      invalidateFinanceSettingsCache();
      setSaved(true);
    } catch (e: any) {
      setError(e.message || "שגיאה בשמירה");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="mt-10 text-center text-gray-400">טוען...</div>;

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-xl font-bold">💰 הגדרות מימון</h1>
        <p className="mt-1 text-sm text-gray-500">
          הון עצמי, תקופת הלוואה ותמהיל משכנתא ממוצע - משמשים לחישוב ההחזר החודשי ותזרים המזומנים
          שמוצגים על כל נכס.
        </p>
      </div>

      <div>
        <label className="mb-1 block text-xs text-gray-400">הון עצמי זמין (₪)</label>
        <input
          type="number"
          value={equity}
          onChange={(e) => setEquity(Number(e.target.value) || 0)}
          className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs text-gray-400">תקופת הלוואה (שנים)</label>
        <input
          type="number"
          value={termYears}
          onChange={(e) => setTermYears(Number(e.target.value) || 1)}
          className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
        />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-600">תמהיל משכנתא ממוצע</h2>
          <span className={`text-xs ${Math.round(totalShare) !== 100 ? "text-red-600" : "text-gray-400"}`}>
            סה"כ: {totalShare.toFixed(1)}%
          </span>
        </div>
        <div className="flex flex-col gap-2">
          {mix.map((t, i) => (
            <div key={i} className="grid grid-cols-3 gap-2 rounded-xl border border-gray-200 p-2">
              <input
                value={t.name}
                onChange={(e) => updateTranche(i, { name: e.target.value })}
                placeholder="שם המסלול"
                className="rounded-md border border-gray-200 px-2 py-1 text-xs"
              />
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={t.share_pct}
                  onChange={(e) => updateTranche(i, { share_pct: Number(e.target.value) || 0 })}
                  className="w-full rounded-md border border-gray-200 px-2 py-1 text-xs"
                />
                <span className="text-xs text-gray-400">%</span>
              </div>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  step="0.1"
                  value={t.annual_rate_pct}
                  onChange={(e) => updateTranche(i, { annual_rate_pct: Number(e.target.value) || 0 })}
                  className="w-full rounded-md border border-gray-200 px-2 py-1 text-xs"
                />
                <span className="text-xs text-gray-400">% ריבית</span>
              </div>
            </div>
          ))}
        </div>
        {Math.round(totalShare) !== 100 && (
          <div className="mt-2 text-xs text-amber-700">⚠️ סכום האחוזים אמור להסתכם ל-100%</div>
        )}
      </div>

      {error && <div className="text-center text-sm text-red-600">{error}</div>}
      {saved && <div className="text-center text-sm text-brand-700">ההגדרות נשמרו ✓</div>}

      <button
        onClick={save}
        disabled={saving}
        className="rounded-full bg-brand-600 py-3 text-lg font-semibold text-white disabled:opacity-50"
      >
        שמירה
      </button>
    </div>
  );
}
