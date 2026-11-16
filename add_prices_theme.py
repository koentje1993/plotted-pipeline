"""Voegt het thema plotted. Prices toe aan de pipeline (accent groen).

Gebruik, vanuit de map plotted-pipeline:
    python3 add_prices_theme.py
    python3 make_brand_assets.py prices   # logo, avatar en banners voor het nieuwe kanaal

Daarna rendert elke spec met "brand": "prices" in de groene huisstijl.
"""
from pathlib import Path

p = Path("plotted/brand.py")
s = p.read_text(encoding="utf-8")

if '"prices"' in s:
    print("Thema 'prices' bestaat al, niets gewijzigd.")
    raise SystemExit(0)

anchor = '"ai": {"accent": SIGNAL_AI, "suffix": "AI", "cta": "Follow plotted. AI"},'
if anchor not in s:
    raise SystemExit("Kon de THEMES-regel van plotted. AI niet vinden in plotted/brand.py. "
                     "Voeg deze regel zelf toe aan THEMES:\n"
                     '    "prices": {"accent": "#4ADE80", "suffix": "Prices", "cta": "Follow plotted. Prices"},')

s = s.replace(anchor, anchor + '\n    "prices": {"accent": "#4ADE80", "suffix": "Prices", "cta": "Follow plotted. Prices"},')
p.write_text(s, encoding="utf-8")
print("Thema 'prices' toegevoegd aan plotted/brand.py.")
