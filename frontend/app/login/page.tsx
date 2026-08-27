"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function Login() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(password);
      router.push("/");
    } catch {
      setError("סיסמה שגויה");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-24 max-w-sm">
      <h1 className="mb-1 text-center text-2xl font-bold">RealEstateTinder</h1>
      <p className="mb-6 text-center text-sm text-gray-400">כלי אישי לאיתור עסקאות נדל"ן</p>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="סיסמה"
          className="rounded-xl border border-gray-200 px-4 py-3"
          autoFocus
        />
        {error && <div className="text-center text-sm text-red-600">{error}</div>}
        <button
          disabled={busy}
          className="rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
        >
          כניסה
        </button>
      </form>
    </div>
  );
}
