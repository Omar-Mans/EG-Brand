"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useBrand } from "@/components/BrandFrame";
import { api } from "@/lib/api";
import { DEFAULT_TZ, FORMAT_LABEL, MONTHS, PLATFORMS, STATUS_LABEL, TIMEZONES, WEEKDAYS } from "@/lib/catalog";
import type { Post, SocialAccount } from "@/lib/types";

type BestTimes = { timezone: string; default: string; slots: string[]; note: string };
const METRIC_LABEL: Record<string, string> = { likes: "إعجاب", comments: "تعليق", shares: "مشاركة", reach: "وصول" };

/** Wall-clock "YYYY-MM-DDTHH:MM" of an instant in a timezone. */
function inTz(d: Date, tz: string) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
    timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(d).map((x) => [x.type, x.value]));
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}
const pad = (n: number) => String(n).padStart(2, "0");
function defaultLocal(p: Post, tz: string) {
  if (p.scheduled_at) return inTz(new Date(p.scheduled_at), tz);
  if (p.design?.plan?.local_at) return p.design.plan.local_at;
  const [hh, mm] = p.time.split(":");
  return `${p.month}-${pad(p.day)}T${pad(Number(hh))}:${mm}`;
}

function QueueRow({ post, platforms, tz, best, onChange }: {
  post: Post; platforms: string[]; tz: string; best: BestTimes | null; onChange: (p: Post) => void;
}) {
  const [at, setAt] = useState(defaultLocal(post, tz));
  const [chosen, setChosen] = useState<string[]>(post.platforms.length ? post.platforms : post.design?.plan?.platforms?.length ? post.design.plan.platforms : platforms);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState<string[]>([]);
  const done = post.status === "published" || post.status === "publishing";

  async function call(fn: () => Promise<Post>) {
    setError("");
    try { onChange(await fn()); } catch (e: any) { setError(e.message); }
  }
  const schedule = () => call(() => api<Post>(`/api/posts/${post.id}/schedule`, { body: { local_at: at, platforms: chosen } }));
  const now = () => call(() => api<Post>(`/api/posts/${post.id}/schedule`, { body: { scheduled_at: new Date(Date.now() - 1000).toISOString(), platforms: chosen } }));
  const unschedule = () => call(() => api<Post>(`/api/posts/${post.id}/unschedule`, { method: "POST" }));
  const metrics = () => call(async () => {
    const r = await api<Post & { notes: string[] }>(`/api/posts/${post.id}/metrics`, { method: "POST" });
    setNotes(r.notes || []);
    return r;
  });

  return (
    <tr>
      <td style={{ minWidth: 220 }}>
        <div className="row" style={{ gap: 10, flexWrap: "nowrap" }}>
          {post.image_url && <img src={post.image_url} alt="" width={56} height={56} style={{ borderRadius: 8, objectFit: "cover", flex: "none" }} />}
          <div><b>{post.headline}</b><br /><span className="small muted">{FORMAT_LABEL[post.format]} · {post.pillar}</span></div>
        </div>
        {post.error && <p className="small err">{post.error}</p>}
        {error && <p className="small err">{error}</p>}
        {Object.entries(post.metrics || {}).map(([pl, m]) => (
          <p key={pl} className="small">{PLATFORMS.find((x) => x.id === pl)?.ab || pl}: {Object.entries(m).map(([k, v]) => `${v} ${METRIC_LABEL[k] || k}`).join(" · ") || "لسه مفيش تفاعل"}</p>
        ))}
        {notes.map((n) => <p key={n} className="small muted">{n}</p>)}
      </td>
      <td style={{ minWidth: 220 }}>
        <input type="datetime-local" value={at} disabled={done || post.status === "scheduled"} onChange={(e) => setAt(e.target.value)} aria-label="ميعاد النشر" />
        {best && !done && post.status !== "scheduled" && (
          <div className="row" style={{ gap: 4, marginTop: 6 }}>
            {best.slots.map((s) => <button key={s} type="button" className="btn sm" onClick={() => setAt(`${at.slice(0, 10)}T${s}`)}>{s}</button>)}
          </div>
        )}
      </td>
      <td style={{ minWidth: 150 }}>
        {platforms.length ? platforms.map((pl) => (
          <label key={pl} className="small" style={{ display: "inline-flex", gap: 4, marginInlineEnd: 8 }}>
            <input type="checkbox" disabled={done || post.status === "scheduled"} checked={chosen.includes(pl)} onChange={(e) => setChosen(e.target.checked ? [...chosen, pl] : chosen.filter((x) => x !== pl))} />
            {PLATFORMS.find((x) => x.id === pl)?.ab || pl}
          </label>
        )) : <Link className="small" href="/settings">اربط حساب</Link>}
      </td>
      <td>
        <span className={`tag ${post.status === "published" ? "ok" : post.status === "failed" ? "bad" : post.status === "draft" ? "" : "gold"}`}>{STATUS_LABEL[post.status]}</span>
        {post.scheduled_at && <p className="small muted">{new Date(post.scheduled_at).toLocaleString("ar-EG", { timeZone: tz, dateStyle: "medium", timeStyle: "short" })}</p>}
      </td>
      <td style={{ whiteSpace: "nowrap" }}>
        {post.status === "scheduled" && <button className="btn sm" type="button" onClick={unschedule}>إلغاء الجدولة</button>}
        {(post.status === "draft" || post.status === "failed") && (
          <>
            <button className="btn sm" type="button" disabled={!chosen.length} onClick={schedule}>جدول</button>{" "}
            <button className="btn sm" type="button" disabled={!chosen.length} onClick={now}>انشر الآن</button>
          </>
        )}
        {post.status === "published" && <button className="btn sm" type="button" onClick={metrics}>تحديث الأرقام</button>}
      </td>
    </tr>
  );
}

const STATUS_TABS: [string, string][] = [["all", "الكل"], ["draft", "مستني"], ["scheduled", "مجدولة"], ["published", "منشورة"], ["failed", "فشلت"]];

export default function PublishPage() {
  const { brand } = useBrand();
  const tz = brand.brief.timezone || DEFAULT_TZ[brand.brief.market];
  const [posts, setPosts] = useState<Post[]>([]);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [best, setBest] = useState<BestTimes | null>(null);
  const [platform, setPlatform] = useState("all");
  const [status, setStatus] = useState("all");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [ps, accs] = await Promise.all([api<Post[]>(`/api/brands/${brand.id}/posts`), api<SocialAccount[]>("/api/social/accounts")]);
    setPosts(ps.filter((p) => p.approved || p.status !== "draft"));
    setAccounts(accs);
  }, [brand.id]);
  useEffect(() => {
    load().catch((e) => setError(e.message));
    api<BestTimes>(`/api/brands/${brand.id}/best-times`).then(setBest).catch(() => {});
    const t = setInterval(() => load().catch(() => {}), 15000); // pick up worker results
    return () => clearInterval(t);
  }, [load, brand.id]);

  const connected = Array.from(new Set(accounts.map((a) => a.platform).filter((p) => p !== "meta_ads")));
  const visible = posts.filter((p) => (status === "all" || p.status === status)
    && (platform === "all" || p.platforms.includes(platform) || (p.status === "draft" && (p.design?.plan?.platforms || connected).includes(platform))));
  const months = Array.from(new Set(visible.map((p) => p.month))).sort();
  const update = (np: Post) => setPosts((ps) => ps.map((x) => (x.id === np.id ? np : x)));
  const count = (s: string) => posts.filter((p) => s === "all" || p.status === s).length;

  return (
    <>
      <section className="panel">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div><h2>طابور النشر</h2><p className="small muted">كل المواعيد بـ{TIMEZONES[tz] || tz}</p></div>
          <Link className="btn sm" href="/settings">الحسابات المربوطة ({connected.length})</Link>
        </div>
        {best && <p className="note">أفضل وقت مقترح: <b>{best.slots.join(" · ")}</b>. {best.note}. ده توجيه عام لحد ما يتجمع عندنا أرقام من حسابك.</p>}
        <div className="row" style={{ gap: 6 }}>
          {STATUS_TABS.map(([k, l]) => <button key={k} type="button" className="chip" aria-pressed={status === k} onClick={() => setStatus(k)}>{l} ({count(k)})</button>)}
        </div>
        {connected.length > 0 && (
          <div className="row" style={{ gap: 6 }}>
            <button type="button" className="chip" aria-pressed={platform === "all"} onClick={() => setPlatform("all")}>كل المنصات</button>
            {connected.map((pl) => <button key={pl} type="button" className="chip" aria-pressed={platform === pl} onClick={() => setPlatform(pl)}>{PLATFORMS.find((x) => x.id === pl)?.label || pl}</button>)}
          </div>
        )}
        {error && <p className="status err">{error}</p>}
      </section>
      {!posts.length && <div className="empty"><p>مفيش بوستات معتمدة. اعتمد البوستات من خطة المحتوى، أو اطلب من الـ Agent يجهّز أسبوع.</p><Link className="btn primary" href={`/brands/${brand.id}/content`}>روح للمحتوى</Link></div>}
      {months.map((mk) => {
        const [y, m] = mk.split("-").map(Number);
        const list = visible.filter((p) => p.month === mk);
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
                <tbody>{list.map((p) => <QueueRow key={p.id + p.status} post={p} platforms={connected} tz={tz} best={best} onChange={update} />)}</tbody>
              </table></div>
            </section>
          </div>
        );
      })}
    </>
  );
}
