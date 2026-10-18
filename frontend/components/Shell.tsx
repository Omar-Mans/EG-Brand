"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";
import type { Me } from "@/lib/types";

const MeCtx = createContext<Me | null>(null);
export const useMe = () => useContext(MeCtx);

export default function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [health, setHealth] = useState<{ ai: string; social: string } | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<Me>("/api/auth/me").then(setMe).catch(() => {});
    api("/api/health").then(setHealth).catch(() => {});
  }, [router]);

  if (!me) return <div className="wrap"><p className="muted" style={{ padding: 24 }}>بنحمّل…</p></div>;

  const nav = [
    ["/brands", "البراندات"],
    ["/settings", "الحسابات"],
    ["/usage", "التكلفة"],
  ];
  return (
    <MeCtx.Provider value={me}>
      <div className="wrap">
        <header className="top">
          <Link href="/brands" className="mark">EG <b>Brand</b></Link>
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
          <button className="btn sm" type="button" onClick={() => { setToken(null); router.replace("/login"); }}>خروج</button>
        </header>
        <main>{children}</main>
      </div>
    </MeCtx.Provider>
  );
}
