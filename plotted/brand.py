"""plotted. huisstijl: kleuren, fonts en het vaste frame (raster, themalabel, wordmark, bron).

Alle maten zijn in pixels op een canvas van 1080 x 1920 (9:16).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

W, H = 1080, 1920
FPS = 30

INK = "#0E1116"
PAPER = "#F2EEE6"
SIGNAL = "#FF6B2C"
SIGNAL_AI = "#3FD0FF"   # plotted. AI: zelfde systeem, eigen accentkleur

# Thema's: het hele systeem is gelijk, alleen het accent en het naamachtervoegsel verschillen.
THEMES = {
    "plotted": {"accent": SIGNAL, "suffix": "", "cta": "Follow plotted."},
    "ai": {"accent": SIGNAL_AI, "suffix": "AI", "cta": "Follow plotted. AI"},
    "prices": {"accent": "#4ADE80", "suffix": "Prices", "cta": "Follow plotted. Prices"},
}
THEME = dict(THEMES["plotted"])


def set_theme(name):
    THEME.clear()
    THEME.update(THEMES[name or "plotted"])


def ACC():
    """Huidige accentkleur (oranje voor plotted., cyaan voor plotted. AI)."""
    return THEME["accent"]
SLATE = "#3A414D"
MUTED = "#8A93A3"
GRID = (242 / 255, 238 / 255, 230 / 255, 0.06)

# Veilige zone voor Shorts/TikTok/Reels: onderste ~300 px en rechter ~120 px
# worden deels afgedekt door de app. Alles wat gelezen moet worden staat erboven.
PAD_X = 80
SAFE_BOTTOM = 1600

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
_FONTS = {
    "bold": FONT_DIR / "SpaceGrotesk-Bold.ttf",
    "medium": FONT_DIR / "SpaceGrotesk-Medium.ttf",
    "mono": FONT_DIR / "JetBrainsMono-Regular.ttf",
    "mono_bold": FONT_DIR / "JetBrainsMono-SemiBold.ttf",
}
for p in _FONTS.values():
    font_manager.fontManager.addfont(str(p))
FP = {k: FontProperties(fname=str(v)) for k, v in _FONTS.items()}

PX_TO_PT = 72 / 100  # figuur op 100 dpi


def text_width(s, font, px):
    """Breedte van een tekst in pixels."""
    if not s:
        return 0
    tp = TextPath((0, 0), s, size=px, prop=FP[font])
    return tp.get_extents().width


def wrap(s, font, px, max_w):
    """Breekt tekst op woordgrenzen zodat elke regel binnen max_w past."""
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if text_width(trial, font, px) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def new_canvas():
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    fig.patch.set_facecolor(INK)
    return fig, ax


def text(ax, x, y, s, font="medium", px=40, color=PAPER, ha="left", va="baseline", alpha=1.0):
    s = str(s).replace("$", r"\$")  # dollartekens niet als formule lezen
    return ax.text(x, y, s, fontproperties=FP[font], fontsize=px * PX_TO_PT, color=color,
                   ha=ha, va=va, alpha=alpha)


def draw_base(ax, tag_num, tag_name, right_label, source, source_alpha=1.0, wordmark=1.0):
    """Achtergrondraster, themalabel linksboven, wordmark en bron onderaan."""
    ax.add_patch(Rectangle((0, 0), W, H, color=INK, zorder=-10))
    for x in range(0, W + 1, 60):
        ax.plot([x, x], [0, H], color=GRID, lw=1.5, zorder=-9)
    for y in range(0, H + 1, 60):
        ax.plot([0, W], [y, y], color=GRID, lw=1.5, zorder=-9)

    # themalabel: oranje stip + "01 DATA"
    ax.add_patch(Circle((PAD_X + 10, 112), 10, color=ACC()))
    text(ax, PAD_X + 34, 112, f"{tag_num} {tag_name}", "mono", 30, PAPER, va="center")
    if right_label:
        text(ax, W - PAD_X, 112, right_label, "mono", 26, MUTED, ha="right", va="center")

    # bron links, wordmark rechts, boven de veilige zone
    # bron krimpt mee als hij lang is, zodat de volg-oproep rechts er nooit overheen valt
    src = f"SOURCE: {source}"
    cta_w = text_width(THEME["cta"], "mono_bold", 28) + 48  # ruimte voor de volg-oproep rechts
    avail = W - 2 * PAD_X - max(420, cta_w + 40)
    spx = max(16, min(24, 24 * avail / max(1, text_width(src, "mono", 24))))
    text(ax, PAD_X, SAFE_BOTTOM, src, "mono", spx, MUTED, alpha=source_alpha)
    if wordmark:
        from .logo import draw_wordmark
        draw_wordmark(ax, W - PAD_X, SAFE_BOTTOM + 4, 52, PAPER, ha="right", alpha=float(wordmark))


def draw_hook(ax, hook, y_top=200, px=104, alpha=1.0, dy=0.0):
    """De hook: groot, vet, maximaal twee regels (cold open). Te lang? Dan krimpt de letter tot 80 px.
    Woorden tussen *sterretjes* krijgen de accentkleur, zodat het oog in de eerste seconde op de kern valt.
    Geeft de onderkant (y) terug."""
    words, on = [], False
    for w in hook.split():
        start = w.startswith("*")
        if start:
            on = True
        end = w.rstrip(".,!?:;").endswith("*")
        words.append((w.replace("*", ""), on))
        if end:
            on = False
    clean = " ".join(w for w, _ in words)
    lines = wrap(clean, "bold", px, W - 2 * PAD_X)
    while len(lines) > 2 and px > 80:
        px -= 4
        lines = wrap(clean, "bold", px, W - 2 * PAD_X)
    lh = px * 1.04
    y = y_top + px * 0.8 + dy
    space = text_width("a a", "bold", px) - 2 * text_width("a", "bold", px)
    i = 0
    for ln in lines:
        x = PAD_X
        for _ in ln.split():
            w, acc = words[i]
            i += 1
            text(ax, x, y, w, "bold", px, ACC() if acc else PAPER, alpha=alpha)
            x += text_width(w, "bold", px) + space
        y += lh
    return y_top + len(lines) * lh


def draw_caption(ax, caption, y, alpha=1.0):
    """Ondertitel in een donker vlak, maximaal twee regels."""
    if not caption or alpha <= 0:
        return
    px = 44
    lines = wrap(caption, "medium", px, W - 2 * PAD_X - 56)[:2]
    h = len(lines) * px * 1.3 + 40
    ax.add_patch(Rectangle((PAD_X, y), W - 2 * PAD_X, h, color=(14 / 255, 17 / 255, 22 / 255, 0.88 * alpha),
                           zorder=5))
    yy = y + 20 + px * 0.95
    for ln in lines:
        t = text(ax, PAD_X + 28, yy, ln, "medium", px, PAPER, alpha=alpha)
        t.set_zorder(6)
        yy += px * 1.3


def _rgb(c):
    import matplotlib.colors as mc
    return mc.to_rgb(c)


def ease(t):
    """Ease-in-out tussen 0 en 1."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ramp(t, start, dur):
    return ease((t - start) / dur) if dur > 0 else float(t >= start)


# ---------- engagement-elementen (gelden voor elke template) ----------
PROGRESS_Y = 150


def draw_progress(ax, frac):
    """Dunne voortgangsbalk onder het themalabel: de kijker ziet dat het ergens naartoe gaat."""
    x0, x1 = PAD_X, W - PAD_X
    ax.plot([x0, x1], [PROGRESS_Y, PROGRESS_Y], color=SLATE, lw=3, solid_capstyle="round")
    f = max(0.0, min(1.0, frac))
    if f > 0:
        ax.plot([x0, x0 + (x1 - x0) * f], [PROGRESS_Y, PROGRESS_Y], color=ACC(), lw=3, solid_capstyle="round")


def draw_prompt(ax, prompt, y, alpha=1.0):
    """Voorspel-prompt onder de hook ('GUESS: ...'): maakt van kijken een spelletje."""
    if not prompt or alpha <= 0:
        return
    text(ax, PAD_X, y, prompt.upper(), "mono_bold", 30, ACC(), alpha=alpha)


def draw_event(ax, x, y, label, alpha=1.0, ha="left"):
    """Label bij een gebeurtenis: klein donker vlak met oranje stip en tekst."""
    if alpha <= 0:
        return
    px = 30
    w = text_width(label, "mono", px) + 64
    x0 = x if ha == "left" else x - w
    ax.add_patch(Rectangle((x0, y - 30), w, 54, color=(23 / 255, 27 / 255, 34 / 255, 0.95 * alpha), zorder=7))
    ax.add_patch(Circle((x0 + 24, y - 3), 8, color=ACC(), alpha=alpha, zorder=8))
    t = text(ax, x0 + 44, y - 3, label, "mono", px, PAPER, va="center", alpha=alpha)
    t.set_zorder(8)


def draw_cta(ax, alpha=1.0):
    """Volg-oproep als overlay op het laatste beeld. Geen apart eindscherm: zo loopt de video naadloos rond."""
    if alpha <= 0:
        return
    # Neutraal: X (@plottedworld) en YouTube (@worldplotted) hebben een andere handle, de naam is overal gelijk
    s = THEME["cta"]
    px = 28
    w = text_width(s, "mono_bold", px) + 48
    x0, y0 = W - PAD_X - w, SAFE_BOTTOM - 46
    ax.add_patch(Rectangle((x0, y0), w, 62, color=(*_rgb(ACC()), alpha), zorder=9))
    t = text(ax, x0 + w / 2, y0 + 32, s, "mono_bold", px, INK, ha="center", va="center", alpha=alpha)
    t.set_zorder(10)
