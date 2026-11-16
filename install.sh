#!/usr/bin/env bash
# plotted. pipeline: eenmalige installatie op een Ubuntu/Debian-VPS.
# Gebruik (als je eigen gebruiker, niet als root), vanuit de uitgepakte map plotted-pipeline:
#     bash install.sh
# Het script vraagt om je Notion-token, installeert alles, test de koppeling en zet de cronjob.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ "$(id -u)" = "0" ]; then
  echo "Draai dit script als je eigen gebruiker, niet als root."; exit 1
fi

echo "== 1/5 Systeempakketten (python3-venv, ffmpeg)"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip ffmpeg unzip > /dev/null

echo "== 2/5 Python-omgeving"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "== 3/5 Instellingen"
if [ ! -f .env ]; then
  read -r -s -p "Plak je Notion-token (begint met ntn_ of secret_): " TOKEN; echo
  OUT_DIR="${HOME}/plotted/out"
  cat > .env <<EOF
export NOTION_TOKEN="${TOKEN}"
export PLOTTED_DB_ID="418618ebd635812fa150e19871c79f75"
export PLOTTED_OUT="${OUT_DIR}"
export PLOTTED_UPLOAD="1"
EOF
  chmod 600 .env
  mkdir -p "${OUT_DIR}"
else
  echo ".env bestaat al, die laat ik staan."
fi
# shellcheck disable=SC1091
. ./.env

echo "== 4/5 Test: render een korte voorbeeldvideo en kijk wat er in Notion klaarstaat"
.venv/bin/python -W ignore -m plotted.render specs/_voorbeeld/dotgrid_demo.json --out "${PLOTTED_OUT}/_test" 2>/dev/null \
  && echo "   rendertest gelukt: ${PLOTTED_OUT}/_test/dotgrid_demo.mp4"
.venv/bin/python -m plotted.notion_sync --dry-run || {
  echo "   De Notion-koppeling werkt nog niet. Controleer het token en of de integratie"
  echo "   is toegevoegd aan de cockpitpagina (... > Verbindingen). Draai daarna opnieuw: bash install.sh"
  exit 1; }

echo "== 5/5 Cronjob: elk kwartier renderen"
LINE="*/15 * * * * cd ${DIR} && . ./.env && .venv/bin/python -W ignore -m plotted.notion_sync >> ${DIR}/sync.log 2>&1"
( crontab -l 2>/dev/null | grep -v "plotted.notion_sync" ; echo "$LINE" ) | crontab -
echo "   cronjob staat. Log: ${DIR}/sync.log"

echo
echo "Klaar. Items met status 'In productie' worden elk kwartier gerenderd, als video aan de"
echo "Notion-pagina toegevoegd (veld Video) en op 'Ter review' gezet."
echo "Nu meteen draaien in plaats van wachten:  cd ${DIR} && . ./.env && .venv/bin/python -m plotted.notion_sync"
