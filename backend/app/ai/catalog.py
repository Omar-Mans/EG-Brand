"""Shared vocabulary between the AI, the API and the frontend renderer.

The frontend draws logos and posts from these keys (frontend/lib/catalog.ts must list the same values).
"""

FONTS_AR = ["Reem Kufi", "Cairo", "Tajawal", "El Messiri", "Lalezar", "Amiri", "Changa", "Almarai", "Aref Ruqaa", "Rakkas"]
FONTS_EN = ["DM Sans", "Playfair Display", "Montserrat", "Cormorant Garamond"]
ICONS = ["cup", "star8", "arch", "leaf", "drop", "crescent", "spark", "hex", "bag", "chat", "bolt", "sun", "book", "heart"]
STYLES = ["عصري", "فاخر", "شبابي", "بسيط", "تراثي", "تقني"]
PALETTE_ROLES = ["primary", "secondary", "accent", "dark", "light"]

MARKETS = {
    "SA": {"label": "السعودية", "currency": "SAR"},
    "EG": {"label": "مصر", "currency": "EGP"},
}
DIALECTS = {
    "saudi": "سعودي (لهجة بيضاء)",
    "egyptian": "مصري",
    "msa": "فصحى مبسطة",
}
POST_FORMATS = ["post", "reel", "story"]
AD_OBJECTIVES = ["وعي بالبراند", "زيارات للمتجر أو الموقع", "رسائل واتساب", "مبيعات"]
AD_PLATFORMS = ["Instagram + Facebook", "TikTok", "Snapchat", "Google"]
MONTHS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
