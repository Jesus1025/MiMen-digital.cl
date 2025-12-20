import urllib.request, urllib.parse, http.cookiejar, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login with default admin/admin123
login_data = urllib.parse.urlencode({'username':'admin', 'password':'admin123'}).encode()
req = urllib.request.Request('http://127.0.0.1:5000/login', data=login_data)
resp = opener.open(req)
print('login status', resp.getcode())

# Now POST to API with JSON
client = {'rut':'99999999-9','razon_social':'HTTP Cliente','giro':'Prueba','direccion':'Calle 2','comuna':'Prueba','telefono':'+569','email':'http@test'}
req2 = urllib.request.Request('http://127.0.0.1:5000/api/clientes', data=json.dumps(client).encode('utf-8'), headers={'Content-Type':'application/json'})
resp2 = opener.open(req2)
print('api status', resp2.getcode())
print(resp2.read().decode('utf-8'))
