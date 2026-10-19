"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import BriefForm from "@/components/BriefForm";
import { useBrand } from "@/components/BrandFrame";
import { api, waitJob } from "@/lib/api";
import { FONTS_AR, ICON_LABELS, ICONS } from "@/lib/catalog";
import { downloadCanvas, drawLogo, nameOf, palette } from "@/lib/render";
import type { Brand, Brief, Dna, Job } from "@/lib/types";

function Logo({ dna, variant }: { dna: Dna; variant: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => { if (ref.current) drawLogo(ref.current, dna, variant); }, [dna, variant]);
  return (
    <div className="card">
      <canvas ref={ref} width={800} height={520} aria-label={`شعار ${nameOf(dna).ar}، شكل ${variant + 1}`} />
      <button className="btn sm" type="button" onClick={() => ref.current && downloadCanvas(ref.current, `${nameOf(dna).en || "logo"}-${variant + 1}.png`)}>تحميل PNG</button>
    </div>
  );
}

export default function IdentityPage() {
  const { brand, setBrand } = useBrand();
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [editBrief, setEditBrief] = useState(false);
  const d = brand.dna;

  async function patch(body: Partial<Dna>) {
    try { setBrand(await api<Brand>(`/api/brands/${brand.id}/dna`, { method: "PATCH", body })); }
    catch (e: any) { setError(e.message); }
  }

  async function regenerate(brief?: Brief) {
    setBusy(true); setError("");
    try {
      if (brief) await api(`/api/brands/${brand.id}/brief`, { method: "PUT", body: brief });
      setStatus("الـ AI بيبني هوية البراند…");
      await waitJob(await api<Job>(`/api/brands/${brand.id}/generate-dna`, { method: "POST" }));
      setBrand(await api<Brand>(`/api/brands/${brand.id}`));
      setEditBrief(false);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); setStatus(""); }
  }

  const controls = (
    <div className="row">
      <button className="btn sm" type="button" onClick={() => setEditBrief(!editBrief)}>{editBrief ? "إلغاء" : "عدّل وصف المشروع"}</button>
      <button className="btn sm" type="button" disabled={busy} onClick={() => regenerate()}>ولّد هوية جديدة</button>
      {status && <span className="status">{status}</span>}
      {error && <span className="status err">{error}</span>}
    </div>
  );

  if (!d || editBrief) {
    return (
      <>
        {d && controls}
        {!d && !brand.strategy && (
          <p className="note">أحسن نتيجة: <Link href={`/brands/${brand.id}/discovery`}>جاوب على أسئلة الدراسة</Link> الأول، والهوية هتتبني على الاستراتيجية. أو ولّدها على طول من الوصف.</p>
        )}
        {!d && brand.strategy && <p className="muted">لسه مفيش هوية للبراند ده. هتتبني على أساس الاستراتيجية.</p>}
        <BriefForm initial={brand.brief} submitLabel="ولّد هوية البراند" busy={busy} onSubmit={regenerate} />
        {!d && (status || error) && <p className={`status ${error ? "err" : ""}`}>{error || status}</p>}
      </>
    );
  }

  const p = palette(d), n = nameOf(d);
  const total = d.pillars.reduce((a, x) => a + x.share, 0) || 1;
  const pillColors = [p.primary, p.accent, p.secondary, p.light];
  return (
    <>
      {controls}
      <section className="panel">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2>{n.ar} <span className="muted" style={{ fontWeight: 400 }}>{n.en}</span></h2>
          <p className="muted">{d.tagline_ar}{d.tagline_en ? ` · ${d.tagline_en}` : ""}</p>
        </div>
        <div className="names">{d.names.map((x, i) => (
          <button key={i} type="button" className="namecard" aria-pressed={(d.chosen || 0) === i} onClick={() => patch({ chosen: i })}>
            <span className="ar">{x.ar}</span><span className="small muted">{x.en}</span><span className="small">{x.meaning}</span>
          </button>
        ))}</div>
      </section>
      <section className="panel">
        <div className="row" style={{ justifyContent: "space-between" }}><h3>الشعار</h3><span className="small muted">مرسوم بالكود بخط {d.font_ar}</span></div>
        <div className="grid3">{[0, 1, 2].map((v) => <Logo key={v} dna={d} variant={v} />)}</div>
        <div className="grid2">
          <label className="f" htmlFor="icon">الأيقونة
            <select id="icon" value={d.icon} onChange={(e) => patch({ icon: e.target.value })}>
              {Object.keys(ICONS).map((k) => <option key={k} value={k}>{ICON_LABELS[k]}</option>)}
            </select>
          </label>
          <label className="f" htmlFor="font">الخط العربي
            <select id="font" value={d.font_ar} onChange={(e) => patch({ font_ar: e.target.value })}>
              {FONTS_AR.map((f) => <option key={f}>{f}</option>)}
            </select>
          </label>
        </div>
      </section>
      <div className="grid2">
        <section className="panel"><h3>الألوان</h3>
          <div className="sw">{d.palette.map((x, i) => (
            <div key={x.role + i}><i style={{ background: x.hex }} />
              <span>{x.name || x.role}<br />
                <label className="small muted" style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <code>{x.hex}</code>
                  <input type="color" value={x.hex} aria-label={`غيّر اللون ${x.name}`} style={{ width: 28, height: 22, border: 0, background: "none", padding: 0 }}
                    onChange={(e) => patch({ palette: d.palette.map((c, j) => (j === i ? { ...c, hex: e.target.value } : c)) })} />
                </label>
              </span>
            </div>
          ))}</div>
        </section>
        <section className="panel"><h3>الخطوط</h3>
          <p style={{ fontFamily: `'${d.font_ar}', serif`, fontSize: 34, lineHeight: 1.4 }}>{n.ar} · {d.tagline_ar}</p>
          <p style={{ fontFamily: `'${d.font_en}', serif`, fontSize: 22 }} dir="ltr">{n.en} — {d.tagline_en}</p>
          <p className="small muted">العناوين: {d.font_ar} · الإنجليزي: {d.font_en} · النص: IBM Plex Sans Arabic</p>
        </section>
      </div>
      <div className="grid2">
        <section className="panel"><h3>الشخصية والنبرة</h3>
          <div className="row">{d.personality.map((x) => <span key={x} className="tag gold">{x}</span>)}</div>
          <p>{d.tone}</p>
          <div className="grid2">
            <div><p className="small muted">اعمل</p><ul className="clean">{d.voice_do.map((x) => <li key={x}>{x}</li>)}</ul></div>
            <div><p className="small muted">ما تعملش</p><ul className="clean">{d.voice_dont.map((x) => <li key={x}>{x}</li>)}</ul></div>
          </div>
        </section>
        <section className="panel"><h3>الجمهور ومحاور المحتوى</h3>
          <p><span className="muted small">التموضع: </span>{d.positioning}</p>
          <p><span className="muted small">الجمهور: </span>{d.audience}</p>
          <div className="bar" aria-hidden>{d.pillars.map((x, i) => <i key={x.name} style={{ width: `${(x.share / total) * 100}%`, background: pillColors[i % 4] }} />)}</div>
          <ul className="clean small">{d.pillars.map((x) => <li key={x.name}>{x.name}: {Math.round((x.share / total) * 100)}٪</li>)}</ul>
        </section>
      </div>
      <div className="row"><Link className="btn primary" href={`/brands/${brand.id}/content`}>كمّل لخطة المحتوى</Link></div>
    </>
  );
}
