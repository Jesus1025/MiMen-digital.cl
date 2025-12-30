import os
import sys
from dotenv import load_dotenv

# Load environment variables
base_dir = os.path.dirname(os.path.abspath(__file__))
env_local_path = os.path.join(base_dir, '.env.local')
if os.path.exists(env_local_path):
    load_dotenv(env_local_path)

from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, 
    flash, session, g, send_from_directory, make_response
)
import pymysql
from pymysql.cursors import DictCursor
from functools import wraps
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import traceback
import logging
from logging.handlers import RotatingFileHandler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


from config import get_config
from flask_session import Session

# ============================================================
# APP INITIALIZATION
# ============================================================


app = Flask(__name__)
app.config.from_object(get_config())

# Configuración de Flask-Session (servidor)
app.config.setdefault('SESSION_TYPE', 'filesystem')  # Cambia a 'redis' en producción si tienes Redis
app.config.setdefault('SESSION_PERMANENT', True)
app.config.setdefault('SESSION_USE_SIGNER', True)
app.config.setdefault('SESSION_FILE_DIR', os.path.join(base_dir, 'flask_session'))
Session(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# ============================================================
# LOGGING
# ============================================================
if not app.debug:
    # Usar /tmp/app.log para evitar problemas de permisos en PythonAnywhere
    file_handler = RotatingFileHandler('/tmp/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Menu Digital startup')

# ============================================================
# DATABASE (moved to database.py)
# ============================================================
try:
    from database import get_db, init_app as db_init_app
    try:
        db_init_app(app)
    except Exception as e:
        app.logger.debug("DB teardown registration skipped: %s", e)
except Exception as e:
    # If database module cannot be imported, keep a simple fallback
    def get_db():
        raise RuntimeError('Database helper not available')

# ============================================================
# HELPERS & DECORATORS (extracted to modules)
# ============================================================

try:
    from utils import dict_from_row, list_from_rows, allowed_file, generar_qr_restaurante, registrar_visita
except Exception as e:
    # Fallbacks if utils not available
    def dict_from_row(row):
        return dict(row) if row else None
    def list_from_rows(rows):
        return [dict(row) for row in rows] if rows else []
    def allowed_file(filename):
        if not filename or '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in {'png','jpg','jpeg','gif','webp'}
    def generar_qr_restaurante(url, filename):
        raise RuntimeError('QR helper not available')
    def registrar_visita(restaurante_id, req):
        raise RuntimeError('registrar_visita not available')


# Decorators: build them from factory functions to avoid circular imports
try:
    from decorators import make_login_required, make_restaurante_owner_required, make_superadmin_required, make_verificar_suscripcion
    login_required = make_login_required()
    restaurante_owner_required = make_restaurante_owner_required()
    superadmin_required = make_superadmin_required()
    verificar_suscripcion = make_verificar_suscripcion(get_db)
except Exception as e:
    # Simple fallbacks
    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'No autorizado'}), 401
                flash('Debes iniciar sesión para acceder a esta página', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated

    def restaurante_owner_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('rol') == 'consulta':
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Acceso denegado. Rol de solo lectura.'}), 403
                flash('No tienes permisos para modificar el menú', 'error')
                return redirect(url_for('menu_gestion'))
            return f(*args, **kwargs)
        return decorated

    def superadmin_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('rol') != 'superadmin':
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Acceso denegado. Solo superadmin.'}), 403
                flash('No tienes permisos de superadministrador', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated

    def verificar_suscripcion(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated


# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    """Página principal - redirige al login o al panel."""
    if 'user_id' in session:
        if session.get('rol') == 'superadmin':
            return redirect(url_for('superadmin_restaurantes'))
        return redirect(url_for('menu_gestion'))
    return render_template('index.html')


# Registrar rutas de autenticación (módulo `auth_blueprint.py`)
try:
    from auth_blueprint import register_auth
    register_auth(app, get_db, dict_from_row)
    app.logger.info('Auth routes registered from auth_blueprint')
except Exception as e:
    app.logger.debug('Could not register auth routes: %s', e)
    app.logger.debug(traceback.format_exc())

# Registrar API de gestión si existe
try:
    from api_gestion_blueprint import register_api_gestion
    register_api_gestion(app)
except Exception as e:
    app.logger.debug('Could not register api_gestion blueprint: %s', e)
    app.logger.debug(traceback.format_exc())


# Login route moved to `auth_blueprint.py` (registered below)
# The auth module uses `register_auth(app, get_db, dict_from_row)` to attach routes.




# Password reset route moved to `auth_blueprint.py` (registered below)
# Logout route is registered by auth module as well; define here as fallback


@app.route('/api/health')
def health_check():
    """Endpoint para verificar que la app está funcionando."""
    status = {
        'app': 'ok',
        'python_version': sys.version,
        'flask_env': os.environ.get('FLASK_ENV', 'not set'),
        'mysql_host': os.environ.get('MYSQL_HOST', 'not set'),
        'mysql_db': os.environ.get('MYSQL_DB', 'not set'),
        'mysql_user': os.environ.get('MYSQL_USER', 'not set'),
        'working_dir': os.getcwd(),
        'script_dir': os.path.dirname(os.path.abspath(__file__)),
    }

    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT 1")
            status['mysql_connection'] = 'ok'
            cur.execute("SHOW TABLES")
            tables = [row[list(row.keys())[0]] for row in cur.fetchall()]
            status['tables'] = tables
    except Exception as e:
        status['mysql_connection'] = f'error: {str(e)}'
        status['mysql_traceback'] = traceback.format_exc()

    return jsonify(status)


# ERROR HANDLERS
@app.errorhandler(404)
def not_found_error(error):
    app.logger.debug("404 Not Found: %s", request.path)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Recurso no encontrado'}), 404
    return render_template('error_publico.html', error_code=404, error_message='Página no encontrada'), 404


@app.errorhandler(500)
def internal_error(error):
    app.logger.error("500 Internal Server Error: %s", traceback.format_exc())
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
    return render_template('error_publico.html', error_code=500, error_message='Error interno del servidor'), 500


@app.errorhandler(403)
def forbidden_error(error):
    app.logger.warning("403 Forbidden error: %s", request.path)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Acceso prohibido'}), 403
    return render_template('error_publico.html', error_code=403, error_message='Acceso prohibido'), 403


@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error("Unhandled exception: %s: %s\n%s", type(e).__name__, e, traceback.format_exc())
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Error interno', 'type': type(e).__name__}), 500
    return render_template('error_publico.html', error_code=500, error_message=f'Error: {str(e)}'), 500

# ============================================================
# CLI COMMANDS
# ============================================================

@app.cli.command("init-db")
def init_db_command():
    """Initializes the database from `schema.sql` and creates defaults.

    This command should be run from the server or locally by the administrator.
    """
    db = get_db()
    messages = []
    with db.cursor() as cur:
        # Basic example: create tables if missing
        try:
            with open('schema.sql') as f:
                cur.execute(f.read())
            db.commit()
            messages.append('Schema applied')
        except Exception as e:
            db.rollback()
            messages.append(f'Error applying schema: {e}')

        # Create superadmin if not exists (example)
        try:
            cur.execute("SELECT id FROM usuarios_admin WHERE username = 'superadmin'")
            if not cur.fetchone():
                pwd = generate_password_hash('superadmin123')
                cur.execute('''
                    INSERT INTO usuarios_admin (restaurante_id, username, password_hash, nombre, rol, activo)
                    VALUES (NULL, %s, %s, %s, %s, 1)
                ''', ('superadmin', pwd, 'Super Admin', 'superadmin'))
                db.commit()
                messages.append('Superadmin created')
            else:
                messages.append('Superadmin already exists')
        except Exception as e:
            db.rollback()
            messages.append(f'Error ensuring superadmin: {e}')

    for m in messages:
        print(m)
    print('Database initialization complete.')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
