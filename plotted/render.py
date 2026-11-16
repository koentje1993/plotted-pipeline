"""Render een post-spec (JSON) naar een MP4 van 1080x1920 met geluidseffecten.

Gebruik:
    python -m plotted.render specs/post01.json               # video met sfx
    python -m plotted.render specs/post01.json --still 9     # alleen frame op 9 s als PNG
    python -m plotted.render specs/post01.json --no-sfx      # zonder geluid
    python -m plotted.render specs/post01.json --audio vo.mp3  # eigen voice-over/muziek i.p.v. sfx
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .brand import FPS, H, W, new_canvas
from .sfx import write_sfx
from .templates import beats, frame, total_duration


def render_frame(spec, t):
    fig, ax = new_canvas()
    frame(ax, spec, t)
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
    plt.close(fig)
    return buf


def render_video(spec, out_path, audio=None, sfx=True):
    dur = total_duration(spec)
    n = int(dur * FPS)
    tmp = None
    if not audio and sfx:
        tmp = Path(tempfile.mkdtemp()) / "sfx.wav"
        write_sfx(beats(spec), dur, tmp)
        audio = tmp
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(render_frame(spec, i / FPS).tobytes())
        if i % FPS == 0:
            print(f"\r{out_path.name}: {i // FPS}/{dur:.0f} s", end="", file=sys.stderr)
    proc.stdin.close()
    proc.wait()
    print(f"\r{out_path.name}: klaar ({dur:.1f} s)      ", file=sys.stderr)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("spec")
    p.add_argument("--out", default="out")
    p.add_argument("--still", type=float, help="render alleen het frame op dit tijdstip (s)")
    p.add_argument("--audio", help="eigen voice-over of muziek (vervangt de sfx)")
    p.add_argument("--no-sfx", action="store_true")
    a = p.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = Path(a.spec).stem
    if a.still is not None:
        import matplotlib.image as mpimg
        mpimg.imsave(out / f"{stem}_{a.still:g}s.png", render_frame(spec, a.still))
    else:
        render_video(spec, out / f"{stem}.mp4", a.audio, not a.no_sfx)


if __name__ == "__main__":
    main()
