"""Royalty-free background music, synthesized here, so there is no licence to worry about.

Soft pads on a slow chord progression, an optional gentle arpeggio, and a simple echo for space.
"""

import os
import tempfile
import wave

import numpy as np

RATE = 44100
PRESETS = {
    "calm": {"label": "هادية", "bpm": 64, "arp": False,
             "chords": [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 66]]},   # Am7 Fmaj7 Cmaj7 G
    "warm": {"label": "دافية", "bpm": 76, "arp": True,
             "chords": [[50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59], [53, 57, 60, 64]]},   # Dm7 G7 Cmaj7 Fmaj7
    "bright": {"label": "متفائلة", "bpm": 90, "arp": True,
               "chords": [[48, 52, 55, 60], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]},  # C G Am F
}
SECONDS = 48


def _hz(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def _lowpass(x: np.ndarray, alpha: float) -> np.ndarray:
    y = np.empty_like(x)
    acc = 0.0
    for i in range(0, len(x), 512):  # block-wise one-pole filter keeps it fast enough without scipy
        block = x[i:i + 512]
        out = np.empty_like(block)
        for j, v in enumerate(block):
            acc += alpha * (v - acc)
            out[j] = acc
        y[i:i + 512] = out
    return y


def synth(preset: str) -> np.ndarray:
    p = PRESETS[preset]
    beat = 60 / p["bpm"]
    bar = beat * 4
    n = int(SECONDS * RATE)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    bars = int(np.ceil(SECONDS / bar))
    for b in range(bars):
        chord = p["chords"][b % len(p["chords"])]
        start, end = int(b * bar * RATE), min(n, int((b + 1) * bar * RATE + 1.5 * RATE))
        seg = t[start:end] - b * bar
        env = np.minimum(1, seg / 1.2) * np.clip((bar + 1.5 - seg) / 1.5, 0, 1)  # slow attack, overlapping release
        for k, note in enumerate(chord):
            f = _hz(note)
            for detune in (-0.12, 0.12):  # two detuned voices give a soft chorus
                out[start:end] += env * 0.05 * np.sin(2 * np.pi * (f + detune) * seg + k)
        out[start:end] += env * 0.06 * np.sin(2 * np.pi * _hz(chord[0] - 12) * seg)  # bass
        if p["arp"]:
            for s in range(8):  # eighth-note pluck on chord tones, one octave up
                st = start + int(s * beat / 2 * RATE)
                ln = min(int(1.4 * RATE), n - st)
                if ln <= 0:
                    continue
                tt = np.arange(ln) / RATE
                note = chord[[0, 2, 1, 3, 2, 1, 3, 2][s]] + 12
                out[st:st + ln] += 0.035 * np.exp(-tt * 3.2) * np.sin(2 * np.pi * _hz(note) * tt)
    out = _lowpass(out, 0.18)
    echo = int(beat * 0.75 * RATE)  # dotted-eighth echo
    wet = np.zeros(n)
    wet[echo:] = out[:-echo] * 0.35
    wet[2 * echo:] += out[:-2 * echo] * 0.15
    out = out + wet
    fade = int(2 * RATE)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.max(np.abs(out)) or 1) * 0.8


def track(preset: str) -> str:
    """Path to a cached WAV for the preset (generated once per container)."""
    if preset not in PRESETS:
        raise ValueError(preset)
    folder = os.path.join(tempfile.gettempdir(), "egbrand-music")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{preset}-v1.wav")
    if not os.path.exists(path):
        data = (synth(preset) * 32767).astype(np.int16)
        tmp = path + ".tmp"
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(data.tobytes())
        os.replace(tmp, path)
    return path
