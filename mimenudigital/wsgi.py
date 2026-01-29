# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE (PLAN GRATUITO)
# ============================================================
# INSTRUCCIONES PARA PLAN GRATUITO (sin variables de entorno):
# 
# 1. En PythonAnywhere ve a: Web → Código → WSGI configuration file
# 2. Al INICIO del archivo (antes de todo), pega estas líneas
#    con TUS valores reales:
# 
# import os
# os.environ['MYSQL_PASSWORD'] = 'tu_password_mysql_aqui'
# os.environ['SECRET_KEY'] = 'tu_clave_secreta_segura_aqui_minimo_32_caracteres'
# os.environ['CLOUDINARY_URL'] = 'cloudinary://tu_api_key:tu_api_secret@tu_cloud_name'
# os.environ['MERCADO_PAGO_ACCESS_TOKEN'] = 'tu_access_token_aqui'
# os.environ['MERCADO_PAGO_PUBLIC_KEY'] = 'tu_public_key_aqui'
#
# 3. Guarda y recarga la aplicación
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

# ============================================================
# PROXY PARA PYTHONANYWHERE FREE TIER - CRÍTICO
# Debe configurarse ANTES de importar cualquier librería HTTP
# ============================================================
_api_proxy = 'http://proxy.server:3128'
os.environ['API_PROXY'] = _api_proxy
os.environ['HTTP_PROXY'] = _api_proxy
os.environ['HTTPS_PROXY'] = _api_proxy
os.environ['http_proxy'] = _api_proxy
os.environ['https_proxy'] = _api_proxy
os.environ['ALL_PROXY'] = _api_proxy
os.environ['no_proxy'] = ''  # No excluir ningún dominio del proxy

# ============================================================
# ⚠️ CREDENCIALES - VER INSTRUCCIONES ARRIBA
# ============================================================
# Las credenciales se configuran AL INICIO del archivo WSGI
# en PythonAnywhere (Web → WSGI configuration file)
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
