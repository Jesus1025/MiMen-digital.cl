# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================
# COPIA ESTE CONTENIDO AL ARCHIVO WSGI DE PYTHONANYWHERE
# En el dashboard Web -> pestaña WSGI configuration file
# ============================================================


import sys
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Optional: use python-dotenv locally for convenience (don't commit .env)
    from dotenv import load_dotenv
    base = os.path.dirname(__file__)
    env_local = os.path.join(base, '.env.local')
    env_file = os.path.join(base, '.env')
    # Prefer .env.local for development convenience (it's gitignored)
    if os.path.exists(env_local):
        load_dotenv(env_local)
        logger.info("Loaded environment variables from .env.local")
    elif os.path.exists(env_file):
        load_dotenv(env_file)
        logger.info("Loaded environment variables from .env")
except Exception as e:
    # dotenv is optional; in production you should set real ENV vars
    logger.warning(f"Could not load .env file: {e}")

# ============================================================
# RUTA DEL PROYECTO - AJUSTAR SEGÚN TU ESTRUCTURA
# ============================================================
def find_project_home():
    """Localiza el directorio del proyecto de forma dinámica."""
    home = os.path.expanduser('~')
    candidates = [
        os.path.join(home, 'MiMen-digital.cl'),
        os.path.join(home, 'MiMen-digital.cl', 'mimenudigital'),
        os.path.join(home, 'MiMen-digital.cl', 'mimenúdigital'),
        os.path.join(home, 'MiMen-digital.cl', 'MiMen-digital.cl'),
    ]

    for candidate in candidates:
        if os.path.isdir(candidate) and 'app_menu.py' in os.listdir(candidate):
            logger.info(f"Found project home: {candidate}")
            return candidate

    # Fallback: scan home for a directory containing app_menu.py
    try:
        for entry in os.listdir(home):
            full = os.path.join(home, entry)
            if os.path.isdir(full):
                try:
                    if 'app_menu.py' in os.listdir(full):
                        logger.info(f"Found project home (fallback scan): {full}")
                        return full
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError) as e:
        logger.warning(f"Could not scan home directory: {e}")

    # Last resort: use current directory
    cwd = os.getcwd()
    logger.info(f"Using current working directory: {cwd}")
    return cwd

project_home = find_project_home()

if project_home not in sys.path:
    sys.path.insert(0, project_home)
    logger.info(f"Added {project_home} to sys.path")

try:
    os.chdir(project_home)
    logger.info(f"Changed working directory to {project_home}")
except (OSError, IOError) as e:
    logger.error(f"Could not change directory to {project_home}: {e}")

# ============================================================
# VARIABLES DE ENTORNO - CONFIGURACIÓN
# ============================================================
# Runtime environment: prefer to read from real environment variables.
# DO NOT commit secrets to the repository. Set these in PythonAnywhere
# Web -> Environment variables, or create a local `.env` (gitignored).

def validate_environment():
    """Valida que las variables de entorno críticas estén configuradas."""
    flask_env = os.environ.get('FLASK_ENV', 'production')
    logger.info(f"Flask environment: {flask_env}")
    
    if flask_env == 'production':
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key or secret_key == 'please-set-a-secret-key-in-your-env':
            logger.warning("SECRET_KEY not properly configured in production!")

os.environ.setdefault('FLASK_ENV', os.environ.get('FLASK_ENV', 'production'))

# Application secret key (must be set in production)
if not os.environ.get('SECRET_KEY'):
    logger.warning("SECRET_KEY not set. Set it in production environment variables.")
    os.environ['SECRET_KEY'] = 'please-set-a-secret-key-in-your-env'

# Base URL (used in some templates/links)
os.environ.setdefault('BASE_URL', os.environ.get('BASE_URL', 'http://localhost:5000'))

validate_environment()

# ============================================================
# IMPORTAR APLICACIÓN
# ============================================================
def import_application():
    """Importa la aplicación Flask con manejo robusto de errores."""
    try:
        from app_menu import app
        logger.info("Successfully imported Flask application")
        return app
    except ImportError as e:
        logger.error(f"Failed to import Flask application: {e}")
        raise ImportError(
            "Failed to import Flask application. Troubleshooting:\n"
            "1. Verify 'app_menu.py' exists in the project directory\n"
            "2. Check that 'app = Flask(__name__)' is defined in app_menu.py\n"
            "3. Ensure all required dependencies are installed\n"
            "4. Verify database environment variables are correctly set\n"
            f"Original error: {e}"
        ) from e

try:
    application = import_application()
except ImportError as e:
    logger.critical(f"Critical error: {e}")
    raise
