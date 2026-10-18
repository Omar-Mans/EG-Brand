"use client";

import { useCallback, useEffect, useState } from "react";
import { useBrand } from "@/components/BrandFrame";
import { api, waitJob } from "@/lib/api";
import { AD_OBJECTIVES, AD_PLATFORMS, MARKETS } from "@/lib/catalog";
import type { AdPlan, Campaign, Job } from "@/lib/types";

const fmt = (n: number) => Math.round(n).toLocaleString("en-US");
const CAMPAIGN_STATUS: Record<string, [string, string]> = {
  draft: ["مسودة", ""], ready: ["جاهزة (من غير حساب إعلانات)", "gold"],
  created_paused: ["اتعملت في Meta وموقوفة", "ok"], failed: ["فشلت", "bad"],
};

export default function AdsPage() {
  const { brand } = useBrand();
  const cur = MARKETS[brand.brief.market].cur;
  const [form, setForm] = useState({ objective: AD_OBJECTIVES[0], budget: brand.brief.market === "SA" ? 1500 : 5000, days: 14, platforms: [AD_PLATFORMS[0]] });
  const [plan, setPlan] = useState<AdPlan | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [insights, setInsights] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setCampaigns((await api<Campaign[]>("/api/ads/campaigns")).filter((c) => c.brand_id === brand.id));
  }, [brand.id]);
  useEffect(() => { load().catch((e) => setError(e.message)); }, [load]);

  async function generate() {
    setBusy(true); setError("");
    try {
      const job = await waitJob(await api<Job>(`/api/brands/${brand.id}/ads/plan`, { body: form }));
      setPlan(job.result.plan);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function save() {
    try { await api("/api/ads/campaigns", { body: { brand_id: brand.id, plan } }); setPlan(null); await load(); }
    catch (e: any) { setError(e.message); }
  }
  async function launch(id: string) {
    try { await api(`/api/ads/campaigns/${id}/launch`, { method: "POST" }); await load(); }
    catch (e: any) { setError(e.message); }
  }
  async function loadInsights(id: string) {
    try { setInsights({ ...insights, [id]: await api(`/api/ads/campaigns/${id}/insights`) }); }
    catch (e: any) { setError(e.message); }
  }

  return (
    <>
      <section className="panel">
        <div><h2>خطط حملتك</h2><p className="muted">حدد الهدف والميزانية، والـ AI يقترح الجمهور وتوزيع الميزانية ونصوص الإعلانات.</p></div>
        <div className="grid3">
          <label className="f">الهدف<select value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })}>{AD_OBJECTIVES.map((o) => <option key={o}>{o}</option>)}</select></label>
          <label className="f">الميزانية الكلية ({cur})<input type="number" min={100} step={50} value={form.budget} onChange={(e) => setForm({ ...form, budget: Number(e.target.value) })} /></label>
          <label className="f">المدة (يوم)<input type="number" min={1} max={90} value={form.days} onChange={(e) => setForm({ ...form, days: Number(e.target.value) })} /></label>
        </div>
        <div className="f"><span>المنصات</span>
          <div className="row">{AD_PLATFORMS.map((x) => (
            <button key={x} type="button" className="chip" aria-pressed={form.platforms.includes(x)}
              onClick={() => setForm({ ...form, platforms: form.platforms.includes(x) ? form.platforms.filter((p) => p !== x) : [...form.platforms, x] })}>{x}</button>
          ))}</div>
        </div>
        <div className="row">
          <button className="btn primary" type="button" disabled={busy || !form.platforms.length || form.budget <= 0} onClick={generate}>{busy ? "الـ AI بيخطط…" : "اقترح الحملة"}</button>
          <span className="small muted">الميزانية اليومية: {fmt(form.budget / Math.max(1, form.days))} {cur}</span>
        </div>
        {error && <p className="status err">{error}</p>}
      </section>
      {plan && (
        <>
          <div className="grid2">
            <section className="panel"><h3>الجمهور المقترح</h3>
              <p><span className="muted small">السن: </span>{plan.audience.age} · <span className="muted small">النوع: </span>{plan.audience.gender}</p>
              <p><span className="muted small">الأماكن: </span>{plan.audience.locations.join("، ")}</p>
              <div className="row">{plan.audience.interests.map((x) => <span key={x} className="tag">{x}</span>)}</div>
            </section>
            <section className="panel"><h3>توزيع الميزانية</h3>
              <div className="tbl"><table>
                <thead><tr><th>المنصة</th><th className="num">النسبة</th><th className="num">المبلغ ({plan.currency})</th><th className="num">في اليوم</th></tr></thead>
                <tbody>{plan.split.map((x) => (
                  <tr key={x.platform}><td>{x.platform}<br /><span className="small muted">{x.why}</span></td><td className="num">{Math.round(x.pct)}٪</td><td className="num">{fmt(x.amount)}</td><td className="num">{fmt(x.daily)}</td></tr>
                ))}</tbody>
              </table></div>
            </section>
          </div>
          <section className="panel"><h3>نصوص الإعلانات</h3>
            <div className="grid3">{plan.ads.map((a, i) => (
              <div key={i} className="card"><span className="tag" style={{ alignSelf: "flex-start" }}>{a.platform}</span><b>{a.headline}</b><p className="small">{a.primary_text}</p><span className="tag gold" style={{ alignSelf: "flex-start" }}>{a.cta}</span></div>
            ))}</div>
          </section>
          <div className="grid2">
            <section className="panel"><h3>تابع الأرقام دي</h3><ul className="clean">{plan.kpis.map((x) => <li key={x}>{x}</li>)}</ul></section>
            <section className="panel"><h3>نصايح</h3><ul className="clean">{plan.tips.map((x) => <li key={x}>{x}</li>)}</ul></section>
          </div>
          <div className="row"><button className="btn primary" type="button" onClick={save}>احفظ الحملة كمسودة</button></div>
        </>
      )}
      {campaigns.length > 0 && (
        <section className="panel"><h3>الحملات</h3>
          <div className="tbl"><table>
            <thead><tr><th>الحملة</th><th className="num">الميزانية</th><th className="num">المدة</th><th>الحالة</th><th /></tr></thead>
            <tbody>{campaigns.map((c) => {
              const [label, cls] = CAMPAIGN_STATUS[c.status] || [c.status, ""];
              const ins = insights[c.id];
              return (
                <tr key={c.id}>
                  <td>{c.objective}<br /><span className="small muted">{c.platforms.join("، ")}</span>{c.error && <p className="small err">{c.error}</p>}
                    {ins && (ins.available ? <p className="small">مشاهدات {ins.data.impressions ?? 0} · نقرات {ins.data.clicks ?? 0} · صرف {ins.data.spend ?? 0}</p> : <p className="small muted">مفيش أرقام لسه</p>)}</td>
                  <td className="num">{fmt(c.budget)} {c.currency}</td>
                  <td className="num">{c.days} يوم</td>
                  <td><span className={`tag ${cls}`}>{label}</span></td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {(c.status === "draft" || c.status === "failed") && <button className="btn sm" type="button" onClick={() => launch(c.id)}>أنشئها في Meta (موقوفة)</button>}
                    {c.status === "created_paused" && <button className="btn sm" type="button" onClick={() => loadInsights(c.id)}>النتايج</button>}
                  </td>
                </tr>
              );
            })}</tbody>
          </table></div>
          <p className="note">الحملة بتتعمل في Meta Ads Manager وهي <b>موقوفة</b>، فمفيش صرف لحد ما صاحب الحساب يشغلها بنفسه. ده محتاج ربط حساب إعلانات Meta من صفحة الحسابات بصلاحية ads_management.</p>
        </section>
      )}
    </>
  );
}
