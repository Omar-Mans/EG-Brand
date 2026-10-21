"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useBrand } from "@/components/BrandFrame";
import { api, waitJob } from "@/lib/api";
import { palette } from "@/lib/render";
import type { Job, Strategy } from "@/lib/types";

const PRIORITY: Record<string, [string, string]> = { high: ["أولوية عالية", "ok"], medium: ["أولوية متوسطة", "gold"], low: ["أولوية أقل", ""] };
const SWOT: [keyof Strategy["diagnosis"], string][] = [
  ["strengths", "نقاط القوة"], ["weaknesses", "نقاط الضعف"], ["opportunities", "الفرص"], ["threats", "التهديدات"],
];

function List({ items }: { items: string[] }) {
  return items.length ? <ul className="clean">{items.map((x) => <li key={x}>{x}</li>)}</ul> : <p className="small muted">—</p>;
}

export default function StrategyPage() {
  const { brand } = useBrand();
  const router = useRouter();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const st = brand.strategy;
  const base = `/brands/${brand.id}`;

  if (!st) {
    return (
      <div className="empty">
        <h2>لسه مفيش استراتيجية</h2>
        <p>جاوب على أسئلة الدراسة، والـ AI هيكتبلك خطة 90 يوم مفصّلة على مشروعك: الجمهور، المنصات، أنواع المحتوى، الميزانية، والأهداف.</p>
        <Link className="btn primary" href={`${base}/discovery`}>ابدأ الدراسة</Link>
      </div>
    );
  }

  const pal = brand.dna ? palette(brand.dna) : null;
  const colors = pal ? [pal.primary, pal.accent, pal.secondary, "#A9A7BC"] : ["#F2B640", "#5BC08A", "#E8A33D", "#A9A7BC"];
  const money = (n: number) => `${n.toLocaleString("en-US")} ${st.currency}`;

  async function makeContent() {
    setBusy("بنجهز محتوى الشهر الجاي على أساس الاستراتيجية…"); setError("");
    try {
      const now = new Date();
      const d = new Date(now.getFullYear(), now.getMonth() + 1, 1);
      await waitJob(await api<Job>(`/api/brands/${brand.id}/calendar`, { body: { year: d.getFullYear(), month: d.getMonth() + 1 } }));
      router.push(`${base}/content`);  // the content page opens on next month
    } catch (e: any) { setError(e.message); setBusy(""); }
  }

  return (
    <div className="strategy">
      <section className="panel">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <p className="eyebrow">استراتيجية 90 يوم · {st.created_at}</p>
            <h2>خطة {brand.name}</h2>
          </div>
          <div className="row noprint" style={{ gap: 6 }}>
            <button className="btn sm" type="button" onClick={() => window.print()}>تحميل PDF</button>
            <Link className="btn sm" href={`${base}/discovery`}>عدّل الإجابات</Link>
            <button className="btn sm primary" type="button" disabled={!!busy || !brand.dna} onClick={makeContent}>جهز محتوى الشهر الجاي</button>
          </div>
        </div>
        <p style={{ fontSize: 17 }}>{st.summary}</p>
        {(busy || error) && <p className={`status ${error ? "err" : ""}`} aria-live="polite">{error || busy}</p>}
      </section>

      <section className="panel">
        <h3>التموضع: إحنا مين في دماغ العميل</h3>
        <p className="note" style={{ color: "var(--fg)", fontSize: 15 }}>{st.positioning.statement}</p>
        <div className="grid2">
          <div className="f"><span>اللي بيميزنا</span><List items={st.positioning.usp} /></div>
          <div className="f"><span>الأدلة اللي هنوريها في المحتوى</span><List items={st.positioning.proof_points} /></div>
        </div>
      </section>

      <section className="panel">
        <h3>تشخيص الوضع الحالي</h3>
        <div className="grid2 swot">
          {SWOT.map(([k, t]) => <div key={k} className={`card ${k}`}><b>{t}</b><List items={st.diagnosis[k]} /></div>)}
        </div>
      </section>

      <section className="panel">
        <h3>العملاء اللي بنكلمهم</h3>
        <div className="grid3">
          {st.personas.map((p) => (
            <div key={p.name} className="card">
              <div className="row" style={{ justifyContent: "space-between" }}><b style={{ fontSize: 17 }}>{p.name}</b><span className="tag">{p.age}</span></div>
              <p className="small">{p.description}</p>
              <div className="f"><span>بيوجعه</span><List items={p.pains} /></div>
              <div className="f"><span>بيحركه</span><List items={p.motivations} /></div>
              <div className="f"><span>بيتردد بسبب</span><List items={p.objections} /></div>
              <div className="meta">{p.where.map((w) => <span key={w} className="tag">{w}</span>)}</div>
              <p className="note" style={{ color: "var(--fg)" }}>«{p.message}»</p>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h3>المنصات ودور كل واحدة</h3>
        <div className="tbl"><table>
          <thead><tr><th>المنصة</th><th>دورها</th><th className="num">بوست في الأسبوع</th><th>الأشكال</th><th>ليه</th></tr></thead>
          <tbody>{st.channels.map((c) => (
            <tr key={c.platform}>
              <td><b>{c.platform}</b><br /><span className={`tag ${PRIORITY[c.priority][1]}`}>{PRIORITY[c.priority][0]}</span></td>
              <td>{c.role}</td><td className="num">{c.posts_per_week}</td><td>{c.formats.join("، ")}</td><td className="small">{c.why}</td>
            </tr>
          ))}</tbody>
        </table></div>
      </section>

      <section className="panel">
        <h3>أعمدة المحتوى</h3>
        <div className="bar" style={{ height: 16 }} aria-hidden>
          {st.content_pillars.map((p, i) => <i key={p.name} style={{ width: `${p.share}%`, background: colors[i % colors.length] }} />)}
        </div>
        <div className="grid2">
          {st.content_pillars.map((p, i) => (
            <div key={p.name} className="card">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <b><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 3, background: colors[i % colors.length], marginInlineEnd: 6 }} />{p.name}</b>
                <span className="tag gold">{p.share}%</span>
              </div>
              <p className="small muted">{p.goal}</p>
              <List items={p.examples} />
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h3>خطة الـ 90 يوم</h3>
        <div className="grid3">
          {st.roadmap.map((r, i) => (
            <div key={r.phase} className="card">
              <p className="eyebrow">مرحلة {i + 1}</p>
              <b style={{ fontSize: 17 }}>{r.phase}</b>
              <p className="small muted">{r.goal}</p>
              <List items={r.actions} />
              {r.kpis.length > 0 && <div className="meta">{r.kpis.map((k) => <span key={k.name} className="tag ok">{k.name}: {k.target}</span>)}</div>}
            </div>
          ))}
        </div>
      </section>

      <div className="grid2">
        <section className="panel">
          <h3>تعمله في أول 7 أيام</h3>
          <ol className="clean">{st.quick_wins.map((q) => <li key={q}>{q}</li>)}</ol>
        </section>
        <section className="panel">
          <h3>الميزانية الشهرية</h3>
          <div className="kpi"><div><span className="small muted">الإجمالي المقترح</span><b>{st.budget.monthly_total > 0 ? money(st.budget.monthly_total) : "من غير إعلانات ممولة"}</b></div></div>
          {st.budget.split.map((b) => (
            <div key={b.item} className="row" style={{ justifyContent: "space-between" }}>
              <span>{b.item}{b.note && <span className="small muted"> · {b.note}</span>}</span>
              <span className="tag">{b.pct}%{st.budget.monthly_total > 0 && ` · ${money(Math.round(st.budget.monthly_total * b.pct / 100))}`}</span>
            </div>
          ))}
          {st.budget.note && <p className="note">{st.budget.note}</p>}
        </section>
      </div>

      <section className="panel">
        <h3>هنقيس النجاح بإيه</h3>
        <div className="tbl"><table>
          <thead><tr><th>المؤشر</th><th>الهدف</th><th>ليه</th></tr></thead>
          <tbody>{st.kpis.map((k) => <tr key={k.name}><td><b>{k.name}</b></td><td>{k.target}</td><td className="small">{k.why}</td></tr>)}</tbody>
        </table></div>
        <p className="small muted">الأهداف دي مبنية على الأرقام اللي انت قلتها. مفيش أرقام سوق متألفة، ولو مدّيتش رقم حالي فالهدف مبدئي ونعدّله بعد أول شهر.</p>
      </section>

      <div className="grid2">
        {st.offers.length > 0 && (
          <section className="panel">
            <h3>عروض مقترحة</h3>
            {st.offers.map((o) => <div key={o.title} className="card"><b>{o.title}</b><p className="small">{o.description}</p><span className="tag gold">{o.when}</span></div>)}
          </section>
        )}
        {st.competitors.length > 0 && (
          <section className="panel">
            <h3>إزاي نكسب المنافسين</h3>
            {st.competitors.map((c) => (
              <div key={c.name} className="card"><b>{c.name}</b><p className="small muted">نقطة قوتهم: {c.their_strength}</p><p className="small">زاويتنا: {c.our_angle}</p></div>
            ))}
          </section>
        )}
      </div>

      {st.risks.length > 0 && (
        <section className="panel">
          <h3>مخاطر وإزاي نتعامل معاها</h3>
          <div className="tbl"><table>
            <thead><tr><th>الخطر</th><th>الحل</th></tr></thead>
            <tbody>{st.risks.map((r) => <tr key={r.risk}><td>{r.risk}</td><td>{r.mitigation}</td></tr>)}</tbody>
          </table></div>
        </section>
      )}
    </div>
  );
}
