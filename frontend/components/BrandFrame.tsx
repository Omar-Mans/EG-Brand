"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Brand } from "@/lib/types";

type Ctx = { brand: Brand; reload: () => Promise<void>; setBrand: (b: Brand) => void };
const BrandCtx = createContext<Ctx | null>(null);
export const useBrand = () => useContext(BrandCtx)!;

export default function BrandFrame({ children }: { children: React.ReactNode }) {
  const { id } = useParams<{ id: string }>();
  const path = usePathname();
  const [brand, setBrand] = useState<Brand | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    try {
      setBrand(await api<Brand>(`/api/brands/${id}`));
    } catch (e: any) {
      setError(e.message);
    }
  }, [id]);
  useEffect(() => { reload(); }, [reload]);

  if (error) return <p className="err">{error}</p>;
  if (!brand) {
    return (
      <div style={{ display: "grid", gap: 16 }} aria-busy="true" aria-label="بنحمّل البراند">
        <div className="skeleton" style={{ height: 40, width: "40%" }} /><div className="skeleton" style={{ height: 44 }} />
        <div className="skeleton" style={{ height: 260 }} />
      </div>
    );
  }

  const tabs = [
    ["/discovery", "الدراسة"],
    ["/strategy", "الاستراتيجية"],
    ["", "الهوية"],
    ["/content", "المحتوى"],
    ["/publish", "النشر"],
    ["/ads", "الإعلانات"],
  ];
  const base = `/brands/${id}`;
  return (
    <BrandCtx.Provider value={{ brand, reload, setBrand }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>{brand.name || "براند جديد"}</h1>
        <Link className="btn sm noprint" href="/brands">كل البراندات</Link>
      </div>
      <nav className="tabs">
        {tabs.map(([suffix, label], i) => (
          <Link key={suffix} href={base + suffix} className={`tab ${path === base + suffix ? "on" : ""}`}>
            <span className="n">{i + 1}</span>{label}
          </Link>
        ))}
      </nav>
      {children}
    </BrandCtx.Provider>
  );
}
