"""Geluidseffecten, synchroon met de beats van de video.

tick      zacht klikje per jaar of per balk (tempo voelbaar maken)
overtake  iets hoger 'blip' bij een inhaalactie
event     twee tonen bij een gebeurtenis-label
reveal    akkoord op het moment van de onthulling
De video werkt ook zonder geluid; dit is een extra laag. Muziek kun je er later onder zetten.
"""
import wave

import numpy as np

SR = 44100


def _tone(freqs, dur, decay, vol):
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
    env = np.exp(-t / decay) * np.minimum(1, t / 0.003)
    return sig * env * vol


SOUNDS = {
    "tick": lambda: _tone([2200], 0.04, 0.008, 0.18),
    "overtake": lambda: _tone([1320, 1760], 0.09, 0.03, 0.22),
    "event": lambda: _tone([660, 990], 0.25, 0.08, 0.28),
    "reveal": lambda: _tone([523.25, 659.25, 783.99, 1046.5], 1.2, 0.35, 0.45),
}


def write_sfx(beat_list, duration, path):
    out = np.zeros(int(SR * (duration + 1.5)))
    cache = {k: f() for k, f in SOUNDS.items()}
    last = {}
    for t, kind in beat_list:
        if kind == "overtake" and t - last.get(kind, -9) < 0.35:
            continue  # niet te druk
        last[kind] = t
        s = cache[kind]
        i = int(t * SR)
        out[i:i + len(s)] += s[: max(0, len(out) - i)]
    out = out[: int(SR * duration)]
    peak = np.max(np.abs(out)) or 1
    out = (out / max(peak, 1.0) * 32767 * 0.9).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())
