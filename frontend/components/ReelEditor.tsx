"use client";

import { useEffect, useRef, useState } from "react";
import { API_URL, api, waitJob } from "@/lib/api";
import { canvasBlob, drawReelOutro, drawReelScene } from "@/lib/render";
import type { Dna, Job, Post, Reel, ReelScene } from "@/lib/types";

type Options = { voices: Record<string, string>; music: Record<string, string>; voice_provider: string };
let optionsCache: Promise<Options> | null = null;
const loadOptions = () => (optionsCache ||= api<Options>("/api/reels/options"));

function ScenePreview({ dna, scene, index, total }: { dna: Dna; scene: ReelScene; index: number; total: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => { if (ref.current) drawReelScene(ref.current, dna, scene, index, total, true); }, [dna, scene, index, total]);
  return <canvas ref={ref} className="reelthumb" aria-label={`المشهد ${index + 1}: ${scene.text}`} />;
}

export default function ReelEditor({ post, dna, onChange }: { post: Post; dna: Dna; onChange: (p: Post) => void }) {
  const reel = post.design?.reel;
  const [opts, setOpts] = useState<Options | null>(null);
  const [scenes, setScenes] = useState<ReelScene[]>(reel?.scenes || []);
  const [outro, setOutro] = useState(reel?.outro_voice || "");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const fileRefs = useRef<(HTMLInputElement | null)[]>([]);
  const musicRef = useRef<HTMLInputElement>(null);
  const sampleRef = useRef<HTMLAudioElement>(null);

  useEffect(() => { loadOptions().then(setOpts).catch(() => {}); }, []);
  useEffect(() => { setScenes(reel?.scenes || []); setOutro(reel?.outro_voice || ""); }, [reel]);

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label); setError("");
    try { await fn(); } catch (e: any) { setError(e.message); } finally { setBusy(""); }
  }
  const reload = async () => {
    const all = await api<Post[]>(`/api/brands/${post.brand_id}/posts?month=${post.month}`);
    const fresh = all.find((p) => p.id === post.id);
    if (fresh) onChange(fresh);
  };
  const patch = (body: Partial<Omit<Reel, "scenes">> & { scenes?: { text: string; sub: string; voice: string }[] }) =>
    run("بنحفظ…", async () => onChange(await api<Post>(`/api/posts/${post.id}/reel`, { method: "PATCH", body })));
  const saveScenes = () => {
    const changed = JSON.stringify(scenes.map((s) => [s.text, s.sub, s.voice])) !== JSON.stringify((reel?.scenes || []).map((s) => [s.text, s.sub, s.voice]))
      || outro !== (reel?.outro_voice || "");
    if (changed) patch({ scenes: scenes.map(({ text, sub, voice }) => ({ text, sub, voice })), outro_voice: outro });
  };

  const script = (voice?: string) => run("الـ AI بيكتب سكريبت الريل…", async () => {
    await waitJob(await api<Job>(`/api/posts/${post.id}/reel/script`, { body: { voice: voice || reel?.voice } }));
    await reload();
  });
  const photo = (i: number, source: "ai" | "stock") => run(source === "stock" ? "بندور على صورة حقيقية للمشهد…" : "الـ AI بيعمل صورة للمشهد…", async () => {
    await waitJob(await api<Job>(`/api/posts/${post.id}/reel/scenes/${i}/photo`, { body: { source } }));
    await reload();
  });
  const upload = (i: number, f: File) => run("بنرفع الصورة…", async () => {
    const form = new FormData(); form.append("file", f);
    onChange(await api<Post>(`/api/posts/${post.id}/reel/scenes/${i}/upload`, { form }));
  });
  const uploadMusic = (f: File) => run("بنرفع الموسيقى…", async () => {
    const form = new FormData(); form.append("file", f);
    onChange(await api<Post>(`/api/posts/${post.id}/reel/music`, { form }));
  });

  const render = () => run("بنجهز طبقات الكلام…", async () => {
    if (!reel) return;
    const form = new FormData();
    const cv = document.createElement("canvas");
    for (let i = 0; i < scenes.length; i++) {
      await drawReelScene(cv, dna, scenes[i], i, scenes.length);
      form.append("overlays", await canvasBlob(cv), `scene-${i}.png`);
    }
    await drawReelOutro(cv, dna, post.cta);
    form.append("overlays", await canvasBlob(cv), "outro.png");
    setBusy("بنعمل الفيديو: صور، وصوت، وموسيقى… (من نص دقيقة لـ 3 دقايق)");
    await waitJob(await api<Job>(`/api/posts/${post.id}/reel/render`, { form }), undefined, 600_000);
    await reload();
  });

  function playSample(v: string) {
    if (!sampleRef.current || !(v in (opts?.voices || {}))) return;
    sampleRef.current.src = `${API_URL}/api/reels/voice-sample/${v}`;
    sampleRef.current.play().catch(() => setError("مقدرناش نشغل عينة الصوت"));
  }

  const voiceSelect = (value: string, onPick: (v: string) => void) => (
    <div className="row" style={{ gap: 6 }}>
      <select value={value} onChange={(e) => onPick(e.target.value)} aria-label="صوت الريل" style={{ flex: 1 }}>
        <option value="none">من غير صوت</option>
        {Object.entries(opts?.voices || {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      {value !== "none" && <button className="btn sm" type="button" onClick={() => playSample(value)}>اسمع</button>}
    </div>
  );

  if (!reel || !reel.scenes?.length) {
    return (
      <div className="reelbox">
        <b>ريل بصوت وموسيقى</b>
        <p className="small muted">الـ AI يكتب مشاهد الريل والكلام اللي هيتقال، وبعدها تختار الصوت والموسيقى ونعملك فيديو جاهز للنشر.</p>
        <label className="f">صوت التعليق
          {voiceSelect(reel?.voice || "sa_m", (v) => onChange({ ...post, design: { ...post.design, reel: { ...(reel || { music: "calm", scenes: [], outro_voice: "" }), voice: v } as Reel } }))}
        </label>
        <button className="btn sm primary" type="button" disabled={!!busy} onClick={() => script()}>اكتب سكريبت الريل</button>
        <audio ref={sampleRef} hidden />
        {(busy || error) && <p className={`status small ${error ? "err" : ""}`}>{error || busy}</p>}
      </div>
    );
  }

  return (
    <div className="reelbox">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <b>الريل · {scenes.length} مشاهد</b>
        <button className="btn sm" type="button" disabled={!!busy} onClick={() => script()}>اكتب سكريبت جديد</button>
      </div>
      <div className="grid2" style={{ gap: 8 }}>
        <label className="f">الصوت
          {voiceSelect(reel.voice, (v) => patch({ voice: v }))}
        </label>
        <label className="f">الموسيقى
          <div className="row" style={{ gap: 6 }}>
            <select value={reel.music} onChange={(e) => (e.target.value === "upload" ? musicRef.current?.click() : patch({ music: e.target.value }))} aria-label="موسيقى الريل" style={{ flex: 1 }}>
              <option value="none">من غير موسيقى</option>
              {Object.entries(opts?.music || {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              {reel.music_url && <option value="custom">الموسيقى بتاعتك</option>}
              <option value="upload">ارفع موسيقى…</option>
            </select>
          </div>
          <input ref={musicRef} type="file" accept="audio/mpeg,audio/wav,audio/mp4,audio/x-m4a" hidden onChange={(e) => e.target.files?.[0] && uploadMusic(e.target.files[0])} />
        </label>
      </div>
      {reel.voice !== "none" && opts?.voice_provider === "edge" && (
        <p className="small muted">الصوت شغال دلوقتي بخدمة مجانية للتجربة. قبل العملاء اللي بيدفعوا حط مفتاح Azure Speech (مجاني برضه) في الإعدادات.</p>
      )}

      <div className="scenes">
        {scenes.map((s, i) => (
          <div key={i} className="scene">
            <ScenePreview dna={dna} scene={s} index={i} total={scenes.length} />
            <div className="f" style={{ flex: 1 }}>
              <span>مشهد {i + 1}{i === 0 && " · الخطّاف"}</span>
              <input type="text" value={s.text} aria-label={`كلام المشهد ${i + 1} على الشاشة`} placeholder="الكلام على الشاشة"
                onChange={(e) => setScenes(scenes.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))} onBlur={saveScenes} />
              <input type="text" value={s.sub} aria-label={`سطر صغير للمشهد ${i + 1}`} placeholder="سطر صغير (اختياري)"
                onChange={(e) => setScenes(scenes.map((x, j) => (j === i ? { ...x, sub: e.target.value } : x)))} onBlur={saveScenes} />
              {reel.voice !== "none" && (
                <textarea rows={2} value={s.voice} aria-label={`الكلام اللي هيتقال في المشهد ${i + 1}`} placeholder="الكلام اللي الصوت هيقوله"
                  onChange={(e) => setScenes(scenes.map((x, j) => (j === i ? { ...x, voice: e.target.value } : x)))} onBlur={saveScenes} />
              )}
              <div className="row" style={{ gap: 6 }}>
                <button className="btn sm" type="button" disabled={!!busy} onClick={() => photo(i, "stock")}>صورة حقيقية</button>
                <button className="btn sm" type="button" disabled={!!busy} onClick={() => photo(i, "ai")}>صورة بالـ AI</button>
                <button className="btn sm" type="button" disabled={!!busy} onClick={() => fileRefs.current[i]?.click()}>ارفع صورتك</button>
                <input ref={(el) => { fileRefs.current[i] = el; }} type="file" accept="image/png,image/jpeg,image/webp" hidden
                  onChange={(e) => e.target.files?.[0] && upload(i, e.target.files[0])} />
              </div>
              {s.credit && <p className="small muted">الصورة: <a href={s.credit.url} target="_blank" rel="noreferrer">{s.credit.name}</a> على {s.credit.source}</p>}
            </div>
          </div>
        ))}
      </div>
      {reel.voice !== "none" && (
        <label className="f">الجملة الأخيرة مع شعار البراند
          <input type="text" value={outro} onChange={(e) => setOutro(e.target.value)} onBlur={saveScenes} />
        </label>
      )}
      <p className="small muted">المشاهد اللي من غير صورة هنجيبلها صورة حقيقية لوحدنا. صور منتجك الحقيقي دايماً أحسن.</p>

      <div className="row">
        <div className="spacer" />
        <button className="btn sm primary" type="button" disabled={!!busy} onClick={render}>{post.video_url ? "اعمل الفيديو تاني" : "اعمل الفيديو"}</button>
      </div>
      {post.video_url && (
        <div className="reelvideo">
          <video src={post.video_url} controls playsInline preload="metadata" aria-label="فيديو الريل" />
          <div className="row" style={{ gap: 6 }}>
            <a className="btn sm" href={post.video_url} download target="_blank" rel="noreferrer">تحميل MP4</a>
            {reel.duration && <span className="small muted">{Math.round(reel.duration)} ثانية</span>}
          </div>
        </div>
      )}
      <audio ref={sampleRef} hidden />
      {(busy || error) && <p className={`status small ${error ? "err" : ""}`} aria-live="polite">{error || busy}</p>}
    </div>
  );
}
