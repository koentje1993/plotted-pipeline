"""Exporteert logo's en platformassets naar brand_assets/.

    python make_brand_assets.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from plotted.brand import ACC, FP, GRID, INK, MUTED, PAPER, PX_TO_PT, SLATE, set_theme, text_width
from plotted.logo import HANDLES, TAGLINES, draw_mark, draw_wordmark, wordmark_width

plt.rcParams["svg.fonttype"] = "path"  # tekst als outlines: geen fonts nodig bij de ontvanger
OUT = Path("brand_assets")
# per merk: map, bestandsprefix, handles en thema's
BRANDS = {
    "plotted": dict(out="brand_assets", prefix="plotted", x="@plottedworld", yt="@worldplotted",
                    themes="DATA  ·  MAPS  ·  MONEY  ·  HISTORY"),
    "ai": dict(out="brand_assets/ai", prefix="plotted-ai", x="@plottedai", yt="@plottedai",
               themes="COMPUTE  ·  MODELS  ·  MONEY  ·  ADOPTION"),
    "prices": dict(out="brand_assets/prices", prefix="plotted-prices", x="@plottedprices", yt="@plottedprices",
                   themes="THEN VS NOW  ·  AROUND THE WORLD  ·  HOURS OF WORK"),
}
B = BRANDS["plotted"]
TAGLINE = TAGLINES["plotted"]


def canvas(w, h, bg=None):
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.axis("off")
    if bg:
        ax.add_patch(Rectangle((0, 0), w, h, color=bg, zorder=-10))
    else:
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
    return fig, ax


def grid(ax, w, h, step):
    for x in range(0, w + 1, step):
        ax.plot([x, x], [0, h], color=GRID, lw=1.2, zorder=-9)
    for y in range(0, h + 1, step):
        ax.plot([0, w], [y, y], color=GRID, lw=1.2, zorder=-9)


def save(fig, name, svg=True):
    path = Path(B["out"]) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    transparent = fig.patch.get_alpha() == 0
    fig.savefig(path.with_suffix(".png"), dpi=100, transparent=transparent)
    if svg:
        fig.savefig(path.with_suffix(".svg"), transparent=transparent)
    plt.close(fig)


def text(ax, x, y, s, font, px, color, ha="left", va="baseline", alpha=1):
    ax.text(x, y, s, fontproperties=FP[font], fontsize=px * PX_TO_PT, color=color, ha=ha, va=va, alpha=alpha)


# ---------- logo ----------
def logos():
    for theme, bg, fg in [("dark", INK, PAPER), ("light", PAPER, INK), ("transparent-paper", None, PAPER),
                          ("transparent-ink", None, INK)]:
        # woordmerk
        px = 220
        w = int(wordmark_width(px) + 160)
        fig, ax = canvas(w, 340, bg)
        draw_wordmark(ax, 80, 230, px, fg)
        save(fig, f"logo/{B['prefix']}-wordmark-{theme}")

        # beeldmerk
        fig, ax = canvas(1024, 1024, bg)
        draw_mark(ax, 112, 112, 800, fg)
        save(fig, f"logo/{B['prefix']}-mark-{theme}")

        # horizontale lockup: beeldmerk + woordmerk
        px = 180
        mark = 210
        w = int(80 + mark + 40 + wordmark_width(px) + 80)
        fig, ax = canvas(w, 340, bg)
        draw_mark(ax, 70, 55, mark, fg)
        draw_wordmark(ax, 80 + mark + 40, 222, px, fg)
        save(fig, f"logo/{B['prefix']}-lockup-{theme}")


# ---------- platformassets ----------
def avatar(size=1080):
    """Profielfoto. Beeldmerk binnen de middelste 56% zodat een ronde uitsnede niets afsnijdt."""
    fig, ax = canvas(size, size, INK)
    grid(ax, size, size, size // 12)
    s = size * 0.56
    draw_mark(ax, (size - s) / 2 + size * 0.02, (size - s) / 2 - size * 0.01, s, PAPER)
    save(fig, f"platform/avatar-{size}", svg=False)


def x_banner():
    W, H = 1500, 500
    fig, ax = canvas(W, H, INK)
    grid(ax, W, H, 50)
    pts = [(0, 430), (120, 418), (240, 424), (360, 400), (480, 404), (600, 376), (720, 382), (840, 340),
           (960, 350), (1080, 300), (1200, 250), (1320, 190), (1390, 150)]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=SLATE, lw=3, solid_joinstyle="round")
    ax.plot([1390, 1390], [150, H], color=ACC(), lw=1.5, alpha=0.6, dashes=(4, 5))
    ax.add_patch(matplotlib.patches.Circle((1390, 150), 16, color=ACC()))
    # links onder valt de profielfoto over de banner: tekst begint pas bij x=560
    draw_wordmark(ax, 560, 205, 112, PAPER)
    text(ax, 564, 262, TAGLINE, "medium", 32, MUTED)
    text(ax, 564, 330, B["themes"], "mono", 20, PAPER)
    text(ax, 564, 372, B["x"], "mono_bold", 22, ACC())
    save(fig, "platform/x-banner-1500x500", svg=False)


def youtube_banner():
    """2560x1440. Alleen de middelste 1546x423 is overal zichtbaar (mobiel)."""
    W, H = 2560, 1440
    fig, ax = canvas(W, H, INK)
    grid(ax, W, H, 80)
    import math
    xs = list(range(0, W + 1, 40))
    ys = [1260 - 290 * (1 / (1 + math.exp(-(x - 1700) / 260))) - 30 * math.sin(x / 140) for x in xs]
    ax.plot(xs, ys, color=SLATE, lw=4)
    ax.add_patch(matplotlib.patches.Circle((2160, ys[54]), 22, color=ACC()))
    cy = H / 2
    mark = 300
    wm_px = 190
    total = mark + 50 + wordmark_width(wm_px)
    x0 = (W - total) / 2
    draw_mark(ax, x0, cy - mark / 2 - 30, mark, PAPER)
    draw_wordmark(ax, x0 + mark + 50, cy + 30, wm_px, PAPER)
    text(ax, x0 + mark + 56, cy + 110, f"{TAGLINE}   {B['yt']}", "mono", 34, MUTED)  # YouTube-handle
    save(fig, "platform/youtube-banner-2560x1440", svg=False)


def logo_sheet():
    """Overzicht om te checken: varianten en kleinste maten."""
    W, H = 1600, 1000
    fig, ax = canvas(W, H, INK)
    text(ax, 80, 100, ("plotted. AI" if B["prefix"] != "plotted" else "plotted.") + " — logo system", "mono", 26, MUTED)
    draw_wordmark(ax, 80, 290, 170, PAPER)
    draw_mark(ax, 1100, 120, 220, PAPER)
    ax.add_patch(Rectangle((80, 400), 700, 260, color=PAPER))
    draw_wordmark(ax, 140, 580, 130, INK)
    ax.add_patch(Rectangle((820, 400), 260, 260, color=PAPER))
    draw_mark(ax, 850, 430, 200, INK)
    ax.add_patch(Rectangle((1120, 400), 260, 260, color=ACC()))
    draw_mark(ax, 1150, 430, 200, INK, accent=PAPER)
    text(ax, 80, 760, "SMALL SIZES", "mono", 22, MUTED)
    x = 80
    for s in (96, 64, 48, 32, 24):
        draw_mark(ax, x, 800, s, PAPER, guides=s >= 48)
        text(ax, x, 800 + s + 40, f"{s}px", "mono", 18, MUTED)
        x += s + 60
    draw_wordmark(ax, 700, 860, 48, PAPER)
    draw_wordmark(ax, 700, 920, 28, PAPER)
    save(fig, f"logo/{B['prefix']}-logo-sheet", svg=False)


def build(brand):
    global B, TAGLINE
    B, TAGLINE = BRANDS[brand], TAGLINES[brand]
    set_theme(brand)
    logos()
    avatar(1080)
    avatar(400)
    x_banner()
    youtube_banner()
    logo_sheet()


if __name__ == "__main__":
    import sys
    for brand in (sys.argv[1:] or BRANDS):  # python make_brand_assets.py ai  -> alleen plotted. AI
        build(brand)
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            print(p)
