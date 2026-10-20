"""Imprime una cookie de sesión firmada del dueño de un local, para grabar el panel en la copia local.
No usa contraseñas. Uso (en blackout, con el venv de la app): venv/bin/python scripts/video/sesion.py lacomarca"""
import sys

import wsgi
from database import get_db

app = wsgi.application
slug = sys.argv[1]
with app.app_context():
    cur = get_db().cursor()
    cur.execute("""SELECT u.id, u.username, u.nombre, u.rol, u.restaurante_id, r.nombre AS rn, r.url_slug
                   FROM usuarios_admin u JOIN restaurantes r ON r.id = u.restaurante_id
                   WHERE r.url_slug = %s AND u.activo = 1 AND u.rol <> 'superadmin' ORDER BY u.id LIMIT 1""", (slug,))
    u = cur.fetchone()
datos = {"user_id": u["id"], "username": u["username"], "nombre": u["nombre"], "rol": u["rol"],
         "restaurante_id": u["restaurante_id"], "restaurante_nombre": u["rn"], "url_slug": u["url_slug"]}
print(app.session_interface.get_signing_serializer(app).dumps(datos))
