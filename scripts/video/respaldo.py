"""Guarda y restaura lo que el video del dueño cambia en un local (horario, platos pausados y precios).
Uso (venv de la app): python respaldo.py guardar|restaurar <url_slug> <archivo.json>"""
import json
import sys

import wsgi
from database import get_db

accion, slug, archivo = sys.argv[1], sys.argv[2], sys.argv[3]
app = wsgi.application
with app.app_context():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, horario FROM restaurantes WHERE url_slug = %s", (slug,))
    r = cur.fetchone()
    if accion == "guardar":
        cur.execute("SELECT id, precio, activo FROM platos WHERE restaurante_id = %s", (r["id"],))
        datos = {"horario": r["horario"], "platos": [[p["id"], str(p["precio"]), p["activo"]] for p in cur.fetchall()]}
        open(archivo, "w", encoding="utf8").write(json.dumps(datos))
        print("respaldo guardado:", len(datos["platos"]), "platos")
    else:
        datos = json.loads(open(archivo, encoding="utf8").read())
        cur.execute("UPDATE restaurantes SET horario = %s WHERE id = %s", (datos["horario"], r["id"]))
        for pid, precio, activo in datos["platos"]:
            cur.execute("UPDATE platos SET precio = %s, activo = %s WHERE id = %s AND restaurante_id = %s",
                        (precio, activo, pid, r["id"]))
        db.commit()
        try:
            from app_menu import invalidar_cache_restaurante
            invalidar_cache_restaurante(r["id"])
        except Exception:
            pass
        print("respaldo restaurado:", len(datos["platos"]), "platos y horario")
