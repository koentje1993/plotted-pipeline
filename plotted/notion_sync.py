"""Haalt items uit de Notion-cockpit en rendert ze lokaal.

Werkwijze in Notion:
  1. Een item met status "In productie" heeft in de pagina-inhoud een codeblok (taal: JSON) met de spec.
  2. Dit script rendert die spec naar <PLOTTED_OUT>/postNN-<slug>.mp4,
     zet "Bestand" op de bestandsnaam en de status op "Ter review".
  3. Gaat er iets mis, dan blijft de status staan en komt de fout in "Notitie".

Instellen (eenmalig):
  - Maak op https://www.notion.so/my-integrations een interne integratie en kopieer het token.
  - Open in Notion de pagina "plotted. – cockpit" > ... > Verbindingen > voeg de integratie toe.
  - Zet omgevingsvariabelen (of draai install.sh, dat doet dit voor je):
        NOTION_TOKEN=secret_...
        PLOTTED_DB_ID=418618ebd635812fa150e19871c79f75
        PLOTTED_OUT=/pad/naar/map/voor/videos   (optioneel, standaard ./out)

Gebruik:
  python -m plotted.notion_sync            # één keer alles verwerken
  python -m plotted.notion_sync --watch 600 # elke 10 minuten kijken
  python -m plotted.notion_sync --dry-run  # alleen tonen wat er zou gebeuren
"""
import argparse
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

import requests

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
TODO = "In productie"
DONE = "Ter review"


def _headers():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("NOTION_TOKEN ontbreekt. Zie de uitleg bovenin dit bestand.")
    return {"Authorization": f"Bearer {token}", "Notion-Version": VERSION, "Content-Type": "application/json"}


def query_todo(db_id):
    body = {"filter": {"property": "Status", "status": {"equals": TODO}}, "page_size": 50}
    r = requests.post(f"{API}/databases/{db_id}/query", headers=_headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.json()["results"]


def page_blocks(page_id):
    blocks, cursor = [], None
    while True:
        url = f"{API}/blocks/{page_id}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
        r = requests.get(url, headers=_headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        blocks += data["results"]
        if not data.get("has_more"):
            return blocks
        cursor = data["next_cursor"]


def spec_from_blocks(blocks):
    """Eerste codeblok met geldige JSON en een 'template'-veld."""
    for b in blocks:
        if b.get("type") != "code":
            continue
        txt = "".join(rt.get("plain_text", "") for rt in b["code"].get("rich_text", []))
        try:
            spec = json.loads(txt)
        except json.JSONDecodeError:
            continue
        if isinstance(spec, dict) and "template" in spec:
            return spec
    return None


def title_of(page):
    for prop in page["properties"].values():
        if prop.get("type") == "title":
            return "".join(t["plain_text"] for t in prop["title"])
    return "untitled"


def number_of(page):
    nr = page["properties"].get("Nr", {}).get("unique_id", {})
    return nr.get("number") or 0


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def update_page(page_id, status=None, bestand=None, notitie=None):
    props = {}
    if status:
        props["Status"] = {"status": {"name": status}}
    if bestand:
        props["Bestand"] = {"rich_text": [{"text": {"content": bestand}}]}
    if notitie is not None:
        props["Notitie"] = {"rich_text": [{"text": {"content": notitie[:1900]}}]}
    r = requests.patch(f"{API}/pages/{page_id}", headers=_headers(), json={"properties": props}, timeout=30)
    r.raise_for_status()


def upload_video(page_id, path):
    """Zet de MP4 in het Files-veld "Video" van de pagina (Notion File Upload API).

    Zo kun je de video op je telefoon in Notion openen en delen naar YouTube of X.
    Lukt het niet (bijv. bestand te groot voor je Notion-abonnement), dan blijft de video
    gewoon in PLOTTED_OUT staan en volgt er een melding in Notitie.
    """
    path = Path(path)
    h = _headers()
    r = requests.post(f"{API}/file_uploads", headers=h,
                      json={"filename": path.name, "content_type": "video/mp4"}, timeout=30)
    r.raise_for_status()
    up = r.json()
    send_url = up.get("upload_url") or f"{API}/file_uploads/{up['id']}/send"
    hs = {k: v for k, v in h.items() if k != "Content-Type"}  # multipart zet zelf het content-type
    with open(path, "rb") as fh:
        r = requests.post(send_url, headers=hs, files={"file": (path.name, fh, "video/mp4")}, timeout=300)
    r.raise_for_status()
    body = {"properties": {"Video": {"files": [
        {"type": "file_upload", "file_upload": {"id": up["id"]}, "name": path.name}]}}}
    r = requests.patch(f"{API}/pages/{page_id}", headers=h, json=body, timeout=30)
    r.raise_for_status()


def process(db_id, out_dir, dry_run=False):
    from .render import render_video
    items = query_todo(db_id)
    print(f"{len(items)} item(s) met status '{TODO}'")
    for page in items:
        name = title_of(page)
        spec = spec_from_blocks(page_blocks(page["id"]))
        if not spec:
            print(f"  overgeslagen (geen JSON-spec in de pagina): {name}")
            if not dry_run:
                update_page(page["id"], notitie="Geen JSON-spec gevonden in de pagina-inhoud.")
            continue
        fname = f"post{number_of(page):02d}-{slug(name)}.mp4"
        print(f"  render: {name} -> {fname}")
        if dry_run:
            continue
        try:
            render_video(spec, Path(out_dir) / fname)
            note = None
            if os.environ.get("PLOTTED_UPLOAD", "1") != "0":
                try:
                    upload_video(page["id"], Path(out_dir) / fname)
                except Exception as e:  # render is gelukt; alleen het uploaden niet
                    note = f"Video staat op de VPS ({fname}), maar uploaden naar Notion mislukte: {e}"
            update_page(page["id"], status=DONE, bestand=fname, notitie=note)
        except Exception as e:  # fout terugmelden in Notion, status laten staan
            traceback.print_exc()
            update_page(page["id"], notitie=f"Render mislukt: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--watch", type=int, help="elke N seconden opnieuw kijken")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    db_id = os.environ.get("PLOTTED_DB_ID", "418618ebd635812fa150e19871c79f75")
    out = Path(os.environ.get("PLOTTED_OUT", "out")).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    while True:
        process(db_id, out, a.dry_run)
        if not a.watch:
            break
        time.sleep(a.watch)


if __name__ == "__main__":
    main()
