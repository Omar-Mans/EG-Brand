"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { api, getToken } from "@/lib/api";
import { ICONS } from "@/lib/catalog";
import { CURRENCY, PLANS, type Market } from "@/lib/plans";
import type { Vertical } from "@/lib/types";

const FALLBACK_VERTICALS: Vertical[] = [
  { id: "cars", label: "معارض ووكلاء سيارات", icon: "bolt", pitch: "استفسارات جادة وزيارات للمعرض، مش لايكات" },
  { id: "restaurants", label: "مطاعم وكافيهات", icon: "cup", pitch: "طلبات وحجوزات وزحمة في الأيام الهادية" },
  { id: "clinics", label: "عيادات وتجميل", icon: "heart", pitch: "حجوزات مواعيد وثقة في الدكتور" },
  { id: "real_estate", label: "عقارات ومطورين", icon: "arch", pitch: "عملاء جادين لوحدات معينة، مش متفرجين" },
  { id: "ecommerce", label: "متاجر أونلاين", icon: "bag", pitch: "مبيعات وسلّات شراء، بعائد واضح على الإعلان" },
  { id: "creators", label: "صناع محتوى وبراند شخصي", icon: "spark", pitch: "ريلز منتظمة، متابعين حقيقيين، وفرص تعاون" },
];

const STEPS = [
  ["ندرس مشروعك", "أسئلة زي اللي بتسألها أي وكالة محترمة، وأسئلة مخصوصة لمجالك، وبنقرا موقعك لو موجود."],
  ["نكتبلك الخطة", "استراتيجية 90 يوم: جمهورك، والمنصات، وأنواع المحتوى، والميزانية، والأهداف، مبنية على أرقامك انت."],
  ["نعمل المحتوى", "هوية البراند، وبوستات بخط عربي سليم، وريلز بصوت سعودي أو مصري وموسيقى. انت تراجع وتعدّل."],
  ["ننشر ونقيس", "جدولة ونشر على فيسبوك وانستجرام، وأرقام التفاعل الحقيقية، وخطط إعلانات ما بتصرفش ريال من غير موافقتك."],
];

const FEATURES: [string, string, string, boolean?][] = [
  ["book", "استراتيجية مش بوستات عشوائية", "كل بوست وريل ليه دور في خطة: جمهور محدد، ورسالة واضحة، وهدف بيتقاس."],
  ["star8", "هوية براند كاملة", "اسم ولوجو وألوان وخطوط وطريقة كلام، وكلها بتمشي في كل تصميم بعد كده."],
  ["chat", "خط عربي سليم 100%", "الكلام على التصميم بيتكتب بخطوط عربية حقيقية، فمستحيل يطلع حرف مشوّه زي أدوات الصور العادية."],
  ["sun", "ريلز بصوت سعودي ومصري", "سكريبت وصور وتعليق صوتي باللهجة وموسيقى بدون حقوق، وفيديو جاهز للنشر في دقايق."],
  ["bolt", "Agent بيشتغل مش بيرد", "\"جهزلي محتوى أسبوع وانشر كل يوم 9 بالليل\": بيكتب ويصمم ويجدول، وانت بتوافق."],
  ["bag", "إعلانات بموافقتك", "جمهور وتوزيع ميزانية ونصوص إعلانات، والحملة بتتعمل موقوفة لحد ما تشغّلها بنفسك."],
];

const COMPARE: [string, string, string, string][] = [
  ["بيفهم مشروعك ويكتب خطة", "✓", "نص بس", "✗"],
  ["تصميمات بخط عربي سليم", "✓", "✗", "بإيدك"],
  ["ريلز بصوت سعودي أو مصري", "✓", "✗", "بإيدك"],
  ["ينشر ويجدول لوحده", "✓", "✗", "✗"],
  ["يخطط الإعلانات ويقيس", "✓", "✗", "✗"],
  ["الوقت اللي بتصرفه", "دقايق للمراجعة", "ساعات", "ساعات"],
];

const FAQ: [string, string][] = [
  ["محتاج أعرف تسويق عشان أستخدمه؟", "لأ. المنصة بتسألك عن مشروعك بلغة بسيطة، وبتطلعلك الخطة والمحتوى. انت بس بتراجع وتوافق."],
  ["بيكتب بالعامية فعلاً؟", "أيوه. بتختار مصري أو سعودي أو فصحى مبسطة، والكلام والتعليق الصوتي بيطلعوا باللهجة دي."],
  ["هينشر حاجة من غير ما أشوفها؟", "لأ. مفيش بوست بيتنشر ولا ريال بيتصرف على إعلان من غير موافقتك."],
  ["الصور والموسيقى ليها حقوق؟", "الصور الحقيقية من مكتبات مسموح استخدامها تجارياً، والموسيقى متولّدة جوه المنصة، وصور منتجك انت دايماً أحسن اختيار."],
  ["أقدر أجرب الأول؟", "أيوه. التجربة المجانية بتطلعلك الدراسة والاستراتيجية والهوية و5 بوستات وريل، من غير بطاقة دفع."],
  ["بيشتغل لوكالات؟", "أيوه. باقة الوكالة فيها كذا براند وفريق ولينكات موافقة لعملائك."],
];

function Icon({ name, size = 22 }: { name: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONS[name] || ICONS.spark} />
    </svg>
  );
}

export default function Landing() {
  const [authed, setAuthed] = useState(false);
  const [market, setMarket] = useState<Market>("EG");
  const [verticals, setVerticals] = useState<Vertical[]>(FALLBACK_VERTICALS);
  useEffect(() => {
    setAuthed(!!getToken());
    try { if (Intl.DateTimeFormat().resolvedOptions().timeZone === "Asia/Riyadh") setMarket("SA"); } catch {}
    api<Vertical[]>("/api/verticals").then((v) => v.length && setVerticals(v)).catch(() => {});
  }, []);
  const start = authed ? "/brands" : "/register";

  return (
    <div className="lp">
      <header className="lp-nav wrap">
        <Logo size={34} href="/" />
        <nav className="lp-links" aria-label="أقسام الصفحة">
          <a href="#how">إزاي بيشتغل</a><a href="#features">المميزات</a><a href="#pricing">الأسعار</a><a href="#faq">أسئلة</a>
        </nav>
        <div className="spacer" />
        <ThemeToggle />
        {authed
          ? <Link className="btn primary" href="/brands">لوحة التحكم</Link>
          : <><Link className="btn lp-login" href="/login">دخول</Link><Link className="btn primary" href="/register">ابدأ مجاناً</Link></>}
      </header>

      <section className="lp-hero wrap">
        <div className="lp-hero-text">
          <p className="eyebrow">للبيزنس في مصر والسعودية</p>
          <h1>فريق التسويق بتاعك<br /><span className="hl">بالذكاء الاصطناعي</span>، بالعربي</h1>
          <p className="lp-lead">بيدرس مشروعك، ويكتب خطة 90 يوم، ويعمل الهوية والبوستات والريلز بصوت سعودي أو مصري، وينشر ويخطط إعلاناتك. وانت بتوافق على كل خطوة.</p>
          <div className="row">
            <Link className="btn primary lg" href={start}>ابدأ مجاناً</Link>
            <a className="btn lg" href="#how">شوف إزاي بيشتغل</a>
          </div>
          <p className="small muted">من غير بطاقة دفع · النتيجة الأولى في دقايق</p>
        </div>
        <div className="lp-visual" aria-hidden="true">
          <div className="lp-phone">
            <div className="lp-phone-screen">
              <span className="lp-brandtag">درب للسيارات</span>
              <span className="lp-dots"><i className="on" /><i /><i /></span>
              <span className="lp-cap">بتدور على عربية<br />مضمونة؟</span>
              <span className="lp-voice"><span className="lp-wave"><i /><i /><i /><i /><i /></span>صوت سعودي</span>
            </div>
          </div>
          <div className="lp-float lp-f1">
            <b>استراتيجية 90 يوم</b>
            <span className="lp-bars"><i style={{ width: "35%" }} /><i style={{ width: "25%" }} /><i style={{ width: "25%" }} /><i style={{ width: "15%" }} /></span>
            <span className="small muted">المنتج · الثقة · تعليمي · عروض</span>
          </div>
          <div className="lp-float lp-f2"><span className="tag ok">مجدول</span><b>الخميس 9:00 م</b><span className="small muted">انستجرام · فيسبوك</span></div>
        </div>
      </section>

      <section className="wrap lp-section" id="how">
        <p className="eyebrow">إزاي بيشتغل</p>
        <h2>من فكرة المشروع لأول بوست منشور</h2>
        <ol className="lp-steps">
          {STEPS.map(([t, d], i) => <li key={t}><span className="lp-num">{i + 1}</span><b>{t}</b><p className="muted">{d}</p></li>)}
        </ol>
      </section>

      <section className="wrap lp-section" id="features">
        <p className="eyebrow">المميزات</p>
        <h2>شغل وكالة كاملة، في مكان واحد</h2>
        <div className="lp-grid">
          {FEATURES.map(([icon, t, d]) => (
            <div key={t} className="lp-card"><span className="vi"><Icon name={icon} /></span><b>{t}</b><p className="muted">{d}</p></div>
          ))}
        </div>
      </section>

      <section className="wrap lp-section">
        <p className="eyebrow">لكل نوع بيزنس</p>
        <h2>بيعرف مجالك من أول يوم</h2>
        <p className="muted lp-sub">لكل مجال أسئلة وأنواع محتوى ومواسم وأهداف خاصة بيه، فالخطة بتطلع مناسبة لمشروعك مش عامة.</p>
        <div className="verticals">
          {verticals.map((v) => (
            <Link key={v.id} href={start} className="vcard" style={{ textDecoration: "none", color: "inherit" }}>
              <span className="vi"><Icon name={v.icon} /></span><b>{v.label}</b><span className="small muted">{v.pitch}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="wrap lp-section">
        <p className="eyebrow">المقارنة</p>
        <h2>ليه مش ChatGPT أو برنامج مونتاج؟</h2>
        <div className="tbl lp-compare">
          <table>
            <thead><tr><th /><th className="lp-us">EG Brand</th><th>ChatGPT وأدوات الكتابة</th><th>CapCut وCanva</th></tr></thead>
            <tbody>{COMPARE.map(([k, a, b, c]) => <tr key={k}><td>{k}</td><td className="lp-us">{a}</td><td>{b}</td><td>{c}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="small muted">ChatGPT بيقولك تعمل إيه. EG Brand بيعمله، وانت بتوافق.</p>
      </section>

      <section className="wrap lp-section" id="pricing">
        <p className="eyebrow">الأسعار</p>
        <h2>أقل من تمن فريلانسر، وشغل فريق كامل</h2>
        <div className="row lp-market" role="group" aria-label="السوق">
          <button type="button" className="chip" aria-pressed={market === "EG"} onClick={() => setMarket("EG")}>مصر</button>
          <button type="button" className="chip" aria-pressed={market === "SA"} onClick={() => setMarket("SA")}>السعودية</button>
        </div>
        <div className="lp-plans">
          {PLANS.map((p) => (
            <div key={p.id} className={`lp-plan ${p.featured ? "featured" : ""}`}>
              {p.featured && <span className="lp-badge">الأكثر اختياراً</span>}
              <b className="lp-plan-name">{p.name}</b>
              <p className="lp-price">{p.price[market] === 0 ? "مجاناً" : <>{p.price[market].toLocaleString("en-US")} <span>{CURRENCY[market]} / شهر</span></>}</p>
              <p className="small muted">{p.blurb}</p>
              <ul className="lp-feat">{p.features.map((f) => <li key={f}>{f}</li>)}</ul>
              <Link className={`btn ${p.featured ? "primary" : ""}`} href={start}>{p.price[market] === 0 ? "ابدأ التجربة" : "اشترك"}</Link>
            </div>
          ))}
        </div>
        <p className="small muted">سعر المؤسسين: أول 50 مشترك خصم 30% وسعرهم ثابت لمدة سنة.</p>
      </section>

      <section className="wrap lp-section" id="faq">
        <p className="eyebrow">أسئلة</p>
        <h2>أسئلة بتتسأل كتير</h2>
        <div className="lp-faq">
          {FAQ.map(([q, a]) => <details key={q}><summary>{q}</summary><p className="muted">{a}</p></details>)}
        </div>
      </section>

      <section className="wrap lp-cta">
        <h2>جرّب على مشروعك النهارده</h2>
        <p>الدراسة والاستراتيجية والهوية وأول بوستات وريل، ببلاش.</p>
        <Link className="btn primary lg" href={start}>ابدأ مجاناً</Link>
      </section>

      <footer className="wrap lp-foot">
        <Logo size={26} />
        <span className="small muted">© {new Date().getFullYear()} EG Brand</span>
        <div className="spacer" />
        <Link className="small muted" href="/login">دخول</Link>
      </footer>
    </div>
  );
}
