# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================
# PythonAnywhere - Producción
# Las variables de entorno se configuran en:
# Web -> Environment variables
# ============================================================

import sys
import os

# 1. AÑADIR RUTA DEL PROYECTO
path = '/home/Jesus1025/MiMen-digital.cl'
if path not in sys.path:
    sys.path.insert(0, path)

# 2. CARGAR VARIABLES DE ENTORNO
# En desarrollo, cargar desde .env si existe
# En producción (PythonAnywhere), las variables ya están en os.environ
try:
    from dotenv import load_dotenv
    env_file = os.path.join(path, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
except ImportError:
    pass
except Exception:
    pass

# FALLBACK TEMPORAL: Si las variables no están en el panel de PA, establecerlas aquí
# (NOTA: Esta es una solución temporal - en producción estas variables deberían estar en el panel)
os.environ.setdefault('MYSQL_HOST', 'MiMenudigital.mysql.pythonanywhere-services.com')
os.environ.setdefault('MYSQL_USER', 'MiMenudigital')
os.environ.setdefault('MYSQL_PASSWORD', '19101810Aa')
os.environ.setdefault('MYSQL_DB', 'MiMenudigital$menu_digital')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('BASE_URL', 'https://mimenudigital.pythonanywhere.com')

# 3. VALIDAR Y MOSTRAR VARIABLES DE ENTORNO
# Debug: mostrar qué variables tiene PythonAnywhere
print("=" * 60)
print("WSGI DEBUG - Checking environment variables:")
print(f"  MYSQL_HOST: {os.environ.get('MYSQL_HOST', 'NOT SET')}")
print(f"  MYSQL_USER: {os.environ.get('MYSQL_USER', 'NOT SET')}")
print(f"  MYSQL_DB: {os.environ.get('MYSQL_DB', 'NOT SET')}")
print(f"  FLASK_ENV: {os.environ.get('FLASK_ENV', 'NOT SET')}")
print("=" * 60)

# 4. IMPORTAR LA APP
try:
    from app_menu import app as application
except ImportError as e:
    # Si falla, crear una app dummy que muestre el error
    import traceback
    from flask import Flask
    application = Flask(__name__)
    
    error_msg = f"Error importando app_menu: {str(e)}\n{traceback.format_exc()}"
    print(f"ERROR: {error_msg}")
    
    @application.route('/')
    def error():
        return f"<pre>Import Error:\n{error_msg}</pre>", 500
