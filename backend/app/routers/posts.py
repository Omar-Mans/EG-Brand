from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..jobs import enqueue
from ..models import Post, SocialAccount, User
from ..serializers import job_out, post_out
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


class RegenIn(BaseModel):
    instruction: str = Field(default="", max_length=500)


class ScheduleIn(BaseModel):
    scheduled_at: datetime
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
    design_changed = any(k in data for k in ("headline", "cta", "template"))
    for k, v in data.items():
        setattr(post, k, v)
    if design_changed:
        post.image_url = None
        if "approved" not in data:
            post.approved = False
    if post.status == "scheduled" and not post.approved:
        post.status, post.scheduled_at = "draft", None
    db.commit()
    return post_out(post)


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
    at = body.scheduled_at if body.scheduled_at.tzinfo else body.scheduled_at.replace(tzinfo=timezone.utc)
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
