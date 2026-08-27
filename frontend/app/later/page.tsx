"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Property } from "@/lib/types";
import PropertyCard from "@/components/PropertyCard";

export default function SaveForLater() {
  const [items, setItems] = useState<Property[] | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setItems(await api.getLater());
    } catch (e: any) {
      setError(e.message || "שגיאה בטעינה");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function act(id: number, decision: "liked" | "passed") {
    setBusyId(id);
    try {
      await api.decide(id, decision);
      setItems((prev) => (prev ? prev.filter((p) => p.id !== id) : prev));
    } catch (e: any) {
      setError(e.message || "שגיאה בשמירת הבחירה");
    } finally {
      setBusyId(null);
    }
  }

  if (error) return <div className="mt-10 text-center text-red-600">{error}</div>;
  if (items === null) return <div className="mt-10 text-center text-gray-400">טוען...</div>;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-bold">🔖 לשמור להמשך</h1>
        <p className="mt-1 text-sm text-gray-500">נכסים שסימנתם לחזור אליהם. אפשר לדרג אותם עכשיו ❤️ / ❌.</p>
      </div>

      {items.length === 0 && (
        <div className="mt-10 text-center text-gray-400">אין נכסים שמורים להמשך כרגע</div>
      )}

      {items.map((p) => (
        <PropertyCard key={p.id} property={p}>
          <div className="flex gap-2 border-t border-gray-100 px-4 py-3">
            <button
              disabled={busyId === p.id}
              onClick={() => act(p.id, "passed")}
              className="flex-1 rounded-full border-2 border-gray-300 py-2 text-sm font-semibold text-gray-500 active:scale-95"
            >
              ❌ העברה
            </button>
            <button
              disabled={busyId === p.id}
              onClick={() => act(p.id, "liked")}
              className="flex-1 rounded-full bg-brand-600 py-2 text-sm font-semibold text-white active:scale-95"
            >
              ❤️ שמירה
            </button>
          </div>
        </PropertyCard>
      ))}
    </div>
  );
}
