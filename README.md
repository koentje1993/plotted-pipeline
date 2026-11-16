# plotted. – videopipeline

Maakt van een JSON-spec een verticale video (1080×1920, 30 fps, H.264) in de plotted.-huisstijl.
Dezelfde file gaat naar X, YouTube Shorts, TikTok en Reels.

## Installatie

```bash
pip install matplotlib numpy
# ffmpeg moet op het pad staan (brew install ffmpeg / apt install ffmpeg)
```

De fonts (Space Grotesk en JetBrains Mono, beide OFL-licentie) staan in `fonts/`.

## Gebruik

```bash
python -m plotted.render specs/post01.json               # -> out/post01.mp4
python -m plotted.render specs/post01.json --still 9     # -> out/post01_9s.png (snelle check)
python -m plotted.render specs/post01.json --audio vo.mp3  # met voice-over of muziek
```

Een video van 12 seconden rendert in ongeveer een minuut.

## Logo en platformassets

```bash
python make_brand_assets.py   # -> brand_assets/logo en brand_assets/platform
```

- `logo/`: woordmerk, beeldmerk en horizontale lockup, elk in donker, licht en transparant (SVG met tekst als outlines, plus PNG).
- `platform/avatar-1080.png`: profielfoto voor X, YouTube, TikTok en Instagram (veilig voor ronde uitsnede).
- `platform/x-banner-1500x500.png` en `platform/youtube-banner-2560x1440.png`.

## Retentie: zit in elke template

| moment | wat er gebeurt | spec-veld |
|---|---|---|
| 0,0 s | hook staat er meteen, voortgangsbalk loopt, alles beweegt al | `hook` |
| 0,3 s | voorspel-prompt in oranje onder de hook | `prompt` |
| elke 2-3 s | nieuwe balk, inhaalactie met flits en blip, label bij gebeurtenis | `events` [{year, text}] |
| tempo | saaie jaren snel, spannende jaren langzaam | `pace` [[van, tot, sec_per_jaar]] |
| reveal | het oranje antwoord staat als ??? klaar en komt na een korte stilte | `highlight`, `reveal_pause` |
| einde | conclusie, daarna "Follow @plottedworld" op de plek van het woordmerk; geen apart eindscherm, zodat de video naadloos loopt | `caption`, `cta`, `hold` |

De lengte volgt uit de data en het tempo; je geeft geen `duration` meer op.

Geluid: elke video krijgt automatisch zachte effecten op de beats (tik per jaar of balk, blip bij inhaalactie, twee tonen bij een event, akkoord bij de onthulling). `--no-sfx` zet dat uit, `--audio` vervangt het door je eigen voice-over of muziek.

## Templates

| template | gebruik | belangrijkste velden |
|---|---|---|
| `bars` | ranglijsten, vergelijkingen, mijlpalen | `rows` (label, value, value_label, highlight), `style`: `stacked` of `inline` |
| `line` | ontwikkeling door de tijd, met jaarteller | `points` [[jaar, waarde]], `highlight_from`, `y_ticks`, `x_labels`, `value_fmt` |
| `dotgrid` | "als de wereld 100 mensen was", aandelen | `highlight` (aantal), `total`, `count_fmt`, `big_label` |
| `race` | bar chart race met groot jaartal en inhaalmomenten | `years`, `series` {naam: [waarden]}, `highlight`, `top_n`, `value_fmt` |

Alle templates gebruiken `tag_num`, `tag`, `right_label`, `hook`, `prompt`, `caption` en `source`. Tussen twee jaren in `line` en `race` wordt lineair geïnterpoleerd.

## Huisstijlregels in de code

- Eén oranje element per beeld (`"highlight": true`), de rest is slate.
- De hook staat vanaf het eerste frame in beeld.
- Themalabel linksboven, wordmark rechtsonder, bron altijd in beeld.
- Alles wat gelezen moet worden staat boven y=1600, buiten de knoppen van Shorts/TikTok/Reels.

## Nieuwe post maken

1. Kopieer een spec uit `specs/` die op je format lijkt.
2. Vul de data in uit de bron in het werkboek, en controleer die bron.
3. Render een still, kijk ernaar, render daarna de video.
4. Voice-over (optioneel): tekst staat in het werkboek, tab Scripts. Genereer met Azure Speech of ElevenLabs en geef het bestand mee met `--audio`.

`specs/_voorbeeld/` bevat testdata om de templates te zien. Niet posten.

## Volgende stappen

- Templates voor kaarten (geopandas) en bar chart races (data per jaar).
- Automatisch posten: begin in de testfase handmatig of met de planner van YouTube Studio en een X-scheduler, zodat je elke video nog ziet. Automatiseer pas als het format staat.

## Automatisch renderen vanuit Notion

De cockpit in Notion stuurt de productie. Dit script draait op je eigen computer of VPS, haalt items met status **In productie** op, rendert ze en zet ze terug op **Ter review**.

### Eenmalig instellen

1. Installeer Python 3.11+ en ffmpeg, en daarna de pakketten:
   ```bash
   pip install -r requirements.txt
   ```
2. Maak een Notion-integratie op https://www.notion.so/my-integrations (type: intern) en kopieer het token.
3. Open in Notion de pagina **plotted. – cockpit**, klik op **...** rechtsboven, kies **Verbindingen** en voeg je integratie toe.
4. Zet drie omgevingsvariabelen (bijvoorbeeld in een `.env` of je shellprofiel):
   ```bash
   export NOTION_TOKEN=secret_xxx
   export PLOTTED_DB_ID=418618ebd635812fa150e19871c79f75
   export PLOTTED_OUT=~/plotted/videos
   ```
5. Test zonder te renderen:
   ```bash
   python -m plotted.notion_sync --dry-run
   ```

### Werkwijze per video

1. Zet de JSON-spec in de Notion-pagina van het item, als codeblok met taal JSON. Voorbeelden staan in `specs/`.
2. Zet de status op **In productie**.
3. Draai `python -m plotted.notion_sync`. De video komt in `PLOTTED_OUT`, het item gaat naar **Ter review** en het veld **Bestand** krijgt de bestandsnaam.
4. Bekijk de video, zet de status op **Klaar** en plan hem in.

Mislukt een render, dan blijft de status staan en staat de fout in **Notitie**.

### Automatisch laten draaien

- **macOS / Linux / VPS** (elk kwartier, via `crontab -e`):
  ```
  */15 * * * * cd ~/plotted-pipeline && . ./.env && python3 -m plotted.notion_sync >> sync.log 2>&1
  ```
- **Windows** (Taakplanner): nieuwe taak, trigger elke 15 minuten, actie `python -m plotted.notion_sync` met als map de pipeline-map. Zet de variabelen bij Systeem > Omgevingsvariabelen.
- **Of gewoon laten openstaan**: `python -m plotted.notion_sync --watch 900`.

### Wie schrijft de spec?

Dat kan op drie manieren:
- **Zelf**: kopieer een spec uit `specs/` en vervang de data.
- **Claude in een chat**: "maak de spec voor <hook> en zet hem in Notion".
- **Geplande taak (spec-maker)**: pakt items met status **Goedgekeurd**, zoekt en controleert de data, schrijft de spec in de pagina en zet de status op **In productie**. Jij ziet de data terug in de pagina voordat er gerenderd wordt.
