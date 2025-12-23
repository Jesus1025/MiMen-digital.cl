import requests
import json

# Hacer login primero
session = requests.Session()
response = session.post('http://127.0.0.1:5000/login', data={
    'username': 'admin',
    'password': 'admin123'
})
print(f"Login: {response.status_code}")

# Probar API de ultimos documentos
response = session.get('http://127.0.0.1:5000/api/ultimos-documentos/FAC')
print(f"API Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    print(f"\nDocumentos: {json.dumps(data, indent=2)}")
