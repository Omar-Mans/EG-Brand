// Must match backend/app/ai/catalog.py
export const FONTS_AR = ["Reem Kufi", "Cairo", "Tajawal", "El Messiri", "Lalezar", "Amiri", "Changa", "Almarai", "Aref Ruqaa", "Rakkas"];
export const FONTS_EN = ["DM Sans", "Playfair Display", "Montserrat", "Cormorant Garamond"];

export const ICONS: Record<string, string> = {
  cup: "M22 38h46v16c0 15-10 26-23 26S22 69 22 54z M68 44h5a9 9 0 0 1 0 18h-6 M36 16c-5 5 5 9 0 15 M50 16c-5 5 5 9 0 15",
  star8: "M24 24h52v52H24z M50 13L87 50L50 87L13 50z",
  arch: "M26 86V46a24 24 0 0 1 48 0v40 M40 86V56a10 10 0 0 1 20 0v30 M18 86h64",
  leaf: "M20 80C20 40 45 18 82 18c0 37-22 62-62 62z M20 80L60 40",
  drop: "M50 14C50 14 24 46 24 62a26 26 0 0 0 52 0C76 46 50 14 50 14z",
  crescent: "M62 16a34 34 0 1 0 22 52A28 28 0 1 1 62 16z",
  spark: "M50 10C54 38 62 46 90 50C62 54 54 62 50 90C46 62 38 54 10 50C38 46 46 38 50 10z",
  hex: "M50 12L83 31V69L50 88L17 69V31z M50 32L66 41V59L50 68L34 59V41z",
  bag: "M24 36h52l-5 48H29z M38 36v-6a12 12 0 0 1 24 0v6",
  chat: "M18 24h64v40H46L30 78V64H18z M34 44h32",
  bolt: "M56 10L24 56h24l-6 34 34-48H52z",
  sun: "M66 50a16 16 0 1 1-32 0a16 16 0 1 1 32 0z M50 12v10 M50 78v10 M12 50h10 M78 50h10 M23 23l7 7 M70 70l7 7 M77 23l-7 7 M30 70l-7 7",
  book: "M50 26c-10-6-22-8-32-6v56c10-2 22 0 32 6c10-6 22-8 32-6V20c-10-2-22 0-32 6z M50 26v56",
  heart: "M50 82S16 62 16 38a16 16 0 0 1 34-6a16 16 0 0 1 34 6c0 24-34 44-34 44z",
};

export const ICON_LABELS: Record<string, string> = {
  cup: "فنجان", star8: "نجمة ثمانية", arch: "قوس", leaf: "ورقة", drop: "قطرة", crescent: "هلال", spark: "لمعة",
  hex: "سداسي", bag: "شنطة", chat: "محادثة", bolt: "برق", sun: "شمس", book: "كتاب", heart: "قلب",
};

export const STYLES = ["عصري", "فاخر", "شبابي", "بسيط", "تراثي", "تقني"];
export const PREF_COLORS: [string, string][] = [
  ["ذهبي", "#D4A23C"], ["كحلي", "#1F3A5F"], ["أخضر", "#2E7D4F"], ["أحمر", "#C0392B"], ["بنفسجي", "#6C4AB6"],
  ["تيل", "#14808A"], ["أسود", "#1A1A1A"], ["برتقالي", "#E07B24"], ["وردي", "#D86A8A"], ["بيج", "#D9C3A0"],
];
export const MARKETS = { EG: { label: "مصر", cur: "EGP" }, SA: { label: "السعودية", cur: "SAR" } } as const;
export const DIALECTS = { egyptian: "مصري", saudi: "سعودي (لهجة بيضاء)", msa: "فصحى مبسطة" } as const;
export const MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
export const WEEKDAYS = ["أحد", "اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت"];
export const FORMAT_LABEL: Record<string, string> = { post: "بوست", reel: "ريلز", story: "ستوري" };
export const PLATFORMS = [
  { id: "instagram", label: "Instagram", color: "#C13584", ab: "IG" },
  { id: "facebook", label: "Facebook", color: "#1877F2", ab: "FB" },
  { id: "tiktok", label: "TikTok", color: "#111111", ab: "TT" },
  { id: "snapchat", label: "Snapchat", color: "#B59A00", ab: "SC" },
  { id: "x", label: "X", color: "#333333", ab: "X" },
];
export const AD_OBJECTIVES = ["وعي بالبراند", "زيارات للمتجر أو الموقع", "رسائل واتساب", "مبيعات"];
export const AD_PLATFORMS = ["Instagram + Facebook", "TikTok", "Snapchat", "Google"];
export const FEATURE_LABEL: Record<string, string> = { dna: "هوية البراند", calendar: "خطة المحتوى", regen: "إعادة صياغة بوست", ads: "خطة إعلانية" };
export const STATUS_LABEL: Record<string, string> = { draft: "مش مجدول", scheduled: "مجدول", publishing: "بيتنشر", published: "اتنشر", failed: "فشل" };
