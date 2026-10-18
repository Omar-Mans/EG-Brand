"use client";

import { useEffect, useRef, useState } from "react";
import { api, waitJob } from "@/lib/api";
import { FORMAT_LABEL, LAYOUTS, MONTHS, PLATFORMS, STATUS_LABEL } from "@/lib/catalog";
import { canvasBlob, downloadCanvas, drawPost, nameOf } from "@/lib/render";
import type { Dna, Job, Post } from "@/lib/types";

type Draft = { headline: string; caption: string; cta: string; subheadline: string; badge: string };
const toDraft = (p: Post): Draft => ({
  headline: p.headline, caption: p.caption, cta: p.cta, subheadline: p.design?.subheadline || "", badge: p.design?.badge || "",
});

export default function PostCard({ post, dna, onChange }: { post: Post; dna: Dna; onChange: (p: Post) => void }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<Draft>(toDraft(post));
  const [instr, setInstr] = useState("");
  const [imgPrompt, setImgPrompt] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(false);
  const [copied, setCopied] = useState(false);
  const locked = post.status === "publishing" || post.status === "published" || post.status === "scheduled";
  const month = Number(post.month.split("-")[1]);
  const view = { ...post, headline: draft.headline, cta: draft.cta, design: { ...post.design, subheadline: draft.subheadline, badge: draft.badge } };

  useEffect(() => setDraft(toDraft(post)), [post]);
  useEffect(() => {
    if (ref.current) drawPost(ref.current, dna, view);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dna, post, draft.headline, draft.cta, draft.subheadline, draft.badge, preview]); // preview swaps the canvas element

  async function run<T>(label: string, fn: () => Promise<T>) {
    setBusy(label); setError("");
    try { return await fn(); } catch (e: any) { setError(e.message); } finally { setBusy(""); }
  }
  const patch = (body: Record<string, unknown>) => run("بنحفظ…", async () => onChange(await api<Post>(`/api/posts/${post.id}`, { method: "PATCH", body })));
  const reload = async () => {
    const all = await api<Post[]>(`/api/brands/${post.brand_id}/posts?month=${post.month}`);
    const fresh = all.find((p) => p.id === post.id);
    if (fresh) onChange(fresh);
  };

  async function saveText() {
    const t = toDraft(post);
    if (JSON.stringify(t) !== JSON.stringify(draft)) await patch(draft);
  }

  async function approve() {
    if (!ref.current) return;
    await run("بنجهّز التصميم ونرفعه…", async () => {
      const t = toDraft(post);
      if (JSON.stringify(t) !== JSON.stringify(draft)) await api<Post>(`/api/posts/${post.id}`, { method: "PATCH", body: draft });
      await drawPost(ref.current!, dna, view);
      const form = new FormData();
      form.append("file", await canvasBlob(ref.current!), `post-${post.day}.png`);
      await api<Post>(`/api/posts/${post.id}/image`, { form });
      onChange(await api<Post>(`/api/posts/${post.id}`, { method: "PATCH", body: { approved: true } }));
    });
  }

  const aiImage = () => run("الـ AI بيعمل صورة للبوست… (ممكن ياخد دقيقة)", async () => {
    await waitJob(await api<Job>(`/api/posts/${post.id}/background`, { body: { prompt: imgPrompt } }));
    await reload();
  });

  const uploadImage = (f: File) => run("بنرفع الصورة…", async () => {
    const form = new FormData();
    form.append("file", f);
    onChange(await api<Post>(`/api/posts/${post.id}/background/upload`, { form }));
  });

  const rewrite = () => run("الـ AI بيعيد الصياغة…", async () => {
    await waitJob(await api<Job>(`/api/posts/${post.id}/regenerate`, { body: { instruction: instr } }));
    await reload();
    setInstr("");
  });

  async function copyCaption() {
    const text = `${post.caption}\n\n${post.hashtags.join(" ")}`;
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { setError("انسخ الكابشن يدوياً"); }
  }

  const plan = post.design?.plan;
  const n = nameOf(dna);
  return (
    <article className={`card ${post.approved ? "approved" : ""}`}>
      <div className="meta">
        <span className="tag">{post.day} {MONTHS[month - 1]} · {post.time}</span>
        <span className="tag">{FORMAT_LABEL[post.format] || post.format}</span>
        {post.pillar && <span className="tag">{post.pillar}</span>}
        {post.occasion && <span className="tag gold">{post.occasion}</span>}
        {plan && post.status === "draft" && (
          <span className="tag gold" title="الـ Agent حدد الميعاد. أول ما تعتمد البوست هيتجدول لوحده">
            مخطط {plan.local_at.replace("T", " ")} · {plan.platforms.map((p) => PLATFORMS.find((x) => x.id === p)?.ab || p).join(" ")}
          </span>
        )}
        {post.approved && <span className="tag ok">معتمد</span>}
        {post.status !== "draft" && <span className={`tag ${post.status === "failed" ? "bad" : post.status === "published" ? "ok" : "gold"}`}>{STATUS_LABEL[post.status]}</span>}
      </div>

      {preview ? (
        <div className="fbpost">
          <div className="fbhead"><span className="fbav">{n.ar.slice(0, 2)}</span><div><b>{n.ar}</b><p className="small muted">منشور · عام</p></div></div>
          <p className="fbcap">{draft.caption}</p>
          <p className="fbtags" dir="auto">{post.hashtags.join(" ")}</p>
          <div className="canvasbox" style={{ padding: 0, borderRadius: 0 }}><canvas ref={ref} className={post.format === "post" ? "" : "story"} aria-label={`تصميم: ${draft.headline}`} /></div>
        </div>
      ) : (
        <div className="canvasbox"><canvas ref={ref} className={post.format === "post" ? "" : "story"} aria-label={`تصميم: ${draft.headline}`} /></div>
      )}

      <div className="row" style={{ gap: 6 }}>
        <button className="btn sm" type="button" onClick={() => setPreview(!preview)}>{preview ? "التصميم بس" : "معاينة كبوست"}</button>
        <button className="btn sm" type="button" onClick={copyCaption}>{copied ? "اتنسخ ✓" : "نسخ الكابشن"}</button>
        <button className="btn sm" type="button" onClick={() => ref.current && downloadCanvas(ref.current, `post-${post.day}.png`)}>PNG</button>
      </div>

      {!locked && (
        <>
          <div className="row" style={{ gap: 6 }}>
            <label className="f" style={{ flex: 1, minWidth: 140 }}>شكل التصميم
              <select value={post.design?.layout || "bold"} onChange={(e) => patch({ layout: e.target.value })}>
                {Object.entries(LAYOUTS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
            <div className="f"><span>صورة الخلفية</span>
              <div className="row" style={{ gap: 6 }}>
                <button className="btn sm" type="button" disabled={!!busy} onClick={aiImage}>صورة بالـ AI</button>
                <button className="btn sm" type="button" disabled={!!busy} onClick={() => fileRef.current?.click()}>ارفع صورتك</button>
                <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => e.target.files?.[0] && uploadImage(e.target.files[0])} />
              </div>
            </div>
          </div>
          <details>
            <summary>وصف الصورة اللي عايزها (اختياري)</summary>
            <input type="text" style={{ marginTop: 8 }} value={imgPrompt} onChange={(e) => setImgPrompt(e.target.value)}
              placeholder={post.design?.visual_prompt || "مثلاً: عربية SUV بيضا في معرض، إضاءة ناعمة"} aria-label="وصف صورة الخلفية" />
          </details>
          <label className="f">العنوان على التصميم
            <input type="text" value={draft.headline} onChange={(e) => setDraft({ ...draft, headline: e.target.value })} onBlur={saveText} />
          </label>
          <div className="grid2" style={{ gap: 8 }}>
            <label className="f">السطر التاني
              <input type="text" value={draft.subheadline} onChange={(e) => setDraft({ ...draft, subheadline: e.target.value })} onBlur={saveText} />
            </label>
            <label className="f">الشارة (خصم، جديد…)
              <input type="text" value={draft.badge} onChange={(e) => setDraft({ ...draft, badge: e.target.value })} onBlur={saveText} />
            </label>
          </div>
          <label className="f">زرار الدعوة (CTA)
            <input type="text" value={draft.cta} onChange={(e) => setDraft({ ...draft, cta: e.target.value })} onBlur={saveText} />
          </label>
          <label className="f">الكابشن
            <textarea rows={3} value={draft.caption} onChange={(e) => setDraft({ ...draft, caption: e.target.value })} onBlur={saveText} />
          </label>
          <details>
            <summary>عدّل الكلام بالـ AI</summary>
            <div className="row" style={{ marginTop: 8 }}>
              <input type="text" value={instr} onChange={(e) => setInstr(e.target.value)} placeholder="مثلاً: خليه أقصر وأكتر حماس" aria-label="تعليمات التعديل" style={{ flex: 1 }} />
              <button className="btn sm" type="button" disabled={!!busy} onClick={rewrite}>أعد الصياغة</button>
            </div>
          </details>
        </>
      )}
      {locked && <p className="small muted" style={{ whiteSpace: "pre-wrap" }}>{post.caption}</p>}

      {(busy || error) && <p className={`status small ${error ? "err" : ""}`}>{error || busy}</p>}
      {!locked && (
        <div className="row">
          <div className="spacer" />
          {post.approved
            ? <button className="btn sm" type="button" onClick={() => patch({ approved: false })}>إلغاء الاعتماد</button>
            : <button className="btn sm primary" type="button" disabled={!!busy} onClick={approve}>{plan ? "اعتمد وجدول" : "اعتمد"}</button>}
        </div>
      )}
    </article>
  );
}
