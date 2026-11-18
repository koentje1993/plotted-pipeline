"""Videotemplates met een vaste engagement-laag.

Elke video volgt dezelfde dramaturgie:
  0,0 s  hook staat er meteen, voortgangsbalk loopt, alles is al in beweging
  0,3 s  voorspel-prompt ("GUESS: ...") verschijnt onder de hook
  ...    lichaam: elke 2-3 s gebeurt er iets (balk, inhaalactie, event-label)
  reveal het oranje antwoord komt als laatste; de prompt verdwijnt
  hold   ondertitel met de conclusie, daarna 'Follow @plottedworld' op de plek van het woordmerk
Het laatste beeld lijkt op het eerste (zelfde opbouw, geen apart eindscherm), zodat de video naadloos loopt.

Een template is een paar functies: timeline(spec) -> {"reveal": s, "beats": [(s, soort)]}
en draw(ax, spec, t, top, tl) die het lichaam tekent onder y=top.
"""
import math

from matplotlib.patches import Circle, FancyBboxPatch

from .brand import (ACC, MUTED, PAD_X, PAPER, SLATE, set_theme, W, draw_base, draw_caption, draw_cta, draw_event,
                    draw_hook, draw_progress, draw_prompt, ramp, text, text_width)
from .logo import draw_mark, draw_wordmark

START = -0.8         # cold open v2: het lichaam is bij frame 0 al 0,8 s op weg, zodat het eerste beeld nooit leeg is
                     # (was 0.15; een leeg eerste beeld liet ~47% wegswipen)
CAPTION_Y = 1380
HOLD = 2.6           # na de onthulling: conclusie + volg-oproep


def _lerp_color(a, b, f):
    import matplotlib.colors as mc
    ca, cb = mc.to_rgb(a), mc.to_rgb(b)
    return tuple(ca[i] + (cb[i] - ca[i]) * f for i in range(3))


def fmt_value(fmt, v):
    """Getal opmaken. Naast een gewone format-string ('{:.1f} yrs') kent dit twee leesbare vormen:
    'count' -> 2,300 / 29K / 3.1M / 208B   en   'usd_b' (waarde in miljard dollar) -> $587B / $4.53T."""
    if fmt == "count":
        for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
            if v >= div:
                x = v / div
                return f"{x:.0f}{suf}" if x >= 100 else f"{x:.1f}{suf}".replace(".0" + suf, suf)
        return f"{v:,.0f}"
    if fmt == "usd_b":
        if v >= 1000:
            return f"${v / 1000:.2f}T"
        return f"${v:.0f}B" if v >= 100 else f"${v:.1f}B"
    if fmt == "usd":
        for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
            if v >= div:
                x = v / div
                return f"${x:.0f}{suf}" if x >= 100 else f"${x:.1f}{suf}"
        return f"${v:,.0f}"
    return fmt.format(v)


# ---------------------------------------------------------------- tijd en tempo
def _time_map(spec, y0, y1):
    """Zet jaren om naar seconden. 'pace' = [[van, tot, sec_per_jaar], ...] voor saaie vs spannende stukken."""
    default = spec.get("seconds_per_year", 0.12)
    pace = spec.get("pace", [])

    def spy(year):
        for a, b, s in pace:
            if a <= year < b:
                return s
        return default

    knots, t, y = [(y0, START)], START, y0
    while y < y1:
        nxt = min(y + 1, y1)
        t += spy(y) * (nxt - y)
        y = nxt
        knots.append((y, t))
    return knots


def _year_at(knots, t):
    if t <= knots[0][1]:
        return knots[0][0]
    for (ya, ta), (yb, tb) in zip(knots, knots[1:]):
        if ta <= t <= tb:
            return ya + (yb - ya) * ((t - ta) / (tb - ta) if tb > ta else 1)
    return knots[-1][0]


def _time_of(knots, year):
    for (ya, ta), (yb, tb) in zip(knots, knots[1:]):
        if ya <= year <= yb:
            return ta + (tb - ta) * ((year - ya) / (yb - ya) if yb > ya else 0)
    return knots[-1][1]


def _year_ticks(knots, min_gap=0.22):
    beats, last = [], -9
    for y, t in knots:
        if t - last >= min_gap and y != knots[0][0]:
            beats.append((t, "tick"))
            last = t
    return beats


def _events(ax, spec, t, knots, x, y, ha="left", until=None):
    """Toont het laatste event als label; elk event blijft ~2,4 s staan."""
    for ev in reversed(spec.get("events", [])):
        te = _time_of(knots, ev["year"])
        if te <= t <= te + 2.4:
            a = ramp(t, te, 0.2) * (1 - ramp(t, te + 2.1, 0.3))
            if until is not None:
                a *= 1 - ramp(t, until, 0.3)  # maak plaats voor de conclusie
            draw_event(ax, x, y, f"{ev['year']}  {ev['text']}", alpha=a, ha=ha)
            break


def _year_counter(ax, year, x, y, px=170, ha="right"):
    text(ax, x, y, f"{int(year)}", "mono_bold", px, PAPER, ha=ha, alpha=0.92)


# ---------------------------------------------------------------- bars
def bars_timeline(spec):
    rows = spec["rows"]
    stagger, grow = spec.get("stagger", 0.45), 0.8
    hi = [i for i, r in enumerate(rows) if r.get("highlight")]
    normal = [i for i in range(len(rows)) if i not in hi]
    starts, t = {}, START
    for i in normal:
        starts[i] = t
        t += stagger
    pause = spec.get("reveal_pause", 0.7)  # dramatische stilte voor het antwoord
    for i in hi:
        starts[i] = t + pause
    reveal = (max(starts.values()) + grow) if starts else START
    beats = [(s, "reveal" if i in hi else "tick") for i, s in starts.items()]
    return {"reveal": reveal, "beats": beats, "starts": starts, "grow": grow}


def bars_draw(ax, spec, t, top, tl):
    rows = spec["rows"]
    style = spec.get("style", "stacked")
    vmax = max(r["value"] for r in rows)
    area = CAPTION_Y - 50 - top
    step = area / len(rows)
    label_w = max(text_width(r["label"], "mono", 34) for r in rows) + 30 if style == "inline" else 0
    max_bar = W - 2 * PAD_X - label_w - (230 if style == "inline" else 0)
    bar_h = min(46, step * (0.38 if style == "stacked" else 0.6))

    for i, r in enumerate(rows):
        s = tl["starts"][i]
        k = ramp(t, s, tl["grow"])
        hi = r.get("highlight", False)
        y = top + i * step
        hidden = hi and k <= 0  # nieuwsgierigheidsgat: het antwoord staat er al, maar onbekend
        if k <= 0 and not hi:
            continue
        label = "?" * 3 if hidden else r["label"]
        val = "" if hidden else r["value_label"]
        color = ACC() if hi else SLATE
        lab_col = MUTED if hidden else (ACC() if hi and style == "inline" else PAPER)
        w = max(10, r["value"] / vmax * max_bar) * k
        # korte opflits wanneer de onthulling binnenkomt
        flash = (1 - ramp(t, s + tl["grow"], 0.5)) * ramp(t, s, 0.15) if hi else 0
        if style == "stacked":
            text(ax, PAD_X, y + 40, label, "medium", 42, lab_col, alpha=1 if hidden else k)
            text(ax, W - PAD_X, y + 40, val, "mono", 36, ACC() if hi else MUTED, ha="right", alpha=k)
            by = y + 62
            if hidden:
                ax.add_patch(FancyBboxPatch((PAD_X, by), max_bar, bar_h, boxstyle="round,pad=0,rounding_size=5",
                                            fill=False, ec=SLATE, lw=2, ls=(0, (4, 4))))
            else:
                ax.add_patch(FancyBboxPatch((PAD_X, by), w, bar_h, boxstyle="round,pad=0,rounding_size=5",
                                            color=_lerp_color(color, PAPER, flash), lw=0))
        else:
            by = y + (step - bar_h) / 2
            text(ax, PAD_X, by + bar_h / 2, label, "mono", 34, lab_col, va="center", alpha=1 if hidden else k)
            if not hidden:
                ax.add_patch(FancyBboxPatch((PAD_X + label_w, by), w, bar_h,
                                            boxstyle="round,pad=0,rounding_size=5",
                                            color=_lerp_color(color, PAPER, flash), lw=0))
                text(ax, PAD_X + label_w + w + 18, by + bar_h / 2, val, "mono", 30, ACC() if hi else MUTED,
                     va="center", alpha=k)


# ---------------------------------------------------------------- line met jaarteller
def line_timeline(spec):
    pts = spec["points"]
    knots = _time_map(spec, pts[0][0], pts[-1][0])
    beats = _year_ticks(knots, spec.get("tick_gap", 0.3))
    beats += [(_time_of(knots, e["year"]), "event") for e in spec.get("events", [])]
    reveal = knots[-1][1]
    beats.append((reveal, "reveal"))
    return {"reveal": reveal, "beats": beats, "knots": knots}


def _interp(pts, x):
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return ya + (yb - ya) * ((x - xa) / (xb - xa) if xb > xa else 0)
    return pts[-1][1] if x > pts[-1][0] else pts[0][1]


def line_draw(ax, spec, t, top, tl):
    log = spec.get("log", False)  # logaritmische y-as: voor exponentiële groei (transistors, rekenkracht)
    L = (lambda v: math.log10(v)) if log else (lambda v: v)
    pts = [(x, L(y)) for x, y in spec["points"]]
    knots = tl["knots"]
    x0, x1 = pts[0][0], pts[-1][0]
    y0 = L(spec.get("y_min", 1 if log else 0))
    y1 = L(spec["y_max"]) if "y_max" in spec else max(p[1] for p in pts) * 1.08
    chart_top, bottom = top + 300, CAPTION_Y - 110
    left, right = PAD_X + 10, W - PAD_X - 10

    def px(x, y):
        return left + (x - x0) / (x1 - x0) * (right - left), bottom - (y - y0) / (y1 - y0) * (bottom - chart_top)

    ax.plot([left, right], [bottom, bottom], color=SLATE, lw=3)
    for gy in spec.get("y_ticks", []):
        _, yy = px(x0, L(gy))
        ax.plot([left, right], [yy, yy], color=SLATE, lw=1, alpha=0.5)
        text(ax, left, yy - 12, fmt_value(spec.get("y_tick_fmt", "{}"), gy), "mono", 24, MUTED)
    for lx in spec.get("x_labels", [x0, x1]):
        xx, _ = px(lx, y0)
        text(ax, xx, bottom + 44, str(lx), "mono", 28, MUTED, ha="center")

    year = _year_at(knots, t)
    hf = spec.get("highlight_from", x1 + 1)
    # lijn in kleine stapjes tekenen, oranje vanaf highlight_from
    n = 240
    xs = [x0 + (min(year, x1) - x0) * i / n for i in range(n + 1)]
    gap = spec.get("gap_until", -1e9)  # tot dit jaar ontbreekt jaardata: dun en gestippeld
    for a, b in zip(xs, xs[1:]):
        pa, pb = px(a, _interp(pts, a)), px(b, _interp(pts, b))
        if a < gap:
            ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color=MUTED, lw=3, dashes=(2, 2))
        else:
            ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color=ACC() if a >= hf else PAPER, lw=7,
                    solid_capstyle="round")
    # punten bij events blijven staan als ankers
    for ev in spec.get("events", []):
        if year >= ev["year"]:
            ax.add_patch(Circle(px(ev["year"], _interp(pts, ev["year"])), 9, color=ACC(), zorder=4))
    cur = px(year, _interp(pts, year))
    ax.add_patch(Circle(cur, 18, color=ACC(), zorder=5))

    # jaarteller links, lopende waarde rechts
    _year_counter(ax, year, PAD_X, top + 150, px=150, ha="left")
    cur_v = _interp(pts, year)
    text(ax, W - PAD_X, top + 150, fmt_value(spec.get("value_fmt", "{:.0f}"), 10 ** cur_v if log else cur_v),
         "mono_bold", 80, ACC(), ha="right")
    _events(ax, spec, t, knots, W - PAD_X, top + 230, ha="right")


# ---------------------------------------------------------------- dotgrid met teller
def dotgrid_timeline(spec):
    dur = spec.get("fill_seconds", 4.0)
    hot = max(1, int(round(spec["highlight"])))  # highlight mag een kommagetal zijn (bijv. 8.2 minuten)
    beats = [(START + dur * i / hot, "tick") for i in range(0, hot, max(1, hot // 12))]
    beats.append((START + dur, "reveal"))
    return {"reveal": START + dur, "beats": beats}


def dotgrid_draw(ax, spec, t, top, tl):
    cols, total, hot = spec.get("cols", 10), spec.get("total", 100), spec["highlight"]
    rows_n = math.ceil(total / cols)
    gw = W - 2 * PAD_X
    cell = min(gw / cols, (CAPTION_Y - 230 - top) / rows_n)
    r = cell * 0.36
    frac = ramp(t, START, spec.get("fill_seconds", 4.0))
    drain = spec.get("mode") == "drain"
    value = total - (total - hot) * frac if drain else hot * frac
    if spec.get("series"):  # echte waarden per jaar i.p.v. een rechte lijn
        y0, y1 = spec["years"][0], max(spec["years"][-1], spec["series"][-1][0])  # eindig op het laatste datapunt
        value = _interp(spec["series"], y0 + (y1 - y0) * frac)
    shown = int(round(value))
    for i in range(total):
        cx = PAD_X + (gw - cols * cell) / 2 + (i % cols + 0.5) * cell
        cy = top + (i // cols + 0.5) * cell
        if i < shown:
            ax.add_patch(Circle((cx, cy), r, color=ACC()))
        else:
            ax.add_patch(Circle((cx, cy), r, fill=False, ec=SLATE, lw=3))
    by = top + rows_n * cell + 110
    fmt = spec.get("count_fmt", "{:.0f} / " + str(total))
    text(ax, PAD_X, by, fmt.format(value), "mono_bold", 110, ACC())
    if spec.get("years"):
        y0, y1 = spec["years"][0], spec["years"][-1]
        if spec.get("series"):
            y1 = max(y1, spec["series"][-1][0])
        _year_counter(ax, y0 + (y1 - y0) * frac, W - PAD_X, by, px=110)
    text(ax, PAD_X, by + 70, spec.get("big_label", ""), "medium", 40, MUTED, alpha=ramp(t, tl["reveal"], 0.4))


# ---------------------------------------------------------------- bar chart race
def _race_value(series, years, name, y):
    vals = series[name]
    if y <= years[0]:
        return vals[0]
    for i in range(len(years) - 1):
        if years[i] <= y <= years[i + 1]:
            f = (y - years[i]) / (years[i + 1] - years[i])
            return vals[i] + (vals[i + 1] - vals[i]) * f
    return vals[-1]


def _race_ranks(spec, y):
    years, series = spec["years"], spec["series"]
    vals = {n: _race_value(series, years, n, y) for n in series}
    order = sorted(vals, key=lambda n: -vals[n])
    return {n: i for i, n in enumerate(order)}, vals


def race_timeline(spec):
    years = spec["years"]
    knots = _time_map(spec, years[0], years[-1])
    beats = _year_ticks(knots, spec.get("tick_gap", 0.25))
    beats += [(_time_of(knots, e["year"]), "event") for e in spec.get("events", [])]
    # inhaalmomenten binnen de top N geven een eigen geluid
    top_n = spec.get("top_n", 8)
    prev = None
    t = START
    while t <= knots[-1][1]:
        ranks, _ = _race_ranks(spec, _year_at(knots, t))
        if prev:
            for n, r in ranks.items():
                if r < prev.get(n, 99) and r < top_n:
                    beats.append((t, "overtake"))
                    break
        prev = ranks
        t += 1 / 15
    reveal = knots[-1][1]
    beats.append((reveal, "reveal"))
    return {"reveal": reveal, "beats": beats, "knots": knots}


def race_draw(ax, spec, t, top, tl):
    knots = tl["knots"]
    top_n = spec.get("top_n", 8)
    hi = spec.get("highlight")
    y = _year_at(knots, t)
    # vloeiende posities: gemiddelde rang over de laatste 0,35 s
    samples = [_race_ranks(spec, _year_at(knots, max(0, t - 0.35 * i / 4)))[0] for i in range(5)]
    ranks, vals = _race_ranks(spec, y)
    vmax = max(vals.values())
    area_top, area_bottom = top + 30, CAPTION_Y - 130
    step = (area_bottom - area_top) / top_n
    bar_h = step * 0.62
    label_w = max(text_width(n, "medium", 34) for n in spec["series"]) + 26
    max_bar = W - 2 * PAD_X - label_w - 170
    fmt = spec.get("value_fmt", "{:,.0f}")

    for name in spec["series"]:
        pos = sum(s[name] for s in samples) / len(samples)
        if pos > top_n - 0.01:
            continue
        a = min(1.0, top_n - pos)  # zachtjes in- en uitschuiven onderaan
        by = area_top + pos * step + (step - bar_h) / 2
        w = max(8, vals[name] / vmax * max_bar)
        # opflits als deze balk iemand net heeft ingehaald
        old = _race_ranks(spec, _year_at(knots, max(0, t - 0.5)))[0][name]
        flash = 0.55 * ramp(old - ranks[name], 0, 1) * (1 - ramp(t, t, 1)) if ranks[name] < old else 0
        base = ACC() if name == hi else SLATE
        ax.add_patch(FancyBboxPatch((PAD_X + label_w, by), w, bar_h, boxstyle="round,pad=0,rounding_size=5",
                                    color=_lerp_color(base, PAPER, flash), lw=0, alpha=a))
        text(ax, PAD_X + label_w - 18, by + bar_h / 2, name, "medium", 34,
             ACC() if name == hi else PAPER, ha="right", va="center", alpha=a)
        text(ax, PAD_X + label_w + w + 14, by + bar_h / 2, fmt_value(fmt, vals[name]), "mono", 28,
             ACC() if name == hi else MUTED, va="center", alpha=a)

    _year_counter(ax, y, W - PAD_X, area_bottom - 40, px=170)
    _events(ax, spec, t, knots, PAD_X, CAPTION_Y - 40, until=tl["reveal"] + 0.1)


TEMPLATES = {
    "bars": (bars_timeline, bars_draw),
    "line": (line_timeline, line_draw),
    "dotgrid": (dotgrid_timeline, dotgrid_draw),
    "race": (race_timeline, race_draw),
}


# ---------------------------------------------------------------- het gezamenlijke frame
def total_duration(spec):
    tl = TEMPLATES[spec["template"]][0](spec)
    return tl["reveal"] + 0.3 + spec.get("hold", HOLD)


def frame(ax, spec, t):
    set_theme(spec.get("brand", "plotted"))  # "ai" = plotted. AI (cyaan accent, AI-label)
    timeline, draw = TEMPLATES[spec["template"]]
    tl = timeline(spec)
    total = tl["reveal"] + 0.3 + spec.get("hold", HOLD)
    cta = ramp(t, total - 1.3, 0.3) if spec.get("cta", True) else 0

    draw_base(ax, spec["tag_num"], spec["tag"], spec.get("right_label", ""), spec["source"], wordmark=1 - cta)
    draw_progress(ax, t / total)
    a = ramp(t, 0, 0.3)
    hook_bottom = draw_hook(ax, spec["hook"], dy=(1 - a) * 24)  # direct volledig leesbaar
    top = hook_bottom + 40
    if spec.get("prompt"):
        pa = ramp(t, 0.3, 0.3) * (1 - ramp(t, tl["reveal"] - 0.2, 0.4))
        draw_prompt(ax, spec["prompt"], hook_bottom + 50, alpha=pa)
        top = hook_bottom + 80
    draw(ax, spec, t, top, tl)
    draw_caption(ax, spec.get("caption"), CAPTION_Y, alpha=ramp(t, tl["reveal"] + 0.3, 0.4))
    draw_cta(ax, cta)


def beats(spec):
    # beats van voor frame 0 (door de negatieve START) vallen weg; er klinkt wel direct een tick
    bs = [(max(0.0, t), k) for t, k in TEMPLATES[spec["template"]][0](spec)["beats"] if t >= -0.05 or k != "tick"]
    return sorted(bs + [(0.0, "tick")])


# ---------------------------------------------------------------- kaart
import math as _m
from functools import lru_cache

_SMALL_STATES = {  # landen die te klein zijn voor de 1:110m-kaart: als stip op hun hoofdstad
    "Mauritius": (-20.2, 57.5), "Seychelles": (-4.6, 55.5), "Maldives": (3.2, 73.2), "Singapore": (1.35, 103.8),
    "Malta": (35.9, 14.4), "Antigua and Barbuda": (17.1, -61.8), "Barbados": (13.2, -59.5),
    "Dominica": (15.4, -61.4), "Grenada": (12.1, -61.7), "Saint Kitts and Nevis": (17.3, -62.7),
    "Saint Lucia": (13.9, -61.0), "Saint Vincent and the Grenadines": (13.25, -61.2), "Kiribati": (1.45, 173.0),
    "Nauru": (-0.53, 166.9), "Samoa": (-13.8, -172.0), "Tonga": (-21.2, -175.2), "Tuvalu": (-8.5, 179.2),
}


def _clip_ring(ring, bbox):
    """Sutherland-Hodgman: knip een polygoonring af op het kaartvenster (zonder geopandas/shapely)."""
    lon0, lat0, lon1, lat1 = bbox
    edges = [(lambda p: p[0] >= lon0, lambda a, b: _cut_x(a, b, lon0)),
             (lambda p: p[0] <= lon1, lambda a, b: _cut_x(a, b, lon1)),
             (lambda p: p[1] >= lat0, lambda a, b: _cut_y(a, b, lat0)),
             (lambda p: p[1] <= lat1, lambda a, b: _cut_y(a, b, lat1))]
    pts = [tuple(p) for p in ring]
    for inside, cut in edges:
        if not pts:
            break
        out, prev = [], pts[-1]
        for cur in pts:
            if inside(cur):
                if not inside(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cut(prev, cur))
            prev = cur
        pts = out
    return pts


def _cut_x(a, b, x):
    k = (x - a[0]) / (b[0] - a[0])
    return (x, a[1] + k * (b[1] - a[1]))


def _cut_y(a, b, y):
    k = (y - a[1]) / (b[1] - a[1])
    return (a[0] + k * (b[0] - a[0]), y)


@lru_cache(maxsize=4)
def _world(bbox):
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).parent / "data" / "world_lowres.json").read_text())
    out = []
    for name, polys in data:
        rings = [r for r in (_clip_ring(p, bbox) for p in polys) if len(r) > 2]
        if rings:
            out.append((name, rings))
    return out


def _map_box(spec, top):
    lon0, lat0, lon1, lat1 = spec.get("bbox", [-180, -58, 180, 84])
    w = W - 2 * PAD_X
    h = w * (lat1 - lat0) / (lon1 - lon0)
    max_h = CAPTION_Y - 330 - top
    if h > max_h:  # te hoog: smaller maken en centreren
        w, h = max_h * (lon1 - lon0) / (lat1 - lat0), max_h
    x0 = (W - w) / 2

    def proj(lon, lat):
        return x0 + (lon - lon0) / (lon1 - lon0) * w, top + (lat1 - lat) / (lat1 - lat0) * h
    return proj, (lon0, lat0, lon1, lat1), top + h


def _dest(lat, lon, bearing, dist_km):
    R = 6371.0
    la1, lo1, b, d = _m.radians(lat), _m.radians(lon), _m.radians(bearing), dist_km / R
    la2 = _m.asin(_m.sin(la1) * _m.cos(d) + _m.cos(la1) * _m.sin(d) * _m.cos(b))
    lo2 = lo1 + _m.atan2(_m.sin(b) * _m.sin(d) * _m.cos(la1), _m.cos(d) - _m.sin(la1) * _m.sin(la2))
    return _m.degrees(la2), (_m.degrees(lo2) + 540) % 360 - 180


def map_timeline(spec):
    if spec.get("mode") == "circle":
        dur = spec.get("grow_seconds", 6.0)
        beats = [(START + dur * i / 16, "tick") for i in range(16)]
    else:
        order = spec["countries"]
        dur = spec.get("fill_seconds", 7.0)
        step = dur / len(order)
        beats = [(START + i * step, "tick") for i in range(len(order)) if i % max(1, int(0.2 / step)) == 0]
    beats += [(START + _time_of_event(spec, e), "event") for e in spec.get("events", [])]
    reveal = START + dur + spec.get("reveal_pause", 0.6)
    beats.append((reveal, "reveal"))
    return {"reveal": reveal, "beats": beats, "dur": dur}


def _time_of_event(spec, e):
    return e.get("at", 0)


def map_draw(ax, spec, t, top, tl):
    from matplotlib.patches import Polygon
    proj, bbox, bottom = _map_box(spec, top + 20)
    lon0, lat0, lon1, lat1 = bbox
    k = (1 - (1 - min(1.0, max(0.0, (t - START) / tl["dur"]))) ** 2) if spec.get("mode") == "circle" else None
    lit = set()
    order = spec.get("countries", [])
    if spec.get("mode") != "circle":
        step = tl["dur"] / len(order)
        n_lit = max(0, min(len(order), int((t - START) / step) + 1)) if t >= START else 0
        lit = set(order[:n_lit])
    for name, rings in _world(tuple(bbox)):
        col = ACC() if name in lit else SLATE
        for ring in rings:
            pts = [proj(lo, la) for lo, la in ring]
            if len(pts) > 2:
                ax.add_patch(Polygon(pts, closed=True, fc=col, ec="#0E1116", lw=0.6, zorder=2))
    for name, (la, lo) in _SMALL_STATES.items():
        if name in lit and lon0 <= lo <= lon1 and lat0 <= la <= lat1:
            ax.add_patch(Circle(proj(lo, la), 7, color=ACC(), zorder=3))

    if spec.get("mode") == "circle":
        clat, clon = spec["center"]
        r = spec["radius_km"] * k
        if r > 1:
            ring = [proj(*reversed(_dest(clat, clon, b, r))) for b in range(0, 361, 3)]
            ax.add_patch(Polygon(ring, closed=True, fc=(*_lerp_color(ACC(), ACC(), 0), 0.18), ec=ACC(), lw=4, zorder=4))
        ax.add_patch(Circle(proj(clon, clat), 9, color=ACC(), zorder=5))
        text(ax, PAD_X, bottom + 120, f"{int(round(r, -1)):,} km", "mono_bold", 96, PAPER)
        text(ax, PAD_X, bottom + 175, spec.get("counter_label", "radius"), "medium", 36, MUTED)
    else:
        n = len(lit)
        text(ax, PAD_X, bottom + 120, f"{n}", "mono_bold", 110, PAPER)
        text(ax, PAD_X, bottom + 175, spec.get("counter_label", "countries"), "medium", 36, MUTED)
    a = ramp(t, tl["reveal"], 0.4)
    if spec.get("big_number") and a > 0:
        text(ax, W - PAD_X, bottom + 120, spec["big_number"], "mono_bold", 96, ACC(), ha="right", alpha=a)
        text(ax, W - PAD_X, bottom + 175, spec.get("big_label", ""), "medium", 36, MUTED, ha="right", alpha=a)


TEMPLATES["map"] = (map_timeline, map_draw)


# ---------------------------------------------------------------- VS-kaart per verkiezing (serie "America votes")
PARTY = {"D": "#3D7DD8", "R": "#D8483F"}   # gangbare partijkleuren, gedempt; neutraal en direct leesbaar


@lru_cache(maxsize=2)
def _us_states():
    import json
    from pathlib import Path
    d = json.load(open(Path(__file__).parent / "data" / "us_states_albers.json"))
    return d["bbox"], d["states"]


@lru_cache(maxsize=4)
def _us_winners(fname):
    import json
    from pathlib import Path
    return json.load(open(Path(__file__).parent / "data" / fname))


def usmap_timeline(spec):
    n = len(spec["elections"])
    spe = spec.get("seconds_per_election", 0.9)
    starts = [START + i * spe for i in range(n)]
    reveal = START + n * spe + spec.get("reveal_pause", 0.7)
    beats = [(s, "tick") for s in starts] + [(reveal, "reveal")]
    return {"reveal": reveal, "beats": beats, "starts": starts, "spe": spe}


def _usmap_idx(spec, tl, t):
    """Index van de huidige verkiezing en de overgang (0..1) vanaf de vorige kaart."""
    i = max(0, sum(1 for s in tl["starts"] if t >= s) - 1)
    k = ramp(t, tl["starts"][i], 0.25) if i > 0 else 1.0
    return i, k


def usmap_draw(ax, spec, t, top, tl):
    from matplotlib.patches import Polygon as MPoly
    bbox, states = _us_states()
    winners = _us_winners(spec.get("winners_file", "us_president_winners_1976_2024.json"))
    all_years = list(range(1976, 2025, 4))
    els = spec["elections"]
    i, k = _usmap_idx(spec, tl, t)
    yi = all_years.index(els[i]["year"])
    yprev = all_years.index(els[i - 1]["year"]) if i > 0 else yi
    rv = ramp(t, tl["reveal"], 0.5)
    hi = set(spec.get("highlight_states", []))

    gw = W - 2 * PAD_X
    sc = gw / (bbox[2] - bbox[0])
    ox, oy = PAD_X - bbox[0] * sc, top + 10 - bbox[1] * sc
    map_h = (bbox[3] - bbox[1]) * sc
    ink = (14 / 255, 17 / 255, 22 / 255)
    for st in states:
        w = winners[st["name"]]
        c = _lerp_color(PARTY[w[yprev]], PARTY[w[yi]], k)
        if rv > 0 and st["name"] not in hi:
            c = _lerp_color(c, "#2A2F38", 0.75 * rv)  # bij de onthulling: de rest dimt
        for poly in st["polys"]:
            ring = [(ox + x * sc, oy + y * sc) for x, y in poly[0]]
            on = st["name"] in hi and rv > 0
            ax.add_patch(MPoly(ring, closed=True, fc=c, ec=ACC() if on else ink,
                               lw=4 if on else 0.8, zorder=3 if on else 2))
    # Washington D.C. als stip (anders onzichtbaar klein)
    dc = next(s for s in states if s["name"] == "District of Columbia")
    xs = [x for x, _ in dc["polys"][0][0]]; ys = [y for _, y in dc["polys"][0][0]]
    ax.add_patch(Circle((ox + sum(xs) / len(xs) * sc + 14, oy + sum(ys) / len(ys) * sc), 6,
                        color=_lerp_color(PARTY[winners["District of Columbia"][yprev]],
                                          PARTY[winners["District of Columbia"][yi]], k), zorder=4))

    y0 = top + map_h + 40
    e = els[i]
    a = 1 - rv
    text(ax, PAD_X, y0 + 120, str(e["year"]), "mono_bold", 150, PAPER, alpha=0.92 * a)
    # kiesmannen: Democraat links, Republikein rechts (vaste plek, ook als de winnaar wisselt)
    text(ax, W - PAD_X, y0 + 45, f'{e["D"]}  {e["ev_D"]}', "mono_bold", 40, PARTY["D"], ha="right", alpha=a)
    text(ax, W - PAD_X, y0 + 100, f'{e["R"]}  {e["ev_R"]}', "mono_bold", 40, PARTY["R"], ha="right", alpha=a)
    text(ax, W - PAD_X, y0 + 140, "ELECTORAL VOTES", "mono", 22, MUTED, ha="right", alpha=a)
    # staten gewonnen, als verdeelde balk
    nd = sum(1 for s, w in winners.items() if s != "District of Columbia" and w[yi] == "D")
    by = y0 + 190
    wd = gw * nd / 50
    ax.add_patch(FancyBboxPatch((PAD_X, by), wd, 26, boxstyle="round,pad=0,rounding_size=4", color=PARTY["D"], alpha=a))
    ax.add_patch(FancyBboxPatch((PAD_X + wd + 4, by), gw - wd - 4, 26, boxstyle="round,pad=0,rounding_size=4",
                                color=PARTY["R"], alpha=a))
    text(ax, PAD_X, by + 64, f"{nd} states", "mono", 26, MUTED, alpha=a)
    text(ax, W - PAD_X, by + 64, f"{50 - nd} states", "mono", 26, MUTED, ha="right", alpha=a)
    # onthulling
    if rv > 0:
        text(ax, PAD_X, y0 + 70, spec.get("big_number", ""), "bold", 88, ACC(), alpha=rv)
        text(ax, PAD_X, y0 + 130, spec.get("big_label", ""), "medium", 38, MUTED, alpha=rv)


TEMPLATES["usmap"] = (usmap_timeline, usmap_draw)
