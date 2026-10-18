"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useBrand } from "@/components/BrandFrame";
import PostCard from "@/components/PostCard";
import { api, waitJob } from "@/lib/api";
import { MARKETS, MONTHS } from "@/lib/catalog";
import type { Job, Post } from "@/lib/types";

function nextMonths(n = 6) {
  const out: { y: number; m: number }[] = [];
  const d = new Date();
  let y = d.getFullYear(), m = d.getMonth() + 2;
  for (let i = 0; i < n; i++) {
    if (m > 12) { m = 1; y++; }
    out.push({ y, m: m++ });
  }
  return out;
}

export default function ContentPage() {
  const { brand } = useBrand();
  const months = useMemo(() => nextMonths(), []);
  const [sel, setSel] = useState(months[0]);
  const key = `${sel.y}-${String(sel.m).padStart(2, "0")}`;
  const [posts, setPosts] = useState<Post[]>([]);
  const [occasions, setOccasions] = useState<{ day: number; title: string }[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setPosts(await api<Post[]>(`/api/brands/${brand.id}/posts?month=${key}`));
    setOccasions(await api(`/api/occasions?year=${sel.y}&month=${sel.m}&market=${brand.brief.market}`));
  }, [brand.id, brand.brief.market, key, sel]);
  useEffect(() => { load().catch((e) => setError(e.message)); }, [load]);

  if (!brand.dna) return <div className="empty"><p>محتاج هوية البراند الأول.</p><Link className="btn primary" href={`/brands/${brand.id}`}>روح للهوية</Link></div>;

  async function generate() {
    setBusy(true); setError(""); setStatus("الـ AI بيخطط الشهر ويكتب البوستات… (ممكن ياخد دقيقة)");
    try {
      await waitJob(await api<Job>(`/api/brands/${brand.id}/calendar`, { body: { year: sel.y, month: sel.m } }));
      await load();
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); setStatus(""); }
  }

  const approved = posts.filter((p) => p.approved).length;
  return (
    <>
      <section className="panel">
        <div><h2>كالندر الشهر</h2><p className="muted">بوستات باللهجة المختارة، موزعة على محاور المحتوى ومناسبات الشهر في {MARKETS[brand.brief.market].label}. خطة جديدة بتستبدل المسودات بس، والمجدول والمنشور بيفضلوا زي ما هم.</p></div>
        <div className="row">
          <label className="f" style={{ minWidth: 180 }}>الشهر
            <select value={key} onChange={(e) => { const [y, m] = e.target.value.split("-").map(Number); setSel({ y, m }); }}>
              {months.map((o) => <option key={`${o.y}-${o.m}`} value={`${o.y}-${String(o.m).padStart(2, "0")}`}>{MONTHS[o.m - 1]} {o.y}</option>)}
            </select>
          </label>
          <div className="spacer" />
          <button className="btn primary" type="button" disabled={busy} onClick={generate}>{posts.length ? "ولّد خطة جديدة" : "ولّد خطة الشهر"}</button>
        </div>
        <div className="row small">
          {occasions.length ? occasions.map((o) => <span key={o.title} className="tag gold">{o.day} {MONTHS[sel.m - 1]} · {o.title}</span>)
            : <span className="muted">مفيش مناسبات كبيرة الشهر ده.</span>}
        </div>
        {(status || error) && <p className={`status ${error ? "err" : ""}`} aria-live="polite">{error || status}</p>}
      </section>
      {posts.length > 0 && (
        <>
          <p className="muted">{posts.length} بوست · {approved} معتمد. اعتماد البوست بيرفع تصميمه عشان يبقى جاهز للنشر.</p>
          <div className="grid3">
            {posts.map((p) => <PostCard key={p.id} post={p} dna={brand.dna!} onChange={(np) => setPosts((ps) => ps.map((x) => (x.id === np.id ? np : x)))} />)}
          </div>
          <div className="row"><Link className="btn primary" href={`/brands/${brand.id}/publish`}>كمّل للنشر والجدولة</Link></div>
        </>
      )}
    </>
  );
}
