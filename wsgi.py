# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE (PRODUCCIÓN)
# ============================================================
# Menú Digital SaaS - Divergent Studio
# Última actualización: Febrero 2026
# ============================================================

import sys
import os

# ============================================================
# 1. CREDENCIALES (¡CRÍTICO! Antes de cualquier import)
# ============================================================
# En PythonAnywhere free tier, las variables de entorno se definen aquí
# porque no hay acceso al panel de Environment Variables.

# --- Base de Datos MySQL ---
os.environ['MYSQL_HOST'] = 'MiMenudigital.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'MiMenudigital'
os.environ['MYSQL_PASSWORD'] = '19101810Aa'
os.environ['MYSQL_DB'] = 'MiMenudigital$menu_digital'
os.environ['MYSQL_PORT'] = '3306'

# --- Configuración de Flask ---
os.environ['FLASK_ENV'] = 'production'
os.environ['BASE_URL'] = 'https://mimenudigital.pythonanywhere.com'

# --- Clave Secreta (para sesiones y CSRF) ---
# ⚠️ IMPORTANTE: Esta clave debe ser única y secreta
os.environ['SECRET_KEY'] = 'a3f8c2e9d4b7a1f6c8e3d2b5a9f7c4e1d8b6a3f9c2e5d7b4a1f8c3e6d9b2a5f7'

# --- Mercado Pago (Pagos Online) ---
os.environ['MERCADO_PAGO_ACCESS_TOKEN'] = 'APP_USR-130838446303286-122321-7a32fce25e8565b16490762a1b0f2254-3090066666'
os.environ['MERCADO_PAGO_PUBLIC_KEY'] = 'APP_USR-56d00f49-c4e2-4b01-8670-d17bf4b841ad'

# --- Cloudinary (Almacenamiento de Imágenes) ---
os.environ['CLOUDINARY_URL'] = 'cloudinary://211225241664362:CV4Q_UfQR9A1GqKUmK02SzE4YiQ@dtrjravmg'

# --- Email (Opcional - Descomenta y configura si lo necesitas) ---
# os.environ['MAIL_USERNAME'] = 'tu_email@gmail.com'
# os.environ['MAIL_PASSWORD'] = 'xxxx xxxx xxxx xxxx'  # Contraseña de aplicación de Gmail
# os.environ['SUPERADMIN_EMAIL'] = 'tu_email@gmail.com'

# --- Sentry (Opcional - Monitoreo de errores) ---
# os.environ['SENTRY_DSN'] = 'https://xxx@xxx.ingest.sentry.io/xxx'

# ============================================================
# 2. PROXY PARA PYTHONANYWHERE FREE TIER
# ============================================================
# El free tier de PythonAnywhere requiere proxy para conexiones externas
# (Cloudinary, Mercado Pago, etc.)

_api_proxy = 'http://proxy.server:3128'
os.environ['API_PROXY'] = _api_proxy
os.environ['HTTP_PROXY'] = _api_proxy
os.environ['HTTPS_PROXY'] = _api_proxy
os.environ['http_proxy'] = _api_proxy
os.environ['https_proxy'] = _api_proxy
os.environ['ALL_PROXY'] = _api_proxy
os.environ['no_proxy'] = 'localhost,127.0.0.1,.pythonanywhere.com'

# ============================================================
# 3. RUTA DEL PROYECTO
# ============================================================
path = '/home/MiMenudigital/MiMen-digital.cl/mimenudigital'
if path not in sys.path:
    sys.path.insert(0, path)

# Cambiar al directorio del proyecto
os.chdir(path)

# ============================================================
# 4. CONFIGURAR LOGGING TEMPRANO
# ============================================================
import logging

# Configurar logging antes de importar la app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('wsgi')

logger.info("=" * 60)
logger.info("🍽️  MENÚ DIGITAL SAAS - Iniciando...")
logger.info("=" * 60)
logger.info("Entorno: %s", os.environ.get('FLASK_ENV'))
logger.info("Base URL: %s", os.environ.get('BASE_URL'))
logger.info("MySQL: %s@%s", os.environ.get('MYSQL_USER'), os.environ.get('MYSQL_HOST'))
logger.info("Proxy: %s", _api_proxy)
logger.info("=" * 60)

# ============================================================
# 5. IMPORTAR LA APLICACIÓN FLASK
# ============================================================
try:
    from app_menu import app as application
    
    # Configuración adicional de producción
    application.config['PROPAGATE_EXCEPTIONS'] = True
    
    logger.info("✅ Aplicación cargada correctamente")
    logger.info("✅ Cloudinary configurado: %s", bool(os.environ.get('CLOUDINARY_URL')))
    logger.info("✅ Mercado Pago configurado: %s", bool(os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')))
    
except Exception as e:
    import traceback
    from flask import Flask
    
    # Crear app de emergencia que muestra el error
    application = Flask(__name__)
    error_msg = f"Error importando app_menu: {str(e)}\n{traceback.format_exc()}"
    logger.error("❌ ERROR CRÍTICO: %s", error_msg)
    
    @application.route('/')
    def error():
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error de Servidor</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }}
                .error-box {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 800px; margin: 0 auto; }}
                h1 {{ color: #e74c3c; }}
                pre {{ background: #2c3e50; color: #ecf0f1; padding: 20px; border-radius: 5px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <h1>⚠️ Error de Inicialización</h1>
                <p>La aplicación no pudo inicializarse correctamente.</p>
                <pre>{error_msg}</pre>
                <p><strong>Posibles causas:</strong></p>
                <ul>
                    <li>Dependencias faltantes (pip install -r requirements.txt)</li>
                    <li>Error de sintaxis en el código</li>
                    <li>Variables de entorno incorrectas</li>
                    <li>Problema de conexión a la base de datos</li>
                </ul>
            </div>
        </body>
        </html>
        """, 500
    
    @application.route('/health')
    def health():
        return {'status': 'error', 'message': str(e)}, 500
