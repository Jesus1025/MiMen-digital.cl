# ============================================================
# WSGI - Menú Digital SaaS (Divergent Studio)
# ============================================================
# Las credenciales NUNCA van en este archivo ni en el repositorio.
# Se leen del entorno o de un archivo .env junto a app_menu.py
# (ver .env.example). El archivo .env está en .gitignore.
# ============================================================

import logging
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.chdir(project_root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    pass

# Proxy opcional (PythonAnywhere free tier lo necesita para salir a internet)
_api_proxy = os.environ.get('API_PROXY')
if _api_proxy:
    for var in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
        os.environ.setdefault(var, _api_proxy)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('wsgi')
logger.info("Menú Digital iniciando (entorno: %s)", os.environ.get('FLASK_ENV', 'development'))

try:
    from app_menu import app as application
except Exception:
    # El detalle del error queda en el log del servidor, nunca en la página pública.
    logger.exception("No se pudo cargar app_menu")
    from flask import Flask
    application = Flask(__name__)

    @application.route('/', defaults={'path': ''})
    @application.route('/<path:path>')
    def error_inicio(path):
        return ("<h1>Servicio no disponible</h1><p>Estamos solucionando un problema. "
                "Vuelve a intentarlo en unos minutos.</p>"), 503
