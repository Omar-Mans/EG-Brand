"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import BriefForm, { EMPTY_BRIEF } from "@/components/BriefForm";
import { api } from "@/lib/api";
import { MARKETS } from "@/lib/catalog";
import type { Brand, Brief } from "@/lib/types";

export default function BrandsPage() {
  const router = useRouter();
  const [brands, setBrands] = useState<Brand[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Brand[]>("/api/brands").then((b) => { setBrands(b); setCreating(b.length === 0); }).catch((e) => setError(e.message));
  }, []);

  async function create(brief: Brief) {
    setBusy(true);
    setError("");
    try {
      setStatus("بنحفظ المشروع…");
      const brand = await api<Brand>("/api/brands", { body: brief });
      router.push(`/brands/${brand.id}/discovery`);  // study the business first, then the strategy builds everything
    } catch (e: any) {
      setError(e.message);
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div><p className="eyebrow">البراندات</p><h1>براندات شركتك</h1></div>
        {!creating && <button className="btn primary" type="button" onClick={() => setCreating(true)}>+ براند جديد</button>}
      </div>
      {creating && (
        <>
          <div><h2>احكيلنا عن المشروع</h2><p className="muted">اكتب الفكرة بجملة أو اتنين. بعدها هنسألك أسئلة زي اللي بتسألها أي وكالة تسويق، عشان الخطة تطلع مفصّلة على مشروعك.</p></div>
          <BriefForm initial={EMPTY_BRIEF} submitLabel="ابدأ دراسة المشروع" busy={busy} onSubmit={create} />
          {status && <p className="status" aria-live="polite">{status}</p>}
        </>
      )}
      {error && <p className="status err">{error}</p>}
      {brands && brands.length > 0 && (
        <div className="grid3">
          {brands.map((b) => {
            const p = b.dna?.palette || [];
            return (
              <Link key={b.id} href={b.dna ? `/brands/${b.id}` : `/brands/${b.id}/discovery`} className="card" style={{ textDecoration: "none", color: "inherit" }}>
                <div className="row" style={{ gap: 4 }}>{p.slice(0, 5).map((c) => <span key={c.role} style={{ width: 22, height: 22, borderRadius: 6, background: c.hex }} />)}</div>
                <h3>{b.name || "براند جديد"}</h3>
                <p className="small muted">{b.brief.idea.slice(0, 90)}</p>
                <span className="tag" style={{ alignSelf: "flex-start" }}>{MARKETS[b.brief.market]?.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
