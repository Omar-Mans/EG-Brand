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
        **_design(i),
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


def _design(i: int) -> dict:
    layouts = ["photo_overlay", "bold", "photo_split", "offer", "minimal", "quote"]
    layout = layouts[i % len(layouts)]
    return {"subheadline": "سطر قصير بيوضح الفايدة", "badge": "خصم 20%" if layout == "offer" else "",
            "layout": layout, "visual_prompt": "modern showroom with soft daylight, wide angle, clean background"}


def posts_for_dates(dates: list[str]) -> list[dict]:
    return [{"date": d, "time": "21:00", "format": "post", "pillar": "المنتج", "occasion": "",
             "headline": ["عرض الأسبوع", "جديدنا وصل", "ليه تختارنا؟"][i % 3], "caption": "سطر أول.\nسطر تاني.",
             "hashtags": ["#براند"], "cta": "تواصل معانا", **_design(i)} for i, d in enumerate(dates)]


def agent_plan(today: str, connected: list[str], best_time: str) -> dict:
    return {"intent": "create_and_schedule", "count": 7, "start_date": today, "every_days": 1, "time": best_time,
            "platforms": connected, "topic": "", "reply": "هجهز 7 بوستات، بوست كل يوم."}


def followups() -> list[dict]:
    return [
        {"question": "إيه أكتر 3 منتجات بتكسب منها؟", "why": "عشان نركز المحتوى والإعلانات على اللي بيجيب فلوس"},
        {"question": "بتقدم توصيل أو تقسيط أو ضمان؟", "why": "دي أقوى أسباب للشراء ولازم تبان في كل بوست"},
        {"question": "مين بيرد على الرسايل وفي خلال قد إيه؟", "why": "سرعة الرد بتفرق في تحويل الرسالة لبيعة"},
        {"question": "عندك تقييمات أو آراء عملاء نقدر نستخدمها؟", "why": "الدليل الاجتماعي بيقلل تردد العميل"},
    ]


def strategy() -> dict:
    kpi = lambda n, t: {"name": n, "target": t}  # noqa: E731
    return {
        "summary": "استراتيجية تجريبية: نبني ثقة الأول بمحتوى بيوري المنتج الحقيقي وآراء العملاء، وبعدين نحوّل التفاعل لرسايل ومبيعات بعروض واضحة.",
        "diagnosis": {"strengths": ["منتج واضح", "خدمة سريعة"], "weaknesses": ["حضور ضعيف على السوشيال"],
                      "opportunities": ["مواسم قريبة", "منافسين محتواهم عام"], "threats": ["حرب أسعار"]},
        "positioning": {"statement": "للعميل اللي عايز جودة مضمونة، إحنا الاختيار الأسرع والأوضح في السعر، مش زي اللي بيخبوا التفاصيل.",
                        "usp": ["أسعار معلنة", "رد خلال ساعة", "ضمان"], "proof_points": ["آراء عملاء", "صور حقيقية", "خطوات الشراء"]},
        "personas": [{"name": "الشاري الحريص", "age": "28-40", "description": "بيقارن كتير قبل ما يشتري.", "pains": ["خايف يتغش"],
                      "motivations": ["الضمان"], "objections": ["السعر"], "where": ["فيسبوك", "انستجرام"], "message": "كل التفاصيل قدامك"}],
        "channels": [{"platform": "Instagram", "role": "الوعي والثقة", "priority": "high", "posts_per_week": 3, "formats": ["Reels", "Carousel"], "why": "جمهورك هناك"},
                     {"platform": "Facebook", "role": "الرسايل والمبيعات", "priority": "medium", "posts_per_week": 3, "formats": ["Post"], "why": "الرسايل أسهل"}],
        "content_pillars": [{"name": "المنتج", "share": 35, "goal": "بيع", "examples": ["مميزات المنتج"]},
                            {"name": "الثقة", "share": 25, "goal": "ثقة", "examples": ["رأي عميل"]},
                            {"name": "تعليمي", "share": 25, "goal": "قيمة", "examples": ["نصيحة"]},
                            {"name": "عروض", "share": 15, "goal": "تحويل", "examples": ["عرض الأسبوع"]}],
        "offers": [{"title": "عرض الافتتاح", "description": "خصم لأول 20 عميل", "when": "الشهر الأول"}],
        "budget": {"monthly_total": 0, "split": [{"item": "إعلانات انستجرام", "pct": 100, "note": ""}], "note": "ابدأ بالمحتوى المجاني"},
        "roadmap": [{"phase": f"الشهر {m}", "goal": "هدف المرحلة", "actions": ["اعمل كذا"], "kpis": [kpi("رسايل", "30")]}
                    for m in ("الأول", "التاني", "التالت")],
        "quick_wins": ["ظبط البايو", "ثبّت 3 بوستات", "رد آلي على الرسايل", "صور المنتج", "اطلب 5 تقييمات"],
        "kpis": [{"name": "الرسايل", "target": "30 في الشهر (هدف مبدئي)", "why": "أقرب حاجة للبيع"}],
        "risks": [{"risk": "قلة المحتوى المصور", "mitigation": "يوم تصوير كل أسبوعين"}],
        "competitors": [{"name": "منافس مباشر", "their_strength": "متابعين أكتر", "our_angle": "شفافية السعر"}],
    }


def reel_script() -> dict:
    return {"scenes": [
        {"text": "بتدور على عربية مضمونة؟", "sub": "", "voice": "بتدور على عربية مستعملة وخايف من العيوب؟",
         "photo_query": "used car showroom", "visual_prompt": "modern used car showroom, soft light"},
        {"text": "فحص 150 نقطة", "sub": "تقرير مكتوب لكل عربية", "voice": "كل عربية عندنا بتعدي فحص كامل وبتاخد تقريرها مكتوب",
         "photo_query": "car inspection mechanic", "visual_prompt": "mechanic inspecting a car engine"},
        {"text": "ضمان 6 شهور", "sub": "", "voice": "ومعاها ضمان ست شهور على المكينة والفتيس",
         "photo_query": "happy customer car keys", "visual_prompt": "customer receiving car keys"},
    ], "outro_voice": "كلمنا على الواتساب النهارده", "title": "عربية مضمونة بجد", "caption": "فحص كامل وضمان.\nكلمنا على الواتساب.",
        "hashtags": ["#سيارات", "#ضمان"], "cta": "كلمنا واتساب"}


def talk_script() -> dict:
    return {"title": "3 حاجات تفحصها قبل ما تشتري", "hook": "قبل ما تشتري عربية مستعملة، اسمع الكلام ده.",
            "lines": ["أول حاجة: اطلب تقرير فحص مكتوب.", "تاني حاجة: اسأل عن الضمان بالتفصيل.", "تالت حاجة: جرب العربية بنفسك."],
            "cta": "ولو عايز عربية مفحوصة ومضمونة، كلمنا على الواتساب.", "broll": ["car inspection", "car keys handover"],
            "caption": "3 حاجات مهمة قبل الشرا.", "hashtags": ["#سيارات"]}
