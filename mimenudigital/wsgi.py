# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================

import sys
import os

# 1. ESTABLECER VARIABLES DE ENTORNO (¡CRÍTICO! Antes de cualquier import)
# Valores por defecto se dejan como respaldo, pero NUNCA incluir contraseñas en el código.
os.environ.setdefault('MYSQL_HOST', 'MiMenudigital.mysql.pythonanywhere-services.com')
os.environ.setdefault('MYSQL_USER', 'MiMenudigital')
os.environ.setdefault('MYSQL_PASSWORD', '19101810Aa')
os.environ.setdefault('MYSQL_DB', 'MiMenudigital$menu_digital')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('BASE_URL', 'https://mimenudigital.pythonanywhere.com')
os.environ.setdefault('SECRET_KEY', 'super_secreto_produccion_123_cambiar')
os.environ.setdefault('MERCADO_PAGO_ACCESS_TOKEN', 'APP_USR-130838446303286-122321-7a32fce25e8565b16490762a1b0f2254-3090066666')
os.environ.setdefault('MERCADO_PAGO_PUBLIC_KEY', 'APP_USR-56d00f49-c4e2-4b01-8670-d17bf4b841ad')
# Credenciales de Cloudinary (Asegúrate de que esta línea esté ANTES de importar la app)
os.environ['CLOUDINARY_URL'] = 'cloudinary://211225241664362:CV4Q_UfQR9A1GqKUmK02SzE4YiQ@dtrjravmg'

import logging
logger = logging.getLogger(__name__)
logger.info("WSGI variables (password hidden): %s@%s/%s", os.environ.get('MYSQL_USER'), os.environ.get('MYSQL_HOST'), os.environ.get('MYSQL_DB'))

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
