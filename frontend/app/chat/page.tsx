"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { ChatMessage } from "@/lib/types";

const SUGGESTIONS = [
  "לאיזה נכס שמור יש את התזרים החודשי הכי טוב?",
  "מה תשואת השכירות הגולמית הגבוהה ביותר בין הנכסים השמורים?",
  "איזה נכס נמצא במחיר הכי נמוך מתחת לממוצע האזורי?",
];

export default function ChatAdvisor() {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .getChatMessages()
      .then(setMessages)
      .catch((e) => setError(e.message || "שגיאה בטעינת השיחה"));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function send(content: string) {
    if (!content.trim() || sending) return;
    setSending(true);
    setError(null);
    setInput("");
    setMessages((prev) => (prev ? [...prev, { id: -1, role: "user", content, created_at: new Date().toISOString() }] : prev));
    try {
      await api.sendChatMessage(content);
      // Refetch the full history so both the user message and the reply land
      // with their real ids/order, rather than reconstructing them locally.
      setMessages(await api.getChatMessages());
    } catch (e: any) {
      setError(e.message || "שגיאה בשליחת ההודעה");
    } finally {
      setSending(false);
    }
  }

  if (error && messages === null) return <div className="mt-10 text-center text-red-600">{error}</div>;
  if (messages === null) return <div className="mt-10 text-center text-gray-400">טוען...</div>;

  return (
    <div className="flex h-[calc(100vh-140px)] flex-col">
      <div>
        <h1 className="text-xl font-bold">🤖 יועץ השקעות AI</h1>
        <p className="mt-1 text-sm text-gray-500">שאלו על הנכסים השמורים שלכם - תזרים, תשואה, השוואה למחירי שוק.</p>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto rounded-2xl border border-gray-200 bg-white p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-gray-400">
            <div className="text-3xl">💬</div>
            <div className="text-sm">התחילו לשאול, לדוגמה:</div>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full bg-gray-100 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-200"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="flex flex-col gap-3">
          {messages.map((m, i) => (
            <div key={m.id ?? i} className={`flex ${m.role === "user" ? "justify-start" : "justify-end"}`}>
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
                  m.role === "user" ? "bg-gray-100 text-gray-800" : "bg-brand-50 text-brand-800"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {sending && <div className="text-center text-xs text-gray-400">היועץ כותב...</div>}
          <div ref={bottomRef} />
        </div>
      </div>

      {error && <div className="mt-2 text-center text-sm text-red-600">{error}</div>}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="שאלו את היועץ..."
          className="flex-1 rounded-full border border-gray-200 px-4 py-2.5 text-sm"
        />
        <button
          disabled={sending}
          className="rounded-full bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          שליחה
        </button>
      </form>
    </div>
  );
}
