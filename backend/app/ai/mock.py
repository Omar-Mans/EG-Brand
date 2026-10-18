"""Deterministic sample outputs used when no AI provider key is configured (local dev, tests, demos)."""


def brand_dna(brief: dict) -> dict:
    name = (brief.get("name") or "").strip() or "نورا"
    return {
        "names": [
            {"ar": name, "en": "Noura" if name == "نورا" else "Brand", "meaning": "اسم قصير وسهل يتقال ويتفتكر"},
            {"ar": "حَبّة", "en": "Habba", "meaning": "اسم مرح ومرتبط بالمنتج"},
            {"ar": "مِحماس", "en": "Mihmas", "meaning": "اسم تراثي بلمسة حديثة"},
        ],
        "tagline_ar": "نورك في فنجان", "tagline_en": "Your light, in a cup",
        "positioning": "براند قريب من الشباب بجودة عالية وسعر مناسب",
        "audience": "شباب من 18 لـ 30 سنة بيدوروا على تجربة مختلفة",
        "personality": ["دافي", "شبابي", "مرح", "أصيل"],
        "tone": "ودود وخفيف ومن غير مبالغة",
        "voice_do": ["كلّم العميل كأنه صاحبك", "اذكر تفاصيل المنتج", "استخدم جمل قصيرة"],
        "voice_dont": ["ما تستخدمش مصطلحات معقدة", "ما تبالغش في الوعود", "ما تكترش الإيموجي"],
        "palette": [
            {"role": "primary", "name": "كراميل", "hex": "#C8742B"},
            {"role": "secondary", "name": "أخضر نخيل", "hex": "#2E4B3C"},
            {"role": "accent", "name": "ذهبي", "hex": "#F2C14E"},
            {"role": "dark", "name": "بن محمّص", "hex": "#1E1A17"},
            {"role": "light", "name": "حليب", "hex": "#F6EFE6"},
        ],
        "font_ar": "Reem Kufi", "font_en": "DM Sans", "icon": "cup",
        "pillars": [
            {"name": "لحظات يومية", "share": 40}, {"name": "المنتج", "share": 30},
            {"name": "القصة", "share": 20}, {"name": "عروض", "share": 10},
        ],
    }


def calendar(days_in_month: int, occasions: list[dict], count: int = 12) -> list[dict]:
    formats = ["post", "reel", "post", "story", "post", "post", "reel", "post", "story", "post", "post", "reel"]
    pillars = ["لحظات يومية", "القصة", "المنتج", "لحظات يومية", "عروض", "القصة", "لحظات يومية", "المنتج", "عروض", "القصة", "عروض", "لحظات يومية"]
    step = max(1, days_in_month // count)
    posts = [{
        "day": min(days_in_month, 1 + i * step), "time": ["09:00", "13:00", "19:30"][i % 3],
        "format": formats[i % len(formats)], "pillar": pillars[i % len(pillars)], "occasion": "",
        "headline": ["صباحك نور", "من الفكرة للفنجان", "جديدنا وصل", "وين تقعد اليوم؟"][i % 4],
        "caption": "سطر أول قصير يشد الانتباه.\nسطر تاني فيه التفاصيل والدعوة.",
        "hashtags": ["#براند", "#عروض", "#جديد"], "cta": "زورونا اليوم",
    } for i in range(count)]
    for occ in occasions:  # move the nearest free post onto each occasion
        free = [p for p in posts if not p["occasion"]]
        if not free:
            break
        nearest = min(free, key=lambda p: abs(p["day"] - occ["day"]))
        nearest.update(day=occ["day"], occasion=occ["title"], headline=occ["title"], pillar="عروض")
    return sorted(posts, key=lambda p: p["day"])


def rewrite_post(post: dict) -> dict:
    return {**{k: post.get(k) for k in ("headline", "caption", "hashtags", "cta")}, "caption": (post.get("caption") or "") + "\n(نسخة معدّلة)"}


def ads_plan(platforms: list[str]) -> dict:
    share = round(100 / max(1, len(platforms)))
    return {
        "audience": {"age": "18-30", "gender": "الكل", "locations": ["الرياض"], "interests": ["القهوة", "المذاكرة", "الخروجات"]},
        "split": [{"platform": p, "pct": share, "why": "مناسبة لجمهور البراند"} for p in platforms],
        "ads": [{"platform": platforms[0], "headline": f"عرض رقم {i + 1}", "primary_text": "نص إعلان تجريبي.", "cta": "اطلب الآن"} for i in range(3)],
        "kpis": ["تكلفة النتيجة", "نسبة النقر", "عدد الرسائل"],
        "tips": ["ابدأ بميزانية صغيرة واختبر", "غيّر التصميم كل أسبوع", "رد على الرسائل بسرعة"],
    }
