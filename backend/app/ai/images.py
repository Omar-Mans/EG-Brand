"""Background photos for post designs. The design itself (Arabic text, layout) is drawn by the frontend on top."""

import base64
import random
import struct
import time
import zlib
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Brand, Post, UsageEvent
from ..storage import save_image
from .catalog import PHOTO_LAYOUTS
from .llm import AIError, month_spend


def _solid_png(hex_color: str, w: int = 16, h: int = 16) -> bytes:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    raw = b"".join(b"\x00" + bytes([r, g, b]) * w for _ in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def build_prompt(post: Post, brand: Brand, custom: str = "") -> str:
    design = post.design or {}
    subject = custom or design.get("visual_prompt") or f"{(brand.brief or {}).get('idea', '')}, {post.headline}"
    return (f"{subject}. Professional advertising photography, high-end commercial look, natural soft light, "
            "sharp focus, rich but realistic colors, clean composition with empty space for a text overlay. "
            "No text, no letters, no words, no logos, no watermark.")


def _size(post: Post) -> tuple[int, int]:
    return (1080, 1080) if post.format == "post" else (1080, 1920)


def _download(client: httpx.Client, url: str) -> tuple[bytes, str]:
    r = client.get(url, follow_redirects=True)
    ctype = r.headers.get("content-type", "").split(";")[0]
    if r.status_code >= 400 or not ctype.startswith("image/"):
        raise AIError("image_failed", f"مزود الصور رجّع {r.status_code}")
    return r.content, ctype


def stock_query(post: Post, brand: Brand, custom: str = "") -> str:
    design = post.design or {}
    q = custom or design.get("photo_query") or ""
    if not q:  # fall back to the first words of the English visual prompt
        q = " ".join((design.get("visual_prompt") or "business").replace(",", " ").split()[:4])
    return q[:80]


def _cloudflare(client: httpx.Client, prompt: str) -> tuple[bytes, str]:
    s = get_settings()
    r = client.post(f"https://api.cloudflare.com/client/v4/accounts/{s.cf_account_id}/ai/run/{s.cf_image_model}",
                    headers={"Authorization": f"Bearer {s.cf_api_token}"}, json={"prompt": prompt[:2000], "steps": 4})
    if r.status_code >= 400:
        raise AIError("image_failed", f"Cloudflare رجّع {r.status_code}: {r.text[:200]}")
    try:
        return base64.b64decode(r.json()["result"]["image"]), "image/jpeg"
    except (KeyError, TypeError, ValueError) as exc:
        raise AIError("image_failed", "Cloudflare ما رجّعش صورة") from exc


def _pexels(client: httpx.Client, query: str, portrait: bool) -> tuple[bytes, str, dict]:
    s = get_settings()
    r = client.get("https://api.pexels.com/v1/search", headers={"Authorization": s.pexels_api_key},
                   params={"query": query, "orientation": "portrait" if portrait else "square", "per_page": 15})
    if r.status_code >= 400:
        raise AIError("image_failed", f"Pexels رجّع {r.status_code}")
    photos = r.json().get("photos") or []
    if not photos:
        raise AIError("no_photo", f"مفيش صور مناسبة لـ \"{query}\"، جرب كلمات تانية بالإنجليزي")
    photo = random.choice(photos[:8])
    src = photo.get("src") or {}
    data, ctype = _download(client, src.get("portrait") if portrait else src.get("large2x") or src.get("original"))
    return data, ctype, {"name": photo.get("photographer", ""), "url": photo.get("url", ""), "source": "Pexels"}


def _pixabay(client: httpx.Client, query: str, portrait: bool) -> tuple[bytes, str, dict]:
    """Pixabay requires saving the file on our side (no hotlinking), which is what we do anyway."""
    s = get_settings()
    r = client.get("https://pixabay.com/api/", params={"key": s.pixabay_api_key, "q": query[:100], "image_type": "photo",
                                                        "orientation": "vertical" if portrait else "all",
                                                        "safesearch": "true", "per_page": 20})
    if r.status_code >= 400:
        raise AIError("image_failed", f"Pixabay رجّع {r.status_code}")
    hits = r.json().get("hits") or []
    if not hits:
        raise AIError("no_photo", f"مفيش صور مناسبة لـ \"{query}\"، جرب كلمات تانية بالإنجليزي")
    hit = random.choice(hits[:8])
    data, ctype = _download(client, hit.get("largeImageURL") or hit["webformatURL"])
    return data, ctype, {"name": hit.get("user", ""), "url": hit.get("pageURL", ""), "source": "Pixabay"}


def make_photo(db: Session, brand: Brand, *, prompt: str, query: str, size: tuple[int, int], source: str = "ai") -> tuple[str, dict | None]:
    """One background photo: source="ai" generates it, source="stock" picks a real photo (Pixabay or Pexels).
    Returns (stored url, credit or None). Checks the AI budget and records the call."""
    s = get_settings()
    company = brand.company_id
    budget = s.default_monthly_ai_budget_usd
    from ..models import Company

    c = db.get(Company, company)
    if c:
        budget = c.monthly_ai_budget_usd
    if budget and month_spend(db, company) >= budget:
        raise AIError("budget_exceeded", "الشركة وصلت لحد ميزانية الـ AI الشهرية")

    if source == "stock":
        backend = s.stock_backend
        if not backend:
            raise AIError("no_stock", "حط PIXABAY_API_KEY في الإعدادات عشان الصور الحقيقية تشتغل (مجاني)")
    else:
        backend = s.image_backend
    w, h = size
    started = time.monotonic()
    cost = 0.0
    credit = None
    if backend == "mock":
        palette = (brand.dna or {}).get("palette") or [{"hex": "#556677"}]
        data, ctype = _solid_png(palette[0]["hex"]), "image/png"
    else:
        try:
            with httpx.Client(timeout=180) as client:
                if backend in ("pexels", "pixabay"):
                    stock = _pexels if backend == "pexels" else _pixabay
                    data, ctype, credit = stock(client, query, h > w)
                elif backend == "fal":
                    r = client.post(f"https://fal.run/{s.fal_model}", headers={"Authorization": f"Key {s.fal_key}"},
                                    json={"prompt": prompt, "image_size": {"width": w, "height": h}, "num_images": 1})
                    if r.status_code >= 400:
                        raise AIError("image_failed", f"fal رجّع {r.status_code}: {r.text[:200]}")
                    data, ctype = _download(client, r.json()["images"][0]["url"])
                    cost = s.image_cost_usd
                elif backend == "cloudflare":
                    data, ctype = _cloudflare(client, prompt)
                else:
                    url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
                           f"?width={w}&height={h}&nologo=true&model=flux&seed={random.randint(1, 10**6)}")
                    data, ctype = _download(client, url)
        except httpx.HTTPError as exc:
            db.add(UsageEvent(company_id=company, brand_id=brand.id, feature="image", model=backend, ok=False,
                              latency_ms=int((time.monotonic() - started) * 1000)))
            db.commit()
            raise AIError("image_failed", f"مزود الصور مش متاح: {exc}") from exc
    ext = "png" if ctype == "image/png" else "jpg"
    url = save_image(data, company, ext, ctype)
    db.add(UsageEvent(company_id=company, brand_id=brand.id, feature="image", model=backend, cost_usd=cost,
                      latency_ms=int((time.monotonic() - started) * 1000), ok=True))
    return url, credit


def generate_background(db: Session, brand: Brand, post: Post, custom_prompt: str = "", source: str = "ai") -> str:
    """source="ai" makes a new photo with the image model; source="stock" picks a real photo from Pixabay or Pexels."""
    url, credit = make_photo(db, brand, prompt=build_prompt(post, brand, custom_prompt),
                             query=stock_query(post, brand, custom_prompt), size=_size(post), source=source)
    post.bg_url = url
    design = dict(post.design or {})
    if credit:
        design["photo_credit"] = credit
    else:
        design.pop("photo_credit", None)
    if design.get("layout") not in PHOTO_LAYOUTS:  # a photo is only visible on the photo layouts
        design["layout"] = "photo_overlay"
    post.design = design
    post.image_url = None
    post.approved = False
    db.commit()
    return url
