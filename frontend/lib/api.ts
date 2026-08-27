// Relative: requests go to the frontend's own origin, which next.config.js
// rewrites to the backend server-side. This keeps everything same-origin
// from the browser's perspective, so the session cookie is first-party.
const API_BASE = "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (res.status === 401) {
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError(401, "Not authenticated");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  login: (password: string) => request<{ ok: boolean }>("/api/auth/login", { method: "POST", body: JSON.stringify({ password }) }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  getFeed: (limit = 20) => request<import("./types").Property[]>(`/api/properties/feed?limit=${limit}`),
  decide: (id: number, decision: "liked" | "passed") =>
    request(`/api/properties/${id}/decision`, { method: "POST", body: JSON.stringify({ decision }) }),
  saveForLater: (id: number, saved_for_later = true) =>
    request(`/api/properties/${id}/save-for-later`, { method: "POST", body: JSON.stringify({ saved_for_later }) }),
  getSaved: () => request<import("./types").Property[]>("/api/properties/saved"),
  getLater: () => request<import("./types").Property[]>("/api/properties/later"),
  updateInventory: (id: number, payload: { inventory_status?: string; notes?: string }) =>
    request(`/api/properties/${id}/inventory`, { method: "PATCH", body: JSON.stringify(payload) }),
  getGuide: () => request<import("./types").PlanningStage[]>("/api/guide/stages"),
  runIngestion: () => request("/api/ingest/run", { method: "POST" }),
  getAreaSettings: () => request<import("./types").SearchAreaSettings>("/api/settings/areas"),
  getAvailableCities: () => request<{ cities: string[] }>("/api/settings/areas/available-cities"),
  updateAreaSettings: (payload: {
    mode: "cities" | "radius";
    cities?: string[];
    address?: string;
    radius_km?: number;
  }) => request<import("./types").SearchAreaSettings>("/api/settings/areas", { method: "PUT", body: JSON.stringify(payload) }),
  updatePremiumCities: (premium_cities: string[]) =>
    request<import("./types").SearchAreaSettings>("/api/settings/areas/premium-cities", {
      method: "PUT",
      body: JSON.stringify({ premium_cities }),
    }),
  getFinanceSettings: () => request<import("./types").FinanceSettings>("/api/settings/finance"),
  updateFinanceSettings: (payload: import("./types").FinanceSettings) =>
    request<import("./types").FinanceSettings>("/api/settings/finance", { method: "PUT", body: JSON.stringify(payload) }),
  getChatMessages: () => request<import("./types").ChatMessage[]>("/api/chat/messages"),
  sendChatMessage: (content: string) =>
    request<import("./types").ChatMessage>("/api/chat/messages", { method: "POST", body: JSON.stringify({ content }) }),
};
