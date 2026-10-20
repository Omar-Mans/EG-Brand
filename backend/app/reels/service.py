"""Reel workflow: the AI writes the scenes, each scene gets a photo, then voice + music + render into one MP4."""

import copy
import os
import tempfile
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..ai import images, mock, prompts
from ..ai.llm import AIError, complete_json
from ..ai.services import brand_context
from ..models import Brand, Post, UsageEvent
from ..storage import load_bytes, save_image
from . import music as music_mod
from . import render as render_mod
from .voice import DEFAULT_VOICE, NO_VOICE, VOICES, synthesize

MUSIC_CHOICES = ["none", "custom", *music_mod.PRESETS]
MAX_SCENES = 6


def default_reel(brand: Brand) -> dict:
    market = (brand.brief or {}).get("market", "EG")
    return {"voice": DEFAULT_VOICE.get(market, "eg_m"), "music": "calm", "music_url": None, "scenes": [], "outro_voice": ""}


def reel_of(post: Post, brand: Brand) -> dict:
    """A deep copy: editing nested scenes in place would hide the change from the ORM and it would never be saved."""
    return copy.deepcopy({**default_reel(brand), **((post.design or {}).get("reel") or {})})


def set_reel(post: Post, reel: dict) -> None:
    post.design = {**copy.deepcopy(post.design or {}), "reel": reel}


def _clean_scene(x: dict) -> dict | None:
    if not isinstance(x, dict) or not str(x.get("text") or "").strip():
        return None
    return {"text": str(x["text"]).strip()[:80], "sub": str(x.get("sub") or "").strip()[:100],
            "voice": str(x.get("voice") or "").strip()[:300], "photo_query": str(x.get("photo_query") or "")[:80],
            "visual_prompt": str(x.get("visual_prompt") or "")[:500], "bg_url": None, "credit": None}


def generate_script(db: Session, brand: Brand, post: Post, voice: str | None = None) -> dict:
    reel = reel_of(post, brand)
    if voice in VOICES or voice == NO_VOICE:
        reel["voice"] = voice
    dialect = VOICES[reel["voice"]]["dialect"] if reel["voice"] in VOICES else (brand.brief or {}).get("dialect", "msa")
    current = {"headline": post.headline, "caption": post.caption, "cta": post.cta, "occasion": post.occasion, "pillar": post.pillar}
    data = complete_json(db, prompts.reel_script(brand.brief or {}, brand.dna or {}, current, dialect, brand_context(brand, 3000)),
                         company_id=brand.company_id, brand_id=brand.id, feature="reel", tier="quality",
                         mock=mock.reel_script, max_tokens=2000)
    items = data.get("scenes") if isinstance(data, dict) else None
    scenes = [s for s in (_clean_scene(x) for x in (items or [])[:MAX_SCENES]) if s]
    if len(scenes) < 2:
        raise AIError("invalid_json", "الـ AI ما رجّعش مشاهد كفاية، جرب تاني")
    old = reel.get("scenes") or []
    for i, s in enumerate(scenes):  # keep photos the user already picked
        if i < len(old) and old[i].get("bg_url"):
            s["bg_url"], s["credit"] = old[i]["bg_url"], old[i].get("credit")
    reel["scenes"] = scenes
    reel["outro_voice"] = str(data.get("outro_voice") or post.cta or "")[:120]
    set_reel(post, reel)
    post.video_url = None
    db.commit()
    return reel


def scene_photo(db: Session, brand: Brand, post: Post, index: int, source: str, custom: str = "") -> dict:
    reel = reel_of(post, brand)
    scenes = reel.get("scenes") or []
    if not 0 <= index < len(scenes):
        raise AIError("not_found", "المشهد مش موجود")
    sc = scenes[index]
    prompt = (f"{custom or sc.get('visual_prompt') or post.headline}. Professional vertical video frame, cinematic light, "
              "photorealistic, clean composition. No text, no letters, no logos, no watermark.")
    url, credit = images.make_photo(db, brand, prompt=prompt, query=(custom or sc.get("photo_query") or "business")[:80],
                                    size=(1080, 1920), source=source)
    sc["bg_url"], sc["credit"] = url, credit
    set_reel(post, reel)
    post.video_url = None
    db.commit()
    return sc


def _fill_photos(db: Session, brand: Brand, post: Post) -> None:
    """Scenes without a photo get one: a real stock photo when available, else an AI photo, else the post photo."""
    reel = reel_of(post, brand)
    for i, sc in enumerate(reel["scenes"]):
        if sc.get("bg_url"):
            continue
        for source in ("stock", "ai"):
            try:
                scene_photo(db, brand, post, i, source)
                break
            except AIError as exc:
                if exc.code == "budget_exceeded":
                    raise
        else:
            if post.bg_url:
                sc["bg_url"] = post.bg_url
                set_reel(post, reel)
            else:
                raise AIError("image_failed", "مقدرناش نجيب صور للمشاهد، ارفع صورك أو جرب تاني")
        reel = reel_of(post, brand)


def render_reel(db: Session, brand: Brand, post: Post, overlay_urls: list[str]) -> dict:
    reel = reel_of(post, brand)
    scenes = reel.get("scenes") or []
    if not scenes:
        raise AIError("no_script", "اعمل سكريبت الريل الأول")
    if len(overlay_urls) != len(scenes) + 1:
        raise AIError("render_failed", "عدد طبقات الكلام مش مظبوط، اعمل الفيديو تاني")
    _fill_photos(db, brand, post)
    reel = reel_of(post, brand)
    started = time.monotonic()
    voice_id = reel["voice"] if reel["voice"] in VOICES else None
    chars, provider = 0, ""
    with tempfile.TemporaryDirectory(prefix="reel-") as work:
        def fetch(url: str, name: str) -> str:
            path = os.path.join(work, name)
            with open(path, "wb") as f:
                f.write(load_bytes(url))
            return path

        parts = []
        lines = [sc["voice"] for sc in reel["scenes"]] + [reel.get("outro_voice") or ""]
        for i, url in enumerate(overlay_urls):
            is_outro = i == len(reel["scenes"])
            photo = None if is_outro else fetch(reel["scenes"][i]["bg_url"], f"photo{i}")
            vpath, vsec = None, 0.0
            if voice_id and lines[i].strip():
                vpath = os.path.join(work, f"voice{i}.mp3")
                info = synthesize(lines[i], voice_id, vpath)
                vsec, chars, provider = info["seconds"], chars + info["chars"], info["provider"]
            parts.append(render_mod.Scene(overlay=fetch(url, f"text{i}.png"), photo=photo, voice=vpath, voice_s=vsec))
        track = None
        if reel["music"] in music_mod.PRESETS:
            track = music_mod.track(reel["music"])
        elif reel["music"] == "custom" and reel.get("music_url"):
            track = fetch(reel["music_url"], "music")
        out = os.path.join(work, "reel.mp4")
        seconds = render_mod.render(parts, track, work, out)
        with open(out, "rb") as f:
            url = save_image(f.read(), brand.company_id, "mp4", "video/mp4")
    if chars:
        db.add(UsageEvent(company_id=brand.company_id, brand_id=brand.id, feature="voice", model=provider,
                          input_tokens=chars, ok=True))
    reel["duration"] = seconds
    reel["rendered_at"] = datetime.now(timezone.utc).isoformat()
    reel["render_ms"] = int((time.monotonic() - started) * 1000)
    set_reel(post, reel)
    post.video_url = url
    post.approved = False
    db.commit()
    return {"video_url": url, "duration": seconds}
