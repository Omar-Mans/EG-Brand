"""Free stock video clips for AI-made reels: Pixabay Videos (same free key as photos) or Pexels Videos.

Clips are downloaded and stored on our side (Pixabay asks for this; no hotlinking). The photographer is credited.
"""

import random
import subprocess
import time

import httpx
from sqlalchemy.orm import Session

from ..ai.llm import AIError
from ..config import get_settings
from ..models import Brand, UsageEvent
from ..storage import save_image

MAX_CLIP_BYTES = 40_000_000


def backend() -> str:
    s = get_settings()
    if s.pexels_api_key:
        return "pexels"
    if s.pixabay_api_key:
        return "pixabay"
    return "mock" if not s.ai_live else ""


def _pick_pixabay(client: httpx.Client, query: str, min_seconds: float) -> tuple[str, dict]:
    s = get_settings()
    r = client.get("https://pixabay.com/api/videos/", params={"key": s.pixabay_api_key, "q": query[:100], "video_type": "film",
                                                             "safesearch": "true", "per_page": 20})
    if r.status_code >= 400:
        raise AIError("video_failed", f"Pixabay رجّع {r.status_code}")
    hits = [h for h in r.json().get("hits") or [] if (h.get("duration") or 0) >= min_seconds] or (r.json().get("hits") or [])
    if not hits:
        raise AIError("no_video", f"مفيش لقطات فيديو لـ «{query}»، جرب كلمات تانية بالإنجليزي")
    # prefer vertical clips, then a random one of the best few so reels don't all look alike
    hits.sort(key=lambda h: -((h.get("videos") or {}).get("medium", {}).get("height", 0) > (h.get("videos") or {}).get("medium", {}).get("width", 1)))
    hit = random.choice(hits[:5])
    files = hit.get("videos") or {}
    f = next((files[k] for k in ("medium", "large", "small") if files.get(k, {}).get("url")), None)
    if not f:
        raise AIError("no_video", "اللقطة مش متاحة")
    return f["url"], {"name": hit.get("user", ""), "url": hit.get("pageURL", ""), "source": "Pixabay"}


def _pick_pexels(client: httpx.Client, query: str, min_seconds: float) -> tuple[str, dict]:
    s = get_settings()
    r = client.get("https://api.pexels.com/videos/search", headers={"Authorization": s.pexels_api_key},
                   params={"query": query, "orientation": "portrait", "per_page": 15})
    if r.status_code >= 400:
        raise AIError("video_failed", f"Pexels رجّع {r.status_code}")
    vids = [v for v in r.json().get("videos") or [] if (v.get("duration") or 0) >= min_seconds] or (r.json().get("videos") or [])
    if not vids:
        raise AIError("no_video", f"مفيش لقطات فيديو لـ «{query}»، جرب كلمات تانية بالإنجليزي")
    v = random.choice(vids[:5])
    files = sorted((f for f in v.get("video_files") or [] if f.get("link") and (f.get("height") or 0) <= 1920),
                   key=lambda f: -(f.get("height") or 0))
    if not files:
        raise AIError("no_video", "اللقطة مش متاحة")
    return files[0]["link"], {"name": (v.get("user") or {}).get("name", ""), "url": v.get("url", ""), "source": "Pexels"}


def _mock_clip(hex_color: str, seconds: float) -> bytes:
    """A short moving test clip in the brand colour, for tests and keyless dev."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=c={hex_color}:s=720x1280:r=30,noise=alls=20:allf=t",
                          "-t", f"{seconds:.1f}", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                          "-movflags", "+frag_keyframe+empty_moov", "-f", "mp4", "-"], capture_output=True, timeout=60)
    if out.returncode != 0:
        raise AIError("video_failed", "مقدرناش نعمل لقطة تجريبية")
    return out.stdout


def fetch_clip(db: Session, brand: Brand, query: str, min_seconds: float = 4.0) -> tuple[str, dict | None]:
    """Downloads one clip for the query and stores it. Returns (url, credit)."""
    kind = backend()
    if not kind:
        raise AIError("no_stock", "حط PIXABAY_API_KEY في الإعدادات عشان لقطات الفيديو تشتغل (مجاني)")
    started = time.monotonic()
    credit = None
    if kind == "mock":
        palette = (brand.dna or {}).get("palette") or [{"hex": "#556677"}]
        data = _mock_clip(palette[0]["hex"].replace("#", "0x"), max(4.0, min_seconds))
    else:
        try:
            with httpx.Client(timeout=120, follow_redirects=True) as client:
                url, credit = (_pick_pexels if kind == "pexels" else _pick_pixabay)(client, query, min_seconds)
                with client.stream("GET", url) as r:
                    if r.status_code >= 400:
                        raise AIError("video_failed", f"تحميل اللقطة رجّع {r.status_code}")
                    chunks, size = [], 0
                    for chunk in r.iter_bytes():
                        size += len(chunk)
                        if size > MAX_CLIP_BYTES:
                            raise AIError("video_failed", "اللقطة كبيرة جداً")
                        chunks.append(chunk)
                    data = b"".join(chunks)
        except httpx.HTTPError as exc:
            raise AIError("video_failed", f"مكتبة الفيديو مش متاحة: {exc.__class__.__name__}") from exc
    stored = save_image(data, brand.company_id, "mp4", "video/mp4")
    db.add(UsageEvent(company_id=brand.company_id, brand_id=brand.id, feature="stock_video", model=kind,
                      latency_ms=int((time.monotonic() - started) * 1000), ok=True))
    return stored, credit
