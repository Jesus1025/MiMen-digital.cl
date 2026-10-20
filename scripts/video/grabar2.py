"""Graba la pantalla del celular para los videos de MiMenú y anota cuándo cambia cada título.

Dos guiones: "cliente" (cómo ve la carta un comensal) y "dueno" (cómo se maneja el panel).
Graba una copia local de la app (127.0.0.1:8099, arrancada con FLASK_ENV=development para que funcione sin https).
La sesión del dueño llega como cookie firmada (sesion.py): no se usa ninguna contraseña.
Todo lo que el guion del dueño cambia se revierte por base de datos al terminar (lo hace hacer_videos.sh).

Uso: video-venv/bin/python grabar2.py <cliente|dueno> <carpeta_salida> [cookie_session]
Deja en la carpeta: pantalla.webm y guion.json (títulos con su segundo y tramos a cortar).
"""
import base64
import json
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8099"
MODO = sys.argv[1]
SALIDA = Path(sys.argv[2])
COOKIE = sys.argv[3] if len(sys.argv) > 3 else ""
SALIDA.mkdir(parents=True, exist_ok=True)

DEDO = """
(() => {
  const css = `#__dedo{position:fixed;z-index:2147483647;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;
     background:rgba(255,255,255,.5);border:3px solid rgba(25,25,25,.5);box-shadow:0 4px 16px rgba(0,0,0,.3);
     pointer-events:none;transition:left .5s cubic-bezier(.3,.8,.3,1),top .5s cubic-bezier(.3,.8,.3,1),transform .15s,opacity .3s;opacity:0}
   #__dedo.toca{transform:scale(.7);background:rgba(255,255,255,.85)}`;
  const poner = () => {
    if (document.getElementById('__dedo') || !document.body) return;
    const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
    const d = document.createElement('div'); d.id = '__dedo'; document.body.appendChild(d);
  };
  document.addEventListener('DOMContentLoaded', poner); poner();
  window.__mover = (x, y) => { poner(); const d = document.getElementById('__dedo'); d.style.opacity = 1; d.style.left = x + 'px'; d.style.top = y + 'px'; };
  window.__tocar = () => { const d = document.getElementById('__dedo'); d.classList.add('toca'); setTimeout(() => d.classList.remove('toca'), 180); };
  window.__ocultar = () => { const d = document.getElementById('__dedo'); if (d) d.style.opacity = 0; };
})();
"""


def main():
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=["--lang=es-CL"])
        ctx = nav.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
            locale="es-CL", timezone_id="America/Santiago", accept_downloads=True,
        )
        ctx.add_init_script(DEDO)
        if COOKIE:
            ctx.add_cookies([{"name": "session", "value": COOKIE, "url": BASE}])
        p = ctx.new_page()
        # Cuadros a resolución real (780x1688): la grabación de video de Playwright solo graba a 390 px de ancho
        cuadros = SALIDA / "cuadros"
        cuadros.mkdir(exist_ok=True)
        lista_cuadros = []
        cdp = ctx.new_cdp_session(p)

        def cuadro(ev):
            n = len(lista_cuadros)
            (cuadros / f"{n:06d}.jpg").write_bytes(base64.b64decode(ev["data"]))
            lista_cuadros.append(ev["metadata"]["timestamp"])
            cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

        cdp.on("Page.screencastFrame", cuadro)
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 780, "maxHeight": 1688, "everyNthFrame": 1})
        t0_epoch = time.time()
        t0 = time.monotonic()
        guion = {"titulos": [], "cortes": []}

        def ahora():
            return time.monotonic() - t0

        def titulo(texto, bajada=""):
            guion["titulos"].append([ahora(), texto, bajada])

        def esperar(s):
            p.wait_for_timeout(int(s * 1000))

        def abrir(url, limpiar=False):
            i = ahora()
            p.goto(url, wait_until="networkidle")
            if limpiar:
                p.evaluate("localStorage.clear()")
                p.reload(wait_until="networkidle")
            esperar(0.35)
            guion["cortes"].append([i, ahora()])

        def tocar(loc, pausa=0.8):
            loc.scroll_into_view_if_needed()
            esperar(0.3)
            c = loc.bounding_box()
            p.evaluate("([x, y]) => window.__mover(x, y)", [c["x"] + c["width"] / 2, c["y"] + c["height"] / 2])
            esperar(0.6)
            p.evaluate("window.__tocar()")
            loc.click()
            esperar(pausa)

        def escribir(loc, texto, borrar=False):
            tocar(loc, 0.35)
            if borrar:
                loc.fill("")
                esperar(0.25)
            loc.press_sequentially(texto, delay=110)
            esperar(0.6)

        def deslizar(px, pasos=14):
            p.evaluate("window.__ocultar && window.__ocultar()")
            for _ in range(pasos):
                p.mouse.wheel(0, px / pasos)
                esperar(0.06)
            esperar(0.5)

        def ir_a(seccion):
            p.evaluate("""t => { const h = [...document.querySelectorAll('.seccion h2')].find(e => e.textContent.trim().startsWith(t));
                          if (h) window.scrollTo({top: h.getBoundingClientRect().top + scrollY - 70, behavior: 'smooth'}); }""", seccion)
            esperar(1.3)

        def agregar(nombre):
            return p.locator(f'[data-control][data-nombre="{nombre}"] [data-mas]')

        if MODO == "cliente":
            abrir(BASE + "/menu/lacomarca?refresh=1", limpiar=True)
            titulo("Escanean el QR de la mesa", "y ven tu carta al instante")
            esperar(2.4)
            deslizar(260)
            titulo("Con fotos de verdad", "y lo más pedido arriba")
            p.evaluate("document.querySelector('.carrusel').scrollBy({left: 520, behavior: 'smooth'})")
            esperar(2.4)
            titulo("Buscan por categoría", "sin perderse en la carta")
            tocar(p.locator('.cat[data-id="cat-2"]'), 1.6)
            titulo("Tocan un plato", "y lo ven en grande")
            tocar(p.locator(".plato", has=p.locator(".nombre", has_text="Churrasco italiano")).first, 2.2)
            tocar(p.locator("#fichaMas"), 0.7)
            titulo("Arman su pedido", "y ven el total al tiro")
            tocar(p.locator("#fichaAgregar"), 1.2)
            ir_a("Completos")
            titulo("¿Sin mayo? Lo anotan", "cada producto lleva su nota")
            tocar(p.locator(".plato", has=p.locator(".nombre", has_text="Completo")).first, 1.3)
            escribir(p.locator("#fichaNota"), "sin mayo")
            tocar(p.locator("#fichaAgregar"), 1.0)
            ir_a("Bebidas")
            tocar(agregar("Bebida en lata"), 1.0)
            titulo("Revisan su pedido", "con el total exacto")
            tocar(p.locator("#barraPedido"), 1.8)
            titulo("Eligen su bebida", "nada de “una bebida cualquiera”")
            escribir(p.locator('#pedidoItems .nota[aria-label="Nota para Bebida en lata"]'), "Coca-Cola")
            esperar(0.8)
            titulo("Y se lo muestran a quien atiende", "o lo envían por WhatsApp")
            tocar(p.locator("#pedidoMostrar"), 4.2)

        else:
            abrir(BASE + "/gestion")
            titulo("Tu panel, en tu celular", "todo se maneja desde aquí")
            esperar(2.6)
            abrir(BASE + "/gestion/platos")
            titulo("¿Se acabó un producto?", "lo pausas con un toque")
            escribir(p.locator("#buscarPlato"), "Chorrillana veg")
            esperar(0.4)
            tocar(p.locator(".plato-estado").first, 1.8)
            abrir(BASE + "/menu/lacomarca?refresh=1", limpiar=True)
            titulo("Y sale de la carta al instante", "sin llamar a nadie")
            ir_a("Chorrillanas")
            esperar(2.2)
            abrir(BASE + "/gestion/platos")
            titulo("¿Subiste un precio?", "lo cambias en segundos")
            escribir(p.locator("#buscarPlato"), "Churrasco ital")
            esperar(0.4)
            tocar(p.locator(".btn-accion-editar").first, 1.3)
            escribir(p.locator("#platoPrecio"), "3500", borrar=True)
            tocar(p.locator('.modal-overlay.active .btn-primary[onclick="guardarPlato()"]'), 1.5)
            abrir(BASE + "/menu/lacomarca?refresh=1", limpiar=True)
            titulo("Tu carta ya muestra el nuevo precio", "en todos los celulares")
            ir_a("Churrascos")
            esperar(2.4)
            abrir(BASE + "/gestion/mi-restaurante")
            titulo("¿Abres el sábado?", "cambias tu horario")
            p.evaluate("window.__ocultar && window.__ocultar()")
            sab = p.locator('.horario-dia[data-dia="sabado"]')
            sab.scroll_into_view_if_needed()
            p.evaluate("window.scrollBy(0, 120)")
            esperar(0.8)
            tocar(sab.locator(".horario-toggle-slider"), 0.9)
            for clase, hora in ((".hora-apertura", "10:00"), (".hora-cierre", "14:00")):
                campo = sab.locator(clase)
                tocar(campo, 0.3)
                campo.fill(hora)
                esperar(0.6)
            esperar(0.8)
            tocar(p.locator('#formRestaurante button[type="submit"]').first, 1.8)
            abrir(BASE + "/gestion/mi-pagina")
            titulo("Editas tu página web", "fotos, textos y lo que ofreces")
            deslizar(650)
            esperar(0.8)
            deslizar(650)
            esperar(1.0)
            abrir(BASE + "/gestion/codigo-qr")
            titulo("Tu código QR, listo", "para imprimir y poner en las mesas")
            esperar(2.6)
            abrir(BASE + "/gestion/descargas")
            titulo("¿Clientes sin celular?", "descargas tu carta en PDF")
            with p.expect_download(timeout=60000) as d:
                tocar(p.locator("#btn-download-pdf"), 0.6)
                i = ahora()
            pdf = SALIDA / "carta.pdf"
            d.value.save_as(pdf)
            import pypdfium2 as pdfium
            img = pdfium.PdfDocument(str(pdf))[0].render(scale=2).to_pil()
            png = SALIDA / "carta.png"
            img.save(png)
            b64 = base64.b64encode(png.read_bytes()).decode()
            p.set_content(f"""<!doctype html><html><head><meta name="viewport" content="width=device-width"><style>
                html,body{{margin:0;height:100%;background:#e9e6df;overflow:hidden;display:grid;place-items:center}}
                img{{display:block;width:94%;max-height:92vh;object-fit:contain;box-shadow:0 18px 44px rgba(0,0,0,.25);border-radius:6px;
                     animation:a .8s cubic-bezier(.2,.8,.2,1) both}}
                @keyframes a{{from{{opacity:0;transform:translateY(40px) scale(.96)}}}}</style></head>
                <body><img src="data:image/png;base64,{b64}"></body></html>""")
            guion["cortes"].append([i, ahora()])
            titulo("Lista para imprimir", "con tus precios siempre al día")
            esperar(4.2)

        guion["fin"] = ahora()
        esperar(0.3)
        cdp.send("Page.stopScreencast")
        ctx.close()
        nav.close()
        # Video a 30 fps desde los cuadros: cada cuadro dura hasta que llega el siguiente
        tiempos = [t - t0_epoch for t in lista_cuadros]
        with open(SALIDA / "cuadros.txt", "w") as f:
            for n, t in enumerate(tiempos):
                sig = tiempos[n + 1] if n + 1 < len(tiempos) else guion["fin"]
                if n == 0 and t > 0:
                    t = 0.0
                f.write(f"file 'cuadros/{n:06d}.jpg'\nduration {max(sig - t, 0.001):.4f}\n")
            f.write(f"file 'cuadros/{len(tiempos) - 1:06d}.jpg'\n")
        import subprocess
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(SALIDA / "cuadros.txt"),
                        "-vf", "fps=30,scale=780:1688:force_original_aspect_ratio=decrease,pad=780:1688:0:0:color=white,format=yuv420p",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "16", str(SALIDA / "pantalla.mp4")], check=True, cwd=SALIDA)
        shutil.rmtree(cuadros)
        (SALIDA / "guion.json").write_text(json.dumps(guion, ensure_ascii=False, indent=1))
        print("OK", MODO, f"{guion['fin']:.1f}s", len(guion["titulos"]), "títulos")


if __name__ == "__main__":
    main()
