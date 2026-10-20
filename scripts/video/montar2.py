"""Arma el video final 1080x1920: fondo de marca + título grande arriba + pantalla del celular enmarcada.

Uso: video-venv/bin/python montar2.py <carpeta_grabacion> <pista.mp3> <salida.mp4> <portada|título> <cierre|título>
Lee pantalla.mp4 y guion.json que deja grabar2.py.
"""
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CARPETA, PISTA, SALIDA = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
PORTADA, CIERRE = sys.argv[4], sys.argv[5]
TMP = CARPETA / "montaje"
TMP.mkdir(exist_ok=True)

W, H = 1080, 1920
SX, SY, SW, SH = 195, 400, 690, 1493   # pantalla del celular dentro del cuadro
RIM, R_IN, R_OUT = 16, 46, 62
ACENTO, OSCURO = "#b5482f", "#2a1510"

FUENTES = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800'
           '&family=Hanken+Grotesk:wght@500;600;700&display=block">')
BASE_CSS = f"""*{{margin:0;padding:0;box-sizing:border-box}}html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{font-family:"Hanken Grotesk",system-ui,sans-serif;color:#fff;
 background:radial-gradient(1100px 900px at 88% -5%,{ACENTO} 0%,transparent 62%),radial-gradient(900px 800px at 0% 105%,#5a2416 0%,transparent 60%),{OSCURO}}}
.chip{{position:absolute;left:70px;top:70px;display:flex;align-items:center;gap:14px;font-weight:700;font-size:30px;
 background:rgba(255,255,255,.12);border:1.5px solid rgba(255,255,255,.22);padding:12px 22px 12px 14px;border-radius:99px}}
.chip i{{width:40px;height:40px;border-radius:12px;background:#ffc21a;display:grid;place-items:center;font-style:normal;color:#151410;font-weight:800;font-size:22px}}
h1{{font-family:"Bricolage Grotesque",sans-serif;font-weight:800;letter-spacing:-1.5px}}"""


def html_fondo(titulo, bajada):
    return f"""<!doctype html><html><head><meta charset="utf-8">{FUENTES}<style>{BASE_CSS}
.t{{position:absolute;left:70px;right:70px;top:160px}}
h1{{font-size:{76 if len(titulo) < 26 else 64}px;line-height:1.02}}
p{{font-size:38px;font-weight:600;opacity:.82;margin-top:14px}}
.sombra{{position:absolute;left:{SX - RIM}px;top:{SY - RIM}px;width:{SW + 2 * RIM}px;height:{SH + 2 * RIM}px;border-radius:{R_OUT}px;
 box-shadow:0 40px 120px rgba(0,0,0,.55),0 0 0 2px rgba(255,255,255,.08)}}</style></head>
<body><div class="chip"><i>M</i>La Comarca · MiMenú</div><div class="t"><h1>{titulo}</h1><p>{bajada}</p></div><div class="sombra"></div></body></html>"""


def html_marco():
    x, y, w, h = SX - RIM, SY - RIM, SW + 2 * RIM, SH + 2 * RIM
    return f"""<!doctype html><html><head><style>html,body{{margin:0;width:{W}px;height:{H}px;background:transparent}}</style></head><body>
<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" fill="#0b0b0c" d="
M{x + R_OUT},{y} h{w - 2 * R_OUT} a{R_OUT},{R_OUT} 0 0 1 {R_OUT},{R_OUT} v{h - 2 * R_OUT} a{R_OUT},{R_OUT} 0 0 1 -{R_OUT},{R_OUT} h-{w - 2 * R_OUT} a{R_OUT},{R_OUT} 0 0 1 -{R_OUT},-{R_OUT} v-{h - 2 * R_OUT} a{R_OUT},{R_OUT} 0 0 1 {R_OUT},-{R_OUT} z
M{SX + R_IN},{SY} h{SW - 2 * R_IN} a{R_IN},{R_IN} 0 0 1 {R_IN},{R_IN} v{SH - 2 * R_IN} a{R_IN},{R_IN} 0 0 1 -{R_IN},{R_IN} h-{SW - 2 * R_IN} a{R_IN},{R_IN} 0 0 1 -{R_IN},-{R_IN} v-{SH - 2 * R_IN} a{R_IN},{R_IN} 0 0 1 {R_IN},-{R_IN} z"/>
<rect x="{W / 2 - 60}" y="{SY + 14}" width="120" height="30" rx="15" fill="#0b0b0c"/></svg></body></html>"""


def html_tarjeta(texto, final=False):
    titulo, _, resto = texto.partition("|")
    extra = ("<div class='url'>mimenudigital.divergentstudio.cl</div><div class='firma'>Divergent Studio · Quinta Normal</div>"
             if final else "")
    return f"""<!doctype html><html><head><meta charset="utf-8">{FUENTES}<style>{BASE_CSS}
body{{display:grid;place-items:center;text-align:center}}.c{{padding:0 90px}}
.logo{{width:150px;height:150px;border-radius:42px;background:#ffc21a;color:#151410;display:grid;place-items:center;margin:0 auto 54px;
 font:800 84px "Bricolage Grotesque",sans-serif}}
h1{{font-size:104px;line-height:.98}}p{{font-size:44px;font-weight:600;opacity:.85;margin-top:30px;line-height:1.3}}
.url{{margin-top:70px;font-size:40px;font-weight:700;background:rgba(255,255,255,.12);padding:20px 34px;border-radius:24px;display:inline-block}}
.firma{{margin-top:34px;font-size:32px;opacity:.7}}</style></head>
<body><div class="c"><div class="logo">M</div><h1>{titulo}</h1><p>{resto}</p>{extra}</div></body></html>"""


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def main():
    guion = json.loads((CARPETA / "guion.json").read_text())
    titulos, cortes, fin = guion["titulos"], guion["cortes"], guion["fin"]

    # Imágenes: un fondo por título, el marco del celular y las tarjetas de portada y cierre
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page(viewport={"width": W, "height": H})

        def foto(html, ruta, transparente=False):
            pag.set_content(html, wait_until="networkidle")
            pag.wait_for_timeout(300)
            pag.screenshot(path=str(ruta), omit_background=transparente)

        for k, (_, t, b) in enumerate(titulos):
            foto(html_fondo(t, b), TMP / f"fondo_{k}.png")
        foto(html_marco(), TMP / "marco.png", transparente=True)
        foto(html_tarjeta(PORTADA), TMP / "portada.png")
        foto(html_tarjeta(CIERRE, final=True), TMP / "cierre.png")
        nav.close()

    # Tramos: cada título dura hasta el siguiente; se quitan las cargas de página
    tramos = []
    for k, (t, _, _) in enumerate(titulos):
        ini = 0.0 if k == 0 else t
        fin_t = titulos[k + 1][0] if k + 1 < len(titulos) else fin
        partes = [[ini, fin_t]]
        for a, b in cortes:
            nuevas = []
            for x, y in partes:
                if b <= x or a >= y:
                    nuevas.append([x, y])
                    continue
                if a > x:
                    nuevas.append([x, a])
                if b < y:
                    nuevas.append([b, y])
            partes = nuevas
        tramos += [(k, x, y) for x, y in partes if y - x > 0.15]

    clips = []

    def tarjeta(png, nombre, dur):
        salida = TMP / nombre
        ffmpeg("-i", str(png), "-vf",
               f"zoompan=z='min(1.0+0.0006*on,1.04)':d={int(dur * 30)}:s={W}x{H}:fps=30,fade=t=in:d=0.4,fade=t=out:st={dur - 0.35}:d=0.35,format=yuv420p",
               "-frames:v", str(int(dur * 30)), "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", "30", str(salida))
        clips.append(salida)

    tarjeta(TMP / "portada.png", "c000.mp4", 2.8)
    for n, (k, a, b) in enumerate(tramos):
        salida = TMP / f"c{n + 1:03d}.mp4"
        dur = b - a
        ffmpeg("-loop", "1", "-i", str(TMP / f"fondo_{k}.png"), "-i", str(CARPETA / "pantalla.mp4"),
               "-loop", "1", "-i", str(TMP / "marco.png"), "-filter_complex",
               f"[1:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS,fps=30,scale={SW}:{SH}:flags=lanczos[s];"
               f"[0:v][s]overlay={SX}:{SY}:shortest=1[t];[t][2:v]overlay=0:0,format=yuv420p",
               "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", "30", str(salida))
        clips.append(salida)
    tarjeta(TMP / "cierre.png", "c999.mp4", 3.6)

    lista = TMP / "lista.txt"
    lista.write_text("".join(f"file '{c.name}'\n" for c in clips))
    unido = TMP / "unido.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(unido))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(unido)],
                               capture_output=True, text=True, check=True).stdout)
    ffmpeg("-i", str(unido), "-stream_loop", "-1", "-i", PISTA, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-af", f"volume=0.32,afade=t=in:d=0.6,afade=t=out:st={max(0, dur - 2.2):.2f}:d=2.2",
           "-c:a", "aac", "-b:a", "128k", "-t", f"{dur:.2f}", "-movflags", "+faststart", str(SALIDA))
    print(f"LISTO {SALIDA} {dur:.1f}s · {len(tramos)} tramos")


if __name__ == "__main__":
    main()
