"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PlanningStage } from "@/lib/types";

const CATEGORY_LABELS: Record<string, string> = {
  general: "שלבי תכנון כלליים",
  pinui_binui: "פינוי בינוי",
  presale: "פרויקטים חדשים",
};

export default function Guide() {
  const [stages, setStages] = useState<PlanningStage[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    api.getGuide().then(setStages);
  }, []);

  if (stages === null) return <div className="mt-10 text-center text-gray-400">טוען...</div>;

  const grouped = stages.reduce<Record<string, PlanningStage[]>>((acc, s) => {
    (acc[s.category] ||= []).push(s);
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-bold">מדריך שלבי תכנון ובנייה</h1>
        <p className="mt-1 text-sm text-gray-500">
          הסבר פשוט למונחים שתפגשו בעת בחינת פרויקטים חדשים ופינוי-בינוי.
        </p>
      </div>

      {Object.entries(grouped).map(([category, list]) => (
        <div key={category}>
          <h2 className="mb-2 text-sm font-semibold text-gray-400">{CATEGORY_LABELS[category] || category}</h2>
          <div className="flex flex-col gap-2">
            {list.map((s) => (
              <div key={s.key} className="overflow-hidden rounded-xl border border-gray-200 bg-white">
                <button
                  onClick={() => setOpen(open === s.key ? null : s.key)}
                  className="flex w-full items-center justify-between px-4 py-3 text-right"
                >
                  <span className="font-medium">{s.title}</span>
                  <span className="text-gray-400">{open === s.key ? "−" : "+"}</span>
                </button>
                <div className="px-4 pb-2 text-sm text-gray-500">{s.short_description}</div>
                {open === s.key && (
                  <div className="border-t border-gray-100 bg-gray-50 px-4 py-3 text-sm leading-relaxed text-gray-700">
                    {s.long_description}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
