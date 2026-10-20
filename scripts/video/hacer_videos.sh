#!/bin/bash
# Graba y monta los dos videos de MiMenú de La Comarca (cliente y dueño) en ~/proyectos/mimenu/video2.
# Levanta una copia local temporal de la app y deja los datos de La Comarca como estaban al terminar.
set -e
APP=~/proyectos/mimenu/app
OUT=~/proyectos/mimenu/video2
MUSICA=~/radar-precios-cl/data/musica/general
RESPALDO=/tmp/mimenu-video-respaldo.json
cd "$APP"

PYTHONPATH=. ../venv/bin/python scripts/video/respaldo.py guardar lacomarca "$RESPALDO" 2>/dev/null | tail -1

FLASK_ENV=development nohup ../venv/bin/gunicorn --workers 1 --threads 4 --bind 127.0.0.1:8099 wsgi:application \
  > /tmp/mimenu-video.log 2>&1 &
PID=$!
restaurar() {
  kill $PID 2>/dev/null || true
  PYTHONPATH=. ../venv/bin/python scripts/video/respaldo.py restaurar lacomarca "$RESPALDO" 2>/dev/null | tail -1
}
trap restaurar EXIT
for i in $(seq 1 30); do sleep 1; curl -s -o /dev/null http://127.0.0.1:8099/api/health && break; done
curl -s -o /dev/null http://127.0.0.1:8099/menu/lacomarca

COOKIE=$(FLASK_ENV=development PYTHONPATH=. ../venv/bin/python scripts/video/sesion.py lacomarca 2>/dev/null | tail -1)
rm -rf "$OUT"; mkdir -p "$OUT"
nice -n 5 ../video-venv/bin/python scripts/video/grabar2.py cliente "$OUT/cliente"
nice -n 5 ../video-venv/bin/python scripts/video/grabar2.py dueno "$OUT/dueno" "$COOKIE"
echo "rechazos CSRF: $(grep -c 'CSRF rechazado' /tmp/mimenu-video.log || true)"

../video-venv/bin/python scripts/video/montar2.py "$OUT/cliente" "$MUSICA/be-jammin-nakarada.mp3" "$OUT/MiMenu-La-Comarca-cliente.mp4" \
  "Así ven tu carta|tus clientes, desde su celular" "Tu carta, en el celular|de cada cliente"
../video-venv/bin/python scripts/video/montar2.py "$OUT/dueno" "$MUSICA/celebration-nakarada.mp3" "$OUT/MiMenu-La-Comarca-panel.mp4" \
  "Así manejas tu carta|desde tu propio panel" "Tú tienes el control|sin depender de nadie"
