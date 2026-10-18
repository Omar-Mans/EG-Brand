"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useBrand } from "@/components/BrandFrame";
import { api } from "@/lib/api";
import { FORMAT_LABEL, MONTHS, PLATFORMS, STATUS_LABEL, WEEKDAYS } from "@/lib/catalog";
import type { Post, SocialAccount } from "@/lib/types";

const pad = (n: number) => String(n).padStart(2, "0");
function localInput(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function defaultAt(p: Post) {
  const [y, m] = p.month.split("-").map(Number);
  const [hh, mm] = p.time.split(":").map(Number);
  return localInput(new Date(y, m - 1, p.day, hh, mm));
}

function QueueRow({ post, accounts, onChange }: { post: Post; accounts: SocialAccount[]; onChange: (p: Post) => void }) {
  const platforms = accounts.map((a) => a.platform).filter((p) => p !== "meta_ads");
  const [at, setAt] = useState(post.scheduled_at ? localInput(new Date(post.scheduled_at)) : defaultAt(post));
  const [chosen, setChosen] = useState<string[]>(post.platforms.length ? post.platforms : platforms.filter((p) => p === "instagram" || p === "facebook"));
  const [error, setError] = useState("");
  const done = post.status === "published" || post.status === "publishing";

  async function schedule(now: boolean) {
    setError("");
    try {
      const when = now ? new Date(Date.now() - 1000) : new Date(at);
      onChange(await api<Post>(`/api/posts/${post.id}/schedule`, { body: { scheduled_at: when.toISOString(), platforms: chosen } }));
    } catch (e: any) { setError(e.message); }
  }
  async function unschedule() {
    try { onChange(await api<Post>(`/api/posts/${post.id}/unschedule`, { method: "POST" })); } catch (e: any) { setError(e.message); }
  }

  return (
    <tr>
      <td style={{ minWidth: 180 }}><b>{post.headline}</b><br /><span className="small muted">{FORMAT_LABEL[post.format]} · {post.pillar}</span>
        {post.error && <p className="small err">{post.error}</p>}
        {error && <p className="small err">{error}</p>}</td>
      <td style={{ minWidth: 200 }}><input type="datetime-local" value={at} disabled={done} onChange={(e) => setAt(e.target.value)} aria-label="ميعاد النشر" /></td>
      <td style={{ minWidth: 170 }}>
        {platforms.length ? platforms.map((pl) => (
          <label key={pl} className="small" style={{ display: "inline-flex", gap: 4, marginInlineEnd: 8 }}>
            <input type="checkbox" disabled={done} checked={chosen.includes(pl)} onChange={(e) => setChosen(e.target.checked ? [...chosen, pl] : chosen.filter((x) => x !== pl))} />
            {PLATFORMS.find((x) => x.id === pl)?.ab || pl}
          </label>
        )) : <span className="small muted">مفيش حسابات</span>}
      </td>
      <td><span className={`tag ${post.status === "published" ? "ok" : post.status === "failed" ? "bad" : post.status === "draft" ? "" : "gold"}`}>{STATUS_LABEL[post.status]}</span></td>
      <td style={{ whiteSpace: "nowrap" }}>
        {post.status === "scheduled" && <button className="btn sm" type="button" onClick={unschedule}>إلغاء الجدولة</button>}
        {(post.status === "draft" || post.status === "failed") && (
          <>
            <button className="btn sm" type="button" disabled={!chosen.length} onClick={() => schedule(false)}>جدول</button>{" "}
            <button className="btn sm" type="button" disabled={!chosen.length} onClick={() => schedule(true)}>انشر الآن</button>
          </>
        )}
      </td>
    </tr>
  );
}

export default function PublishPage() {
  const { brand } = useBrand();
  const [posts, setPosts] = useState<Post[]>([]);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [ps, accs] = await Promise.all([api<Post[]>(`/api/brands/${brand.id}/posts`), api<SocialAccount[]>("/api/social/accounts")]);
    setPosts(ps.filter((p) => p.approved || p.status !== "draft"));
    setAccounts(accs);
  }, [brand.id]);
  useEffect(() => {
    load().catch((e) => setError(e.message));
    const t = setInterval(() => load().catch(() => {}), 15000); // pick up worker results
    return () => clearInterval(t);
  }, [load]);

  const months = Array.from(new Set(posts.map((p) => p.month))).sort();
  const update = (np: Post) => setPosts((ps) => ps.map((x) => (x.id === np.id ? np : x)));

  return (
    <>
      <section className="panel">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2>طابور النشر</h2>
          <Link className="btn sm" href="/settings">الحسابات المربوطة ({accounts.filter((a) => a.platform !== "meta_ads").length})</Link>
        </div>
        <p className="note">الـ Worker بيتشيك كل شوية على البوستات اللي ميعادها جه وينشرها. الحالة هنا بتتحدث لوحدها كل 15 ثانية.</p>
        {error && <p className="status err">{error}</p>}
      </section>
      {!posts.length && <div className="empty"><p>مفيش بوستات معتمدة. اعتمد البوستات من خطة المحتوى.</p><Link className="btn primary" href={`/brands/${brand.id}/content`}>روح للمحتوى</Link></div>}
      {months.map((mk) => {
        const [y, m] = mk.split("-").map(Number);
        const list = posts.filter((p) => p.month === mk);
        const first = new Date(y, m - 1, 1).getDay(), dim = new Date(y, m, 0).getDate();
        return (
          <div key={mk} className="grid2" style={{ gridTemplateColumns: "minmax(0,1fr)" }}>
            <section className="panel"><h3>{MONTHS[m - 1]} {y}</h3>
              <div className="cal">
                {WEEKDAYS.map((w) => <div key={w} className="h">{w}</div>)}
                {Array.from({ length: first }, (_, i) => <div key={`e${i}`} style={{ background: "none" }} />)}
                {Array.from({ length: dim }, (_, i) => (
                  <div key={i}><span>{i + 1}</span>
                    {list.filter((p) => p.day === i + 1).map((p) => (
                      <i key={p.id} title={p.headline} style={{ background: p.status === "published" ? "var(--ok)" : p.status === "scheduled" ? "var(--gold)" : p.status === "failed" ? "var(--bad)" : "var(--line)" }} />
                    ))}
                  </div>
                ))}
              </div>
              <p className="small muted">رمادي: معتمد ومش مجدول · ذهبي: مجدول · أخضر: اتنشر · أحمر: فشل</p>
            </section>
            <section className="panel">
              <div className="tbl"><table>
                <thead><tr><th>البوست</th><th>الميعاد</th><th>المنصات</th><th>الحالة</th><th /></tr></thead>
                <tbody>{list.map((p) => <QueueRow key={p.id + p.status} post={p} accounts={accounts} onChange={update} />)}</tbody>
              </table></div>
            </section>
          </div>
        );
      })}
    </>
  );
}
