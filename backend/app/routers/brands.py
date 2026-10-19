from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import discovery as disc
from ..ai import timing
from ..ai.catalog import AD_OBJECTIVES, AD_PLATFORMS, DEFAULT_TZ, DIALECTS, FONTS_AR, FONTS_EN, ICONS, LAYOUTS, MARKETS, STYLES, TIMEZONES
from ..ai.occasions import occasions_for
from ..ai.services import HEX
from ..db import get_db
from ..deps import current_user, get_brand
from ..jobs import enqueue
from ..models import Brand, Post, User
from ..serializers import brand_out, job_out, post_out

router = APIRouter(prefix="/api", tags=["brands"])


class BriefIn(BaseModel):
    idea: str = Field(min_length=10, max_length=2000)
    name: str = Field(default="", max_length=60)
    market: str = "EG"
    dialect: str = "egyptian"
    styles: list[str] = []
    colors: list[str] = []
    timezone: str = ""


class DnaPatch(BaseModel):
    chosen: int | None = None
    icon: str | None = None
    font_ar: str | None = None
    font_en: str | None = None
    palette: list[dict] | None = None
    tagline_ar: str | None = None
    tagline_en: str | None = None


class CalendarIn(BaseModel):
    year: int = Field(ge=2024, le=2100)
    month: int = Field(ge=1, le=12)
    count: int | None = Field(default=None, ge=4, le=30)  # None: follow the strategy's cadence


class ImagesIn(BaseModel):
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    replace: bool = False
    source: str = Field(default="ai", pattern="^(ai|stock)$")


class DiscoveryIn(BaseModel):
    answers: dict = {}


class FollowupAnswersIn(BaseModel):
    answers: list[str] = Field(default=[], max_length=6)


class AgentIn(BaseModel):
    command: str = Field(min_length=3, max_length=500)


class AdsPlanIn(BaseModel):
    objective: str
    budget: float = Field(gt=0, le=10_000_000)
    days: int = Field(ge=1, le=90)
    platforms: list[str]


def _clean_brief(body: BriefIn) -> dict:
    if body.market not in MARKETS:
        raise HTTPException(422, "السوق لازم يكون مصر أو السعودية")
    if body.dialect not in DIALECTS:
        raise HTTPException(422, "اللهجة مش مدعومة")
    return {"idea": body.idea.strip(), "name": body.name.strip(), "market": body.market, "dialect": body.dialect,
            "styles": [s for s in body.styles if s in STYLES][:4], "colors": [c for c in body.colors if HEX.match(c)][:3],
            "timezone": body.timezone if body.timezone in TIMEZONES else DEFAULT_TZ[body.market]}


@router.get("/catalog")
def catalog():
    return {"fonts_ar": FONTS_AR, "fonts_en": FONTS_EN, "icons": ICONS, "styles": STYLES, "markets": MARKETS,
            "dialects": DIALECTS, "ad_objectives": AD_OBJECTIVES, "ad_platforms": AD_PLATFORMS,
            "layouts": LAYOUTS, "timezones": TIMEZONES}


@router.get("/occasions")
def occasions(year: int, month: int, market: str = "EG"):
    return occasions_for(year, month, market)


@router.get("/brands")
def list_brands(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Brand).where(Brand.company_id == user.company_id).order_by(Brand.created_at.desc())).all()
    return [brand_out(b) for b in rows]


@router.post("/brands")
def create_brand(body: BriefIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brief = _clean_brief(body)
    brand = Brand(company_id=user.company_id, name=brief["name"] or "براند جديد", brief=brief)
    db.add(brand)
    db.commit()
    return brand_out(brand)


@router.get("/brands/{brand_id}")
def read_brand(brand_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return brand_out(get_brand(brand_id, user, db))


@router.put("/brands/{brand_id}/brief")
def update_brief(brand_id: str, body: BriefIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    brand.brief = _clean_brief(body)
    db.commit()
    return brand_out(brand)


@router.patch("/brands/{brand_id}/dna")
def patch_dna(brand_id: str, body: DnaPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    if not brand.dna:
        raise HTTPException(409, "ولّد هوية البراند الأول")
    dna = dict(brand.dna)
    if body.chosen is not None and 0 <= body.chosen < len(dna.get("names", [])):
        dna["chosen"] = body.chosen
        brand.name = dna["names"][body.chosen]["ar"]
    if body.icon in ICONS:
        dna["icon"] = body.icon
    if body.font_ar in FONTS_AR:
        dna["font_ar"] = body.font_ar
    if body.font_en in FONTS_EN:
        dna["font_en"] = body.font_en
    if body.palette is not None:
        dna["palette"] = [{"role": str(p.get("role", "")), "name": str(p.get("name", "")), "hex": p["hex"]}
                          for p in body.palette if HEX.match(str(p.get("hex", "")))]
    for k in ("tagline_ar", "tagline_en"):
        if getattr(body, k) is not None:
            dna[k] = getattr(body, k)
    brand.dna = dna
    db.commit()
    return brand_out(brand)


@router.delete("/brands/{brand_id}")
def delete_brand(brand_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    for p in db.scalars(select(Post).where(Post.brand_id == brand.id)).all():
        db.delete(p)
    db.delete(brand)
    db.commit()
    return {"ok": True}


@router.post("/brands/{brand_id}/generate-dna")
def generate_dna(brand_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    return job_out(enqueue(db, user.company_id, "dna", {"brand_id": brand.id}))


@router.post("/brands/{brand_id}/calendar")
def generate_calendar(brand_id: str, body: CalendarIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    if not brand.dna:
        raise HTTPException(409, "ولّد هوية البراند الأول")
    return job_out(enqueue(db, user.company_id, "calendar", {"brand_id": brand.id, **body.model_dump()}))


@router.get("/brands/{brand_id}/posts")
def list_posts(brand_id: str, month: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    q = select(Post).where(Post.brand_id == brand.id)
    if month:
        q = q.where(Post.month == month)
    rows = db.scalars(q.order_by(Post.month, Post.day, Post.time)).all()
    return [post_out(p) for p in rows]


@router.post("/brands/{brand_id}/ads/plan")
def plan_ads(brand_id: str, body: AdsPlanIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    if not brand.dna:
        raise HTTPException(409, "ولّد هوية البراند الأول")
    if body.objective not in AD_OBJECTIVES:
        raise HTTPException(422, "هدف الحملة مش معروف")
    return job_out(enqueue(db, user.company_id, "ads", {"brand_id": brand.id, **body.model_dump()}))


@router.post("/brands/{brand_id}/images")
def generate_images(brand_id: str, body: ImagesIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    return job_out(enqueue(db, user.company_id, "images", {"brand_id": brand.id, **body.model_dump()}))


@router.post("/brands/{brand_id}/agent")
def agent(brand_id: str, body: AgentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    if not brand.dna:
        raise HTTPException(409, "ولّد هوية البراند الأول")
    return job_out(enqueue(db, user.company_id, "agent", {"brand_id": brand.id, "command": body.command.strip()}))


@router.get("/brands/{brand_id}/best-times")
def best_times(brand_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return timing.best_times(get_brand(brand_id, user, db).brief or {})


@router.get("/discovery/questions")
def discovery_questions():
    return {"sections": disc.SECTIONS, "required": disc.REQUIRED}


@router.put("/brands/{brand_id}/discovery")
def save_discovery(brand_id: str, body: DiscoveryIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    brand.discovery = {**(brand.discovery or {}), "answers": disc.clean_answers(body.answers)}
    db.commit()
    return brand_out(brand)


@router.post("/brands/{brand_id}/discovery/followups")
def discovery_followups(brand_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    missing = disc.missing_required((brand.discovery or {}).get("answers") or {})
    if missing:
        raise HTTPException(409, "كمّل الأسئلة الأساسية الأول: " + "، ".join(disc.QUESTIONS[q]["label"] for q in missing))
    return job_out(enqueue(db, user.company_id, "followups", {"brand_id": brand.id}))


@router.put("/brands/{brand_id}/discovery/followups")
def answer_followups(brand_id: str, body: FollowupAnswersIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    d = dict(brand.discovery or {})
    d["followups"] = [{**f, "answer": (body.answers[i] if i < len(body.answers) else "").strip()[:1500]}
                      for i, f in enumerate(d.get("followups") or [])]
    brand.discovery = d
    db.commit()
    return brand_out(brand)


@router.post("/brands/{brand_id}/strategy")
def make_strategy(brand_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(brand_id, user, db)
    missing = disc.missing_required((brand.discovery or {}).get("answers") or {})
    if missing:
        raise HTTPException(409, "كمّل الأسئلة الأساسية الأول: " + "، ".join(disc.QUESTIONS[q]["label"] for q in missing))
    return job_out(enqueue(db, user.company_id, "strategy", {"brand_id": brand.id}))
