import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_menu import app

c = app.test_client()
print('GET / ->', c.get('/').status_code)
print('GET /login ->', c.get('/login').status_code)
print('login contains (Iniciar):', b'Iniciar' in c.get('/login').data)
print('GET /una-ruta-que-no-existe ->', c.get('/una-ruta-que-no-existe').status_code)
body_404 = c.get('/una-ruta-que-no-existe').data.decode('utf-8', errors='ignore')
print("404 contains (Página no encontrada):", 'Página no encontrada' in body_404)
print('GET /api/health ->', c.get('/api/health').status_code)
print('api/health json keys:', list(c.get('/api/health').get_json().keys()))
