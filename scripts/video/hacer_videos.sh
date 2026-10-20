#!/bin/bash
# Graba y monta los dos videos de MiMenú de un local (cliente y dueño) en ~/proyectos/mimenu/videos/<slug>.
# Uso: bash hacer_videos.sh <slug> "<Nombre del local>"   (los platos del guion van en locales.json)
# Levanta una copia local temporal de la app y deja los datos del local como estaban al terminar.
set -e
SLUG=${1:?falta el slug}
NOMBRE=${2:?falta el nombre}
APP=~/proyectos/mimenu/app
OUT=~/proyectos/mimenu/videos/$SLUG
MUSICA=~/radar-precios-cl/data/musica/general
RESPALDO=/tmp/mimenu-video-respaldo-$SLUG.json
cd "$APP"

PYTHONPATH=. ../venv/bin/python scripts/video/respaldo.py guardar "$SLUG" "$RESPALDO" 2>/dev/null | tail -1

FLASK_ENV=development nohup ../venv/bin/gunicorn --workers 1 --threads 4 --bind 127.0.0.1:8099 wsgi:application \
  > /tmp/mimenu-video.log 2>&1 &
PID=$!
restaurar() {
  kill $PID 2>/dev/null || true
  PYTHONPATH=. ../venv/bin/python scripts/video/respaldo.py restaurar "$SLUG" "$RESPALDO" 2>/dev/null | tail -1
}
trap restaurar EXIT
for i in $(seq 1 30); do sleep 1; curl -s -o /dev/null http://127.0.0.1:8099/api/health && break; done
curl -s -o /dev/null "http://127.0.0.1:8099/menu/$SLUG"

COOKIE=$(FLASK_ENV=development PYTHONPATH=. ../venv/bin/python scripts/video/sesion.py "$SLUG" 2>/dev/null | tail -1)
rm -rf "$OUT"; mkdir -p "$OUT"
nice -n 5 ../video-venv/bin/python scripts/video/grabar2.py cliente "$OUT/cliente" "$SLUG"
nice -n 5 ../video-venv/bin/python scripts/video/grabar2.py dueno "$OUT/dueno" "$SLUG" "$COOKIE"
echo "rechazos CSRF: $(grep -c 'CSRF rechazado' /tmp/mimenu-video.log || true)"

ARCHIVO=$(echo "$NOMBRE" | tr ' ' '-')
../video-venv/bin/python scripts/video/montar2.py "$OUT/cliente" "$MUSICA/be-jammin-nakarada.mp3" "$OUT/MiMenu-$ARCHIVO-cliente.mp4" \
  "Así ven tu carta|tus clientes, desde su celular" "Tu carta, en el celular|de cada cliente" "$NOMBRE"
../video-venv/bin/python scripts/video/montar2.py "$OUT/dueno" "$MUSICA/celebration-nakarada.mp3" "$OUT/MiMenu-$ARCHIVO-panel.mp4" \
  "Así manejas tu carta|desde tu propio panel" "Tú tienes el control|sin depender de nadie" "$NOMBRE"
