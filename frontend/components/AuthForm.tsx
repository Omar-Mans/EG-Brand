"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, setToken } from "@/lib/api";

export default function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [form, setForm] = useState({ company_name: "", name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = mode === "login" ? { email: form.email, password: form.password } : form;
      const res = await api<{ token: string }>(`/api/auth/${mode}`, { body });
      setToken(res.token);
      router.replace("/brands");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="wrap">
      <form className="panel auth" onSubmit={submit}>
        <p className="mark">EG <b>Brand</b></p>
        <h2>{mode === "login" ? "تسجيل الدخول" : "حساب جديد لشركتك"}</h2>
        {mode === "register" && (
          <>
            <label className="f" htmlFor="company">اسم الشركة<input id="company" type="text" required minLength={2} value={form.company_name} onChange={set("company_name")} /></label>
            <label className="f" htmlFor="name">اسمك<input id="name" type="text" value={form.name} onChange={set("name")} /></label>
          </>
        )}
        <label className="f" htmlFor="email">الإيميل<input id="email" type="email" required value={form.email} onChange={set("email")} autoComplete="email" /></label>
        <label className="f" htmlFor="password">كلمة السر{mode === "register" ? " (8 حروف على الأقل)" : ""}
          <input id="password" type="password" required minLength={mode === "register" ? 8 : 1} value={form.password} onChange={set("password")} autoComplete={mode === "login" ? "current-password" : "new-password"} />
        </label>
        <button className="btn primary" type="submit" disabled={busy}>{mode === "login" ? "دخول" : "اعمل الحساب"}</button>
        {error && <p className="status err">{error}</p>}
        <p className="small muted">
          {mode === "login" ? <>معندكش حساب؟ <Link href="/register">اعمل حساب</Link></> : <>عندك حساب؟ <Link href="/login">سجّل دخول</Link></>}
        </p>
      </form>
    </div>
  );
}
