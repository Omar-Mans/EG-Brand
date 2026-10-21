"""Builds the MP4 with ffmpeg: real video clips (or a slow camera pan on photos), the Arabic text layer (drawn by the
frontend with real fonts) sliding in, transitions in the chosen rhythm, cuts on the music beat, one colour grade
across all shots, a branded outro, voice-over per scene and music underneath."""

import math

import os
import subprocess
from dataclasses import dataclass

from ..ai.llm import AIError
from ..config import get_settings

W, H, FPS = 1080, 1920, 30
GRADE = "eq=contrast=1.06:saturation=1.1:brightness=0.01"  # same look on every clip, so mixed sources feel like one shoot
RHYTHMS = {
    # transition length, transitions cycled between scenes, shortest scene
    "calm": {"xfade": 0.4, "transitions": ["fade"], "floor": 3.2},
    "fast": {"xfade": 0.25, "transitions": ["slideleft", "slideup", "wipeleft", "circleopen"], "floor": 2.2},
    "cinematic": {"xfade": 0.6, "transitions": ["fadeblack", "fade"], "floor": 3.6},
}
PAD_W, PAD_H = 1188, 2112  # photo is scaled 10% larger than the frame so the camera can pan


@dataclass
class Scene:
    overlay: str            # PNG, 1080x1920, transparent except the text (or opaque for the outro)
    photo: str | None       # background photo; None for the outro card
    voice: str | None       # MP3 of this scene's voice-over
    voice_s: float = 0.0
    clip: str | None = None  # stock or uploaded video; used instead of the photo when set


def _run(args: list[str], timeout: int = 600) -> None:
    out = subprocess.run([get_settings().ffmpeg_bin, "-y", "-v", "error", *args], capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise AIError("render_failed", f"ffmpeg: {out.stderr.strip()[-300:]}")


def _size(path: str) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30)
    try:
        w, h = (int(x) for x in out.stdout.strip().split(",")[:2])
    except ValueError as exc:
        raise AIError("render_failed", "الصورة مش بتفتح") from exc
    if w <= 0 or h <= 0:
        raise AIError("render_failed", "الصورة مش بتفتح")
    return w, h


def _prep_photo(src: str, dst: str) -> None:
    """Scale once to the pan size, so the main render only crops (much faster than per-frame scaling).
    Vertical photos fill the frame; square or wide photos are shown whole on a blurred copy of themselves,
    so a product is never cut in half."""
    w, h = _size(src)
    if w / h <= 0.8:
        vf = f"scale={PAD_W}:{PAD_H}:force_original_aspect_ratio=increase,crop={PAD_W}:{PAD_H}"
    else:
        vf = (f"split[a][b];[a]scale={PAD_W // 4}:{PAD_H // 4}:force_original_aspect_ratio=increase,crop={PAD_W // 4}:{PAD_H // 4},"
              f"boxblur=12:2,eq=brightness=-0.08,scale={PAD_W}:{PAD_H}[bg];[b]scale={PAD_W}:-2[fg];[bg][fg]overlay=0:(H-h)/2")
    _run(["-i", src, "-filter_complex", vf, "-frames:v", "1", "-q:v", "3", dst])


def durations(scenes: list[Scene], rhythm: str = "calm", beat: float | None = None) -> list[float]:
    """Each scene lasts long enough for its voice line; with music, it is rounded up to whole beats so cuts land on the beat."""
    r = RHYTHMS.get(rhythm, RHYTHMS["calm"])
    out = []
    for s in scenes:
        outro = s.photo is None and s.clip is None
        floor = 2.6 if outro else r["floor"]
        d = max(floor, s.voice_s + 0.9 + r["xfade"] if s.voice else floor)
        if beat and not outro:
            d = math.ceil(d / beat) * beat
        out.append(round(d, 2))
    return out


def _prep_clip(src: str, dst: str, seconds: float) -> None:
    """Trim (looping if the clip is short), fill the 9:16 frame, 30 fps, graded, no sound."""
    try:
        _run(["-stream_loop", "-1", "-t", f"{seconds:.2f}", "-i", src, "-an",
              "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,{GRADE},format=yuv420p",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", dst])
    except AIError as exc:
        raise AIError("render_failed", "لقطة فيديو مش بتفتح، غيّرها") from exc


def render(scenes: list[Scene], music: str | None, workdir: str, out_path: str,
           rhythm: str = "calm", beat: float | None = None) -> float:
    """Returns the video length in seconds."""
    if not scenes:
        raise AIError("render_failed", "مفيش مشاهد")
    r = RHYTHMS.get(rhythm, RHYTHMS["calm"])
    xfade = r["xfade"]
    durs = durations(scenes, rhythm, beat)
    args: list[str] = []
    graph: list[str] = []
    idx = 0
    labels = []
    for i, (s, d) in enumerate(zip(scenes, durs)):
        if s.clip:
            prepped = os.path.join(workdir, f"clip{i}.mp4")
            _prep_clip(s.clip, prepped, d)
            args += ["-i", prepped]
            graph.append(f"[{idx}:v]setpts=PTS-STARTPTS[b{i}]")
            idx += 1
        elif s.photo:
            prepped = os.path.join(workdir, f"bg{i}.jpg")
            try:
                _prep_photo(s.photo, prepped)
            except AIError as exc:
                raise AIError("render_failed", f"صورة المشهد {i + 1} مش بتفتح، غيّرها أو ارفع صورة تانية") from exc
            args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d}", "-i", prepped]
            bg = idx
            idx += 1
            # alternate the camera move: drift left, drift up, drift right...
            dx, dy = [("(iw-ow)*t/{d}", "(ih-oh)/2"), ("(iw-ow)/2", "(ih-oh)*(1-t/{d})"),
                      ("(iw-ow)*(1-t/{d})", "(ih-oh)/2"), ("(iw-ow)/2", "(ih-oh)*t/{d}")][i % 4]
            graph.append(f"[{bg}:v]crop={W}:{H}:x='{dx.format(d=d)}':y='{dy.format(d=d)}',{GRADE}[b{i}]")
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d}", "-i", s.overlay]
        ov = idx
        idx += 1
        if s.photo or s.clip:
            graph.append(f"[{ov}:v]format=rgba,fade=t=in:st=0.25:d=0.5:alpha=1[o{i}]")
            graph.append(f"[b{i}][o{i}]overlay=x=0:y='if(lt(t,0.75),60*(1-t/0.75),0)',fps={FPS},format=yuv420p,setsar=1[v{i}]")
        else:
            graph.append(f"[{ov}:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[v{i}]")
        labels.append(f"v{i}")

    # cross-fade the scenes into one stream
    starts, t = [], 0.0
    for d in durs:
        starts.append(t)
        t += d - xfade
    total = round(sum(durs) - xfade * (len(durs) - 1), 2)
    last = labels[0]
    for i in range(1, len(labels)):
        out = f"x{i}" if i < len(labels) - 1 else "vout"
        kind = r["transitions"][(i - 1) % len(r["transitions"])] if i < len(labels) - 1 else "fade"  # the outro always fades in
        graph.append(f"[{last}][{labels[i]}]xfade=transition={kind}:duration={xfade}:offset={starts[i]:.2f}[{out}]")
        last = out
    if len(labels) == 1:
        graph.append(f"[{last}]null[vout]")

    # audio: each voice line starts shortly after its scene, music loops underneath
    mix = []
    for i, s in enumerate(scenes):
        if s.voice:
            args += ["-i", s.voice]
            ms = int((starts[i] + 0.35) * 1000)
            graph.append(f"[{idx}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms},apad[a{i}]")
            mix.append(f"[a{i}]")
            idx += 1
    has_voice = bool(mix)
    if music:
        args += ["-stream_loop", "-1", "-i", music]
        vol = 0.22 if has_voice else 0.5
        graph.append(f"[{idx}:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:{total},volume={vol},"
                     f"afade=t=in:d=1,afade=t=out:st={max(0, total - 1.8):.2f}:d=1.8[m]")
        mix.append("[m]")
        idx += 1
    if mix:
        graph.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{total},alimiter=limit=0.95[aout]")
    else:
        args += ["-f", "lavfi", "-t", f"{total}", "-i", "anullsrc=r=44100:cl=stereo"]
        graph.append(f"[{idx}:a]anull[aout]")

    _run([*args, "-filter_complex", ";".join(graph), "-map", "[vout]", "-map", "[aout]",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
          "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-t", f"{total}", out_path])
    return total
