"use client";

import { useEffect, useRef, useState } from "react";
import { api, waitJob } from "@/lib/api";
import { FORMAT_LABEL, MONTHS, STATUS_LABEL } from "@/lib/catalog";
import { canvasBlob, downloadCanvas, drawPost } from "@/lib/render";
import type { Dna, Job, Post } from "@/lib/types";

export default function PostCard({ post, dna, onChange }: { post: Post; dna: Dna; onChange: (p: Post) => void }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [draft, setDraft] = useState({ headline: post.headline, caption: post.caption });
  const [instr, setInstr] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const locked = post.status === "publishing" || post.status === "published";
  const month = Number(post.month.split("-")[1]);

  useEffect(() => setDraft({ headline: post.headline, caption: post.caption }), [post.headline, post.caption]);
  useEffect(() => {
    if (ref.current) drawPost(ref.current, dna, { ...post, headline: draft.headline });
  }, [dna, post, draft.headline]);

  async function patch(body: Partial<Post>) {
    setError("");
    try { onChange(await api<Post>(`/api/posts/${post.id}`, { method: "PATCH", body })); }
    catch (e: any) { setError(e.message); }
  }

  async function saveText() {
    if (draft.headline !== post.headline || draft.caption !== post.caption) await patch(draft);
  }

  async function approve() {
    if (!ref.current) return;
    setBusy("بنرفع التصميم…"); setError("");
    try {
      await saveText();
      await drawPost(ref.current, dna, { ...post, headline: draft.headline });
      const form = new FormData();
      form.append("file", await canvasBlob(ref.current), `post-${post.day}.png`);
      await api<Post>(`/api/posts/${post.id}/image`, { form });
      onChange(await api<Post>(`/api/posts/${post.id}`, { method: "PATCH", body: { approved: true } }));
    } catch (e: any) { setError(e.message); }
    finally { setBusy(""); }
  }

  async function regenerate() {
    setBusy("الـ AI بيعيد الصياغة…"); setError("");
    try {
      await waitJob(await api<Job>(`/api/posts/${post.id}/regenerate`, { body: { instruction: instr } }));
      const all = await api<Post[]>(`/api/brands/${post.brand_id}/posts?month=${post.month}`);
      const fresh = all.find((p) => p.id === post.id);
      if (fresh) onChange(fresh);
      setInstr("");
    } catch (e: any) { setError(e.message); }
    finally { setBusy(""); }
  }

  return (
    <article className={`card ${post.approved ? "approved" : ""}`}>
      <div className="meta">
        <span className="tag">{post.day} {MONTHS[month - 1]} · {post.time}</span>
        <span className="tag">{FORMAT_LABEL[post.format] || post.format}</span>
        {post.pillar && <span className="tag">{post.pillar}</span>}
        {post.occasion && <span className="tag gold">{post.occasion}</span>}
        {post.approved && <span className="tag ok">معتمد</span>}
        {post.status !== "draft" && <span className={`tag ${post.status === "failed" ? "bad" : post.status === "published" ? "ok" : "gold"}`}>{STATUS_LABEL[post.status]}</span>}
      </div>
      <div className="canvasbox"><canvas ref={ref} className={post.format === "post" ? "" : "story"} aria-label={`تصميم: ${draft.headline}`} /></div>
      <label className="f">العنوان على التصميم
        <input type="text" value={draft.headline} disabled={locked} onChange={(e) => setDraft({ ...draft, headline: e.target.value })} onBlur={saveText} />
      </label>
      <label className="f">الكابشن
        <textarea rows={3} value={draft.caption} disabled={locked} onChange={(e) => setDraft({ ...draft, caption: e.target.value })} onBlur={saveText} />
      </label>
      <p className="small muted" dir="auto">{post.hashtags.join(" ")} · {post.cta}</p>
      {!locked && (
        <details>
          <summary>عدّل بالـ AI</summary>
          <div className="row" style={{ marginTop: 8 }}>
            <input type="text" value={instr} onChange={(e) => setInstr(e.target.value)} placeholder="مثلاً: خليه أقصر وأكتر حماس" aria-label="تعليمات التعديل" style={{ flex: 1 }} />
            <button className="btn sm" type="button" disabled={!!busy} onClick={regenerate}>أعد الصياغة</button>
          </div>
        </details>
      )}
      {(busy || error) && <p className={`status small ${error ? "err" : ""}`}>{error || busy}</p>}
      <div className="row">
        {!locked && <button className="btn sm" type="button" onClick={() => patch({ template: (post.template + 1) % 3 })}>غيّر القالب</button>}
        <button className="btn sm" type="button" onClick={() => ref.current && downloadCanvas(ref.current, `post-${post.day}.png`)}>PNG</button>
        <div className="spacer" />
        {!locked && (post.approved
          ? <button className="btn sm" type="button" onClick={() => patch({ approved: false })}>إلغاء الاعتماد</button>
          : <button className="btn sm primary" type="button" disabled={!!busy} onClick={approve}>اعتمد</button>)}
      </div>
    </article>
  );
}
