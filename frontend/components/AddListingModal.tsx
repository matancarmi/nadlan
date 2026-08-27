"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { ASSET_TYPE_LABELS, AssetType, ManualPrefill, Property } from "@/lib/types";

const ASSET_TYPES: AssetType[] = ["rooms_4", "garden_apartment", "new_project", "pinui_binui", "other"];

export default function AddListingModal({
  onClose,
  onAdded,
}: {
  onClose: () => void;
  onAdded: (property: Property) => void;
}) {
  const [mode, setMode] = useState<"url" | "manual">("url");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const [manual, setManual] = useState({
    title: "",
    city: "",
    street: "",
    asset_type: "other" as AssetType,
    rooms: "",
    size_sqm: "",
    asking_price: "",
    image_url: "",
    source_url: "",
    contact_info: "",
  });

  function applyPrefill(prefill: ManualPrefill | null) {
    if (!prefill) return;
    setManual((m) => ({
      ...m,
      title: prefill.title || m.title,
      city: prefill.city || m.city,
      street: prefill.street || m.street,
      asset_type: prefill.asset_type || m.asset_type,
      rooms: prefill.rooms != null ? String(prefill.rooms) : m.rooms,
      size_sqm: prefill.size_sqm != null ? String(prefill.size_sqm) : m.size_sqm,
      asking_price: prefill.asking_price != null ? String(prefill.asking_price) : m.asking_price,
      image_url: prefill.image_url || m.image_url,
      source_url: prefill.source_url || m.source_url,
    }));
  }

  async function submitUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const result = await api.ingestUrl(url.trim());
      if (result.status === "created" && result.property) {
        onAdded(result.property);
      } else {
        applyPrefill(result.prefill);
        setInfo(result.message || "לא הצלחנו לשלוף את כל הפרטים אוטומטית - השלימו את החסר.");
        setMode("manual");
      }
    } catch (e: any) {
      setError(e.message || "שגיאה בייבוא הקישור");
    } finally {
      setLoading(false);
    }
  }

  async function submitManual(e: React.FormEvent) {
    e.preventDefault();
    if (!manual.title.trim() || !manual.city.trim() || !manual.asking_price) {
      setError("יש למלא לפחות כותרת, עיר ומחיר מבוקש");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const property = await api.createManualProperty({
        title: manual.title.trim(),
        city: manual.city.trim(),
        street: manual.street.trim() || null,
        asset_type: manual.asset_type,
        rooms: manual.rooms ? Number(manual.rooms) : null,
        size_sqm: manual.size_sqm ? Number(manual.size_sqm) : null,
        asking_price: Number(manual.asking_price),
        image_url: manual.image_url.trim() || null,
        source_url: manual.source_url.trim() || null,
        contact_info: manual.contact_info.trim() || null,
      });
      onAdded(property);
    } catch (e: any) {
      setError(e.message || "שגיאה בהוספת הנכס");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/40 sm:items-center" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-5 sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">➕ הוספת נכס לפי קישור</h2>
          <button onClick={onClose} className="text-gray-400">
            ✕
          </button>
        </div>

        {mode === "url" && (
          <form onSubmit={submitUrl} className="flex flex-col gap-3">
            <p className="text-sm text-gray-500">הדביקו קישור למודעה מיד2 או כל אתר נדל"ן אחר.</p>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.yad2.co.il/realestate/item/..."
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
              dir="ltr"
              autoFocus
            />
            {error && <div className="text-sm text-red-600">{error}</div>}
            <button
              disabled={loading}
              className="rounded-full bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
            >
              {loading ? "מייבא..." : "ייבוא"}
            </button>
            <button type="button" onClick={() => setMode("manual")} className="text-xs text-gray-400 underline">
              או הזינו את פרטי הנכס ידנית
            </button>
          </form>
        )}

        {mode === "manual" && (
          <form onSubmit={submitManual} className="flex flex-col gap-3">
            {info && <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">{info}</div>}
            <div>
              <label className="mb-1 block text-xs text-gray-400">כותרת *</label>
              <input
                value={manual.title}
                onChange={(e) => setManual((m) => ({ ...m, title: e.target.value }))}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-xs text-gray-400">עיר *</label>
                <input
                  value={manual.city}
                  onChange={(e) => setManual((m) => ({ ...m, city: e.target.value }))}
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-400">רחוב</label>
                <input
                  value={manual.street}
                  onChange={(e) => setManual((m) => ({ ...m, street: e.target.value }))}
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">סוג נכס</label>
              <select
                value={manual.asset_type}
                onChange={(e) => setManual((m) => ({ ...m, asset_type: e.target.value as AssetType }))}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
              >
                {ASSET_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {ASSET_TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="mb-1 block text-xs text-gray-400">חדרים</label>
                <input
                  type="number"
                  value={manual.rooms}
                  onChange={(e) => setManual((m) => ({ ...m, rooms: e.target.value }))}
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-400">גודל (מ"ר)</label>
                <input
                  type="number"
                  value={manual.size_sqm}
                  onChange={(e) => setManual((m) => ({ ...m, size_sqm: e.target.value }))}
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-400">מחיר (₪) *</label>
                <input
                  type="number"
                  value={manual.asking_price}
                  onChange={(e) => setManual((m) => ({ ...m, asking_price: e.target.value }))}
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">קישור למקור</label>
              <input
                value={manual.source_url}
                onChange={(e) => setManual((m) => ({ ...m, source_url: e.target.value }))}
                dir="ltr"
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">קישור לתמונה (אופציונלי)</label>
              <input
                value={manual.image_url}
                onChange={(e) => setManual((m) => ({ ...m, image_url: e.target.value }))}
                dir="ltr"
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            {error && <div className="text-sm text-red-600">{error}</div>}
            <button
              disabled={loading}
              className="rounded-full bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
            >
              {loading ? "מוסיף..." : "הוספת הנכס"}
            </button>
            <button type="button" onClick={() => setMode("url")} className="text-xs text-gray-400 underline">
              חזרה לייבוא לפי קישור
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
