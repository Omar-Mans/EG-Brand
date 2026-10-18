"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useBrand } from "@/components/BrandFrame";
import PostCard from "@/components/PostCard";
import { api, waitJob } from "@/lib/api";
import { MARKETS, MONTHS } from "@/lib/catalog";
import type { Job, Post } from "@/lib/types";

type Ym = { y: number; m: number };
const key = (o: Ym) => `${o.y}-${String(o.m).padStart(2, "0")}`;

function nextMonths(n = 6): Ym[] {
  const out: Ym[] = [];
  const d = new Date();
  let y = d.getFullYear(), m = d.getMonth() + 1;
  for (let i = 0; i < n; i++) {
    if (m > 12) { m = 1; y++; }
    out.push({ y, m: m++ });
  }
  return out;
}

const QUICK = [
  "جهزلي محتوى أسبوع وانشر كل يوم في أفضل وقت",
  "جهزلي 3 بوستات عروض للويكند الجاي الساعة 9 بالليل",
  "خطة شهر كامل: بوست كل يومين",
  "وريني حالة البوستات المجدولة والمنشورة",
];

export default function ContentPage() {
  const { brand } = useBrand();
  const [months, setMonths] = useState<Ym[]>(() => nextMonths());
  const [sel, setSel] = useState<Ym>(() => { const m = nextMonths(); return m[1] || m[0]; });
  const k = key(sel);
  const [posts, setPosts] = useState<Post[]>([]);
  const [occasions, setOccasions] = useState<{ day: number; title: string }[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [command, setCommand] = useState("");
  const [agentMsg, setAgentMsg] = useState("");

  const load = useCallback(async () => {
    setPosts(await api<Post[]>(`/api/brands/${brand.id}/posts?month=${k}`));
    setOccasions(await api(`/api/occasions?year=${sel.y}&month=${sel.m}&market=${brand.brief.market}`));
  }, [brand.id, brand.brief.market, k, sel]);
  useEffect(() => { load().catch((e) => setError(e.message)); }, [load]);

  const missingPhotos = useMemo(() => posts.filter((p) => p.status === "draft" && !p.bg_url).length, [posts]);

  if (!brand.dna) return <div className="empty"><p>محتاج هوية البراند الأول.</p><Link className="btn primary" href={`/brands/${brand.id}`}>روح للهوية</Link></div>;

  async function task(label: string, fn: () => Promise<void>) {
    setBusy(true); setError(""); setStatus(label);
    try { await fn(); } catch (e: any) { setError(e.message); } finally { setBusy(false); setStatus(""); }
  }

  const generate = () => task("الـ AI بيخطط الشهر ويصمم البوستات… (ممكن ياخد دقيقة)", async () => {
    await waitJob(await api<Job>(`/api/brands/${brand.id}/calendar`, { body: { year: sel.y, month: sel.m } }));
    await load();
  });

  const photos = () => task(`الـ AI بيعمل صور لـ ${missingPhotos} بوست… (حوالي 10 ثواني لكل صورة)`, async () => {
    const job = await waitJob(await api<Job>(`/api/brands/${brand.id}/images`, { body: { month: k } }), undefined, 600_000);
    await load();
    if (job.result?.failed) setError(`${job.result.failed} صورة ما اتعملتش. جرّب تاني على البوستات دي.`);
  });

  const runAgent = (cmd: string) => task("الـ Agent بيخطط وبيكتب البوستات…", async () => {
    setAgentMsg("");
    const job = await waitJob(await api<Job>(`/api/brands/${brand.id}/agent`, { body: { command: cmd } }));
    setAgentMsg(job.result?.message || "تم.");
    const first: string | undefined = job.result?.months?.[0];
    if (first) {
      const [y, m] = first.split("-").map(Number);
      setMonths((ms) => (ms.some((o) => o.y === y && o.m === m) ? ms : [...ms, { y, m }].sort((a, b) => a.y - b.y || a.m - b.m)));
      if (first === k) await load(); else setSel({ y, m });
    }
  });

  const approved = posts.filter((p) => p.approved).length;
  return (
    <>
      <section className="panel agent">
        <div><p className="eyebrow">الـ Agent</p><h2>قوله عايز إيه، وهو يجهّز ويجدول</h2>
          <p className="muted">بيكتب البوستات ويحدد المواعيد والمنصات. انت بتراجع التصميم وتعتمد، وأول ما تعتمد البوست بيتجدول لوحده.</p></div>
        <div className="quick">{QUICK.map((q) => <button key={q} type="button" className="chip" disabled={busy} onClick={() => { setCommand(q); runAgent(q); }}>{q}</button>)}</div>
        <form className="row" onSubmit={(e) => { e.preventDefault(); if (command.trim().length > 2) runAgent(command); }}>
          <input type="text" value={command} onChange={(e) => setCommand(e.target.value)} placeholder="مثلاً: جهزلي 5 بوستات عن التمويل بالتقسيط وانشرهم كل يوم الساعة 8 مساءً" style={{ flex: 1 }} aria-label="أمر للـ Agent" />
          <button className="btn primary" type="submit" disabled={busy || command.trim().length < 3}>نفّذ</button>
        </form>
        {agentMsg && <p className="note" style={{ whiteSpace: "pre-wrap" }}>{agentMsg}</p>}
      </section>

      <section className="panel">
        <div><h2>كالندر الشهر</h2><p className="muted">بوستات باللهجة المختارة، موزعة على محاور المحتوى ومناسبات الشهر في {MARKETS[brand.brief.market].label}. خطة جديدة بتستبدل المسودات بس.</p></div>
        <div className="row">
          <label className="f" style={{ minWidth: 180 }}>الشهر
            <select value={k} onChange={(e) => { const [y, m] = e.target.value.split("-").map(Number); setSel({ y, m }); }}>
              {months.map((o) => <option key={key(o)} value={key(o)}>{MONTHS[o.m - 1]} {o.y}</option>)}
            </select>
          </label>
          <div className="spacer" />
          {missingPhotos > 0 && <button className="btn" type="button" disabled={busy} onClick={photos}>صور بالـ AI لكل البوستات ({missingPhotos})</button>}
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
          <p className="muted">{posts.length} بوست · {approved} معتمد. ارفع صور منتجك الحقيقية للبوستات المهمة، واعتمد اللي جاهز.</p>
          <div className="grid3">
            {posts.map((p) => <PostCard key={p.id} post={p} dna={brand.dna!} onChange={(np) => setPosts((ps) => ps.map((x) => (x.id === np.id ? np : x)))} />)}
          </div>
          <div className="row"><Link className="btn primary" href={`/brands/${brand.id}/publish`}>كمّل للنشر والجدولة</Link></div>
        </>
      )}
    </>
  );
}
