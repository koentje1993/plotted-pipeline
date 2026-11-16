"""plotted. logo: beeldmerk (het plotpunt) en woordmerk.

Beeldmerk: een assenkruis (L-vorm) met één oranje punt erin, plus stippellijntjes
naar de assen. Dat is het "ene oranje ding" uit de huisstijl, teruggebracht tot een icoon.
"""
from matplotlib.patches import Circle

from matplotlib.patches import FancyBboxPatch

from .brand import ACC, FP, PX_TO_PT, THEME, THEMES, text_width

HANDLES = {"plotted": "@plottedworld", "ai": "@plottedai", "prices": "@plottedprices"}
TAGLINES = {"plotted": "The world, measured.", "ai": "AI, measured.", "prices": "What things cost."}
HANDLE = HANDLES["plotted"]
TAGLINE = TAGLINES["plotted"]


def draw_mark(ax, x, y, s, fg, accent=None, guides=True):
    accent = accent or ACC()
    """Beeldmerk in een vierkant van s x s px met linksboven (x, y)."""
    lw = s * (0.085 if s >= 64 else 0.11)
    ax_x, ax_y = x + s * 0.18, y + s * 0.82   # oorsprong van de assen
    top, right = y + s * 0.14, x + s * 0.86
    pt_lw = lw * 72 / 100
    ax.plot([ax_x, ax_x], [top, ax_y], color=fg, lw=pt_lw, solid_capstyle="round")
    ax.plot([ax_x, right], [ax_y, ax_y], color=fg, lw=pt_lw, solid_capstyle="round")
    cx, cy, r = x + s * 0.62, y + s * 0.38, s * 0.15
    if guides:
        # stippellijntjes van het punt naar beide assen
        dr, gap = lw * 0.26, lw * 0.95
        y_ = cy + r + gap * 1.2
        while y_ < ax_y - lw * 1.1:
            ax.add_patch(Circle((cx, y_), dr, color=accent, alpha=0.6, lw=0))
            y_ += gap
        x_ = cx - r - gap * 1.2
        while x_ > ax_x + lw * 1.1:
            ax.add_patch(Circle((x_, cy), dr, color=accent, alpha=0.6, lw=0))
            x_ -= gap
    ax.add_patch(Circle((cx, cy), r, color=accent, lw=0))


def _suffix_w(px, suffix):
    if not suffix:
        return 0
    return px * 0.16 + text_width(suffix, "bold", px * 0.62) + px * 0.30  # gat + label met binnenmarge


def wordmark_width(px, suffix=None):
    suffix = THEME["suffix"] if suffix is None else suffix
    return text_width("plotted", "bold", px) + px * 0.035 + text_width(".", "bold", px) + _suffix_w(px, suffix)


def draw_wordmark(ax, x, baseline, px, fg, accent=None, ha="left", alpha=1.0, suffix=None, label_fg=None):
    """Woordmerk 'plotted.'; bij plotted. AI volgt een gevuld accentlabel met 'AI'."""
    accent = accent or ACC()
    suffix = THEME["suffix"] if suffix is None else suffix
    w1 = text_width("plotted", "bold", px)
    gap = px * 0.035  # de punt mag de d niet raken
    wd = w1 + gap + text_width(".", "bold", px)
    total = wd + _suffix_w(px, suffix)
    if ha == "center":
        x -= total / 2
    elif ha == "right":
        x -= total
    ax.text(x, baseline, "plotted", fontproperties=FP["bold"], fontsize=px * PX_TO_PT, color=fg, alpha=alpha)
    ax.text(x + w1 + gap, baseline, ".", fontproperties=FP["bold"], fontsize=px * PX_TO_PT, color=accent,
            alpha=alpha)
    if suffix:
        spx = px * 0.62
        lx = x + wd + px * 0.16
        lw_ = text_width(suffix, "bold", spx) + px * 0.30
        h = px * 0.62
        ax.add_patch(FancyBboxPatch((lx, baseline - h * 1.0), lw_, h, boxstyle=f"round,pad=0,rounding_size={h*0.22}",
                                    fc=accent, ec="none", alpha=alpha))
        ax.text(lx + lw_ / 2, baseline - h * 0.5, suffix, fontproperties=FP["bold"], fontsize=spx * PX_TO_PT,
                color=label_fg or "#0E1116", ha="center", va="center_baseline", alpha=alpha)
    return total
