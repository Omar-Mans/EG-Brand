"""Business discovery questionnaire: what an agency strategist asks before planning anything.

The answers feed the strategy, the brand identity and every content prompt.
"""

SECTORS = ["مطاعم وكافيهات", "تجارة إلكترونية", "عربيات", "عقارات", "عيادات وتجميل", "تعليم وتدريب",
           "خدمات للشركات", "أزياء وموضة", "جيم ورياضة", "سياحة وسفر", "تقنية وتطبيقات", "أخرى"]
CHANNELS = ["انستجرام", "تيك توك", "فيسبوك", "سناب شات", "X", "لينكدإن", "يوتيوب", "واتساب بيزنس", "جوجل"]

# type: text | textarea | select | multi | url
SECTIONS = [
    {"id": "business", "title": "عن البيزنس", "questions": [
        {"id": "sector", "label": "مجال البيزنس", "type": "select", "options": SECTORS, "required": True},
        {"id": "offer", "label": "إيه المنتجات أو الخدمات الأساسية؟ ومين فيهم الأكثر مبيعاً؟", "type": "textarea", "required": True},
        {"id": "price_level", "label": "مستوى الأسعار مقارنة بالسوق", "type": "select",
         "options": ["اقتصادي", "متوسط", "أعلى من المتوسط", "فاخر"]},
        {"id": "avg_ticket", "label": "متوسط سعر البيع للعميل الواحد (تقريباً)", "type": "text"},
        {"id": "locations", "label": "بتبيع فين؟ (مدن، فروع، أونلاين، توصيل)", "type": "text"},
        {"id": "stage", "label": "عمر البيزنس", "type": "select", "options": ["لسه بنبدأ", "أقل من سنة", "من سنة لـ 3 سنين", "أكتر من 3 سنين"]},
        {"id": "website", "label": "رابط موقعك لو موجود (الـ AI هيقراه)", "type": "url"},
    ]},
    {"id": "customer", "title": "العميل", "questions": [
        {"id": "customer", "label": "مين العميل المثالي؟ (السن، النوع، الشغل، الاهتمامات، المنطقة)", "type": "textarea", "required": True},
        {"id": "pains", "label": "إيه المشكلة أو الاحتياج اللي بيخلي العميل يدور عليك؟", "type": "textarea", "required": True},
        {"id": "why_buy", "label": "ليه العميل بيختارك انت بالذات؟", "type": "textarea", "required": True},
        {"id": "objections", "label": "إيه أكتر حاجة بتخلي العميل يتردد أو ما يشتريش؟", "type": "textarea"},
        {"id": "found_us", "label": "العملاء بيعرفوك منين غالباً؟", "type": "multi",
         "options": CHANNELS + ["ترشيحات", "المحل نفسه", "إعلانات"]},
    ]},
    {"id": "competition", "title": "المنافسين", "questions": [
        {"id": "competitors", "label": "اذكر 2 أو 3 منافسين (اسم أو رابط)، وإيه اللي بيعملوه أحسن منك", "type": "textarea"},
        {"id": "differentiator", "label": "إيه اللي عندك ومش عند المنافسين؟", "type": "textarea"},
    ]},
    {"id": "marketing", "title": "التسويق الحالي", "questions": [
        {"id": "platforms_now", "label": "انت موجود على أنهي منصات دلوقتي؟", "type": "multi", "options": CHANNELS + ["مفيش"]},
        {"id": "followers", "label": "عدد المتابعين تقريباً على أهم منصة", "type": "text"},
        {"id": "what_worked", "label": "إيه اللي جربته في التسويق ونجح؟ وإيه اللي ما نجحش؟", "type": "textarea"},
        {"id": "content_capacity", "label": "تقدر تصور صور أو فيديو لمنتجك؟", "type": "select",
         "options": ["مقدرش", "صور بالموبايل", "صور وفيديو بالموبايل", "عندي مصور أو فريق"]},
        {"id": "team", "label": "مين بيدير السوشيال؟", "type": "select", "options": ["أنا لوحدي", "حد من الفريق", "وكالة أو فريلانسر", "محدش"]},
    ]},
    {"id": "goals", "title": "الأهداف والميزانية", "questions": [
        {"id": "goal", "label": "أهم هدف في الـ 3 شهور الجاية", "type": "select", "required": True,
         "options": ["ناس أكتر تعرفنا", "رسايل واستفسارات", "زيارات للمحل", "مبيعات أونلاين", "حجوزات ومواعيد", "متابعين وتفاعل"]},
        {"id": "goal_number", "label": "رقم عايز توصله؟ (مثلاً 100 رسالة في الشهر، 50 طلب)", "type": "text"},
        {"id": "baseline", "label": "وصلت لكام حالياً في نفس الحاجة؟", "type": "text"},
        {"id": "ads_budget", "label": "ميزانية الإعلانات الممولة في الشهر (بعملتك)", "type": "select",
         "options": ["مفيش دلوقتي", "أقل من 1,000", "من 1,000 لـ 3,000", "من 3,000 لـ 10,000", "أكتر من 10,000"]},
        {"id": "seasons", "label": "فيه مواسم أو مناسبات بتفرق معاك في البيع؟", "type": "textarea"},
        {"id": "offers", "label": "فيه عروض أو خصومات تقدر تعملها؟", "type": "textarea"},
    ]},
    {"id": "voice", "title": "الشخصية", "questions": [
        {"id": "voice", "label": "تحب البراند يتكلم إزاي؟", "type": "select", "options": ["رسمي ومحترم", "ودود وقريب", "شبابي ومرح", "فخم وراقي"]},
        {"id": "avoid", "label": "فيه حاجات ممنوع نقولها أو نستخدمها؟ (كلمات، صور، مواضيع)", "type": "textarea"},
    ]},
]

QUESTIONS = {q["id"]: q for s in SECTIONS for q in s["questions"]}
REQUIRED = [q["id"] for q in QUESTIONS.values() if q.get("required")]


def clean_answers(raw: dict) -> dict:
    out: dict = {}
    for qid, q in QUESTIONS.items():
        v = raw.get(qid)
        if v in (None, "", []):
            continue
        if q["type"] == "multi":
            out[qid] = [x for x in v if x in q["options"]] if isinstance(v, list) else []
        elif q["type"] == "select":
            if v in q["options"]:
                out[qid] = v
        else:
            out[qid] = str(v).strip()[:1500]
    return out


def missing_required(answers: dict) -> list[str]:
    return [q for q in REQUIRED if not answers.get(q)]


def as_text(discovery: dict | None, limit: int = 6000) -> str:
    """Compact 'question: answer' block for prompts, including AI follow-ups and the website excerpt."""
    if not discovery:
        return ""
    lines = []
    answers = discovery.get("answers") or {}
    for qid, q in QUESTIONS.items():
        if answers.get(qid):
            v = answers[qid]
            lines.append(f"- {q['label']}: {'، '.join(v) if isinstance(v, list) else v}")
    for f in discovery.get("followups") or []:
        if f.get("answer"):
            lines.append(f"- {f['question']}: {f['answer']}")
    if discovery.get("website_text"):
        lines.append(f"- Excerpt from the business website: {discovery['website_text'][:2500]}")
    return "\n".join(lines)[:limit]
