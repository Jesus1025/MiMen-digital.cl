# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================
# COPIA ESTE CONTENIDO AL ARCHIVO WSGI DE PYTHONANYWHERE
# En el dashboard Web -> pestaña WSGI configuration file
# ============================================================


import sys
import os
try:
    # Optional: use python-dotenv locally for convenience (don't commit .env)
    from dotenv import load_dotenv
    base = os.path.dirname(__file__)
    env_local = os.path.join(base, '.env.local')
    env_file = os.path.join(base, '.env')
    # Prefer .env.local for development convenience (it's gitignored)
    if os.path.exists(env_local):
        load_dotenv(env_local)
    elif os.path.exists(env_file):
        load_dotenv(env_file)
except Exception:
    # dotenv is optional; in production you should set real ENV vars
    pass

# Basic logging for WSGI import-time diagnostics (writes to stderr so PA shows it)
import logging
_wsgi_logger = logging.getLogger('wsgi')
if not _wsgi_logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    _wsgi_logger.addHandler(ch)
_wsgi_logger.setLevel(logging.INFO)

# ============================================================
# RUTA DEL PROYECTO - AJUSTAR SEGÚN TU ESTRUCTURA
# ============================================================
# Opción 1: Si clonaste directamente (sin carpeta anidada)
# project_home = '/home/MiMenudigital/MiMen-digital.cl'

# Opción 2: Si hay carpeta anidada con caracteres especiales
# Prueba estas variantes según tu estructura:
# Try to locate the project directory dynamically. This avoids problems with
# accented folder names or different layouts between local and PythonAnywhere.
home = os.path.expanduser('~')
candidates = [
    os.path.join(home, 'MiMen-digital.cl'),
    os.path.join(home, 'MiMen-digital.cl', 'mimenudigital'),
    os.path.join(home, 'MiMen-digital.cl', 'mimenúdigital'),
    os.path.join(home, 'MiMen-digital.cl', 'MiMen-digital.cl'),
]

project_home = None
for c in candidates:
    if os.path.isdir(c) and 'app_menu.py' in os.listdir(c):
        project_home = c
        break

if project_home is None:
    # Fallback: scan home for a directory containing app_menu.py
    for entry in os.listdir(home):
        full = os.path.join(home, entry)
        if os.path.isdir(full):
            try:
                if 'app_menu.py' in os.listdir(full):
                    project_home = full
                    break
            except Exception:
                continue

if project_home is None:
    # Last resort: use current directory
    project_home = os.getcwd()

if project_home not in sys.path:
    sys.path.insert(0, project_home)

try:
    os.chdir(project_home)
except Exception:
    pass

_wsgi_logger.info('WSGI: Using project_home=%s', project_home)

# ============================================================
# VARIABLES DE ENTORNO - CONFIGURACIÓN MYSQL
# ============================================================
# Runtime environment: prefer to read from real environment variables.
# DO NOT commit secrets to the repository. Set these in PythonAnywhere
# Web -> Environment variables, or create a local `.env` (gitignored).
os.environ.setdefault('FLASK_ENV', os.environ.get('FLASK_ENV', 'production'))

# Application secret key (must be set in production)
if os.environ.get('FLASK_ENV') == 'production':
    if not os.environ.get('SECRET_KEY') or os.environ.get('SECRET_KEY') == 'please-set-a-secret-key-in-your-env':
        # Fail fast in production: do not start with an insecure placeholder
        msg = (
            'SECRET_KEY is not set for production environment. ' 
            'Set SECRET_KEY in the Web -> Environment variables on PythonAnywhere and reload the app.'
        )
        _wsgi_logger.error(msg)
        raise RuntimeError(msg)
else:
    # Keep a clear placeholder for development convenience
    os.environ.setdefault('SECRET_KEY', 'please-set-a-secret-key-in-your-env')

# MySQL / Database settings - set these in the server environment
# Example variables expected: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT
# Leave them empty here so deployment environment (PythonAnywhere) provides them.

# Base URL (used in some templates/links)
os.environ.setdefault('BASE_URL', os.environ.get('BASE_URL', 'http://localhost:5000'))

# Log presence of common DB envs (non-fatal)
for k in ('MYSQL_HOST', 'MYSQL_USER', 'MYSQL_DB'):
    _wsgi_logger.info('%s=%s', k, bool(os.environ.get(k)))

# ============================================================
# IMPORTAR APLICACIÓN
# ============================================================
try:
    # Prefer importing as a package (when app is inside `mimenudigital` package)
    from mimenudigital.app_menu import app as application
except Exception:
    # Fallback: try a top-level module named app_menu
    try:
        from app_menu import app as application
    except Exception as e:
        # Provide a helpful error explaining why import failed.
        _wsgi_logger.exception('Failed to import Flask application: %s', e)
        raise ImportError(
            "Failed to import Flask application. Check project path, package layout, and dependencies. "
            "Ensure `app = Flask(__name__)` is defined in `app_menu.py` before routes, and that required "
            "env vars (e.g., SECRET_KEY) are set. Original error: %s" % e
        )
    else:
        _wsgi_logger.info('Imported application from top-level module app_menu')
else:
    _wsgi_logger.info('Imported application from package mimenudigital.app_menu')

# Ensure WSGI callable is named 'application' (some servers require this)
if 'application' not in globals():
    try:
        application = application
    except NameError:
        raise ImportError('WSGI callable `application` not found; ensure your Flask app is assigned to `app`')
