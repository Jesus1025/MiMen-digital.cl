#!/usr/bin/env python3
from app_menu import app
from pathlib import Path

with app.app_context():
    restaurante = {
        'nombre':'La Casa de Prueba',
        'logo_url':'',
        'slogan':'Sabores que inspiran',
        'direccion':'Calle Falsa 123',
        'telefono':'+56 9 1234 5678',
        'url_slug':'la-casa-de-prueba'
    }
    menu = [
        {'id':1,'nombre':'Entradas','platos':[{'nombre':'Ensalada Fresca','descripcion':'Mezcla de hojas, aderezo especial','precio':3500,'etiquetas':'nuevo,vegano'},{'nombre':'Empanada','descripcion':'Carne y especias','precio':1200,'etiquetas':'popular'}]},
        {'id':2,'nombre':'Platos Fuertes','platos':[{'nombre':'Lomo a lo pobre','descripcion':'Carne, huevo y papas fritas','precio':8500,'etiquetas':''},{'nombre':'Risotto de hongos','descripcion':'A base de hongos seleccionados','precio':7600,'etiquetas':'vegetariano'}]}
    ]
    base_url = 'https://mimenudigital.pythonanywhere.com'
    html = app.jinja_env.get_template('menu_pdf.html').render(restaurante=restaurante, menu=menu, base_url=base_url)
    out = Path('tmp')
    out.mkdir(exist_ok=True)
    (out/'menu_preview.html').write_text(html, encoding='utf-8')
    print('Wrote tmp/menu_preview.html')
