"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AreaMode } from "@/lib/types";

export default function AreasSettings() {
  const [mode, setMode] = useState<AreaMode>("cities");
  const [allCities, setAllCities] = useState<string[]>([]);
  const [selectedCities, setSelectedCities] = useState<string[]>([]);
  const [address, setAddress] = useState("");
  const [radiusKm, setRadiusKm] = useState(20);
  const [resolvedCities, setResolvedCities] = useState<string[] | null>(null);
  const [geocodeFailed, setGeocodeFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getAreaSettings(), api.getAvailableCities()])
      .then(([settings, { cities }]) => {
        setAllCities(cities);
        setMode(settings.mode);
        setSelectedCities(settings.cities || []);
        setAddress(settings.address || "");
        setRadiusKm(settings.radius_km || 20);
        setResolvedCities(settings.resolved_cities);
        setGeocodeFailed(settings.mode === "radius" && !!settings.address && settings.center_lat == null);
      })
      .catch((e) => setError(e.message || "שגיאה בטעינת ההגדרות"))
      .finally(() => setLoading(false));
  }, []);

  function toggleCity(city: string) {
    setSelectedCities((prev) => (prev.includes(city) ? prev.filter((c) => c !== city) : [...prev, city]));
  }

  async function save() {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const result = await api.updateAreaSettings(
        mode === "cities"
          ? { mode: "cities", cities: selectedCities }
          : { mode: "radius", address, radius_km: radiusKm }
      );
      setResolvedCities(result.resolved_cities);
      setGeocodeFailed(mode === "radius" && !!address && result.center_lat == null);
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
        <h1 className="text-xl font-bold">אזורי חיפוש</h1>
        <p className="mt-1 text-sm text-gray-500">
          בחרו ערים ספציפיות, או הזינו כתובת ורדיוס לחיפוש אוטומטי של כל הערים סביבה.
          ההגדרה חלה על סבב האיסוף היומי הבא.
        </p>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => setMode("cities")}
          className={`flex-1 rounded-xl py-2 text-sm font-medium ${mode === "cities" ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-600"}`}
        >
          בחירת ערים
        </button>
        <button
          onClick={() => setMode("radius")}
          className={`flex-1 rounded-xl py-2 text-sm font-medium ${mode === "radius" ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-600"}`}
        >
          כתובת + רדיוס
        </button>
      </div>

      {mode === "cities" && (
        <div className="grid grid-cols-2 gap-2">
          {allCities.map((city) => (
            <label
              key={city}
              className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                selectedCities.includes(city) ? "border-brand-600 bg-brand-50" : "border-gray-200"
              }`}
            >
              <input
                type="checkbox"
                checked={selectedCities.includes(city)}
                onChange={() => toggleCity(city)}
                className="accent-brand-600"
              />
              {city}
            </label>
          ))}
        </div>
      )}

      {mode === "radius" && (
        <div className="flex flex-col gap-3">
          <div>
            <label className="mb-1 block text-xs text-gray-400">כתובת מרכזית</label>
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="לדוגמה: רוטשילד 1, תל אביב"
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-400">רדיוס חיפוש (ק"מ): {radiusKm}</label>
            <input
              type="range"
              min={5}
              max={60}
              step={5}
              value={radiusKm}
              onChange={(e) => setRadiusKm(Number(e.target.value))}
              className="w-full accent-brand-600"
            />
          </div>
          {geocodeFailed && (
            <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
              ⚠️ לא הצלחנו לאתר את הכתובת. בינתיים ממשיכים עם רשימת הערים הכללית של האפליקציה.
            </div>
          )}
          {resolvedCities && resolvedCities.length > 0 && (
            <div className="rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700">
              נמצאו {resolvedCities.length} ערים ברדיוס: {resolvedCities.join(", ")}
            </div>
          )}
        </div>
      )}

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
