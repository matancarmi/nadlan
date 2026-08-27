"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Property } from "@/lib/types";
import PropertyCard from "@/components/PropertyCard";
import AddListingModal from "@/components/AddListingModal";
import { useFinanceSettings } from "@/lib/useFinanceSettings";

export default function DiscoveryFeed() {
  const [queue, setQueue] = useState<Property[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const financeSettings = useFinanceSettings();

  function handleAdded(property: Property) {
    // New manually/URL-added listings go straight to the front of the
    // discovery feed, as if it were just fetched.
    setQueue((q) => [property, ...(q || []).filter((p) => p.id !== property.id)]);
    setShowAddModal(false);
  }

  async function load() {
    try {
      const feed = await api.getFeed(20);
      setQueue(feed);
    } catch (e: any) {
      setError(e.message || "שגיאה בטעינת הנכסים");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function act(decision: "liked" | "passed") {
    if (!queue || queue.length === 0 || busy) return;
    setBusy(true);
    const current = queue[0];
    try {
      await api.decide(current.id, decision);
      setQueue((q) => (q ? q.slice(1) : q));
    } catch (e: any) {
      setError(e.message || "שגיאה בשמירת הבחירה");
    } finally {
      setBusy(false);
    }
  }

  async function pushToBack() {
    if (!queue || queue.length === 0 || busy) return;
    setBusy(true);
    const current = queue[0];
    try {
      // Not a final decision - the property stays "pending" on the server
      // (also bookmarked so it's findable on /later). Locally, move it to
      // the very end of the current queue instead of removing it: it keeps
      // cycling through the same discovery feed, just deprioritized behind
      // everything not yet viewed this session. Use the server's response
      // (not the stale local `current`) so the 🔖 badge reflects the update.
      const updated = await api.saveForLater(current.id);
      setQueue((q) => (q ? [...q.slice(1), updated] : q));
    } catch (e: any) {
      setError(e.message || "שגיאה בדחיפה לסוף התור");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return <div className="mt-10 text-center text-red-600">{error}</div>;
  }

  if (queue === null) {
    return <div className="mt-10 text-center text-gray-400">טוען נכסים...</div>;
  }

  if (queue.length === 0) {
    return (
      <div className="mt-16 flex flex-col items-center gap-4 text-center text-gray-500">
        <div className="mb-2 text-4xl">🎉</div>
        <div className="font-medium">אין עוד נכסים חדשים כרגע</div>
        <div className="mt-1 text-sm">האיסוף הבא ירוץ אוטומטית מחר, או לחצו לרענון</div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white"
          >
            רענון
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="rounded-full border-2 border-brand-600 px-4 py-2 text-sm font-medium text-brand-700"
          >
            ➕ הוספת נכס לפי קישור
          </button>
        </div>
        {showAddModal && <AddListingModal onClose={() => setShowAddModal(false)} onAdded={handleAdded} />}
      </div>
    );
  }

  const current = queue[0];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-400">{queue.length} נכסים בתור</div>
        <button onClick={() => setShowAddModal(true)} className="text-xs font-medium text-brand-600 underline">
          ➕ הוספת נכס לפי קישור
        </button>
      </div>
      <PropertyCard property={current} financeSettings={financeSettings} />
      {showAddModal && <AddListingModal onClose={() => setShowAddModal(false)} onAdded={handleAdded} />}
      <div className="fixed inset-x-0 bottom-0 z-10 mx-auto flex max-w-2xl gap-2 border-t border-gray-200 bg-white/95 px-4 py-3 backdrop-blur">
        <button
          disabled={busy}
          onClick={() => act("passed")}
          className="flex-1 rounded-full border-2 border-gray-300 py-3 text-base font-semibold text-gray-500 active:scale-95"
        >
          ❌ העברה
        </button>
        <button
          disabled={busy}
          onClick={pushToBack}
          className="flex-1 rounded-full border-2 border-amber-300 py-3 text-base font-semibold text-amber-600 active:scale-95"
        >
          🔖 להמשך
        </button>
        <button
          disabled={busy}
          onClick={() => act("liked")}
          className="flex-1 rounded-full bg-brand-600 py-3 text-base font-semibold text-white active:scale-95"
        >
          ❤️ שמירה
        </button>
      </div>
      <div className="h-16" />
    </div>
  );
}
