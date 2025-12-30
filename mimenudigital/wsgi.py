# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================

import sys
import os

# 1. ESTABLECER VARIABLES DE ENTORNO (¡CRÍTICO! Antes de cualquier import)
os.environ['MYSQL_HOST'] = 'MiMenudigital.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'MiMenudigital'
os.environ['MYSQL_PASSWORD'] = '19101810Aa'
os.environ['MYSQL_DB'] = 'MiMenudigital$menu_digital'
os.environ['MYSQL_PORT'] = '3306'
os.environ['FLASK_ENV'] = 'production'
os.environ['BASE_URL'] = 'https://mimenudigital.pythonanywhere.com'

print("=" * 70)
print("WSGI - Variables establecidas:")
print(f"  MYSQL_HOST = {os.environ['MYSQL_HOST']}")
print(f"  MYSQL_USER = {os.environ['MYSQL_USER']}")
print(f"  MYSQL_DB = {os.environ['MYSQL_DB']}")
print("=" * 70)

# 2. AÑADIR RUTA DEL PROYECTO
path = '/home/MiMenudigital/MiMen-digital.cl'
if path not in sys.path:
    sys.path.insert(0, path)

# 3. CARGAR .env si existe (desarrollo)
try:
    from dotenv import load_dotenv
    env_file = os.path.join(path, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
except ImportError:
    pass
except Exception:
    pass

# 4. IMPORTAR LA APP
try:
    from app_menu import app as application
except ImportError as e:
    import traceback
    from flask import Flask
    application = Flask(__name__)
    
    error_msg = f"Error importando app_menu: {str(e)}\n{traceback.format_exc()}"
    print(f"ERROR: {error_msg}")
    
    @application.route('/')
    def error():
        return f"<pre>Import Error:\n{error_msg}</pre>", 500
