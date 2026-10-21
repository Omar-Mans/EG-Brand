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
from . import stock_video
from .voice import DEFAULT_VOICE, NO_VOICE, VOICES, synthesize

MUSIC_CHOICES = ["none", "custom", *music_mod.PRESETS]
MAX_SCENES = 6
STYLES = ["photo", "montage"]          # photo scenes with camera moves, or a montage of real video clips
RHYTHM_CHOICES = list(render_mod.RHYTHMS)
SECONDS = {15: 3, 30: 4, 60: 6}        # reel length -> number of scenes
WORDS_PER_SECOND = 2.3                 # comfortable Arabic speaking pace, used to size a talking script


def default_reel(brand: Brand) -> dict:
    market = (brand.brief or {}).get("market", "EG")
    return {"voice": DEFAULT_VOICE.get(market, "eg_m"), "music": "calm", "music_url": None, "scenes": [], "outro_voice": "",
            "style": "photo", "rhythm": "calm", "captions": True, "seconds": 30}


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
            "visual_prompt": str(x.get("visual_prompt") or "")[:500], "bg_url": None, "clip_url": None, "credit": None}


def _dialect(reel: dict, brand: Brand) -> str:
    return VOICES[reel["voice"]]["dialect"] if reel["voice"] in VOICES else (brand.brief or {}).get("dialect", "msa")


def _fill_post_text(post: Post, data: dict) -> None:
    """Reels made from a topic in the studio get their headline, caption and hashtags from the AI."""
    if not isinstance(data, dict):
        return
    if data.get("title") and (not post.headline or (post.design or {}).get("studio")):
        post.headline = str(data["title"])[:120]
    if data.get("caption") and not post.caption:
        post.caption = str(data["caption"])[:2000]
    if isinstance(data.get("hashtags"), list) and not post.hashtags:
        post.hashtags = [str(h) for h in data["hashtags"][:6]]
    if data.get("cta") and not post.cta:
        post.cta = str(data["cta"])[:120]


def generate_script(db: Session, brand: Brand, post: Post, voice: str | None = None, style: str | None = None,
                    seconds: int | None = None) -> dict:
    reel = reel_of(post, brand)
    if voice in VOICES or voice == NO_VOICE:
        reel["voice"] = voice
    if style in STYLES:
        reel["style"] = style
    if seconds in SECONDS:
        reel["seconds"] = seconds
    current = {"headline": post.headline, "caption": post.caption, "cta": post.cta, "occasion": post.occasion, "pillar": post.pillar}
    data = complete_json(db, prompts.reel_script(brand.brief or {}, brand.dna or {}, current, _dialect(reel, brand),
                                                 brand_context(brand, 3000), SECONDS.get(reel["seconds"], 4), reel["style"] == "montage"),
                         company_id=brand.company_id, brand_id=brand.id, feature="reel", tier="quality",
                         mock=mock.reel_script, max_tokens=2000)
    items = data.get("scenes") if isinstance(data, dict) else None
    scenes = [s for s in (_clean_scene(x) for x in (items or [])[:MAX_SCENES]) if s]
    if len(scenes) < 2:
        raise AIError("invalid_json", "الـ AI ما رجّعش مشاهد كفاية، جرب تاني")
    old = reel.get("scenes") or []
    for i, s in enumerate(scenes):  # keep media the user already picked
        if i < len(old):
            for k in ("bg_url", "clip_url", "credit"):
                s[k] = old[i].get(k) or s.get(k)
    reel["scenes"] = scenes
    reel["outro_voice"] = str(data.get("outro_voice") or post.cta or "")[:120]
    _fill_post_text(post, data)
    set_reel(post, reel)
    post.video_url = None
    db.commit()
    return reel


def generate_talk(db: Session, brand: Brand, post: Post, topic: str, own_script: str, seconds: int) -> dict:
    """A script the owner reads to camera (teleprompter): written by the AI, or the owner's own script polished."""
    reel = reel_of(post, brand)
    seconds = seconds if seconds in SECONDS else 30
    data = complete_json(db, prompts.talk_script(brand.brief or {}, brand.dna or {}, topic, own_script, seconds,
                                                 int(seconds * WORDS_PER_SECOND), _dialect(reel, brand), brand_context(brand, 3000)),
                         company_id=brand.company_id, brand_id=brand.id, feature="talk", tier="quality",
                         mock=mock.talk_script, max_tokens=1800)
    if not isinstance(data, dict):
        raise AIError("invalid_json", "شكل السكريبت مش صحيح")
    lines = [str(x).strip() for x in (data.get("lines") or []) if str(x).strip()][:20]
    hook = str(data.get("hook") or "").strip()
    cta = str(data.get("cta") or "").strip()
    if not hook and not lines:
        raise AIError("invalid_json", "الـ AI ما رجّعش سكريبت، جرب تاني")
    words = len(" ".join([hook, *lines, cta]).split())
    reel["talk"] = {"topic": topic[:300], "own": bool(own_script.strip()), "seconds": seconds, "hook": hook, "lines": lines, "cta": cta,
                    "broll": [str(x)[:80] for x in (data.get("broll") or [])][:8], "words": words,
                    "read_seconds": round(words / WORDS_PER_SECOND)}
    _fill_post_text(post, data)
    set_reel(post, reel)
    db.commit()
    return reel["talk"]


def _scene(post: Post, brand: Brand, index: int) -> tuple[dict, dict]:
    reel = reel_of(post, brand)
    scenes = reel.get("scenes") or []
    if not 0 <= index < len(scenes):
        raise AIError("not_found", "المشهد مش موجود")
    return reel, scenes[index]


def scene_photo(db: Session, brand: Brand, post: Post, index: int, source: str, custom: str = "") -> dict:
    """source: "stock" (real photo), "ai" (generated photo) or "video" (a real stock video clip)."""
    reel, sc = _scene(post, brand, index)
    query = (custom or sc.get("photo_query") or "business")[:80]
    if source == "video":
        sc["clip_url"], sc["credit"] = stock_video.fetch_clip(db, brand, query, render_mod.RHYTHMS[reel.get("rhythm", "calm")]["floor"])
    else:
        prompt = (f"{custom or sc.get('visual_prompt') or post.headline}. Professional vertical video frame, cinematic light, "
                  "photorealistic, clean composition. No text, no letters, no logos, no watermark.")
        url, credit = images.make_photo(db, brand, prompt=prompt, query=query, size=(1080, 1920), source=source)
        sc["bg_url"], sc["clip_url"], sc["credit"] = url, None, credit
    set_reel(post, reel)
    post.video_url = None
    db.commit()
    return sc


def _fill_media(db: Session, brand: Brand, post: Post) -> None:
    """Scenes without media get some. Montage: a real video clip first; photo reels (and fallback): stock photo, then AI photo."""
    reel = reel_of(post, brand)
    order = ("video", "stock", "ai") if reel.get("style") == "montage" else ("stock", "ai")
    for i, sc in enumerate(reel["scenes"]):
        if sc.get("bg_url") or sc.get("clip_url"):
            continue
        for source in order:
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
                raise AIError("image_failed", "مقدرناش نجيب صور أو لقطات للمشاهد، ارفع صورك أو جرب تاني")
        reel = reel_of(post, brand)


def create_studio_post(db: Session, brand: Brand, topic: str, kind: str, seconds: int, voice: str | None) -> Post:
    """A reel started from the studio (not from the monthly plan), dated today in the brand's timezone."""
    from ..ai import timing

    today = timing.now_local(timing.brand_tz(brand.brief or {})).date()
    reel = default_reel(brand)
    reel.update(style="montage" if kind == "montage" else "photo", seconds=seconds if seconds in SECONDS else 30)
    if voice in VOICES or voice == NO_VOICE:
        reel["voice"] = voice
    if kind == "talk":
        reel["voice"] = NO_VOICE  # the owner's own voice is the voice-over
    post = Post(company_id=brand.company_id, brand_id=brand.id, month=f"{today.year:04d}-{today.month:02d}", day=today.day,
                time="21:00", format="reel", pillar="", headline=topic[:120], caption="", hashtags=[], cta="",
                design={"layout": "photo_overlay", "studio": kind, "reel": reel})
    db.add(post)
    db.commit()
    return post


def render_reel(db: Session, brand: Brand, post: Post, overlay_urls: list[str]) -> dict:
    reel = reel_of(post, brand)
    scenes = reel.get("scenes") or []
    if not scenes:
        raise AIError("no_script", "اعمل سكريبت الريل الأول")
    if len(overlay_urls) != len(scenes) + 1:
        raise AIError("render_failed", "عدد طبقات الكلام مش مظبوط، اعمل الفيديو تاني")
    _fill_media(db, brand, post)
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
            sc = None if is_outro else reel["scenes"][i]
            clip = fetch(sc["clip_url"], f"clip{i}") if sc and sc.get("clip_url") else None
            photo = fetch(sc["bg_url"], f"photo{i}") if sc and not clip else None
            vpath, vsec = None, 0.0
            if voice_id and lines[i].strip():
                vpath = os.path.join(work, f"voice{i}.mp3")
                info = synthesize(lines[i], voice_id, vpath)
                vsec, chars, provider = info["seconds"], chars + info["chars"], info["provider"]
            parts.append(render_mod.Scene(overlay=fetch(url, f"text{i}.png"), photo=photo, clip=clip, voice=vpath, voice_s=vsec))
        track, beat = None, None
        if reel["music"] in music_mod.PRESETS:
            track = music_mod.track(reel["music"])
            beat = 120 / music_mod.PRESETS[reel["music"]]["bpm"]  # cut every two beats
        elif reel["music"] == "custom" and reel.get("music_url"):
            track = fetch(reel["music_url"], "music")
        out = os.path.join(work, "reel.mp4")
        seconds = render_mod.render(parts, track, work, out, reel.get("rhythm", "calm"), beat)
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
