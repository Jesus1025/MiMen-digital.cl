"""Capturas del local de ejemplo (Brasa & Pan) para el catálogo de WhatsApp de MiMenú.
Usa la copia local de la app (127.0.0.1:8099, FLASK_ENV=development); el panel se abre con una sesión
de solo lectura del local de ejemplo (cookie firmada, sin contraseña). No guarda nada.
Uso: video-venv/bin/python capturas.py <carpeta> <cookie_panel>"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8099"
OUT = Path(sys.argv[1])
COOKIE = sys.argv[2]
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as pw:
    nav = pw.chromium.launch(args=["--lang=es-CL"])
    ctx = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True,
                          has_touch=True, locale="es-CL", timezone_id="America/Santiago")
    p = ctx.new_page()

    def foto(nombre, espera=600):
        p.wait_for_timeout(espera)
        p.screenshot(path=str(OUT / f"{nombre}.png"))

    # Carta del cliente
    p.goto(BASE + "/menu/ejemplo?refresh=1", wait_until="networkidle")
    p.evaluate("localStorage.clear()")
    p.reload(wait_until="networkidle")
    foto("carta_portada", 900)
    p.evaluate("window.scrollTo(0, document.querySelector('.seccion').offsetTop - 60)")
    foto("carta_lista", 900)

    # Pedido con notas
    controles = p.locator("[data-control] ")
    nombres = p.eval_on_selector_all("[data-control]", "els => els.map(e => e.dataset.nombre)")
    for n in nombres[:3]:
        p.locator(f'[data-control][data-nombre="{n}"] [data-mas]').first.click()
        p.wait_for_timeout(250)
    p.locator(f'[data-control][data-nombre="{nombres[0]}"] [data-mas]').first.click()
    p.wait_for_timeout(500)
    p.locator("#barraPedido").click()
    p.wait_for_timeout(700)
    notas = p.locator("#pedidoItems .nota")
    notas.nth(0).fill("sin cebolla")
    notas.nth(0).dispatch_event("input")
    foto("pedido", 700)
    p.locator("#pedidoMostrar").click()
    foto("mostrar", 800)
    p.locator("#mostrarCerrar").click()

    # Página del local
    p.goto(BASE + "/local/ejemplo", wait_until="networkidle")
    p.add_style_tag(content=".rev{opacity:1!important;transform:none!important;transition:none!important}")
    foto("local", 1200)

    # Panel (solo lectura)
    ctx.add_cookies([{"name": "session", "value": COOKIE, "url": BASE}])
    p.goto(BASE + "/gestion/platos", wait_until="networkidle")
    foto("panel_platos", 900)
    p.locator(".btn-accion-editar").first.click()
    foto("panel_editar", 900)
    p.goto(BASE + "/gestion/codigo-qr", wait_until="networkidle")
    foto("panel_qr", 900)
    nav.close()
print("capturas listas en", OUT)
