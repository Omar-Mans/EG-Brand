"use client";

import { useCallback, useEffect, useState } from "react";
import { useBrand } from "@/components/BrandFrame";
import PostCard from "@/components/PostCard";
import Teleprompter from "@/components/Teleprompter";
import { api, waitJob } from "@/lib/api";
import { ICONS } from "@/lib/catalog";
import type { Job, Post, Talk } from "@/lib/types";

type Options = { voices: Record<string, string>; video_provider: string };
const KIND_LABEL: Record<string, string> = { montage: "مونتاج فيديو", photo: "صور وصوت", talk: "تصوير بنفسك" };
const SECONDS = [15, 30, 60];

function Icon({ name }: { name: string }) {
  return <svg width="20" height="20" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={ICONS[name]} /></svg>;
}

function Seconds({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <div className="f" role="group" aria-label="مدة الريل"><span>المدة</span>
      <div className="row" style={{ gap: 6 }}>
        {SECONDS.map((s) => <button key={s} type="button" className="chip" aria-pressed={value === s} onClick={() => onChange(s)}>{s} ثانية</button>)}
      </div>
    </div>
  );
}

function TalkPanel({ post, onChange }: { post: Post; onChange: (p: Post) => void }) {
  const talk = post.design.reel?.talk as Talk;
  const [hook, setHook] = useState(talk.hook);
  const [lines, setLines] = useState(talk.lines);
  const [cta, setCta] = useState(talk.cta);
  const [prompter, setPrompter] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { setHook(talk.hook); setLines(talk.lines); setCta(talk.cta); }, [talk]);

  async function save() {
    if (hook === talk.hook && cta === talk.cta && JSON.stringify(lines) === JSON.stringify(talk.lines)) return;
    try { onChange(await api<Post>(`/api/posts/${post.id}/reel/talk`, { method: "PATCH", body: { hook, lines, cta } })); }
    catch (e: any) { setError(e.message); }
  }
  const words = [hook, ...lines, cta].join(" ").split(/\s+/).filter(Boolean).length;
  const secs = Math.round(words / 2.3);
  const raw = post.design.reel?.raw || [];

  return (
    <section className="panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div><p className="eyebrow">سكريبت للتصوير · {talk.own ? "سكريبتك بعد التظبيط" : "مكتوب بالـ AI"}</p><h3>{post.headline}</h3></div>
        <button className="btn primary" type="button" onClick={async () => { await save(); setPrompter(true); }}>افتح شاشة التلقين</button>
      </div>
      <p className={`small ${secs > talk.seconds * 1.25 ? "err" : "muted"}`}>
        {words} كلمة · حوالي {secs} ثانية قراءة (المطلوب {talk.seconds} ثانية){secs > talk.seconds * 1.25 ? ". أطول من المطلوب، قصّر شوية" : ""}
      </p>
      <label className="f">الخطّاف (أول جملة، لازم تشد في ثانيتين)
        <input type="text" value={hook} onChange={(e) => setHook(e.target.value)} onBlur={save} />
      </label>
      <div className="f"><span>السطور</span>
        {lines.map((l, i) => (
          <div key={i} className="talk-line">
            <span>{i + 1}</span>
            <input type="text" value={l} aria-label={`سطر ${i + 1}`} onChange={(e) => setLines(lines.map((x, j) => (j === i ? e.target.value : x)))} onBlur={save} />
            <button className="btn sm" type="button" aria-label={`امسح سطر ${i + 1}`} onClick={() => setLines(lines.filter((_, j) => j !== i))}>×</button>
          </div>
        ))}
        <button className="btn sm" type="button" style={{ alignSelf: "flex-start" }} onClick={() => setLines([...lines, ""])}>+ سطر</button>
      </div>
      <label className="f">الختام (الدعوة لإجراء)
        <input type="text" value={cta} onChange={(e) => setCta(e.target.value)} onBlur={save} />
      </label>
      {talk.broll.length > 0 && (
        <p className="small muted">لقطات تصوّرها كمان وتقطع عليها وانت بتتكلم: {talk.broll.join(" · ")}</p>
      )}
      <div className="note">صوّر الموبايل طولي وفي مكان منوّر، وبص للكاميرا مش للكلام. لو غلطت كمّل وأعد الجملة: مونتاج الفيديو المتصور (قص السكتات والإعادات وكتابة الكلام عليه) هو الخطوة الجاية في المنصة.</div>
      {raw.length > 0 && (
        <div className="f"><span>اللقطات اللي صورتها ({raw.length})</span>
          <div className="takes">{raw.map((r) => <video key={r.url} src={r.url} controls playsInline preload="metadata" />)}</div>
        </div>
      )}
      {error && <p className="status err">{error}</p>}
      {prompter && <Teleprompter talk={{ ...talk, hook, lines, cta }} postId={post.id} onClose={() => setPrompter(false)} onSaved={onChange} />}
    </section>
  );
}

export default function StudioPage() {
  const { brand } = useBrand();
  const [reels, setReels] = useState<Post[] | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [opts, setOpts] = useState<Options | null>(null);
  const [topic, setTopic] = useState("");
  const [mSeconds, setMSeconds] = useState(30);
  const [voice, setVoice] = useState(brand.brief.market === "SA" ? "sa_m" : "eg_m");
  const [talkMode, setTalkMode] = useState<"ai" | "own">("ai");
  const [talkTopic, setTalkTopic] = useState("");
  const [own, setOwn] = useState("");
  const [tSeconds, setTSeconds] = useState(30);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => setReels(await api<Post[]>(`/api/brands/${brand.id}/reels`)), [brand.id]);
  useEffect(() => { load().catch((e) => setError(e.message)); api<Options>("/api/reels/options").then(setOpts).catch(() => {}); }, [load]);

  async function start(body: Record<string, unknown>, label: string) {
    setBusy(label); setError("");
    try {
      const r = await api<{ post: Post; job: Job }>(`/api/brands/${brand.id}/reels`, { body });
      await waitJob(r.job);
      await load();
      setSelected(r.post.id);
      setTimeout(() => document.getElementById("studio-selected")?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (e: any) { setError(e.message); } finally { setBusy(""); }
  }

  if (!brand.dna) return <div className="empty"><h2>الهوية الأول</h2><p>اعمل هوية البراند من تبويب الهوية، وبعدها ارجع هنا.</p></div>;
  const current = reels?.find((p) => p.id === selected);
  const update = (p: Post) => setReels((rs) => (rs || []).map((x) => (x.id === p.id ? p : x)));

  return (
    <>
      <div><p className="eyebrow">استوديو الريلز</p><h2>اعمل ريل من فكرة، أو صوّر نفسك بسكريبت جاهز</h2></div>
      <div className="studio-start">
        <section className="panel">
          <h3><span className="vi"><Icon name="sun" /></span>ريل كامل من الـ AI</h3>
          <p className="small muted">من غير تصوير: الـ AI يكتب السكريبت، ويختار لقطات فيديو حقيقية لكل مشهد، ويعمل المونتاج على إيقاع الموسيقى، ويضيف صوت سعودي أو مصري والكلام مكتوب على الفيديو.</p>
          <label className="f">عن إيه الريل؟
            <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="مثلاً: ليه تشتري عربيتك المستعملة من عندنا" />
          </label>
          <Seconds value={mSeconds} onChange={setMSeconds} />
          <label className="f">الصوت
            <select value={voice} onChange={(e) => setVoice(e.target.value)}>
              <option value="none">من غير صوت (موسيقى بس)</option>
              {Object.entries(opts?.voices || {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <button className="btn primary" type="button" disabled={!!busy || topic.trim().length < 3}
            onClick={() => start({ kind: "montage", topic, seconds: mSeconds, voice }, "الـ AI بيكتب سكريبت الريل…")}>اكتب الريل</button>
          {opts?.video_provider === "off" && <p className="small err">لقطات الفيديو محتاجة PIXABAY_API_KEY في الإعدادات (مجاني).</p>}
        </section>

        <section className="panel">
          <h3><span className="vi"><Icon name="chat" /></span>سكريبت وصوّر بنفسك</h3>
          <p className="small muted">الـ AI يكتبلك سكريبت بلهجتك ومظبوط على المدة، أو يظبط السكريبت بتاعك، وتقراه من شاشة التلقين وانت بتصوّر.</p>
          <div className="row" style={{ gap: 6 }} role="group" aria-label="مين يكتب السكريبت">
            <button type="button" className="chip" aria-pressed={talkMode === "ai"} onClick={() => setTalkMode("ai")}>الـ AI يكتب</button>
            <button type="button" className="chip" aria-pressed={talkMode === "own"} onClick={() => setTalkMode("own")}>عندي سكريبت</button>
          </div>
          {talkMode === "ai"
            ? <label className="f">عن إيه هتتكلم؟<input type="text" value={talkTopic} onChange={(e) => setTalkTopic(e.target.value)} placeholder="مثلاً: 3 حاجات تفحصها قبل ما تشتري عربية مستعملة" /></label>
            : <label className="f">السكريبت بتاعك (هنظبطه ونقسمه سطور)<textarea rows={4} value={own} onChange={(e) => setOwn(e.target.value)} /></label>}
          <Seconds value={tSeconds} onChange={setTSeconds} />
          <button className="btn primary" type="button" disabled={!!busy || (talkMode === "ai" ? talkTopic.trim().length < 3 : own.trim().length < 10)}
            onClick={() => start({ kind: "talk", topic: talkMode === "ai" ? talkTopic : "", script: talkMode === "own" ? own : "", seconds: tSeconds },
              talkMode === "own" ? "بنظبط السكريبت بتاعك…" : "الـ AI بيكتب السكريبت…")}>
            {talkMode === "own" ? "ظبّط السكريبت" : "اكتب السكريبت"}
          </button>
        </section>
      </div>
      {(busy || error) && <p className={`status ${error ? "err" : ""}`} aria-live="polite">{error || busy}</p>}

      <section className="panel">
        <h3>الريلز بتاعتك</h3>
        {reels === null ? <div className="skeleton" style={{ height: 90 }} /> : reels.length === 0 ? (
          <p className="small muted">لسه مفيش ريلز. ابدأ من فوق، أو من بوستات الريلز في خطة المحتوى.</p>
        ) : (
          <div className="studio-list">
            {reels.map((p) => {
              const kind = p.design.studio || "plan";
              return (
                <button key={p.id} type="button" className="studio-item" aria-pressed={p.id === selected} onClick={() => setSelected(p.id)}>
                  <b>{p.headline || "ريل"}</b>
                  <div className="meta">
                    <span className="tag">{KIND_LABEL[kind] || "من خطة المحتوى"}</span>
                    {p.video_url && <span className="tag ok">الفيديو جاهز</span>}
                    {kind === "talk" && (p.design.reel?.raw?.length ? <span className="tag ok">متصور</span> : <span className="tag gold">مستني التصوير</span>)}
                    {p.status !== "draft" && <span className="tag gold">{p.status === "published" ? "اتنشر" : "مجدول"}</span>}
                  </div>
                  <span className="small muted">{p.day}/{p.month.split("-")[1]}</span>
                </button>
              );
            })}
          </div>
        )}
      </section>

      <div id="studio-selected">
        {current && (current.design.studio === "talk" && current.design.reel?.talk
          ? <TalkPanel post={current} onChange={update} />
          : <div style={{ maxWidth: 560 }}><PostCard post={current} dna={brand.dna} onChange={update} /></div>)}
      </div>
    </>
  );
}
