"""Video demo de MiMenú (La Comarca): la carta vista por un cliente y el panel del dueño.

Graba con Playwright una copia local de la app (127.0.0.1:8099, arrancada con FLASK_ENV=development
para que funcione sin https) en tamaño celular 1080x1920.
La sesión del dueño se pasa como cookie ya firmada (ver sesion.py): no se usa ninguna contraseña.
Los cambios de la demo (pausar un plato, cambiar un precio) se revierten al final.

Uso (en blackout):  video-venv/bin/python scripts/video/grabar.py <cookie_session> <carpeta_salida>
"""
import base64
import sys
import time
from pathlib import Path

import pypdfium2 as pdfium
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8099"
COOKIE = sys.argv[1]
SALIDA = Path(sys.argv[2])
SALIDA.mkdir(parents=True, exist_ok=True)

ACENTO = "#a8452e"

# Dedo que marca dónde se toca + subtítulos abajo
INIT = """
(() => {
  const css = `#__dedo{position:fixed;z-index:2147483647;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;
     background:rgba(255,255,255,.55);border:3px solid rgba(20,20,20,.55);box-shadow:0 4px 18px rgba(0,0,0,.35);
     pointer-events:none;transition:left .45s cubic-bezier(.3,.8,.3,1),top .45s cubic-bezier(.3,.8,.3,1),transform .15s;opacity:0}
   #__dedo.toca{transform:scale(.72);background:rgba(255,255,255,.85)}
   #__sub{position:fixed;left:14px;right:14px;bottom:18px;z-index:2147483646;background:rgba(17,17,17,.92);color:#fff;
     font:700 19px/1.3 system-ui,sans-serif;padding:14px 16px;border-radius:16px;text-align:center;pointer-events:none;
     box-shadow:0 10px 30px rgba(0,0,0,.35);transform:translateY(160%);transition:transform .35s cubic-bezier(.2,.9,.25,1)}
   #__sub.ver{transform:none}`;
  const poner = () => {
    if (document.getElementById('__dedo') || !document.body) return;
    const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
    const d = document.createElement('div'); d.id = '__dedo'; document.body.appendChild(d);
    const t = document.createElement('div'); t.id = '__sub'; document.body.appendChild(t);
  };
  document.addEventListener('DOMContentLoaded', poner); poner();
  window.__mover = (x, y) => { poner(); const d = document.getElementById('__dedo'); d.style.opacity = 1; d.style.left = x + 'px'; d.style.top = y + 'px'; };
  window.__tocar = () => { const d = document.getElementById('__dedo'); d.classList.add('toca'); setTimeout(() => d.classList.remove('toca'), 180); };
  window.__sub = (txt) => { poner(); const t = document.getElementById('__sub'); if (!txt) { t.classList.remove('ver'); return; } t.textContent = txt; t.classList.add('ver'); };
})();
"""


def tarjeta(titulo, bajada="", fondo="#2a1a12"):
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<style>html,body{{margin:0;height:100%;background:radial-gradient(120% 90% at 85% 0%,{ACENTO},{fondo});color:#fff;
font-family:system-ui,sans-serif;display:grid;place-items:center;text-align:center}}
.c{{padding:0 30px;animation:a .6s cubic-bezier(.2,.8,.2,1) both}}@keyframes a{{from{{opacity:0;transform:translateY(30px)}}}}
h1{{font-size:40px;line-height:1.08;margin:0 0 16px;letter-spacing:-.5px}}p{{font-size:20px;opacity:.85;margin:0;line-height:1.4}}
.m{{display:inline-block;margin-bottom:26px;font-weight:800;font-size:17px;background:rgba(255,255,255,.14);padding:8px 14px;border-radius:99px}}</style>
</head><body><div class="c"><div class="m">MiMenú · La Comarca</div><h1>{titulo}</h1><p>{bajada}</p></div></body></html>"""


def main():
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        ctx = nav.new_context(
            viewport={"width": 432, "height": 768}, device_scale_factor=2.5, is_mobile=True, has_touch=True,
            locale="es-CL", timezone_id="America/Santiago", accept_downloads=True,
            record_video_dir=str(SALIDA / "crudo"), record_video_size={"width": 1080, "height": 1920},
        )
        ctx.add_init_script(INIT)
        p = ctx.new_page()
        t0 = time.monotonic()
        cortes = []  # tramos [inicio, fin] (segundos del video) que se quitan: cargas de página y esperas

        def cortar_desde():
            return time.monotonic() - t0

        def cortar_hasta(inicio):
            cortes.append((inicio, time.monotonic() - t0))

        def abrir(url, limpiar_pedido=False):
            i = cortar_desde()
            p.goto(url, wait_until="networkidle")
            if limpiar_pedido:
                p.evaluate("localStorage.clear()")
                p.reload(wait_until="networkidle")
            p.wait_for_timeout(250)
            cortar_hasta(i)

        def esperar(s):
            p.wait_for_timeout(int(s * 1000))

        def sub(txt=""):
            p.evaluate("t => window.__sub && window.__sub(t)", txt)

        def tocar(loc, pausa=0.7):
            loc.scroll_into_view_if_needed()
            esperar(0.25)
            caja = loc.bounding_box()
            x, y = caja["x"] + caja["width"] / 2, caja["y"] + caja["height"] / 2
            p.evaluate("([x, y]) => window.__mover(x, y)", [x, y])
            esperar(0.55)
            p.evaluate("window.__tocar()")
            loc.click()
            esperar(pausa)

        def escribir(loc, texto):
            tocar(loc, 0.3)
            loc.press_sequentially(texto, delay=85)
            esperar(0.5)

        def bajar(px, pasos=8):
            for _ in range(pasos):
                p.mouse.wheel(0, px / pasos)
                esperar(0.09)
            esperar(0.4)

        def ir_a(texto_seccion):
            p.evaluate("""t => { const h = [...document.querySelectorAll('.seccion h2')].find(e => e.textContent.trim().startsWith(t));
                          if (h) window.scrollTo({top: h.getBoundingClientRect().top + scrollY - 80, behavior: 'smooth'}); }""", texto_seccion)
            esperar(1.2)

        def plato(nombre):
            return p.locator(f'[data-control][data-nombre="{nombre}"]')

        # ---------- 1. Portada ----------
        p.set_content(tarjeta("Tu carta en el celular de cada cliente", "Así la ve un cliente en La Comarca 👇"))
        esperar(3.2)

        # ---------- 2. El cliente ----------
        abrir(BASE + "/menu/lacomarca?refresh=1", limpiar_pedido=True)
        esperar(1.2)
        sub("Escanea el QR y ve la carta con fotos y precios")
        esperar(2.2)
        bajar(520)
        esperar(0.8)
        sub("Toca “Agregar” en lo que quiere")
        ir_a("Churrascos")
        tocar(plato("Churrasco italiano").locator("[data-mas]"), 1.0)
        tocar(plato("Churrasco italiano").locator("[data-mas]"), 0.9)
        sub("¿Un detalle? Lo anota en el producto")
        ir_a("Completos")
        tocar(p.locator(".plato", has=p.locator(".nombre", has_text="Completo")).filter(has_not_text="Italiano").first, 1.2)
        escribir(p.locator("#fichaNota"), "sin mayo")
        tocar(p.locator("#fichaAgregar"), 1.0)
        ir_a("Bebidas")
        tocar(plato("Bebida en lata").locator("[data-mas]"), 1.0)
        sub("Ve el total al tiro")
        tocar(p.locator("#barraPedido"), 1.4)
        nota = p.locator('#pedidoItems .nota[aria-label="Nota para Bebida en lata"]')
        sub("Y elige la bebida que quiere")
        escribir(nota, "Coca-Cola")
        esperar(0.8)
        sub("Se lo muestra a quien atiende y listo")
        tocar(p.locator("#pedidoMostrar"), 3.6)
        sub("")

        # ---------- 3. Panel ----------
        p.set_content(tarjeta("Y tú lo manejas todo desde tu panel", "Desde el celular, sin llamar a nadie"))
        esperar(3.0)
        ctx.add_cookies([{"name": "session", "value": COOKIE, "url": BASE}])

        abrir(BASE + "/gestion/platos")
        esperar(1.2)
        sub("¿Se acabó un producto? Lo pausas con un toque")
        escribir(p.locator("#buscarPlato"), "Chorrillana veg")
        esperar(0.6)
        fila = p.locator(".plato-estado").first
        tocar(fila, 1.8)
        sub("Y desaparece de la carta al instante")
        esperar(1.2)
        abrir(BASE + "/menu/lacomarca?refresh=1", limpiar_pedido=True)
        esperar(0.6)
        ir_a("Chorrillanas")
        esperar(2.4)

        abrir(BASE + "/gestion/platos")
        esperar(1.0)
        sub("Cambiar un precio toma segundos")
        escribir(p.locator("#buscarPlato"), "Churrasco ital")
        esperar(0.5)
        tocar(p.locator(".btn-accion-editar").first, 1.4)
        precio = p.locator("#platoPrecio")
        tocar(precio, 0.3)
        precio.fill("")
        esperar(0.3)
        precio.press_sequentially("3500", delay=150)
        esperar(0.8)
        tocar(p.locator('.modal-overlay.active .btn-primary[onclick="guardarPlato()"]'), 1.6)
        sub("Y la carta se actualiza sola")
        abrir(BASE + "/menu/lacomarca?refresh=1", limpiar_pedido=True)
        esperar(0.6)
        ir_a("Churrascos")
        esperar(2.6)

        abrir(BASE + "/gestion/mi-pagina")
        esperar(1.2)
        sub("También editas fotos, textos y tu página web")
        bajar(700, 10)
        esperar(1.2)
        bajar(700, 10)
        esperar(1.4)

        abrir(BASE + "/gestion/descargas")
        esperar(1.0)
        sub("¿Clientes sin celular? Descarga tu carta en PDF")
        with p.expect_download(timeout=60000) as d:
            tocar(p.locator("#btn-download-pdf"), 0.6)
            i = cortar_desde()
        ruta_pdf = SALIDA / "carta.pdf"
        d.value.save_as(ruta_pdf)
        cortar_hasta(i)
        esperar(1.2)
        pdf = pdfium.PdfDocument(str(ruta_pdf))
        img = pdf[0].render(scale=2.2).to_pil()
        png = SALIDA / "carta_p1.png"
        img.save(png)
        i = cortar_desde()
        b64 = base64.b64encode(png.read_bytes()).decode()
        p.set_content(f"""<!doctype html><html><head><meta name="viewport" content="width=device-width"><style>
            html,body{{margin:0;height:100%;background:#e9e6df;display:grid;place-items:center;overflow:hidden}}
            img{{width:88%;box-shadow:0 20px 50px rgba(0,0,0,.25);border-radius:6px;animation:a .7s cubic-bezier(.2,.8,.2,1) both}}
            @keyframes a{{from{{opacity:0;transform:translateY(40px) scale(.96)}}}}</style></head>
            <body><img src="data:image/png;base64,{b64}"></body></html>""")
        cortar_hasta(i)
        sub("Lista para imprimir, con tus precios al día")
        esperar(3.4)

        # ---------- 4. Cierre ----------
        p.set_content(tarjeta("MiMenú", "Carta digital, página web y código QR<br><b>mimenudigital.divergentstudio.cl</b><br><br>Divergent Studio · Quinta Normal"))
        esperar(3.6)

        (SALIDA / "cortes.json").write_text(__import__("json").dumps(cortes))
        video = p.video.path()
        ctx.close()
        nav.close()
        print("VIDEO", video)


if __name__ == "__main__":
    main()
