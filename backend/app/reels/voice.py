"""Arabic text-to-speech. Saudi and Egyptian neural voices, free.

azure: official Azure Speech free tier (needs AZURE_SPEECH_KEY), safe for paying clients.
edge:  the same Microsoft neural voices through the free Edge read-aloud service (no key). Unofficial: fine for
       demos and testing; switch to azure for production.
mock:  silence with a realistic length, for tests and keyless dev.
"""

import asyncio
import subprocess
import time
from xml.sax.saxutils import escape

import httpx

from ..config import get_settings
from ..ai.llm import AIError

VOICES = {
    "sa_m": {"label": "سعودي - رجل", "name": "ar-SA-HamedNeural", "lang": "ar-SA", "dialect": "saudi"},
    "sa_f": {"label": "سعودي - ست", "name": "ar-SA-ZariyahNeural", "lang": "ar-SA", "dialect": "saudi"},
    "eg_m": {"label": "مصري - رجل", "name": "ar-EG-ShakirNeural", "lang": "ar-EG", "dialect": "egyptian"},
    "eg_f": {"label": "مصري - ست", "name": "ar-EG-SalmaNeural", "lang": "ar-EG", "dialect": "egyptian"},
}
NO_VOICE = "none"
DEFAULT_VOICE = {"SA": "sa_m", "EG": "eg_m"}


def probe_seconds(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                         capture_output=True, text=True, timeout=30)
    try:
        return float(out.stdout.strip())
    except ValueError as exc:
        raise AIError("voice_failed", "ملف الصوت بايظ") from exc


def _azure(text: str, voice: dict) -> bytes:
    s = get_settings()
    ssml = (f"<speak version='1.0' xml:lang='{voice['lang']}'><voice name='{voice['name']}'>"
            f"<prosody rate='+4%'>{escape(text)}</prosody></voice></speak>")
    r = httpx.post(f"https://{s.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1", content=ssml.encode(),
                   headers={"Ocp-Apim-Subscription-Key": s.azure_speech_key, "Content-Type": "application/ssml+xml",
                            "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3", "User-Agent": "egbrand"},
                   timeout=60)
    if r.status_code >= 400:
        raise AIError("voice_failed", f"Azure Speech رجّع {r.status_code}")
    return r.content


def _edge(text: str, voice: dict) -> bytes:
    try:
        import edge_tts
    except ImportError as exc:
        raise AIError("voice_failed", "مكتبة edge-tts مش متسطبة") from exc

    async def run() -> bytes:
        chunks = []
        async for chunk in edge_tts.Communicate(text, voice["name"], rate="+4%").stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        return b"".join(chunks)

    try:
        data = asyncio.run(run())
    except Exception as exc:  # network errors come in many types from aiohttp
        raise AIError("voice_failed", f"خدمة الصوت مش متاحة دلوقتي: {exc.__class__.__name__}") from exc
    if not data:
        raise AIError("voice_failed", "خدمة الصوت ما رجّعتش صوت")
    return data


def _mock(text: str, path: str) -> None:
    seconds = 0.6 + 0.38 * len(text.split())
    subprocess.run([get_settings().ffmpeg_bin, "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", f"{seconds:.2f}", "-q:a", "9", path], check=True, timeout=60)


def synthesize(text: str, voice_id: str, path: str) -> dict:
    """Writes an MP3 to `path`. Returns {"seconds", "provider", "chars", "ms"}."""
    voice = VOICES.get(voice_id)
    if not voice:
        raise AIError("voice_failed", "الصوت ده مش موجود")
    backend = get_settings().voice_backend
    started = time.monotonic()
    if backend == "mock":
        _mock(text, path)
    else:
        data = _azure(text, voice) if backend == "azure" else _edge(text, voice)
        with open(path, "wb") as f:
            f.write(data)
    return {"seconds": probe_seconds(path), "provider": backend, "chars": len(text),
            "ms": int((time.monotonic() - started) * 1000)}
