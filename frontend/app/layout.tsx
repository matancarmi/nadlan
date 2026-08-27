import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "RealEstateTinder",
  description: "כלי אישי לאיתור וסינון עסקאות נדל\"ן בין חדרה לגדרה",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl">
      <body className="min-h-screen">
        <Navbar />
        <main className="mx-auto max-w-2xl px-4 pb-16 pt-4">{children}</main>
      </body>
    </html>
  );
}
