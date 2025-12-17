import urllib.request, json

data = {
    'rut': '99999999-9',
    'razon_social': 'Test Cliente',
    'giro': 'Prueba',
    'direccion': 'Calle 1',
    'comuna': 'Prueba',
    'telefono': '+569',
    'email': 'test@local'
}

req = urllib.request.Request('http://127.0.0.1:5000/api/clientes', data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as res:
    print(res.status)
    print(res.read().decode('utf-8'))
