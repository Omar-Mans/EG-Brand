// Plans shown on the landing page. Proposed prices (docs/research.md §6) until the founders approve them.
export type Market = "EG" | "SA";
export type Plan = { id: string; name: string; price: Record<Market, number>; blurb: string; features: string[]; featured?: boolean };

export const CURRENCY: Record<Market, string> = { EG: "جنيه", SA: "ريال" };

export const PLANS: Plan[] = [
  {
    id: "free", name: "جرّب مجاناً", price: { EG: 0, SA: 0 }, blurb: "شوف النتيجة على مشروعك قبل ما تدفع",
    features: ["دراسة المشروع واستراتيجية 90 يوم", "هوية البراند كاملة", "5 بوستات بتصميم جاهز", "ريل واحد بصوت وموسيقى", "من غير بطاقة دفع"],
  },
  {
    id: "start", name: "بداية", price: { EG: 499, SA: 99 }, blurb: "لمشروع واحد بيبدأ يبني حضوره",
    features: ["براند واحد", "30 بوست في الشهر", "4 ريلز بصوت سعودي أو مصري", "جدولة ونشر على فيسبوك وانستجرام", "الـ Agent بأوامر عربي"],
  },
  {
    id: "grow", name: "نمو", price: { EG: 1299, SA: 249 }, blurb: "الأنسب لمعظم البيزنس", featured: true,
    features: ["كل اللي في بداية", "60 بوست في الشهر", "12 ريل", "خطط إعلانات وحملات Meta (بموافقتك)", "تقرير أسبوعي بالأرقام الحقيقية"],
  },
  {
    id: "agency", name: "وكالة", price: { EG: 3499, SA: 699 }, blurb: "لو بتدير أكتر من عميل",
    features: ["5 براندات", "40 ريل في الشهر", "3 حسابات إعلانات", "3 أعضاء فريق", "لينكات موافقة لعملائك", "دعم على واتساب"],
  },
];
