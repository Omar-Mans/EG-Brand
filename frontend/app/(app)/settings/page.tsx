"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PLATFORMS } from "@/lib/catalog";
import type { SocialAccount } from "@/lib/types";

type Status = { live: boolean; meta_configured: boolean; platforms: string[]; live_platforms: string[] };
const META_RESULT: Record<string, string> = {
  connected: "اتربطت صفحة Facebook وحساب Instagram بنجاح.",
  cancelled: "الربط اتلغى.",
  expired: "رابط الربط انتهى. جرّب تاني.",
  error: "Meta رفضت الربط",
};

export default function SettingsPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [s, a] = await Promise.all([api<Status>("/api/social/status"), api<SocialAccount[]>("/api/social/accounts")]);
    setStatus(s);
    setAccounts(a);
  }, []);
  useEffect(() => {
    load().catch((e) => setError(e.message));
    const q = new URLSearchParams(window.location.search);
    const r = q.get("meta");
    if (r) setMsg(`${META_RESULT[r] || r}${q.get("reason") ? `: ${q.get("reason")}` : ""}`);
  }, [load]);

  async function connectMeta() {
    try { window.location.href = (await api<{ url: string }>("/api/social/meta/login-url")).url; }
    catch (e: any) { setError(e.message); }
  }
  async function connectMock(platform: string) {
    try { await api("/api/social/mock/connect", { body: { platform } }); await load(); }
    catch (e: any) { setError(e.message); }
  }
  async function disconnect(id: string) {
    try { await api(`/api/social/accounts/${id}`, { method: "DELETE" }); await load(); }
    catch (e: any) { setError(e.message); }
  }

  const byPlatform = (p: string) => accounts.find((a) => a.platform === p);
  const adAccount = byPlatform("meta_ads");
  return (
    <>
      <div><p className="eyebrow">الحسابات</p><h1>ربط السوشيال ميديا</h1></div>
      {msg && <p className="note">{msg}</p>}
      {error && <p className="status err">{error}</p>}
      {status && (
        <section className="panel">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h3>Meta: Facebook + Instagram + الإعلانات</h3>
            {status.live
              ? <button className="btn primary" type="button" onClick={connectMeta}>{byPlatform("facebook") ? "أعد الربط" : "اربط بحساب Meta"}</button>
              : <span className="tag warn">وضع تجريبي</span>}
          </div>
          {status.live
            ? <p className="small muted">هتتنقل لـ Facebook عشان توافق على الصلاحيات، وبعدها بنربط أول صفحة ليها حساب Instagram Business، وحساب الإعلانات لو موجود.</p>
            : <p className="note">ربط Meta الحقيقي محتاج META_APP_ID و META_APP_SECRET في ملف .env للـ backend، وتطبيق Meta عدّى App Review. لحد ده، استخدم الربط التجريبي تحت عشان تجرب الجدولة والنشر.</p>}
          {adAccount && <p className="small">حساب الإعلانات: <b>{adAccount.name}</b></p>}
        </section>
      )}
      <section className="panel"><h3>الحسابات</h3>
        <div className="grid3">
          {PLATFORMS.map((pl) => {
            const a = byPlatform(pl.id);
            const canMock = status && !status.live;
            return (
              <div key={pl.id} className="acct">
                <span className="ic" style={{ background: pl.color }}>{pl.ab}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <b>{pl.label}</b>
                  <p className="small muted">{a ? `${a.name}${a.provider === "mock" ? " · تجريبي" : ""}` : "مش متصل"}</p>
                </div>
                {a ? <button className="btn sm" type="button" onClick={() => disconnect(a.id)}>فصل</button>
                  : canMock ? <button className="btn sm" type="button" onClick={() => connectMock(pl.id)}>ربط تجريبي</button>
                  : <span className="small muted">{status?.live_platforms.includes(pl.id) ? "عن طريق Meta" : "قريباً"}</span>}
              </div>
            );
          })}
        </div>
        <p className="small muted">النشر الحقيقي مدعوم حالياً على Facebook و Instagram. TikTok محتاج Audit من TikTok، و Snapchat و X في المرحلة الجاية.</p>
      </section>
    </>
  );
}
