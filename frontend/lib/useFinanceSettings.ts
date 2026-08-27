"use client";

import { useEffect, useState } from "react";
import { api } from "./api";
import { FinanceSettings } from "./types";

// Module-level cache: several pages render property cards that all need the
// same finance settings, so fetch once per page load rather than once per card.
let cache: FinanceSettings | null = null;
let inFlight: Promise<FinanceSettings> | null = null;

export function useFinanceSettings(): FinanceSettings | null {
  const [settings, setSettings] = useState<FinanceSettings | null>(cache);

  useEffect(() => {
    if (cache) return;
    if (!inFlight) inFlight = api.getFinanceSettings();
    inFlight
      .then((s) => {
        cache = s;
        setSettings(s);
      })
      .catch(() => {
        // Leave settings null - PropertyCard simply omits the interactive
        // mortgage widget (it still shows the server-computed cash flow).
      });
  }, []);

  return settings;
}

export function invalidateFinanceSettingsCache() {
  cache = null;
  inFlight = null;
}
