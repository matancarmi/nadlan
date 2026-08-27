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
  getSaved: () => request<import("./types").Property[]>("/api/properties/saved"),
  updateInventory: (id: number, payload: { inventory_status?: string; notes?: string }) =>
    request(`/api/properties/${id}/inventory`, { method: "PATCH", body: JSON.stringify(payload) }),
  getGuide: () => request<import("./types").PlanningStage[]>("/api/guide/stages"),
  runIngestion: () => request("/api/ingest/run", { method: "POST" }),
};
