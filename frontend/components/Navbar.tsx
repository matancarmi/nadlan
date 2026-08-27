"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";

const links = [
  { href: "/", label: "🏠 גילוי" },
  { href: "/saved", label: "❤️ שמורים" },
  { href: "/later", label: "🔖 להמשך" },
  { href: "/guide", label: "📖 מדריך תכנוני" },
  { href: "/areas", label: "📍 אזורי חיפוש" },
  { href: "/finance", label: "💰 מימון" },
  { href: "/chat", label: "🤖 יועץ AI" },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();

  if (pathname === "/login") return null;

  return (
    <nav className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-white/90 px-4 py-3 backdrop-blur">
      <div className="flex flex-wrap gap-1">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium transition ${
              pathname === l.href ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {l.label}
          </Link>
        ))}
      </div>
      <button
        onClick={async () => {
          await api.logout();
          router.push("/login");
        }}
        className="text-xs text-gray-400 hover:text-gray-600"
      >
        התנתקות
      </button>
    </nav>
  );
}
