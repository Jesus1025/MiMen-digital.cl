import sqlite3

conn = sqlite3.connect('database/teknetau.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Ver estructura de tabla documentos
cursor.execute("PRAGMA table_info(documentos)")
print("=== Estructura tabla 'documentos' ===")
for row in cursor.fetchall():
    print(f"{row[1]}: {row[2]}")

# Ver documentos en la BD
print("\n=== Documentos en la BD ===")
cursor.execute("SELECT * FROM documentos LIMIT 5")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(dict(row))
else:
    print("No hay documentos")

# Ver clientes
print("\n=== Clientes en la BD ===")
cursor.execute("SELECT * FROM clientes LIMIT 3")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(dict(row))
else:
    print("No hay clientes")

# Ver proyectos
print("\n=== Proyectos en la BD ===")
cursor.execute("SELECT * FROM proyectos LIMIT 3")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(dict(row))
else:
    print("No hay proyectos")

conn.close()
