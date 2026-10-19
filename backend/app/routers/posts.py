from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import timing
from ..ai.catalog import LAYOUTS
from ..ai.services import connected_platforms
from ..db import get_db
from ..deps import current_user
from ..jobs import enqueue
from ..models import Brand, Post, SocialAccount, User
from ..security import decrypt
from ..serializers import job_out, post_out
from ..social import meta
from ..storage import save_image

router = APIRouter(prefix="/api/posts", tags=["posts"])
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class PostPatch(BaseModel):
    headline: str | None = Field(default=None, max_length=300)
    caption: str | None = Field(default=None, max_length=2200)  # Instagram caption limit
    hashtags: list[str] | None = None
    cta: str | None = Field(default=None, max_length=300)
    template: int | None = Field(default=None, ge=0, le=2)
    day: int | None = Field(default=None, ge=1, le=31)
    time: str | None = Field(default=None, pattern=r"^\d{1,2}:\d{2}$")
    approved: bool | None = None
    subheadline: str | None = Field(default=None, max_length=200)
    badge: str | None = Field(default=None, max_length=40)
    layout: str | None = None


class BackgroundIn(BaseModel):
    prompt: str = Field(default="", max_length=600)
    source: str = Field(default="ai", pattern="^(ai|stock)$")


class RegenIn(BaseModel):
    instruction: str = Field(default="", max_length=500)


class ScheduleIn(BaseModel):
    scheduled_at: datetime | None = None
    local_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")  # in the brand's timezone
    platforms: list[str] = Field(min_length=1)


def _post(post_id: str, user: User, db: Session) -> Post:
    post = db.get(Post, post_id)
    if not post or post.company_id != user.company_id:
        raise HTTPException(404, "البوست مش موجود")
    return post


def _editable(post: Post) -> None:
    if post.status in ("publishing", "published"):
        raise HTTPException(409, "البوست اتنشر خلاص ومينفعش يتعدل")


@router.patch("/{post_id}")
def patch_post(post_id: str, body: PostPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = _post(post_id, user, db)
    _editable(post)
    data = body.model_dump(exclude_none=True)
    design = dict(post.design or {})
    for k in ("subheadline", "badge", "layout"):
        if k in data:
            v = data.pop(k)
            if k == "layout" and v not in LAYOUTS:
                raise HTTPException(422, "شكل التصميم مش معروف")
            design[k] = v
    design_changed = design != (post.design or {}) or any(k in data for k in ("headline", "cta", "template"))
    post.design = design
    for k, v in data.items():
        setattr(post, k, v)
    if design_changed:
        post.image_url = None
        if "approved" not in data:
            post.approved = False
    if post.status == "scheduled" and not post.approved:
        post.status, post.scheduled_at = "draft", None
    if data.get("approved") and post.status == "draft" and post.image_url and design.get("plan"):
        _apply_plan(db, post, user)
    db.commit()
    return post_out(post)


def _apply_plan(db: Session, post: Post, user: User) -> None:
    """The agent planned a time and platforms for this post: schedule it as soon as the owner approves it."""
    plan = (post.design or {}).get("plan") or {}
    platforms = [p for p in plan.get("platforms", []) if p in connected_platforms(db, user.company_id)]
    if not platforms or not plan.get("local_at"):
        return
    brand = db.get(Brand, post.brand_id)
    at = timing.local_to_utc(plan["local_at"], timing.brand_tz(brand.brief if brand else {}))
    now = datetime.now(timezone.utc)
    post.scheduled_at = at if at > now else now
    post.platforms, post.status, post.error, post.attempts = platforms, "scheduled", "", 0


@router.post("/{post_id}/regenerate")
def regenerate(post_id: str, body: RegenIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = _post(post_id, user, db)
    _editable(post)
    return job_out(enqueue(db, user.company_id, "regen", {"brand_id": post.brand_id, "post_id": post.id, "instruction": body.instruction}))


@router.post("/{post_id}/image")
async def upload_image(post_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = _post(post_id, user, db)
    _editable(post)
    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(415, "الصورة لازم تكون PNG أو JPEG")
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "الصورة أكبر من 8MB")
    ext = "png" if file.content_type == "image/png" else "jpg"
    post.image_url = save_image(data, user.company_id, ext, file.content_type)
    db.commit()
    return post_out(post)


@router.post("/{post_id}/schedule")
def schedule(post_id: str, body: ScheduleIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = _post(post_id, user, db)
    _editable(post)
    if not post.approved:
        raise HTTPException(409, "اعتمد البوست الأول")
    if not post.image_url:
        raise HTTPException(409, "التصميم لسه ما اترفعش")
    connected = set(db.scalars(select(SocialAccount.platform).where(SocialAccount.company_id == user.company_id)).all())
    missing = [p for p in body.platforms if p not in connected]
    if missing:
        raise HTTPException(409, f"اربط الحسابات دي الأول: {', '.join(missing)}")
    if body.local_at:
        brand = db.get(Brand, post.brand_id)
        at = timing.local_to_utc(body.local_at, timing.brand_tz(brand.brief if brand else {}))
    elif body.scheduled_at:
        at = body.scheduled_at if body.scheduled_at.tzinfo else body.scheduled_at.replace(tzinfo=timezone.utc)
    else:
        raise HTTPException(422, "حدد ميعاد النشر")
    post.scheduled_at, post.platforms, post.status, post.error, post.attempts = at, list(dict.fromkeys(body.platforms)), "scheduled", "", 0
    db.commit()
    return post_out(post)


@router.post("/{post_id}/unschedule")
def unschedule(post_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = _post(post_id, user, db)
    if post.status != "scheduled":
        raise HTTPException(409, "البوست مش مجدول")
    post.status, post.scheduled_at = "draft", None
    db.commit()
    return post_out(post)


@router.post("/{post_id}/background")
def background(post_id: str, body: BackgroundIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = _post(post_id, user, db)
    _editable(post)
    return job_out(enqueue(db, user.company_id, "background", {"brand_id": post.brand_id, "post_id": post.id,
                                                            "prompt": body.prompt, "source": body.source}))


@router.post("/{post_id}/background/upload")
async def upload_background(post_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The owner's own photo (their real product) as the design background."""
    post = _post(post_id, user, db)
    _editable(post)
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(415, "الصورة لازم تكون PNG أو JPEG أو WEBP")
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "الصورة أكبر من 8MB")
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[file.content_type]
    post.bg_url = save_image(data, user.company_id, ext, file.content_type)
    post.image_url, post.approved = None, False
    design = dict(post.design or {})
    design.pop("photo_credit", None)
    if design.get("layout") not in ("photo_overlay", "photo_split"):
        design["layout"] = "photo_overlay"
    post.design = design
    db.commit()
    return post_out(post)


@router.post("/{post_id}/metrics")
def refresh_metrics(post_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Reads real likes, comments and reach back from the platforms. Never invents numbers."""
    post = _post(post_id, user, db)
    out, notes = {}, []
    for platform, res in (post.publish_results or {}).items():
        if not res.get("ok") or not res.get("id"):
            continue
        acct = db.scalar(select(SocialAccount).where(SocialAccount.company_id == user.company_id, SocialAccount.platform == platform))
        if not acct or acct.provider != "meta":
            notes.append(f"{platform}: نشر تجريبي، مفيش أرقام حقيقية")
            continue
        try:
            out[platform] = meta.post_metrics(platform, res["id"], decrypt(acct.access_token_enc))
        except meta.MetaError as exc:
            notes.append(f"{platform}: {exc}")
    post.metrics = {**(post.metrics or {}), **out}
    post.metrics_at = datetime.now(timezone.utc)
    db.commit()
    return {**post_out(post), "notes": notes}
