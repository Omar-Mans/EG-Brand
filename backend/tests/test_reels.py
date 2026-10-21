"""Reels: AI script, scene photos, Arabic voice, synthesized music, ffmpeg render and video publishing."""

import shutil
import struct
import subprocess
import wave
import zlib

import pytest

from app import jobs
from app.reels import music
from app.social import meta

from .conftest import register
from .test_features import ready_brand
from .test_flow import PNG, run_job

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def overlay_png(w=1080, h=1920) -> bytes:
    """A transparent PNG with an opaque bar, like the text layer the frontend draws."""
    row_clear = b"\x00" + b"\x00\x00\x00\x00" * w
    row_bar = b"\x00" + b"\xf2\xb6\x40\xff" * w
    raw = b"".join(row_bar if 1000 <= y < 1200 else row_clear for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def reel_brand(client, h):
    return next(b["id"] for b in client.get("/api/brands", headers=h).json())


def reel_post(client, h):
    brand = ready_brand(client, h)  # Saudi market brand
    run_job(client, h, client.post(f"/api/brands/{brand['id']}/calendar", headers=h, json={"year": 2030, "month": 4}).json())
    post = client.get(f"/api/brands/{brand['id']}/posts", headers=h).json()[0]
    return client.patch(f"/api/posts/{post['id']}", headers=h, json={"format": "reel"}).json()


def test_options_and_voice_sample(client):
    o = client.get("/api/reels/options").json()
    assert set(o["voices"]) == {"sa_m", "sa_f", "eg_m", "eg_f"} and "calm" in o["music"] and o["voice_provider"] == "mock"
    r = client.get("/api/reels/voice-sample/eg_f")
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg" and len(r.content) > 100
    assert client.get("/api/reels/voice-sample/xx").status_code == 404


def test_script_edit_and_validation(client):
    h = register(client)
    post = reel_post(client, h)
    pid = post["id"]
    reel = run_job(client, h, client.post(f"/api/posts/{pid}/reel/script", headers=h, json={}).json())["result"]["reel"]
    assert reel["voice"] == "sa_m" and reel["music"] == "calm" and len(reel["scenes"]) == 3 and reel["outro_voice"]

    scenes = [{"text": s["text"], "sub": s["sub"], "voice": s["voice"]} for s in reel["scenes"]]
    scenes[0]["text"] = "عرض اليوم الوطني"
    scenes.append({"text": "", "sub": "", "voice": ""})  # empty scenes are dropped
    p = client.patch(f"/api/posts/{pid}/reel", headers=h, json={"voice": "eg_f", "music": "warm", "scenes": scenes}).json()
    r = p["design"]["reel"]
    assert r["voice"] == "eg_f" and r["music"] == "warm" and len(r["scenes"]) == 3 and r["scenes"][0]["text"] == "عرض اليوم الوطني"
    assert r["scenes"][0]["photo_query"]  # AI fields survive text edits
    assert client.patch(f"/api/posts/{pid}/reel", headers=h, json={"voice": "fr_m"}).status_code == 422
    assert client.patch(f"/api/posts/{pid}/reel", headers=h, json={"music": "custom"}).status_code == 422  # nothing uploaded
    assert client.patch(f"/api/posts/{pid}/reel", headers=h, json={"voice": "none"}).status_code == 200

    other = register(client, email="x@other.test", company="شركة تانية")
    assert client.post(f"/api/posts/{pid}/reel/script", headers=other, json={}).status_code == 404


@needs_ffmpeg
def test_render_reel_and_publish_video(client, monkeypatch):
    h = register(client)
    pid = reel_post(client, h)["id"]
    run_job(client, h, client.post(f"/api/posts/{pid}/reel/script", headers=h, json={}).json())
    run_job(client, h, client.post(f"/api/posts/{pid}/reel/scenes/0/photo", headers=h, json={"source": "stock"}).json())
    client.post(f"/api/posts/{pid}/reel/scenes/1/upload", headers=h, files={"file": ("car.png", overlay_png(400, 300), "image/png")})
    client.patch(f"/api/posts/{pid}/reel", headers=h, json={"music": "warm"})
    saved = next(p for p in client.get(f"/api/brands/{reel_brand(client, h)}/posts", headers=h).json() if p["id"] == pid)["design"]["reel"]
    assert saved["scenes"][0]["bg_url"] and saved["scenes"][1]["bg_url"].endswith(".png")  # both photos persisted
    uploaded = saved["scenes"][1]["bg_url"]

    files = [("overlays", (f"s{i}.png", overlay_png(), "image/png")) for i in range(3)]
    assert client.post(f"/api/posts/{pid}/reel/render", headers=h, files=files).status_code == 422  # outro layer missing
    files.append(("overlays", ("outro.png", overlay_png(), "image/png")))
    res = run_job(client, h, client.post(f"/api/posts/{pid}/reel/render", headers=h, files=files).json())["result"]
    assert res["video_url"].endswith(".mp4") and 8 < res["duration"] < 40
    after = next(p for p in client.get(f"/api/brands/{reel_brand(client, h)}/posts", headers=h).json() if p["id"] == pid)
    assert after["design"]["reel"]["scenes"][1]["bg_url"] == uploaded  # the render kept the owner's photo

    from app.storage import load_bytes
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
        f.write(load_bytes(res["video_url"]))
        f.flush()
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height", "-of", "csv=p=0", f.name],
                              capture_output=True, text=True).stdout
    assert "h264,1080,1920" in info and "aac" in info

    # The rendered reel is published as a video, not as the cover image.
    assets = {"pages": [{"id": "111", "name": "سيارتنا", "access_token": "PAGE_TOKEN",
                         "instagram_business_account": {"id": "222", "username": "s"}}], "ad_accounts": []}
    monkeypatch.setattr(meta, "assets_from_token", lambda t: (t, assets))
    client.post("/api/social/meta/token", headers=h, json={"token": "EAAB" + "x" * 40})
    sent = {}
    monkeypatch.setattr(meta, "publish_facebook_video", lambda page, tok, url, cap: sent.update(fb=url) or "fbv")
    monkeypatch.setattr(meta, "publish_instagram", lambda uid, tok, img, cap, fmt, video: sent.update(ig=video, fmt=fmt) or "igr")
    client.post(f"/api/posts/{pid}/image", headers=h, files={"file": ("cover.png", PNG, "image/png")})
    client.patch(f"/api/posts/{pid}", headers=h, json={"approved": True})
    client.post(f"/api/posts/{pid}/schedule", headers=h, json={"scheduled_at": "2020-01-01T00:00:00Z", "platforms": ["facebook", "instagram"]})
    assert jobs.process_due_posts() == 1
    assert sent == {"fb": res["video_url"], "ig": res["video_url"], "fmt": "reel"}


def test_music_presets_are_real_audio():
    for preset in music.PRESETS:
        with wave.open(music.track(preset)) as w:
            assert w.getframerate() == 44100 and w.getnframes() / 44100 >= 40
            frames = w.readframes(44100 * 5)
        peak = max(abs(int.from_bytes(frames[i:i + 2], "little", signed=True)) for i in range(0, len(frames), 200))
        assert 3000 < peak < 32767  # audible, not clipped


@needs_ffmpeg
def test_broken_scene_photo_gives_a_clear_error(client):
    h = register(client)
    pid = reel_post(client, h)["id"]
    run_job(client, h, client.post(f"/api/posts/{pid}/reel/script", headers=h, json={}).json())
    client.post(f"/api/posts/{pid}/reel/scenes/1/upload", headers=h, files={"file": ("bad.png", PNG, "image/png")})
    files = [("overlays", (f"s{i}.png", overlay_png(), "image/png")) for i in range(4)]
    job = client.post(f"/api/posts/{pid}/reel/render", headers=h, files=files).json()
    jobs.process_jobs()
    assert "صورة المشهد 2" in client.get(f"/api/jobs/{job['id']}", headers=h).json()["error"]


@needs_ffmpeg
def test_studio_montage_with_video_clips(client):
    h = register(client)
    brand = ready_brand(client, h)
    bad = client.post(f"/api/brands/{brand['id']}/reels", headers=h, json={"kind": "montage", "topic": "x", "seconds": 45})
    assert bad.status_code == 422
    r = client.post(f"/api/brands/{brand['id']}/reels", headers=h, json={"kind": "montage", "topic": "ليه تشتري من عندنا", "seconds": 15, "voice": "eg_m"}).json()
    run_job(client, h, r["job"])
    post = client.get(f"/api/brands/{brand['id']}/reels", headers=h).json()[0]
    reel = post["design"]["reel"]
    assert post["format"] == "reel" and reel["style"] == "montage" and reel["voice"] == "eg_m" and reel["seconds"] == 15
    assert post["headline"] == "عربية مضمونة بجد" and post["caption"] and post["hashtags"]  # filled from the AI script

    pid = post["id"]
    run_job(client, h, client.post(f"/api/posts/{pid}/reel/scenes/0/photo", headers=h, json={"source": "video", "prompt": "car showroom"}).json())
    assert client.patch(f"/api/posts/{pid}/reel", headers=h, json={"rhythm": "turbo"}).status_code == 422
    client.patch(f"/api/posts/{pid}/reel", headers=h, json={"rhythm": "fast", "music": "bright"})
    files = [("overlays", (f"s{i}.png", overlay_png(), "image/png")) for i in range(len(reel["scenes"]) + 1)]
    res = run_job(client, h, client.post(f"/api/posts/{pid}/reel/render", headers=h, files=files).json())["result"]
    done = client.get(f"/api/brands/{brand['id']}/reels", headers=h).json()[0]["design"]["reel"]
    assert all(s["clip_url"] for s in done["scenes"])  # montage fills every scene with a video clip
    assert res["video_url"].endswith(".mp4") and res["duration"] > 6


def test_studio_talk_script_and_raw_take(client):
    h = register(client)
    brand = ready_brand(client, h)
    assert client.post(f"/api/brands/{brand['id']}/reels", headers=h, json={"kind": "talk", "seconds": 30}).status_code == 422
    r = client.post(f"/api/brands/{brand['id']}/reels", headers=h,
                    json={"kind": "talk", "script": "عايز أتكلم عن الفحص والضمان عندنا", "seconds": 30}).json()
    talk = run_job(client, h, r["job"])["result"]["talk"]
    assert talk["own"] and talk["hook"] and talk["lines"] and talk["cta"] and talk["read_seconds"] > 0
    pid = r["post"]["id"]
    assert r["post"]["design"]["reel"]["voice"] == "none"  # the owner's own voice

    p = client.patch(f"/api/posts/{pid}/reel/talk", headers=h, json={"hook": "اسمع دي قبل ما تشتري", "lines": ["سطر واحد", ""], "cta": "كلمنا"}).json()
    assert p["design"]["reel"]["talk"]["lines"] == ["سطر واحد"] and p["design"]["reel"]["talk"]["words"] == 8

    take = client.post(f"/api/posts/{pid}/reel/raw", headers=h, files={"file": ("take.webm", b"\x1aE\xdf\xa3" + b"0" * 100, "video/webm")}).json()
    assert take["design"]["reel"]["raw"][0]["url"].endswith(".webm")
    assert client.post(f"/api/posts/{pid}/reel/raw", headers=h, files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 415


def test_pixabay_video_pick(monkeypatch):
    from app.reels import stock_video

    class Fake:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): return False

        def get(self, url, **kw):
            assert "videos" in url and kw["params"]["video_type"] == "film"
            return httpx.Response(200, json={"hits": [
                {"duration": 2, "user": "short", "pageURL": "p0", "videos": {"medium": {"url": "https://cdn/0.mp4", "width": 1280, "height": 720}}},
                {"duration": 9, "user": "Lina", "pageURL": "p1", "videos": {"medium": {"url": "https://cdn/1.mp4", "width": 720, "height": 1280}}}]})

    import httpx
    monkeypatch.setattr(stock_video.get_settings(), "pixabay_api_key", "k")
    url, credit = stock_video._pick_pixabay(Fake(), "car", 4)
    assert url == "https://cdn/1.mp4" and credit["name"] == "Lina"  # long enough, and vertical first
