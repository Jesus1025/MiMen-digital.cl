import sqlite3
import json

conn = sqlite3.connect('database/teknetau.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Ver documentos con tipo FAC
cursor.execute('''
    SELECT d.id, d.numero_doc, d.tipo_doc, d.fecha_emision, d.valor_total, 
           d.estado, d.proyecto_codigo, c.razon_social as cliente_nombre
    FROM documentos d
    LEFT JOIN clientes c ON d.cliente_rut = c.rut
    WHERE d.tipo_doc = ?
    ORDER BY d.fecha_emision DESC, d.id DESC
    LIMIT 20
''', ('FAC',))

rows = cursor.fetchall()
print("=== Documentos FAC ===")
if rows:
    for row in rows:
        doc_dict = dict(row)
        print(json.dumps(doc_dict, indent=2, default=str))
else:
    print("No hay documentos FAC")

conn.close()
