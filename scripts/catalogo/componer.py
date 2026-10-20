"""Arma las imágenes del catálogo de WhatsApp de MiMenú (1080x1080) con las capturas de capturas.py.
Uso: video-venv/bin/python componer.py <carpeta_capturas> <carpeta_salida>"""
import base64
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

CAP, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)


def b64(nombre, recorte_arriba=0):
    im = Image.open(CAP / f"{nombre}.png").convert("RGB")
    if recorte_arriba:
        im = im.crop((0, recorte_arriba, im.width, im.height))
    ruta = CAP / f"_{nombre}.jpg"
    im.save(ruta, quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(ruta.read_bytes()).decode()


CSS = """*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1080px;overflow:hidden}
body{font-family:"Hanken Grotesk",system-ui,sans-serif;color:#fff;position:relative;
 background:radial-gradient(900px 700px at 100% 0%,#3a3015 0%,transparent 60%),radial-gradient(700px 600px at 0% 100%,#2a2210 0%,transparent 60%),#121110}
.marca{position:absolute;left:64px;top:60px;display:flex;align-items:center;gap:14px;font:800 34px "Bricolage Grotesque",sans-serif}
.marca i{width:52px;height:52px;border-radius:15px;background:#ffc21a;color:#151410;display:grid;place-items:center;font-style:normal;font-size:30px}
.txt{position:absolute;left:64px;top:170px;width:520px}
h1{font:800 64px/1.0 "Bricolage Grotesque",sans-serif;letter-spacing:-1.5px}
h1 em{font-style:normal;color:#ffc21a}
p{font-size:30px;line-height:1.35;opacity:.82;margin-top:22px;font-weight:500}
ul{list-style:none;margin-top:30px;display:grid;gap:14px}
li{font-size:27px;font-weight:600;display:flex;gap:12px;align-items:flex-start}
li:before{content:"";flex:none;width:14px;height:14px;border-radius:50%;background:#ffc21a;margin-top:11px}
.tel{position:absolute;width:390px;height:844px;border-radius:52px;background:#050505;padding:12px;
 box-shadow:0 0 0 2px #2c2a26,0 40px 90px rgba(0,0,0,.6),0 0 120px rgba(255,194,26,.12)}
.tel img{width:100%;height:100%;object-fit:cover;object-position:top;border-radius:41px;display:block}
.tel:after{content:"";position:absolute;left:50%;top:22px;width:96px;height:26px;margin-left:-48px;border-radius:14px;background:#050505}
.pie{position:absolute;left:64px;bottom:56px;font-size:24px;font-weight:600;opacity:.6}
.chip{display:inline-block;margin-top:34px;background:#ffc21a;color:#151410;font:800 34px "Bricolage Grotesque",sans-serif;padding:16px 26px;border-radius:18px}
.chip small{font:700 22px "Hanken Grotesk",sans-serif;opacity:.75}"""
FUENTES = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800'
           '&family=Hanken+Grotesk:wght@500;600;700&display=block">')


def pagina(cuerpo):
    return f'<!doctype html><html><head><meta charset="utf-8">{FUENTES}<style>{CSS}</style></head><body>' \
           f'<div class="marca"><i>M</i>MiMenú</div>{cuerpo}<div class="pie">mimenudigital.divergentstudio.cl</div></body></html>'


def tel(src, x, y, escala=1.0, giro=0):
    return (f'<div class="tel" style="left:{x}px;top:{y}px;transform:scale({escala}) rotate({giro}deg);transform-origin:top left">'
            f'<img src="{src}"></div>')


PIEZAS = {
    "01-portada": pagina(f"""
<div class="txt"><h1>Tu carta<br>digital<br><em>con QR</em></h1>
<p>Fotos, precios al día y pedidos desde el celular de tus clientes.</p>
<div class="chip">Desde $7.990 <small>/ mes</small></div></div>
{tel(b64("carta_portada"), 640, 120, 1.0, 3)}"""),
    "02-clientes": pagina(f"""
<div class="txt"><h1>Tus clientes<br>la ven <em>con fotos</em></h1>
<ul><li>Escanean el QR de la mesa</li><li>Fotos y precios de cada plato</li><li>Buscador y categorías</li>
<li>“Abierto ahora” según tu horario</li></ul></div>
{tel(b64("carta_lista"), 640, 120)}"""),
    "03-pedido": pagina(f"""
<div class="txt"><h1>Arman su pedido<br>y ven <em>el total</em></h1>
<ul><li>Notas por producto: “sin mayo”, “Coca-Cola”</li><li>Se lo muestran a quien atiende</li>
<li>O lo envían por WhatsApp</li></ul></div>
{tel(b64("pedido"), 600, 150, 0.95, -2)}{tel(b64("mostrar"), 760, 230, 0.78, 4)}"""),
    "04-panel": pagina(f"""
<div class="txt"><h1>Tú la manejas<br><em>desde tu celular</em></h1>
<ul><li>Cambias precios en segundos</li><li>Pausas lo que se acabó</li><li>Subes fotos y descripciones</li>
<li>Sin depender de nadie</li></ul></div>
{tel(b64("panel_platos", 180), 600, 150, 0.95, -2)}{tel(b64("panel_editar", 180), 760, 230, 0.78, 4)}"""),
    "05-pagina-web": pagina(f"""
<div class="txt"><h1>Incluye tu<br><em>página web</em></h1>
<ul><li>Portada, fotos y quiénes son</li><li>Horario, mapa y “Cómo llegar”</li><li>Instagram, Facebook y WhatsApp</li>
<li>La editas tú mismo</li></ul></div>
{tel(b64("local"), 640, 120)}"""),
    "06-qr-y-planes": pagina(f"""
<div class="txt"><h1>QR listo<br>para <em>tus mesas</em></h1>
<p>Y tu carta en PDF para imprimir, siempre con los precios al día.</p>
<ul style="margin-top:34px"><li><b>Plan Local</b>&nbsp;· $7.990/mes<br></li></ul>
<p style="font-size:24px;margin-top:6px;padding-left:26px">Carta, página web y QR para imprimir</p>
<ul style="margin-top:20px"><li><b>Plan Tótem</b>&nbsp;· $9.990/mes</li></ul>
<p style="font-size:24px;margin-top:6px;padding-left:26px">Todo lo anterior + 5 tótems QR y NFC</p></div>
{tel(b64("panel_qr", 180), 640, 120)}"""),
}

with sync_playwright() as pw:
    nav = pw.chromium.launch()
    pag = nav.new_page(viewport={"width": 1080, "height": 1080})
    for nombre, html in PIEZAS.items():
        pag.set_content(html, wait_until="networkidle")
        pag.wait_for_timeout(400)
        png = OUT / f"{nombre}.png"
        pag.screenshot(path=str(png))
        Image.open(png).convert("RGB").save(OUT / f"{nombre}.jpg", quality=92)
        png.unlink()
    nav.close()
print("listas:", sorted(p.name for p in OUT.glob("*.jpg")))
