# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================

import sys
import os

# 1. ESTABLECER VARIABLES DE ENTORNO (¡CRÍTICO! Antes de cualquier import)
# Valores por defecto se dejan como respaldo, pero NUNCA incluir contraseñas en el código.
os.environ.setdefault('MYSQL_HOST', 'MiMenudigital.mysql.pythonanywhere-services.com')
os.environ.setdefault('MYSQL_USER', 'MiMenudigital')
# NO establecer MYSQL_PASSWORD en el repositorio; configúralo en el entorno seguro del hosting.
# os.environ.setdefault('MYSQL_PASSWORD', '')
os.environ.setdefault('MYSQL_DB', 'MiMenudigital$menu_digital')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('BASE_URL', 'https://mimenudigital.pythonanywhere.com')

import logging
logger = logging.getLogger(__name__)
logger.info("WSGI variables (password hidden): %s@%s/%s", os.environ.get('MYSQL_USER'), os.environ.get('MYSQL_HOST'), os.environ.get('MYSQL_DB'))

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
    logger.error("ERROR: %s", error_msg)
    
    @application.route('/')
    def error():
        return f"<pre>Import Error:\n{error_msg}</pre>", 500
