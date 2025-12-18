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

# ============================================================
# VARIABLES DE ENTORNO - CONFIGURACIÓN MYSQL
# ============================================================
# Runtime environment: prefer to read from real environment variables.
# DO NOT commit secrets to the repository. Set these in PythonAnywhere
# Web -> Environment variables, or create a local `.env` (gitignored).
os.environ.setdefault('FLASK_ENV', os.environ.get('FLASK_ENV', 'production'))

# Application secret key (must be set in production)
if not os.environ.get('SECRET_KEY'):
    # note: we don't set a production secret here; raise helpful message
    os.environ['SECRET_KEY'] = 'please-set-a-secret-key-in-your-env'

# MySQL / Database settings - set these in the server environment
# Example variables expected: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT
# Leave them empty here so deployment environment (PythonAnywhere) provides them.

# Base URL (used in some templates/links)
os.environ.setdefault('BASE_URL', os.environ.get('BASE_URL', 'http://localhost:5000'))

# ============================================================
# IMPORTAR APLICACIÓN
# ============================================================
try:
    # Intentar import directo (si el módulo está en project_home)
    from app_menu import app as application
except Exception:
    # Fallback: importar como paquete si existe la carpeta 'mimenudigital'
    try:
        from mimenudigital.app_menu import app as application
    except Exception as e:
        # Provide a helpful error explaining why import failed.
        raise ImportError(
            "Failed to import Flask application. Make sure your project path is correct, "
            "and that `app = Flask(__name__)` is defined in `app_menu.py` (before any @app.route). "
            "Also ensure required dependencies are installed and environment variables are set. "
            f"Original error: {e!s}"
        )
