import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..ai.llm import AIError
from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..jobs import enqueue
from ..models import Brand, User
from ..reels import music
from ..reels.service import MAX_SCENES, MUSIC_CHOICES, reel_of, set_reel
from ..reels.voice import NO_VOICE, VOICES, synthesize
from ..serializers import job_out, post_out
from ..storage import save_image
from .posts import MAX_IMAGE_BYTES, _editable, _post

router = APIRouter(prefix="/api", tags=["reels"])
MAX_AUDIO_BYTES = 12 * 1024 * 1024
SAMPLE = {"saudi": "هلا والله، هذا مثال لصوت الإعلان حقك. واضح وطبيعي؟",
          "egyptian": "أهلاً بيك، ده مثال لصوت الإعلان بتاعك. واضح وطبيعي؟"}


class ScriptIn(BaseModel):
    voice: str | None = None


class SceneEdit(BaseModel):
    text: str = Field(default="", max_length=80)
    sub: str = Field(default="", max_length=100)
    voice: str = Field(default="", max_length=300)


class ReelPatch(BaseModel):
    voice: str | None = None
    music: str | None = None
    outro_voice: str | None = Field(default=None, max_length=120)
    scenes: list[SceneEdit] | None = Field(default=None, max_length=MAX_SCENES)


class PhotoIn(BaseModel):
    source: str = Field(default="stock", pattern="^(ai|stock)$")
    prompt: str = Field(default="", max_length=300)


@router.get("/reels/options")
def options():
    return {"voices": {k: v["label"] for k, v in VOICES.items()}, "music": {k: v["label"] for k, v in music.PRESETS.items()},
            "voice_provider": get_settings().voice_backend}


@router.get("/reels/voice-sample/{voice}")
def voice_sample(voice: str):
    """Short demo of a voice, cached on disk so each voice is synthesized once."""
    if voice not in VOICES:
        raise HTTPException(404, "الصوت ده مش موجود")
    folder = os.path.join(tempfile.gettempdir(), "egbrand-voices")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{voice}-{get_settings().voice_backend}.mp3")
    if not os.path.exists(path):
        try:
            synthesize(SAMPLE[VOICES[voice]["dialect"]], voice, path + ".tmp.mp3")
        except AIError as exc:
            raise HTTPException(503, exc.message) from exc
        os.replace(path + ".tmp.mp3", path)
    return FileResponse(path, media_type="audio/mpeg")


def _reel_post(post_id: str, user: User, db: Session):
    post = _post(post_id, user, db)
    _editable(post)
    return post, db.get(Brand, post.brand_id)


@router.post("/posts/{post_id}/reel/script")
def make_script(post_id: str, body: ScriptIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post, brand = _reel_post(post_id, user, db)
    if body.voice and body.voice not in VOICES and body.voice != NO_VOICE:
        raise HTTPException(422, "الصوت ده مش موجود")
    return job_out(enqueue(db, user.company_id, "reel_script", {"brand_id": brand.id, "post_id": post.id, "voice": body.voice}))


@router.patch("/posts/{post_id}/reel")
def patch_reel(post_id: str, body: ReelPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post, brand = _reel_post(post_id, user, db)
    reel = reel_of(post, brand)
    if body.voice is not None:
        if body.voice not in VOICES and body.voice != NO_VOICE:
            raise HTTPException(422, "الصوت ده مش موجود")
        reel["voice"] = body.voice
    if body.music is not None:
        if body.music not in MUSIC_CHOICES or (body.music == "custom" and not reel.get("music_url")):
            raise HTTPException(422, "اختيار الموسيقى مش صحيح")
        reel["music"] = body.music
    if body.outro_voice is not None:
        reel["outro_voice"] = body.outro_voice.strip()
    if body.scenes is not None:
        old = reel.get("scenes") or []
        reel["scenes"] = [{**(old[i] if i < len(old) else {"photo_query": "", "visual_prompt": "", "bg_url": None, "credit": None}),
                           "text": e.text.strip(), "sub": e.sub.strip(), "voice": e.voice.strip()}
                          for i, e in enumerate(body.scenes) if e.text.strip()]
    set_reel(post, reel)
    post.video_url = None
    post.approved = False
    db.commit()
    return post_out(post)


@router.post("/posts/{post_id}/reel/scenes/{index}/photo")
def scene_photo(post_id: str, index: int, body: PhotoIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post, brand = _reel_post(post_id, user, db)
    if not 0 <= index < len(reel_of(post, brand)["scenes"]):
        raise HTTPException(404, "المشهد مش موجود")
    return job_out(enqueue(db, user.company_id, "reel_photo", {"brand_id": brand.id, "post_id": post.id, "index": index, **body.model_dump()}))


@router.post("/posts/{post_id}/reel/scenes/{index}/upload")
async def scene_upload(post_id: str, index: int, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    post, brand = _reel_post(post_id, user, db)
    reel = reel_of(post, brand)
    if not 0 <= index < len(reel["scenes"]):
        raise HTTPException(404, "المشهد مش موجود")
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(415, "الصورة لازم تكون PNG أو JPEG أو WEBP")
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "الصورة أكبر من 8MB")
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[file.content_type]
    reel["scenes"][index].update(bg_url=save_image(data, user.company_id, ext, file.content_type), credit=None)
    set_reel(post, reel)
    post.video_url = None
    db.commit()
    return post_out(post)


@router.post("/posts/{post_id}/reel/music")
async def music_upload(post_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The owner's own track. They are responsible for having the rights to it."""
    post, brand = _reel_post(post_id, user, db)
    kinds = {"audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav", "audio/x-wav": "wav", "audio/mp4": "m4a", "audio/x-m4a": "m4a"}
    if file.content_type not in kinds:
        raise HTTPException(415, "الموسيقى لازم تكون MP3 أو WAV أو M4A")
    data = await file.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "الملف أكبر من 12MB")
    reel = reel_of(post, brand)
    reel["music_url"] = save_image(data, user.company_id, kinds[file.content_type], file.content_type)
    reel["music"] = "custom"
    set_reel(post, reel)
    post.video_url = None
    db.commit()
    return post_out(post)


@router.post("/posts/{post_id}/reel/render")
async def render(post_id: str, overlays: list[UploadFile] = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The frontend draws each scene's Arabic text (plus the outro card) as PNGs; the worker builds the video."""
    post, brand = _reel_post(post_id, user, db)
    reel = reel_of(post, brand)
    if not reel["scenes"]:
        raise HTTPException(409, "اعمل سكريبت الريل الأول")
    if len(overlays) != len(reel["scenes"]) + 1:
        raise HTTPException(422, "عدد طبقات الكلام مش مظبوط")
    urls = []
    for f in overlays:
        data = await f.read()
        if f.content_type != "image/png" or len(data) > MAX_IMAGE_BYTES or not data.startswith(b"\x89PNG"):
            raise HTTPException(415, "طبقات الكلام لازم تكون PNG")
        urls.append(save_image(data, user.company_id, "png", "image/png"))
    return job_out(enqueue(db, user.company_id, "reel_render", {"brand_id": brand.id, "post_id": post.id, "overlays": urls}))
