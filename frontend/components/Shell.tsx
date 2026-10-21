"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { api, ApiError, getToken, setToken } from "@/lib/api";
import type { Me } from "@/lib/types";
import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";

const MeCtx = createContext<Me | null>(null);
export const useMe = () => useContext(MeCtx);

export default function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [health, setHealth] = useState<{ ai: string; social: string } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<Me>("/api/auth/me").then(setMe).catch((e: ApiError) => {
      if (e.status === 401) {
        setToken(null);
        router.replace("/login");
      } else setError(e.message);
    });
    api("/api/health").then(setHealth).catch(() => {});
  }, [router]);

  if (!me) {
    return (
      <div className="wrap" style={{ padding: 24 }}>
        {error
          ? <div className="empty"><p className="err">{error}</p><button className="btn" type="button" onClick={() => window.location.reload()}>جرّب تاني</button></div>
          : <div style={{ display: "grid", gap: 16 }} aria-busy="true" aria-label="بنحمّل"><div className="skeleton" style={{ height: 48 }} /><div className="skeleton" style={{ height: 180 }} /><div className="skeleton" style={{ height: 180 }} /></div>}
      </div>
    );
  }

  const nav = [
    ["/brands", "البراندات"],
    ["/settings", "الحسابات"],
    ["/usage", "التكلفة"],
  ];
  return (
    <MeCtx.Provider value={me}>
      <div className="wrap">
        <header className="top">
          <Link href="/brands" aria-label="EG Brand" style={{ textDecoration: "none" }}><Logo size={30} /></Link>
          <nav className="nav">
            {nav.map(([href, label]) => (
              <Link key={href} href={href} className={path.startsWith(href) ? "on" : ""}>{label}</Link>
            ))}
          </nav>
          <div className="spacer" />
          {health && (
            <span className={`pill ${health.ai === "live" ? "ok" : "warn"}`} title="لو مكتوب تجريبي، حط مفاتيح الـ AI في ملف .env">
              <span className="dot" />AI {health.ai === "live" ? "حقيقي" : "تجريبي"} · نشر {health.social === "live" ? "حقيقي" : "تجريبي"}
            </span>
          )}
          <span className="small muted">{me.company.name}</span>
          <ThemeToggle />
          <button className="btn sm" type="button" onClick={() => { setToken(null); router.replace("/login"); }}>خروج</button>
        </header>
        <main>{children}</main>
      </div>
    </MeCtx.Provider>
  );
}
