"""Background photos for post designs. The design itself (Arabic text, layout) is drawn by the frontend on top."""

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


def generate_background(db: Session, brand: Brand, post: Post, custom_prompt: str = "") -> str:
    s = get_settings()
    company = brand.company_id
    budget = s.default_monthly_ai_budget_usd
    from ..models import Company

    c = db.get(Company, company)
    if c:
        budget = c.monthly_ai_budget_usd
    if budget and month_spend(db, company) >= budget:
        raise AIError("budget_exceeded", "الشركة وصلت لحد ميزانية الـ AI الشهرية")

    backend = s.image_backend
    prompt = build_prompt(post, brand, custom_prompt)
    w, h = _size(post)
    started = time.monotonic()
    cost = 0.0
    if backend == "mock":
        palette = (brand.dna or {}).get("palette") or [{"hex": "#556677"}]
        data, ctype = _solid_png(palette[0]["hex"]), "image/png"
    else:
        try:
            with httpx.Client(timeout=180) as client:
                if backend == "fal":
                    r = client.post(f"https://fal.run/{s.fal_model}", headers={"Authorization": f"Key {s.fal_key}"},
                                    json={"prompt": prompt, "image_size": {"width": w, "height": h}, "num_images": 1})
                    if r.status_code >= 400:
                        raise AIError("image_failed", f"fal رجّع {r.status_code}: {r.text[:200]}")
                    data, ctype = _download(client, r.json()["images"][0]["url"])
                    cost = s.image_cost_usd
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
    post.bg_url = url
    post.image_url = None
    post.approved = False
    db.commit()
    return url
