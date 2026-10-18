"""AI features: each one builds a prompt, calls the gateway and normalizes the answer into safe data."""

import calendar as pycal
import re
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import Brand, Post, SocialAccount
from . import mock, prompts, timing
from .catalog import AD_PLATFORMS, FONTS_AR, FONTS_EN, ICONS, LAYOUTS, MARKETS, PALETTE_ROLES, POST_FORMATS
from .llm import AIError, complete_json
from .occasions import occasions_for

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _list(value, n: int) -> list:
    return [v for v in value if v][:n] if isinstance(value, list) else []


def normalize_dna(d: dict, preferred_name: str = "") -> dict:
    if not isinstance(d, dict):
        raise AIError("invalid_json", "شكل هوية البراند مش صحيح")
    names = [{"ar": str(n.get("ar", "")).strip(), "en": str(n.get("en", "")).strip(), "meaning": str(n.get("meaning", ""))}
             for n in _list(d.get("names"), 3) if isinstance(n, dict) and n.get("ar")]
    if preferred_name and (not names or names[0]["ar"] != preferred_name):
        names = [{"ar": preferred_name, "en": "", "meaning": ""}] + [n for n in names if n["ar"] != preferred_name][:2]
    palette = [{"role": str(p.get("role", "")), "name": str(p.get("name", "")), "hex": p["hex"]}
               for p in _list(d.get("palette"), 6) if isinstance(p, dict) and HEX.match(str(p.get("hex", "")))]
    defaults = mock.brand_dna({})["palette"]
    have = {p["role"] for p in palette}
    palette += [p for p in defaults if p["role"] not in have and p["role"] in PALETTE_ROLES]
    pillars = [{"name": str(p.get("name", "")), "share": float(p.get("share") or 0)}
               for p in _list(d.get("pillars"), 6) if isinstance(p, dict) and p.get("name")]
    total = sum(p["share"] for p in pillars) or 1
    for p in pillars:
        p["share"] = round(p["share"] / total * 100)
    return {
        "names": names or [{"ar": "براند", "en": "Brand", "meaning": ""}], "chosen": 0,
        "tagline_ar": str(d.get("tagline_ar", "")), "tagline_en": str(d.get("tagline_en", "")),
        "positioning": str(d.get("positioning", "")), "audience": str(d.get("audience", "")),
        "personality": [str(x) for x in _list(d.get("personality"), 6)], "tone": str(d.get("tone", "")),
        "voice_do": [str(x) for x in _list(d.get("voice_do"), 5)], "voice_dont": [str(x) for x in _list(d.get("voice_dont"), 5)],
        "palette": palette,
        "font_ar": d.get("font_ar") if d.get("font_ar") in FONTS_AR else "Cairo",
        "font_en": d.get("font_en") if d.get("font_en") in FONTS_EN else "DM Sans",
        "icon": d.get("icon") if d.get("icon") in ICONS else "spark",
        "pillars": pillars,
        "prompt_version": prompts.PROMPT_VERSION,
    }


def generate_dna(db: Session, brand: Brand) -> dict:
    brief = brand.brief or {}
    data = complete_json(db, prompts.brand_dna(brief), company_id=brand.company_id, brand_id=brand.id,
                         feature="dna", tier="quality", mock=lambda: mock.brand_dna(brief))
    dna = normalize_dna(data, (brief.get("name") or "").strip())
    brand.dna = dna
    brand.name = dna["names"][0]["ar"]
    db.commit()
    return dna


def _clean_post(x: dict, days: int) -> dict | None:
    if not isinstance(x, dict) or not x.get("headline"):
        return None
    try:
        day = min(days, max(1, int(x.get("day") or 1)))
    except (TypeError, ValueError):
        day = 1
    t = str(x.get("time") or "")
    return {
        "day": day, "time": t if re.match(r"^\d{1,2}:\d{2}$", t) else "19:00",
        "format": x.get("format") if x.get("format") in POST_FORMATS else "post",
        "pillar": str(x.get("pillar") or ""), "occasion": str(x.get("occasion") or ""),
        "headline": str(x.get("headline") or ""), "caption": str(x.get("caption") or ""),
        "hashtags": [str(h) for h in _list(x.get("hashtags"), 6)], "cta": str(x.get("cta") or ""),
        "design": clean_design(x),
    }


def clean_design(x: dict) -> dict:
    layout = x.get("layout") if x.get("layout") in LAYOUTS else "bold"
    return {"subheadline": str(x.get("subheadline") or "")[:120], "badge": str(x.get("badge") or "")[:30],
            "layout": layout, "visual_prompt": str(x.get("visual_prompt") or "")[:600]}


def generate_calendar(db: Session, brand: Brand, year: int, month: int, count: int = 12) -> list[Post]:
    if not brand.dna:
        raise AIError("no_dna", "ولّد هوية البراند الأول")
    brief = brand.brief or {}
    days = pycal.monthrange(year, month)[1]
    occ = occasions_for(year, month, brief.get("market", "EG"))
    data = complete_json(db, prompts.calendar(brief, brand.dna, year, month, days, occ, count),
                         company_id=brand.company_id, brand_id=brand.id, feature="calendar", tier="quality",
                         mock=lambda: mock.calendar(days, occ, count))
    items = data if isinstance(data, list) else (data.get("posts") if isinstance(data, dict) else None) or []
    cleaned = [p for p in (_clean_post(x, days) for x in items[: count + 4]) if p]
    if not cleaned:
        raise AIError("invalid_json", "الـ AI ما رجّعش بوستات")
    key = f"{year:04d}-{month:02d}"
    # Replace the month's unpublished drafts; keep anything already scheduled or published.
    db.execute(delete(Post).where(Post.brand_id == brand.id, Post.month == key, Post.status == "draft"))
    posts = [Post(company_id=brand.company_id, brand_id=brand.id, month=key, **p)
             for p in sorted(cleaned, key=lambda p: p["day"])]
    db.add_all(posts)
    db.commit()
    return posts


def rewrite_post(db: Session, brand: Brand, post: Post, instruction: str) -> Post:
    current = {"headline": post.headline, "caption": post.caption, "hashtags": post.hashtags, "cta": post.cta,
               "format": post.format, "occasion": post.occasion}
    data = complete_json(db, prompts.rewrite_post(brand.brief or {}, brand.dna or {}, current, instruction),
                         company_id=brand.company_id, brand_id=brand.id, feature="regen", tier="fast",
                         mock=lambda: mock.rewrite_post(current), max_tokens=1500)
    if isinstance(data, dict):
        post.headline = str(data.get("headline") or post.headline)
        post.caption = str(data.get("caption") or post.caption)
        if isinstance(data.get("hashtags"), list):
            post.hashtags = [str(h) for h in data["hashtags"][:6]]
        post.cta = str(data.get("cta") or post.cta)
        post.image_url = None  # the design must be re-rendered
        post.approved = False
    db.commit()
    return post


def plan_ads(db: Session, brand: Brand, objective: str, budget: float, days: int, platforms: list[str]) -> dict:
    if not brand.dna:
        raise AIError("no_dna", "ولّد هوية البراند الأول")
    platforms = [p for p in platforms if p in AD_PLATFORMS] or [AD_PLATFORMS[0]]
    brief = brand.brief or {}
    currency = MARKETS.get(brief.get("market"), MARKETS["EG"])["currency"]
    data = complete_json(db, prompts.ads_plan(brief, brand.dna, objective, budget, currency, days, platforms),
                         company_id=brand.company_id, brand_id=brand.id, feature="ads", tier="quality",
                         mock=lambda: mock.ads_plan(platforms), max_tokens=3000)
    if not isinstance(data, dict):
        raise AIError("invalid_json", "شكل الخطة الإعلانية مش صحيح")
    a = data.get("audience") if isinstance(data.get("audience"), dict) else {}
    split = [{"platform": str(x.get("platform", "")), "pct": float(x.get("pct") or 0), "why": str(x.get("why", ""))}
             for x in _list(data.get("split"), 6) if isinstance(x, dict)]
    split = [x for x in split if x["pct"] > 0]
    total = sum(x["pct"] for x in split) or 1
    for x in split:
        x["pct"] = round(x["pct"] / total * 100, 1)
        x["amount"] = round(budget * x["pct"] / 100, 2)
        x["daily"] = round(x["amount"] / max(1, days), 2)
    return {
        "objective": objective, "budget": budget, "currency": currency, "days": days, "platforms": platforms,
        "audience": {"age": str(a.get("age", "")), "gender": str(a.get("gender", "")),
                     "locations": [str(x) for x in _list(a.get("locations"), 8)],
                     "interests": [str(x) for x in _list(a.get("interests"), 8)]},
        "split": split,
        "ads": [{"platform": str(x.get("platform", "")), "headline": str(x.get("headline", "")),
                 "primary_text": str(x.get("primary_text", "")), "cta": str(x.get("cta", ""))}
                for x in _list(data.get("ads"), 3) if isinstance(x, dict)],
        "kpis": [str(x) for x in _list(data.get("kpis"), 6)],
        "tips": [str(x) for x in _list(data.get("tips"), 6)],
    }


def connected_platforms(db: Session, company_id: str) -> list[str]:
    rows = db.scalars(select(SocialAccount.platform).where(SocialAccount.company_id == company_id)).all()
    return sorted({p for p in rows if p != "meta_ads"})


def generate_posts_for_dates(db: Session, brand: Brand, dates: list[date], topic: str, time: str, platforms: list[str]) -> list[Post]:
    if not brand.dna:
        raise AIError("no_dna", "ولّد هوية البراند الأول")
    brief = brand.brief or {}
    labels = [d.isoformat() for d in dates]
    occ = []
    for d in dates:
        occ += [f"{d.isoformat()}: {o['title']}" for o in occasions_for(d.year, d.month, brief.get("market", "EG")) if o["day"] == d.day]
    data = complete_json(db, prompts.posts_for_dates(brief, brand.dna, labels, occ, topic),
                         company_id=brand.company_id, brand_id=brand.id, feature="calendar", tier="quality",
                         mock=lambda: mock.posts_for_dates(labels))
    items = data if isinstance(data, list) else (data.get("posts") if isinstance(data, dict) else None) or []
    posts = []
    for i, d in enumerate(dates):
        item = items[i] if i < len(items) and isinstance(items[i], dict) else None
        cleaned = _clean_post(item, 31) if item else None
        if not cleaned:
            continue
        cleaned["day"], cleaned["time"] = d.day, time
        cleaned["design"]["plan"] = {"local_at": f"{d.isoformat()}T{time}", "platforms": platforms}
        posts.append(Post(company_id=brand.company_id, brand_id=brand.id, month=f"{d.year:04d}-{d.month:02d}", **cleaned))
    if not posts:
        raise AIError("invalid_json", "الـ AI ما رجّعش بوستات")
    db.add_all(posts)
    db.commit()
    return posts


def run_agent(db: Session, brand: Brand, command: str) -> dict:
    brief = brand.brief or {}
    tz = timing.brand_tz(brief)
    now = timing.now_local(tz)
    best = timing.best_times(brief)["default"]
    connected = connected_platforms(db, brand.company_id)
    tomorrow = (now + timedelta(days=1)).date().isoformat()
    plan = complete_json(db, prompts.agent_plan(command, now.date().isoformat(), timing.WEEKDAYS_AR[now.weekday()], tz, connected, best),
                         company_id=brand.company_id, brand_id=brand.id, feature="agent", tier="fast",
                         mock=lambda: mock.agent_plan(tomorrow, connected, best), max_tokens=1200)
    if not isinstance(plan, dict):
        raise AIError("invalid_json", "الـ Agent ما فهمش الأمر")
    intent = plan.get("intent")
    if intent == "status":
        rows = db.scalars(select(Post).where(Post.brand_id == brand.id)).all()
        counts = {k: sum(1 for p in rows if p.status == k) for k in ("draft", "scheduled", "published", "failed")}
        waiting = sum(1 for p in rows if p.status == "draft" and (p.design or {}).get("plan"))
        msg = (f"عندك {counts['scheduled']} بوست مجدول، و{counts['published']} اتنشر، "
               f"و{waiting} مستني اعتمادك، و{counts['failed']} فشل.")
        return {"intent": "status", "message": msg, "counts": counts}
    if intent != "create_and_schedule":
        return {"intent": "unsupported", "message": str(plan.get("reply") or "الأمر ده لسه مش مدعوم.")}
    try:
        count = max(1, min(30, int(plan.get("count") or 7)))
        every = max(1, min(14, int(plan.get("every_days") or 1)))
        start = date.fromisoformat(str(plan.get("start_date")))
    except (TypeError, ValueError):
        count, every, start = 7, 1, now.date() + timedelta(days=1)
    if start < now.date():
        start = now.date() + timedelta(days=1)
    t = str(plan.get("time") or best)
    if not re.match(r"^\d{1,2}:\d{2}$", t):
        t = best
    hh, mm = t.split(":")
    t = f"{int(hh):02d}:{mm}"
    wanted = [p for p in (plan.get("platforms") or []) if p in connected] or connected
    dates = [start + timedelta(days=i * every) for i in range(count)]
    posts = generate_posts_for_dates(db, brand, dates, str(plan.get("topic") or ""), t, wanted)
    where = "، ".join(wanted) if wanted else "لسه مفيش حسابات مربوطة، اربطها عشان النشر يشتغل"
    msg = (f"{plan.get('reply') or ''}\nجهزت {len(posts)} بوست من {dates[0].isoformat()} الساعة {t} على: {where}. "
           "راجع التصميمات واعتمدها من صفحة المحتوى، وكل بوست تعتمده هيتجدول لوحده في ميعاده.").strip()
    return {"intent": "create_and_schedule", "message": msg, "post_ids": [p.id for p in posts],
            "months": sorted({p.month for p in posts})}
