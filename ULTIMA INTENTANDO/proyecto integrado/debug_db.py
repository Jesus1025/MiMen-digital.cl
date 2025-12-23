import sqlite3
import json

conn = sqlite3.connect('database/teknetau.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Ver todos los documentos
cursor.execute('SELECT id, numero_doc, tipo_doc, fecha_emision, valor_total, estado, proyecto_codigo FROM documentos ORDER BY id DESC')
print('=== TODOS LOS DOCUMENTOS ===')
for row in cursor.fetchall():
    print(dict(row))

# Ver proyectos
print('\n=== PROYECTOS ===')
cursor.execute('SELECT codigo, nombre, presupuesto FROM proyectos')
for row in cursor.fetchall():
    print(dict(row))

conn.close()
