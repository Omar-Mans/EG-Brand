"use client";

import { useCallback, useEffect, useState } from "react";
import { useMe } from "@/components/Shell";
import { api } from "@/lib/api";
import { FEATURE_LABEL } from "@/lib/catalog";

type Summary = { company_name: string; spent_usd: number; budget_usd: number; calls: number;
  by_feature: { feature: string; calls: number; input_tokens: number; output_tokens: number; cost_usd: number }[] };
type Event = { id: string; feature: string; model: string; input_tokens: number; output_tokens: number; cost_usd: number; latency_ms: number; ok: boolean; created_at: string };
type Economics = {
  per_call: Record<string, { input_tokens: number; output_tokens: number; cost_usd: number; measured_calls: number }>;
  setup_cost_usd: number; monthly_ai_usd: number; monthly_images_usd: number; monthly_cost_usd: number;
  markets: { market: string; price: number; currency: string; price_usd: number; payment_fee_usd: number; ai_cost_usd: number; gross_profit_usd: number; gross_margin_pct: number }[];
};

const usd = (n: number) => "$" + (n > 0 && n < 0.01 ? n.toFixed(4) : n.toFixed(n < 1 ? 3 : 2));
const num = (n: number) => Math.round(n).toLocaleString("en-US");
const ASSUMPTIONS: [string, string][] = [
  ["in_per_m", "سعر 1M توكن داخل ($)"], ["out_per_m", "سعر 1M توكن خارج ($)"], ["image_cost", "تكلفة الصورة ($)"],
  ["images_per_month", "صور مولّدة في الشهر"], ["regens_per_month", "إعادات صياغة في الشهر"], ["ads_plans_per_month", "خطط إعلانية في الشهر"],
  ["price_egp", "الاشتراك في مصر (جنيه)"], ["price_sar", "الاشتراك في السعودية (ريال)"], ["fee_pct", "رسوم الدفع (٪)"],
  ["fx_egp", "جنيه لكل دولار"], ["fx_sar", "ريال لكل دولار"],
];

export default function UsagePage() {
  const me = useMe();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [all, setAll] = useState<Summary[] | null>(null);
  const [inputs, setInputs] = useState<Record<string, number>>({
    in_per_m: 3, out_per_m: 15, image_cost: 0.04, images_per_month: 0, regens_per_month: 20, ads_plans_per_month: 1,
    price_egp: 225, price_sar: 74, fee_pct: 3, fx_egp: 48, fx_sar: 3.75,
  });
  const [econ, setEcon] = useState<Economics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<Summary>("/api/usage/summary"), api<Event[]>("/api/usage/events")])
      .then(([s, e]) => { setSummary(s); setEvents(e); }).catch((e) => setError(e.message));
    if (me?.is_admin) api<Summary[]>("/api/usage/admin/companies").then(setAll).catch(() => {});
  }, [me]);
  const calc = useCallback(() => { api<Economics>("/api/usage/economics", { body: inputs }).then(setEcon).catch((e) => setError(e.message)); }, [inputs]);
  useEffect(() => { calc(); }, [calc]);

  return (
    <>
      <div><p className="eyebrow">التكلفة</p><h1>تكلفة الـ AI وهامش الربح</h1>
        <p className="muted">كل طلب AI بيتسجل على الشركة بعدد التوكنز الحقيقي وتكلفته من المزود. لما الـ AI يكون في الوضع التجريبي، التكلفة صفر والتوكنز تقديرية.</p></div>
      {error && <p className="status err">{error}</p>}
      {summary && (
        <section className="panel"><h3>الشهر ده · {summary.company_name}</h3>
          <div className="kpi">
            <div><span className="small muted">اتصرف على الـ AI</span><b>{usd(summary.spent_usd)}</b><span className="small muted">من ميزانية {usd(summary.budget_usd)}</span></div>
            <div><span className="small muted">عدد الطلبات</span><b>{num(summary.calls)}</b></div>
          </div>
          {summary.by_feature.length > 0 && (
            <div className="tbl"><table>
              <thead><tr><th>العملية</th><th className="num">طلبات</th><th className="num">توكنز داخل</th><th className="num">توكنز خارج</th><th className="num">التكلفة</th></tr></thead>
              <tbody>{summary.by_feature.map((f) => (
                <tr key={f.feature}><td>{FEATURE_LABEL[f.feature] || f.feature}</td><td className="num">{f.calls}</td><td className="num">{num(f.input_tokens)}</td><td className="num">{num(f.output_tokens)}</td><td className="num">{usd(f.cost_usd)}</td></tr>
              ))}</tbody>
            </table></div>
          )}
        </section>
      )}
      {econ && (
        <section className="panel"><h3>اقتصاديات الاشتراك (لكل شركة)</h3>
          <div className="kpi">
            <div><span className="small muted">تكلفة الإعداد مرة واحدة</span><b>{usd(econ.setup_cost_usd)}</b><span className="small muted">هوية البراند · الشعار بالكود = $0</span></div>
            <div><span className="small muted">تكلفة شهرية</span><b>{usd(econ.monthly_cost_usd)}</b><span className="small muted">نصوص {usd(econ.monthly_ai_usd)} + صور {usd(econ.monthly_images_usd)}</span></div>
            {econ.markets.map((m) => (
              <div key={m.market}><span className="small muted">هامش الربح · {m.market === "EG" ? "مصر" : "السعودية"}</span>
                <b style={{ color: m.gross_margin_pct >= 60 ? "var(--ok)" : m.gross_margin_pct >= 30 ? "var(--warn)" : "var(--bad)" }}>{Math.round(m.gross_margin_pct)}٪</b>
                <span className="small muted">{m.price} {m.currency} ≈ {usd(m.price_usd)} · ربح {usd(m.gross_profit_usd)}</span></div>
            ))}
          </div>
          <div className="tbl"><table>
            <thead><tr><th>العملية</th><th className="num">توكنز داخل</th><th className="num">توكنز خارج</th><th className="num">تكلفة الطلب</th><th>المصدر</th></tr></thead>
            <tbody>{Object.entries(econ.per_call).map(([k, v]) => (
              <tr key={k}><td>{FEATURE_LABEL[k]}</td><td className="num">{num(v.input_tokens)}</td><td className="num">{num(v.output_tokens)}</td><td className="num">{usd(v.cost_usd)}</td>
                <td className="small muted">{v.measured_calls ? `متوسط ${v.measured_calls} طلب حقيقي` : "تقدير افتراضي"}</td></tr>
            ))}</tbody>
          </table></div>
          <div className="grid3">{ASSUMPTIONS.map(([k, label]) => (
            <label key={k} className="f">{label}
              <input type="number" min={0} step="any" value={inputs[k]} onChange={(e) => setInputs({ ...inputs, [k]: Number(e.target.value) })} />
            </label>
          ))}</div>
          <p className="small muted">مش داخل في الحساب: الاستضافة، والدعم، وتكلفة جذب العميل.</p>
        </section>
      )}
      <section className="panel"><h3>آخر الطلبات</h3>
        {events.length ? (
          <div className="tbl"><table>
            <thead><tr><th>الوقت</th><th>العملية</th><th>الموديل</th><th className="num">توكنز</th><th className="num">الوقت</th><th className="num">التكلفة</th></tr></thead>
            <tbody>{events.map((e) => (
              <tr key={e.id}><td className="small">{new Date(e.created_at).toLocaleString("ar-EG", { dateStyle: "short", timeStyle: "short" })}</td>
                <td>{FEATURE_LABEL[e.feature] || e.feature}{!e.ok && <span className="tag bad" style={{ marginInlineStart: 6 }}>فشل</span>}</td>
                <td className="small" dir="ltr">{e.model}</td><td className="num">{num(e.input_tokens + e.output_tokens)}</td>
                <td className="num">{(e.latency_ms / 1000).toFixed(1)}s</td><td className="num">{usd(e.cost_usd)}</td></tr>
            ))}</tbody>
          </table></div>
        ) : <p className="muted">لسه مفيش طلبات.</p>}
      </section>
      {all && (
        <section className="panel"><h3>كل الشركات (أدمن)</h3>
          <div className="tbl"><table>
            <thead><tr><th>الشركة</th><th className="num">طلبات</th><th className="num">الصرف</th><th className="num">الميزانية</th></tr></thead>
            <tbody>{all.map((c) => <tr key={c.company_name + c.calls}><td>{c.company_name}</td><td className="num">{c.calls}</td><td className="num">{usd(c.spent_usd)}</td><td className="num">{usd(c.budget_usd)}</td></tr>)}</tbody>
          </table></div>
        </section>
      )}
    </>
  );
}
