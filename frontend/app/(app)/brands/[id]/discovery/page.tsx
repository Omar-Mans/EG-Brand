"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useBrand } from "@/components/BrandFrame";
import { api, waitJob } from "@/lib/api";
import { VERTICAL_SECTOR } from "@/lib/catalog";
import type { Answers, Brand, Followup, Job, Question, Section } from "@/lib/types";

function Field({ q, value, onChange }: { q: Question; value: Answers[string] | undefined; onChange: (v: Answers[string]) => void }) {
  const label = <>{q.label}{q.required && <b style={{ color: "var(--gold)" }}> *</b>}</>;
  if (q.type === "select" || q.type === "multi") {
    const list = Array.isArray(value) ? value : value ? [value] : [];
    const toggle = (o: string) => q.type === "select"
      ? onChange(value === o ? "" : o)
      : onChange(list.includes(o) ? list.filter((x) => x !== o) : [...list, o]);
    return (
      <div className="f" role="group" aria-label={q.label}>
        <span>{label}{q.type === "multi" && <span className="muted"> (اختار أكتر من حاجة)</span>}</span>
        <div className="row" style={{ gap: 8 }}>
          {q.options!.map((o) => <button key={o} type="button" className="chip" aria-pressed={list.includes(o)} onClick={() => toggle(o)}>{o}</button>)}
        </div>
      </div>
    );
  }
  const v = typeof value === "string" ? value : "";
  return (
    <label className="f">{label}
      {q.type === "textarea"
        ? <textarea rows={3} value={v} onChange={(e) => onChange(e.target.value)} />
        : <input type="text" dir={q.type === "url" ? "ltr" : undefined} inputMode={q.type === "url" ? "url" : undefined}
            placeholder={q.type === "url" ? "https://" : undefined} value={v} onChange={(e) => onChange(e.target.value)} />}
    </label>
  );
}

export default function DiscoveryPage() {
  const { brand, setBrand } = useBrand();
  const router = useRouter();
  const [sections, setSections] = useState<Section[] | null>(null);
  const [answers, setAnswers] = useState<Answers>(brand.discovery?.answers || {});
  const [followups, setFollowups] = useState<Followup[]>(brand.discovery?.followups || []);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const vertical = brand.brief.vertical || "";
  useEffect(() => {
    api<{ sections: Section[] }>(`/api/discovery/questions${vertical ? `?vertical=${vertical}` : ""}`).then((r) => setSections(r.sections)).catch((e) => setError(e.message));
  }, [vertical]);
  useEffect(() => { // the business type already tells us the sector
    const sector = VERTICAL_SECTOR[vertical];
    if (sector) setAnswers((a) => (a.sector ? a : { ...a, sector }));
  }, [vertical]);
  if (!sections) return <p className="muted">{error || "بنحمّل الأسئلة…"}</p>;

  const last = sections.length; // the step after the sections holds the AI follow-up questions
  const missing = (s: Section) => s.questions.filter((q) => q.required && !(Array.isArray(answers[q.id]) ? answers[q.id].length : answers[q.id]));
  const filled = Object.values(answers).filter((v) => (Array.isArray(v) ? v.length : v)).length;
  const total = sections.reduce((n, s) => n + s.questions.length, 0);

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label); setError("");
    try { await fn(); } catch (e: any) { setError(e.message); } finally { setBusy(""); }
  }
  const save = async () => setBrand(await api<Brand>(`/api/brands/${brand.id}/discovery`, { method: "PUT", body: { answers } }));

  const next = () => run("بنحفظ…", async () => {
    const m = missing(sections[step]);
    if (m.length) throw new Error("جاوب على الأسئلة اللي عليها نجمة: " + m.map((q) => q.label).join("، "));
    await save();
    if (step + 1 === last) {
      const all = sections.flatMap(missing);
      if (all.length) throw new Error("فيه أسئلة أساسية لسه ناقصة في خطوات قبل كده");
      if (!followups.length) {
        setBusy("الـ AI بيقرا إجاباتك وموقعك ويجهز أسئلة مخصوصة لمجالك…");
        const job = await waitJob(await api<Job>(`/api/brands/${brand.id}/discovery/followups`, { method: "POST" }));
        setFollowups(job.result.followups);
      }
    }
    setStep(step + 1);
    window.scrollTo({ top: 0 });
  });

  const regenFollowups = () => run("بنجهز أسئلة جديدة…", async () => {
    const job = await waitJob(await api<Job>(`/api/brands/${brand.id}/discovery/followups`, { method: "POST" }));
    setFollowups(job.result.followups);
  });

  const buildStrategy = () => run("بنحفظ إجاباتك…", async () => {
    await api(`/api/brands/${brand.id}/discovery/followups`, { method: "PUT", body: { answers: followups.map((f) => f.answer) } });
    setBusy("الـ AI بيكتب استراتيجية 90 يوم لمشروعك… (ممكن ياخد دقيقة)");
    await waitJob(await api<Job>(`/api/brands/${brand.id}/strategy`, { method: "POST" }), undefined, 400_000);
    if (!brand.dna) {
      setBusy("بنبني هوية البراند على أساس الاستراتيجية…");
      await waitJob(await api<Job>(`/api/brands/${brand.id}/generate-dna`, { method: "POST" }));
    }
    setBrand(await api<Brand>(`/api/brands/${brand.id}`));
    router.push(`/brands/${brand.id}/strategy`);
  });

  const site = brand.discovery;
  return (
    <>
      <section className="panel">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <p className="eyebrow">دراسة المشروع · خطوة {Math.min(step + 1, last + 1)} من {last + 1}</p>
            <h2>{step < last ? sections[step].title : "أسئلة مخصوصة لمشروعك"}</h2>
          </div>
          <span className="pill"><span className="dot" />{filled} من {total} إجابة</span>
        </div>
        <div className="bar" aria-hidden><i style={{ width: `${((step + 1) / (last + 1)) * 100}%`, background: "var(--gold)" }} /></div>
        <nav className="row" style={{ gap: 6 }} aria-label="خطوات الدراسة">
          {[...sections.map((s) => s.title), "أسئلة الـ AI"].map((t, i) => (
            <button key={t} type="button" className="chip" aria-pressed={i === step} disabled={i > step || !!busy} onClick={() => setStep(i)}>{t}</button>
          ))}
        </nav>
        {step === 0 && <p className="note">كل ما تجاوب بتفاصيل أكتر، الخطة هتطلع أدق. الأسئلة اللي عليها نجمة بس هي الإجبارية.</p>}
      </section>

      {step < last ? (
        <section className="panel">
          {sections[step].questions.map((q) => (
            <Field key={q.id} q={q} value={answers[q.id]} onChange={(v) => setAnswers({ ...answers, [q.id]: v })} />
          ))}
          <div className="row">
            {step > 0 && <button className="btn" type="button" disabled={!!busy} onClick={() => setStep(step - 1)}>السابق</button>}
            <div className="spacer" />
            <button className="btn primary" type="button" disabled={!!busy} onClick={next}>{step + 1 === last ? "كمّل لأسئلة الـ AI" : "التالي"}</button>
          </div>
        </section>
      ) : (
        <section className="panel">
          <p className="muted">الأسئلة دي الـ AI كتبها مخصوص لمجالك بعد ما قرا إجاباتك. جاوب اللي تقدر عليه، وسيب الباقي فاضي.</p>
          {site?.website_url && (
            <p className={`note ${site.website_error ? "err" : ""}`}>
              {site.website_error ? `مقدرناش نقرا الموقع (${site.website_error})، هنكمّل بإجاباتك بس.` : `قرينا موقعك ${site.website_url} وهنستخدمه في الخطة.`}
            </p>
          )}
          {followups.map((f, i) => (
            <label key={f.question} className="f">
              <span style={{ color: "var(--fg)" }}>{f.question}</span>
              <span className="small">{f.why}</span>
              <textarea rows={2} value={f.answer} onChange={(e) => setFollowups(followups.map((x, j) => (j === i ? { ...x, answer: e.target.value } : x)))} />
            </label>
          ))}
          <div className="row">
            <button className="btn" type="button" disabled={!!busy} onClick={() => setStep(step - 1)}>السابق</button>
            <button className="btn sm" type="button" disabled={!!busy} onClick={regenFollowups}>أسئلة تانية</button>
            <div className="spacer" />
            <button className="btn primary" type="button" disabled={!!busy} onClick={buildStrategy}>{brand.strategy ? "حدّث الاستراتيجية" : "اعمل الاستراتيجية"}</button>
          </div>
        </section>
      )}
      {(busy || error) && <p className={`status ${error ? "err" : ""}`} aria-live="polite">{error || busy}</p>}
    </>
  );
}
