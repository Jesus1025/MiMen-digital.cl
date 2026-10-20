"""Cookie de sesión de solo lectura para el panel del local de ejemplo (sin usuario propio).
Solo para capturas en la copia local. Uso (venv de la app): python sesion_ejemplo.py"""
import wsgi
from database import get_db

app = wsgi.application
with app.app_context():
    cur = get_db().cursor()
    cur.execute("SELECT id, nombre, url_slug FROM restaurantes WHERE url_slug = 'ejemplo'")
    r = cur.fetchone()
datos = {"user_id": 0, "username": "demo", "nombre": "Brasa & Pan", "rol": "admin",
         "restaurante_id": r["id"], "restaurante_nombre": r["nombre"], "url_slug": r["url_slug"]}
print(app.session_interface.get_signing_serializer(app).dumps(datos))
