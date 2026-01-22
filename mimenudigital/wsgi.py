# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================
# IMPORTANTE: Las credenciales sensibles deben configurarse en:
# PythonAnywhere → Web → WSGI configuration file (al inicio)
# O en un archivo .env que NO se suba a Git
# ============================================================

import sys
import os

# 1. ESTABLECER VARIABLES DE ENTORNO NO SENSIBLES
os.environ.setdefault('MYSQL_HOST', 'MiMenudigital.mysql.pythonanywhere-services.com')
os.environ.setdefault('MYSQL_USER', 'MiMenudigital')
os.environ.setdefault('MYSQL_DB', 'MiMenudigital$menu_digital')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('BASE_URL', 'https://mimenudigital.pythonanywhere.com')

# API_PROXY para cuentas gratuitas de PythonAnywhere
os.environ.setdefault('API_PROXY', 'http://proxy.server:3128')

# ============================================================
# ⚠️ CREDENCIALES SENSIBLES - NO SUBIR A GIT
# ============================================================
# Configura estas variables en PythonAnywhere:
# Web → Files → Edita el archivo wsgi que está en /var/www/
# Y añade ANTES de este archivo:
#
# os.environ['MYSQL_PASSWORD'] = 'tu_password_mysql'
# os.environ['SECRET_KEY'] = 'genera_con_secrets.token_hex(32)'
# os.environ['MERCADO_PAGO_ACCESS_TOKEN'] = 'APP_USR-xxx'
# os.environ['MERCADO_PAGO_PUBLIC_KEY'] = 'APP_USR-xxx'
# os.environ['CLOUDINARY_URL'] = 'cloudinary://api_key:api_secret@cloud_name'
# ============================================================

# Verificar que las credenciales críticas estén configuradas
_missing_vars = []
if not os.environ.get('MYSQL_PASSWORD'):
    _missing_vars.append('MYSQL_PASSWORD')
if not os.environ.get('SECRET_KEY'):
    _missing_vars.append('SECRET_KEY')
if not os.environ.get('CLOUDINARY_URL'):
    _missing_vars.append('CLOUDINARY_URL')

if _missing_vars and os.environ.get('FLASK_ENV') == 'production':
    import logging
    logging.warning("⚠️ CREDENCIALES FALTANTES: %s - Configúralas en PythonAnywhere", ', '.join(_missing_vars))

import logging
logger = logging.getLogger(__name__)
logger.info("WSGI initialized: %s@%s/%s", os.environ.get('MYSQL_USER'), os.environ.get('MYSQL_HOST'), os.environ.get('MYSQL_DB'))

# 2. AÑADIR RUTA DEL PROYECTO
# CORRECCIÓN: Tu código está dentro de la carpeta 'mimenudigital'
path = '/home/MiMenudigital/MiMen-digital.cl/mimenudigital'
if path not in sys.path:
    sys.path.insert(0, path)

# Cambiar al directorio de trabajo para que Flask encuentre las carpetas static/templates
os.chdir(path)

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
except Exception as e:
    import traceback
    from flask import Flask
    application = Flask(__name__)
    error_msg = f"Error importando app_menu: {str(e)}\n{traceback.format_exc()}"
    logger.error("ERROR: %s", error_msg)
    @application.route('/')
    def error():
        return f"<pre>Import Error:\n{error_msg}</pre>", 500
