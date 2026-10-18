"use client";

import { useState } from "react";
import { DEFAULT_TZ, DIALECTS, MARKETS, PREF_COLORS, STYLES, TIMEZONES } from "@/lib/catalog";
import type { Brief } from "@/lib/types";

export const EMPTY_BRIEF: Brief = { idea: "", name: "", market: "EG", dialect: "egyptian", styles: [], colors: [], timezone: "Africa/Cairo" };

export default function BriefForm({ initial, submitLabel, busy, onSubmit }: {
  initial: Brief; submitLabel: string; busy: boolean; onSubmit: (b: Brief) => void;
}) {
  const [b, setB] = useState<Brief>(initial);
  const toggle = (key: "styles" | "colors", v: string, max: number) =>
    setB({ ...b, [key]: b[key].includes(v) ? b[key].filter((x) => x !== v) : [...b[key], v].slice(-max) });

  return (
    <form className="panel" onSubmit={(e) => { e.preventDefault(); onSubmit(b); }}>
      <label className="f" htmlFor="idea">فكرة المشروع
        <textarea id="idea" rows={3} required minLength={10} value={b.idea} onChange={(e) => setB({ ...b, idea: e.target.value })}
          placeholder="مثلاً: محل حلويات شرقية أونلاين في القاهرة، بيبيع علب هدايا للمناسبات" />
      </label>
      <div className="grid3">
        <label className="f" htmlFor="bname">اسم البراند (اختياري)
          <input id="bname" type="text" value={b.name} maxLength={60} onChange={(e) => setB({ ...b, name: e.target.value })} placeholder="سيبه فاضي ونقترح 3 أسماء" />
        </label>
        <label className="f" htmlFor="market">السوق
          <select id="market" value={b.market} onChange={(e) => setB({ ...b, market: e.target.value as Brief["market"], dialect: e.target.value === "SA" ? "saudi" : "egyptian", timezone: DEFAULT_TZ[e.target.value] })}>
            {Object.entries(MARKETS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </label>
        <label className="f" htmlFor="dialect">لهجة المحتوى
          <select id="dialect" value={b.dialect} onChange={(e) => setB({ ...b, dialect: e.target.value as Brief["dialect"] })}>
            {Object.entries(DIALECTS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="f" htmlFor="tz">المنطقة الزمنية للنشر
          <select id="tz" value={b.timezone || DEFAULT_TZ[b.market]} onChange={(e) => setB({ ...b, timezone: e.target.value })}>
            {Object.entries(TIMEZONES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>
      <div className="f"><span>الأسلوب</span>
        <div className="row">{STYLES.map((s) => (
          <button key={s} type="button" className="chip" aria-pressed={b.styles.includes(s)} onClick={() => toggle("styles", s, 4)}>{s}</button>
        ))}</div>
      </div>
      <div className="f"><span>ألوان بتحبها (لحد 3)</span>
        <div className="row">{PREF_COLORS.map(([n, h]) => (
          <button key={h} type="button" className="chip" aria-pressed={b.colors.includes(h)} onClick={() => toggle("colors", h, 3)}>
            <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: "50%", background: h, verticalAlign: "middle", marginInlineEnd: 6 }} />{n}
          </button>
        ))}</div>
      </div>
      <div className="row"><button className="btn primary" type="submit" disabled={busy || b.idea.trim().length < 10}>{submitLabel}</button></div>
    </form>
  );
}
