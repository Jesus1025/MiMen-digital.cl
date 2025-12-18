# =====================
# SUPERADMIN USUARIOS Y SUSCRIPCIONES
# =====================
@app.route('/superadmin/usuarios')
@login_required
@superadmin_required
def superadmin_usuarios():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, nombre, email, rol, creado_en FROM usuarios_admin WHERE rol != 'superadmin' ORDER BY creado_en DESC")
        usuarios = cur.fetchall()
    return render_template('superadmin/usuarios.html', usuarios=usuarios)

@app.route('/superadmin/suscripciones')
@login_required
@superadmin_required
def superadmin_suscripciones():
    return render_template('superadmin/suscripciones.html')
# =====================
# SUPERADMIN DASHBOARD ESTADÍSTICAS
# =====================
@app.route('/superadmin/estadisticas')
@login_required
@superadmin_required
def superadmin_estadisticas():
    return render_template('superadmin/estadisticas.html')

# API para estadísticas globales
@app.route('/api/superadmin/stats')
@login_required
@superadmin_required
def api_superadmin_stats():
    db = get_db()
    with db.cursor() as cur:
        # Total restaurantes
        cur.execute("SELECT COUNT(*) as total FROM restaurantes")
        total_restaurantes = cur.fetchone()['total']
        # Total usuarios (sin superadmin)
        cur.execute("SELECT COUNT(*) as total FROM usuarios_admin WHERE rol != 'superadmin'")
        total_usuarios = cur.fetchone()['total']
        # Total visitas y escaneos
        cur.execute("SELECT COALESCE(SUM(visitas),0) as visitas, COALESCE(SUM(escaneos_qr),0) as escaneos FROM estadisticas_diarias")
        row = cur.fetchone()
        total_visitas = row['visitas']
        total_escaneos = row['escaneos']
        # Visitas últimos 30 días
        cur.execute("""
            SELECT fecha, COALESCE(SUM(visitas),0) as visitas
            FROM estadisticas_diarias
            WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY fecha
            ORDER BY fecha
        """)
        visitas_30dias = list_from_rows(cur.fetchall())
    return jsonify({
        'total_restaurantes': total_restaurantes,
        'total_usuarios': total_usuarios,
        'total_visitas': total_visitas,
        'total_escaneos': total_escaneos,
        'visitas_30dias': visitas_30dias
    })
import qrcode
# Carpeta para los QR
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'qrs')
os.makedirs(QR_FOLDER, exist_ok=True)

def generar_qr_restaurante(url, filename):
    qr_path = os.path.join(QR_FOLDER, filename)
    if not os.path.exists(qr_path):
        img = qrcode.make(url)
        img.save(qr_path)
    return qr_path
# ============================================================
# MENU DIGITAL SAAS - DIVERGENT STUDIO
# Sistema Multi-Tenant para Menús Digitales
# Versión: 2.0 - MySQL Production Ready
# ============================================================
# ...existing code...
# Ejemplo de uso en una vista (ajusta según tu lógica):
#
# @app.route('/superadmin/generar_qr/<int:restaurante_id>')
# def generar_qr(restaurante_id):
#     # Obtén el restaurante y su url_slug desde la base de datos
#     restaurante = ... # tu lógica aquí
#     url = f"{BASE_URL}/menu/{restaurante['url_slug']}"
#     filename = f"{restaurante['id']}_qr.png"
#     qr_path = generar_qr_restaurante(url, filename)
#     return send_from_directory(QR_FOLDER, filename)


import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g, send_from_directory
import pymysql
from pymysql.cursors import DictCursor
import uuid
from functools import wraps
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import traceback
import logging

# Configurar logging para archivo y consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# Handler para error 403 (prohibido)
@app.errorhandler(403)
def forbidden_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Acceso prohibido'}), 403
    return render_template('error_publico.html', error_code=403, error_message='Acceso prohibido'), 403

# ============================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'menu_digital_divergent_secret_key_2025_prod')

# Añadir función now() a Jinja2 para templates
app.jinja_env.globals['now'] = datetime.now

# Configuración de sesiones
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configuración de subida de imágenes
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB máximo
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Crear carpeta de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================================
# CONFIGURACIÓN MYSQL
# ============================================================
# Para desarrollo local (XAMPP/WAMP):
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DB', 'menu_digital'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
    'autocommit': False
}

# Para PythonAnywhere, las variables de entorno serán:
# MYSQL_HOST=tuusuario.mysql.pythonanywhere-services.com
# MYSQL_USER=tuusuario
# MYSQL_PASSWORD=tu_password
# MYSQL_DB=tuusuario$menu_digital

# Dominio base (se detecta automáticamente)
BASE_URL = os.environ.get('BASE_URL', '')

# ============================================================
# CONEXIÓN A BASE DE DATOS MYSQL
# ============================================================

def get_db():
    """Obtiene una conexión a MySQL con soporte de reconexión."""
    if 'db' not in g:
        try:
            g.db = pymysql.connect(**MYSQL_CONFIG)
        except pymysql.Error as e:
            print(f"❌ Error conectando a MySQL: {e}")
            raise
    else:
        # Verificar si la conexión sigue activa
        try:
            g.db.ping(reconnect=True)
        except pymysql.Error:
            try:
                g.db = pymysql.connect(**MYSQL_CONFIG)
            except pymysql.Error as e:
                print(f"❌ Error reconectando a MySQL: {e}")
                raise
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """Cierra la conexión a la base de datos al terminar la request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except:
            pass


# ============================================================
# MANEJADORES DE ERRORES GLOBALES
# ============================================================

@app.errorhandler(500)
def internal_error(error):
    """Manejador de errores internos del servidor."""
    logger.error(f"Error 500: {error}\n{traceback.format_exc()}")
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False, 
            'error': 'Error interno del servidor',
            'details': str(error)
        }), 500
    return render_template('error_publico.html', 
                          error_code=500, 
                          error_message='Error interno del servidor'), 500


@app.errorhandler(404)
def not_found_error(error):
    """Manejador de errores 404."""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Recurso no encontrado'}), 404
    return render_template('error_publico.html', 
                          error_code=404, 
                          error_message='Página no encontrada'), 404


@app.errorhandler(Exception)
def handle_exception(e):
    """Manejador global de excepciones."""
    logger.error(f"Excepción no manejada: {e}\n{traceback.format_exc()}")
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False, 
            'error': str(e),
            'type': type(e).__name__
        }), 500
    return render_template('error_publico.html', 
                          error_code=500, 
                          error_message=f'Error: {str(e)}'), 500


def dict_from_row(row):
    """Convierte una fila a diccionario (PyMySQL con DictCursor ya lo hace)."""
    return dict(row) if row else None


def list_from_rows(rows):
    """Convierte lista de filas a lista de diccionarios."""
    return [dict(row) for row in rows] if rows else []


def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Context processor para inyectar menu_url en todos los templates
@app.context_processor
def inject_menu_url():
    """Inyecta la URL del menú público en todos los templates."""
    menu_url = None
    if 'restaurante_id' in session and session['restaurante_id']:
        try:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SELECT url_slug FROM restaurantes WHERE id = %s", (session['restaurante_id'],))
                row = cur.fetchone()
                if row and row['url_slug']:
                    menu_url = f"/menu/{row['url_slug']}"
        except:
            pass
    return {'menu_url_global': menu_url}


# ============================================================
# DECORADORES PERSONALIZADOS
# ============================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No autorizado'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def restaurante_owner_required(f):
    """Permite solo acceso al administrador del restaurante actual o a un superadmin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'rol' in session and session.get('rol') == 'consulta':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Acceso denegado. Rol de solo lectura.'}), 403
            flash('No tienes permisos para modificar el menú', 'error')
            return redirect(url_for('menu_gestion'))
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    """Solo permite acceso a superadmins."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Acceso denegado. Solo superadmin.'}), 403
            flash('No tienes permisos de superadministrador', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ============================================================
# TRACKING DE VISITAS Y ESCANEOS QR
# ============================================================

def registrar_visita(restaurante_id, req):
    """Registra una visita/escaneo QR para el restaurante."""
    try:
        db = get_db()
        with db.cursor() as cur:
            # Obtener información del visitante
            ip_address = req.headers.get('X-Forwarded-For', req.remote_addr)
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()[:45]
            
            user_agent = req.headers.get('User-Agent', '')[:500]
            referer = req.headers.get('Referer', '')[:500]
            
            # Detectar si es móvil
            es_movil = any(x in user_agent.lower() for x in ['mobile', 'android', 'iphone', 'ipad'])
            es_qr = 'qr' in referer.lower() or req.args.get('qr') == '1'
            
            # Insertar registro de visita
            cur.execute('''
                INSERT INTO visitas (restaurante_id, ip_address, user_agent, referer, es_movil, es_qr, fecha)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ''', (restaurante_id, ip_address, user_agent, referer, 1 if es_movil else 0, 1 if es_qr else 0))
            
            # Actualizar contador diario
            hoy = date.today().isoformat()
            cur.execute('''
                INSERT INTO estadisticas_diarias (restaurante_id, fecha, visitas, escaneos_qr, visitas_movil, visitas_desktop)
                VALUES (%s, %s, 1, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    visitas = visitas + 1,
                    escaneos_qr = escaneos_qr + %s,
                    visitas_movil = visitas_movil + %s,
                    visitas_desktop = visitas_desktop + %s
            ''', (
                restaurante_id, hoy, 
                1 if es_qr else 0, 
                1 if es_movil else 0, 
                0 if es_movil else 1,
                1 if es_qr else 0,
                1 if es_movil else 0,
                0 if es_movil else 1
            ))
            
            db.commit()
            
    except Exception as e:
        print(f"Error registrando visita: {e}")
        try:
            db.rollback()
        except:
            pass


# ============================================================
# RUTAS PÚBLICAS - MENÚ
# ============================================================

@app.route('/')
def index():
    """Página principal - redirige al login o al panel."""
    if 'user_id' in session:
        if session.get('rol') == 'superadmin':
            return redirect(url_for('superadmin_restaurantes'))
        return redirect(url_for('menu_gestion'))
    return render_template('index.html')


@app.route('/menu/<string:url_slug>')
def ver_menu_publico(url_slug):
    """Ruta pública para ver el menú. Accesible por QR."""
    try:
        db = get_db()
        with db.cursor() as cur:
            # 1. Obtener datos del restaurante
            cur.execute("SELECT * FROM restaurantes WHERE url_slug = %s AND activo = 1", (url_slug,))
            row = cur.fetchone()
            
            if not row:
                return render_template('menu_404.html', slug=url_slug), 404
            
            restaurante = dict_from_row(row)
            
            # Preview de tema
            preview_tema = request.args.get('preview_tema')
            if preview_tema:
                restaurante['tema'] = preview_tema
            
            # 2. Registrar visita (solo si no es preview)
            if not preview_tema:
                registrar_visita(restaurante['id'], request)

            # 3. Obtener categorías y platos
            cur.execute('''
                SELECT c.id as categoria_id, c.nombre as categoria_nombre, c.icono as categoria_icono,
                       p.id as plato_id, p.nombre as plato_nombre, p.descripcion, p.precio, 
                       p.precio_oferta, p.imagen_url, p.etiquetas, p.es_nuevo, p.es_popular,
                       p.es_vegetariano, p.es_vegano, p.es_sin_gluten, p.es_picante
                FROM categorias c
                LEFT JOIN platos p ON c.id = p.categoria_id AND p.activo = 1
                WHERE c.restaurante_id = %s AND c.activo = 1
                ORDER BY c.orden, p.orden, p.nombre
            ''', (restaurante['id'],))
            
            platos_raw = cur.fetchall()

            # 4. Estructurar el menú
            menu_estructurado = {}
            for row in platos_raw:
                cat_id = row['categoria_id']
                if cat_id not in menu_estructurado:
                    menu_estructurado[cat_id] = {
                        'nombre': row['categoria_nombre'],
                        'icono': row['categoria_icono'],
                        'platos': []
                    }
                
                if row['plato_id']:
                    plato = {
                        'id': row['plato_id'],
                        'nombre': row['plato_nombre'],
                        'descripcion': row['descripcion'],
                        'precio': float(row['precio'] or 0),
                        'precio_oferta': float(row['precio_oferta']) if row['precio_oferta'] else None,
                        'imagen_url': row['imagen_url'],
                        'etiquetas': row['etiquetas'].split(',') if row['etiquetas'] else [],
                        'es_nuevo': row['es_nuevo'],
                        'es_popular': row['es_popular'],
                        'es_vegetariano': row['es_vegetariano'],
                        'es_vegano': row['es_vegano'],
                        'es_sin_gluten': row['es_sin_gluten'],
                        'es_picante': row['es_picante']
                    }
                    menu_estructurado[cat_id]['platos'].append(plato)

            return render_template('menu_publico.html', 
                                   restaurante=restaurante, 
                                   menu=list(menu_estructurado.values()))

    except Exception as e:
        print(f"Error al cargar menú para {url_slug}: {e}")
        return render_template('error_publico.html'), 500


# ============================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        with db.cursor() as cur:
            cur.execute('''
                SELECT u.*, r.nombre as restaurante_nombre 
                FROM usuarios_admin u
                LEFT JOIN restaurantes r ON u.restaurante_id = r.id
                WHERE u.username = %s AND u.activo = 1
            ''', (username,))
            row = cur.fetchone()
            
            if row:
                user = dict_from_row(row)
                if check_password_hash(user['password_hash'], password):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['nombre'] = user['nombre']
                    session['rol'] = user['rol']
                    session['restaurante_id'] = user['restaurante_id']
                    session['restaurante_nombre'] = user['restaurante_nombre'] or 'Panel Admin'
                    
                    # Actualizar último login
                    cur.execute("UPDATE usuarios_admin SET ultimo_login = NOW() WHERE id = %s", (user['id'],))
                    db.commit()
                    
                    flash('Bienvenido ' + user['nombre'], 'success')
                    
                    if user['rol'] == 'superadmin':
                        return redirect(url_for('superadmin_restaurantes'))
                    return redirect(url_for('menu_gestion'))
            
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))


# ============================================================
# RUTAS DE GESTIÓN (PANEL ADMIN)
# ============================================================

@app.route('/gestion')
@login_required
def menu_gestion():
    """Panel de gestión principal."""
    return render_template('gestion/dashboard.html')


@app.route('/gestion/platos')
@login_required
def gestion_platos():
    """Página de gestión de platos."""
    return render_template('gestion/platos.html')


@app.route('/gestion/categorias')
@login_required
def gestion_categorias():
    """Página de gestión de categorías."""
    return render_template('gestion/categorias.html')


@app.route('/gestion/mi-restaurante')
@login_required
def gestion_mi_restaurante():
    """Página de configuración del restaurante."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM restaurantes WHERE id = %s", (session['restaurante_id'],))
        restaurante = dict_from_row(cur.fetchone())
    return render_template('gestion/mi_restaurante.html', restaurante=restaurante)


@app.route('/gestion/codigo-qr')
@login_required
def gestion_codigo_qr():
    """Página del código QR."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM restaurantes WHERE id = %s", (session['restaurante_id'],))
        restaurante = dict_from_row(cur.fetchone())
    
    base_url = request.host_url.rstrip('/')
    menu_url = f"{base_url}/menu/{restaurante['url_slug']}"
    return render_template('gestion/codigo_qr.html', restaurante=restaurante, menu_url=menu_url)


@app.route('/gestion/apariencia')
@login_required
def gestion_apariencia():
    """Página de personalización de apariencia."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM restaurantes WHERE id = %s", (session['restaurante_id'],))
        restaurante = dict_from_row(cur.fetchone())
    return render_template('gestion/apariencia.html', restaurante=restaurante)


# ============================================================
# API - PLATOS
# ============================================================

@app.route('/api/platos', methods=['GET', 'POST'])
@login_required
def api_platos():
    """API para listar y crear platos."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute('''
                    SELECT p.*, c.nombre as categoria_nombre 
                    FROM platos p 
                    LEFT JOIN categorias c ON p.categoria_id = c.id
                    WHERE p.restaurante_id = %s 
                    ORDER BY p.orden, p.nombre
                ''', (restaurante_id,))
                return jsonify(list_from_rows(cur.fetchall()))
                
            if request.method == 'POST':
                data = request.get_json()
                
                cur.execute('''
                    INSERT INTO platos (restaurante_id, categoria_id, nombre, descripcion, precio, 
                                        precio_oferta, imagen_url, etiquetas, es_vegetariano, es_vegano,
                                        es_sin_gluten, es_picante, es_nuevo, es_popular, orden, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                ''', (
                    restaurante_id,
                    data.get('categoria_id'),
                    data.get('nombre'),
                    data.get('descripcion', ''),
                    data.get('precio', 0),
                    data.get('precio_oferta'),
                    data.get('imagen_url', ''),
                    data.get('etiquetas', ''),
                    data.get('es_vegetariano', 0),
                    data.get('es_vegano', 0),
                    data.get('es_sin_gluten', 0),
                    data.get('es_picante', 0),
                    data.get('es_nuevo', 0),
                    data.get('es_popular', 0),
                    data.get('orden', 0)
                ))
                db.commit()
                return jsonify({'success': True, 'id': cur.lastrowid})
                
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_platos: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/platos/<int:plato_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@restaurante_owner_required
def api_plato(plato_id):
    """API para obtener, editar o eliminar un plato."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute("SELECT * FROM platos WHERE id = %s AND restaurante_id = %s", 
                           (plato_id, restaurante_id))
                plato = cur.fetchone()
                if not plato:
                    return jsonify({'error': 'Plato no encontrado'}), 404
                return jsonify(dict_from_row(plato))
                
            if request.method == 'PUT':
                data = request.get_json()
                cur.execute('''
                    UPDATE platos SET 
                        categoria_id = %s, nombre = %s, descripcion = %s, precio = %s,
                        precio_oferta = %s, imagen_url = %s, etiquetas = %s, 
                        es_vegetariano = %s, es_vegano = %s, es_sin_gluten = %s,
                        es_picante = %s, es_nuevo = %s, es_popular = %s,
                        orden = %s, activo = %s
                    WHERE id = %s AND restaurante_id = %s
                ''', (
                    data.get('categoria_id'),
                    data.get('nombre'),
                    data.get('descripcion', ''),
                    data.get('precio', 0),
                    data.get('precio_oferta'),
                    data.get('imagen_url', ''),
                    data.get('etiquetas', ''),
                    data.get('es_vegetariano', 0),
                    data.get('es_vegano', 0),
                    data.get('es_sin_gluten', 0),
                    data.get('es_picante', 0),
                    data.get('es_nuevo', 0),
                    data.get('es_popular', 0),
                    data.get('orden', 0),
                    data.get('activo', 1),
                    plato_id, restaurante_id
                ))
                db.commit()
                return jsonify({'success': True})
                
            if request.method == 'DELETE':
                cur.execute("DELETE FROM platos WHERE id = %s AND restaurante_id = %s", 
                           (plato_id, restaurante_id))
                db.commit()
                return jsonify({'success': True})
                
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_plato: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - CATEGORÍAS
# ============================================================

@app.route('/api/categorias', methods=['GET', 'POST'])
@login_required
def api_categorias():
    """API para listar y crear categorías."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute('''
                    SELECT c.*, 
                           (SELECT COUNT(*) FROM platos WHERE categoria_id = c.id AND activo = 1) as total_platos
                    FROM categorias c 
                    WHERE c.restaurante_id = %s 
                    ORDER BY c.orden, c.nombre
                ''', (restaurante_id,))
                return jsonify(list_from_rows(cur.fetchall()))
                
            if request.method == 'POST':
                data = request.get_json()
                
                cur.execute('''
                    INSERT INTO categorias (restaurante_id, nombre, descripcion, icono, orden, activo)
                    VALUES (%s, %s, %s, %s, %s, 1)
                ''', (
                    restaurante_id,
                    data.get('nombre'),
                    data.get('descripcion', ''),
                    data.get('icono', ''),
                    data.get('orden', 0)
                ))
                db.commit()
                return jsonify({'success': True, 'id': cur.lastrowid})
                
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_categorias: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/categorias/<int:categoria_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@restaurante_owner_required
def api_categoria(categoria_id):
    """API para obtener, editar o eliminar una categoría."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute("SELECT * FROM categorias WHERE id = %s AND restaurante_id = %s", 
                           (categoria_id, restaurante_id))
                cat = cur.fetchone()
                if not cat:
                    return jsonify({'error': 'Categoría no encontrada'}), 404
                return jsonify(dict_from_row(cat))
                
            if request.method == 'PUT':
                data = request.get_json()
                cur.execute('''
                    UPDATE categorias SET 
                        nombre = %s, descripcion = %s, icono = %s, orden = %s, activo = %s
                    WHERE id = %s AND restaurante_id = %s
                ''', (
                    data.get('nombre'),
                    data.get('descripcion', ''),
                    data.get('icono', ''),
                    data.get('orden', 0),
                    data.get('activo', 1),
                    categoria_id, restaurante_id
                ))
                db.commit()
                return jsonify({'success': True})
                
            if request.method == 'DELETE':
                # Primero eliminar platos de la categoría
                cur.execute("DELETE FROM platos WHERE categoria_id = %s AND restaurante_id = %s", 
                           (categoria_id, restaurante_id))
                cur.execute("DELETE FROM categorias WHERE id = %s AND restaurante_id = %s", 
                           (categoria_id, restaurante_id))
                db.commit()
                return jsonify({'success': True})
                
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_categoria: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - RESTAURANTE
# ============================================================

@app.route('/api/mi-restaurante', methods=['GET', 'PUT'])
@login_required
def api_mi_restaurante():
    """API para obtener y actualizar datos del restaurante actual."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute("SELECT * FROM restaurantes WHERE id = %s", (restaurante_id,))
                return jsonify(dict_from_row(cur.fetchone()))
                
            if request.method == 'PUT':
                data = request.get_json()
                cur.execute('''
                    UPDATE restaurantes SET 
                        nombre = %s, descripcion = %s, slogan = %s, telefono = %s, 
                        email = %s, direccion = %s, horario = %s, instagram = %s, 
                        facebook = %s, whatsapp = %s, mostrar_precios = %s, 
                        mostrar_descripciones = %s, mostrar_imagenes = %s, moneda = %s
                    WHERE id = %s
                ''', (
                    data.get('nombre'),
                    data.get('descripcion', ''),
                    data.get('slogan', ''),
                    data.get('telefono', ''),
                    data.get('email', ''),
                    data.get('direccion', ''),
                    data.get('horario', ''),
                    data.get('instagram', ''),
                    data.get('facebook', ''),
                    data.get('whatsapp', ''),
                    data.get('mostrar_precios', 1),
                    data.get('mostrar_descripciones', 1),
                    data.get('mostrar_imagenes', 1),
                    data.get('moneda', '$'),
                    restaurante_id
                ))
                db.commit()
                
                # Actualizar nombre en sesión
                session['restaurante_nombre'] = data.get('nombre')
                
                return jsonify({'success': True})
                
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_mi_restaurante: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mi-restaurante/tema', methods=['PUT'])
@login_required
@restaurante_owner_required
def api_actualizar_tema():
    """Actualiza el tema del restaurante."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        data = request.get_json()
        with db.cursor() as cur:
            cur.execute('''
                UPDATE restaurantes SET 
                    tema = %s, color_primario = %s, color_secundario = %s
                WHERE id = %s
            ''', (
                data.get('tema', 'elegante'),
                data.get('color_primario', '#c0392b'),
                data.get('color_secundario', '#2c3e50'),
                restaurante_id
            ))
            db.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_actualizar_tema: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mi-restaurante/logo', methods=['POST'])
@login_required
@restaurante_owner_required
def api_subir_logo():
    """Sube el logo del restaurante."""
    if 'logo' not in request.files:
        return jsonify({'success': False, 'error': 'No se envió ningún archivo'}), 400
    
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Archivo vacío'}), 400
    
    if file and allowed_file(file.filename):
        # Generar nombre único
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"logo_{session['restaurante_id']}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        
        # Actualizar en BD
        logo_url = f"/static/uploads/{filename}"
        db = get_db()
        with db.cursor() as cur:
            cur.execute("UPDATE restaurantes SET logo_url = %s WHERE id = %s", 
                       (logo_url, session['restaurante_id']))
            db.commit()
        
        return jsonify({'success': True, 'logo_url': logo_url})
    
    return jsonify({'success': False, 'error': 'Tipo de archivo no permitido'}), 400


# ============================================================
# API - DASHBOARD STATS
# ============================================================

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """Obtiene estadísticas del restaurante para el dashboard."""
    db = get_db()
    restaurante_id = session.get('restaurante_id')
    
    if not restaurante_id:
        return jsonify({
            'total_platos': 0,
            'total_categorias': 0,
            'total_vistas': 0,
            'total_scans': 0,
            'visitas_hoy': 0,
            'scans_hoy': 0,
            'ultimos_7_dias': [],
            'url_slug': '',
            'base_url': request.host_url.rstrip('/')
        })
    
    try:
        with db.cursor() as cur:
            # Contar platos activos
            cur.execute("SELECT COUNT(*) as total FROM platos WHERE restaurante_id = %s AND activo = 1", 
                       (restaurante_id,))
            total_platos = cur.fetchone()['total']
            
            # Contar categorías
            cur.execute("SELECT COUNT(*) as total FROM categorias WHERE restaurante_id = %s AND activo = 1", 
                       (restaurante_id,))
            total_categorias = cur.fetchone()['total']
            
            # Obtener url_slug
            cur.execute("SELECT url_slug FROM restaurantes WHERE id = %s", (restaurante_id,))
            row = cur.fetchone()
            url_slug = row['url_slug'] if row else ''
            
            # Estadísticas del mes
            primer_dia_mes = date.today().replace(day=1).isoformat()
            cur.execute('''
                SELECT COALESCE(SUM(visitas), 0) as visitas, COALESCE(SUM(escaneos_qr), 0) as scans
                FROM estadisticas_diarias 
                WHERE restaurante_id = %s AND fecha >= %s
            ''', (restaurante_id, primer_dia_mes))
            stats = cur.fetchone()
            total_vistas = stats['visitas'] if stats else 0
            total_scans = stats['scans'] if stats else 0
            
            # Estadísticas de hoy
            hoy = date.today().isoformat()
            cur.execute('''
                SELECT COALESCE(visitas, 0) as visitas, COALESCE(escaneos_qr, 0) as scans
                FROM estadisticas_diarias 
                WHERE restaurante_id = %s AND fecha = %s
            ''', (restaurante_id, hoy))
            hoy_row = cur.fetchone()
            visitas_hoy = hoy_row['visitas'] if hoy_row else 0
            scans_hoy = hoy_row['scans'] if hoy_row else 0
            
            # Últimos 7 días
            cur.execute('''
                SELECT fecha, visitas, escaneos_qr as scans
                FROM estadisticas_diarias 
                WHERE restaurante_id = %s AND fecha >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                ORDER BY fecha
            ''', (restaurante_id,))
            ultimos_7_dias = list_from_rows(cur.fetchall())
            
            return jsonify({
                'total_platos': total_platos,
                'total_categorias': total_categorias,
                'total_vistas': total_vistas,
                'total_scans': total_scans,
                'visitas_hoy': visitas_hoy,
                'scans_hoy': scans_hoy,
                'ultimos_7_dias': ultimos_7_dias,
                'url_slug': url_slug,
                'base_url': request.host_url.rstrip('/')
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# RUTAS DE SUPERADMIN
# ============================================================

@app.route('/superadmin/restaurantes')
@login_required
@superadmin_required
def superadmin_restaurantes():
    """Panel de gestión de restaurantes (SuperAdmin)."""
    db = get_db()
    with db.cursor() as cur:
        # Obtener restaurantes con estadísticas
        cur.execute("""
            SELECT r.*, 
                   (SELECT COUNT(*) FROM categorias WHERE restaurante_id = r.id) as total_categorias,
                   (SELECT COUNT(*) FROM platos WHERE restaurante_id = r.id) as total_platos,
                   (SELECT COUNT(*) FROM usuarios_admin WHERE restaurante_id = r.id) as total_usuarios,
                   (SELECT COALESCE(SUM(visitas), 0) FROM estadisticas_diarias WHERE restaurante_id = r.id) as total_visitas
            FROM restaurantes r 
            ORDER BY r.nombre
        """)
        restaurantes = list_from_rows(cur.fetchall())
        
        # Nuevos este mes
        primer_dia_mes = date.today().replace(day=1).isoformat()
        cur.execute("SELECT COUNT(*) as total FROM restaurantes WHERE fecha_creacion >= %s", (primer_dia_mes,))
        nuevos_este_mes = cur.fetchone()['total']
        
        # Total usuarios
        cur.execute("SELECT COUNT(*) as total FROM usuarios_admin WHERE rol != 'superadmin'")
        total_usuarios = cur.fetchone()['total']
    
    return render_template('superadmin/restaurantes.html', 
                           restaurantes=restaurantes,
                           nuevos_este_mes=nuevos_este_mes,
                           total_usuarios=total_usuarios)


@app.route('/api/restaurantes', methods=['GET', 'POST'])
@login_required
@superadmin_required
def api_restaurantes():
    """API para listar y crear restaurantes."""
    db = get_db()
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute("SELECT * FROM restaurantes ORDER BY nombre")
                return jsonify(list_from_rows(cur.fetchall()))
                
            if request.method == 'POST':
                data = request.get_json()
                
                if not data:
                    return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
                
                if not data.get('nombre') or not data.get('url_slug'):
                    return jsonify({'success': False, 'error': 'Nombre y URL slug son obligatorios'}), 400
                
                # Verificar que el url_slug no exista
                cur.execute("SELECT id FROM restaurantes WHERE url_slug = %s", (data['url_slug'],))
                if cur.fetchone():
                    return jsonify({'success': False, 'error': 'El URL slug ya existe'}), 400
                
                cur.execute('''
                    INSERT INTO restaurantes (nombre, rut, url_slug, logo_url, tema, plan_id, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, 1)
                ''', (
                    data['nombre'],
                    data.get('rut', ''),
                    data['url_slug'],
                    data.get('logo_url', ''),
                    data.get('tema', 'elegante'),
                    data.get('plan_id', 1)  # Plan gratis por defecto
                ))
                db.commit()
                return jsonify({'success': True, 'id': cur.lastrowid})

    except pymysql.IntegrityError as e:
        try:
            db.rollback()
        except:
            pass
        error_msg = str(e)
        if 'Duplicate' in error_msg or 'duplicate' in error_msg.lower():
            return jsonify({'success': False, 'error': 'El URL slug ya existe'}), 400
        if 'foreign key' in error_msg.lower():
            return jsonify({'success': False, 'error': 'Error de referencia en la base de datos'}), 400
        return jsonify({'success': False, 'error': f'Error de integridad: {error_msg}'}), 500
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_restaurantes: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/restaurantes/<int:rest_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@superadmin_required
def api_restaurante(rest_id):
    """API para obtener, editar o eliminar un restaurante."""
    db = get_db()
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute("SELECT * FROM restaurantes WHERE id = %s", (rest_id,))
                rest = cur.fetchone()
                if not rest:
                    return jsonify({'error': 'Restaurante no encontrado'}), 404
                return jsonify(dict_from_row(rest))
                
            if request.method == 'PUT':
                data = request.get_json()
                cur.execute('''
                    UPDATE restaurantes SET 
                        nombre = %s, rut = %s, url_slug = %s, logo_url = %s, tema = %s, activo = %s
                    WHERE id = %s
                ''', (
                    data.get('nombre'),
                    data.get('rut', ''),
                    data.get('url_slug'),
                    data.get('logo_url', ''),
                    data.get('tema', 'elegante'),
                    data.get('activo', 1),
                    rest_id
                ))
                db.commit()
                return jsonify({'success': True})
                
            if request.method == 'DELETE':
                # Eliminar en cascada (las FK con ON DELETE CASCADE lo manejan)
                cur.execute("DELETE FROM restaurantes WHERE id = %s", (rest_id,))
                db.commit()
                return jsonify({'success': True})

    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_restaurante: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/usuarios', methods=['GET', 'POST'])
@login_required
@superadmin_required
def api_usuarios():
    """API para listar y crear usuarios."""
    db = get_db()
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute('''
                    SELECT u.id, u.restaurante_id, u.username, u.nombre, u.email, u.rol, 
                           u.activo, u.ultimo_login, u.fecha_creacion, r.nombre as restaurante_nombre 
                    FROM usuarios_admin u 
                    LEFT JOIN restaurantes r ON u.restaurante_id = r.id
                    ORDER BY u.nombre
                ''')
                return jsonify(list_from_rows(cur.fetchall()))
                
            if request.method == 'POST':
                data = request.get_json()
                
                if not data:
                    return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
                
                if not data.get('username') or not data.get('password') or not data.get('nombre'):
                    return jsonify({'success': False, 'error': 'Username, password y nombre son obligatorios'}), 400
                
                # Verificar si username existe
                cur.execute("SELECT id FROM usuarios_admin WHERE username = %s", (data['username'],))
                if cur.fetchone():
                    return jsonify({'success': False, 'error': 'El nombre de usuario ya existe'}), 400
                
                # Verificar que el restaurante existe si se proporciona
                restaurante_id = data.get('restaurante_id')
                if restaurante_id:
                    cur.execute("SELECT id FROM restaurantes WHERE id = %s", (restaurante_id,))
                    if not cur.fetchone():
                        return jsonify({'success': False, 'error': 'El restaurante seleccionado no existe'}), 400
                else:
                    restaurante_id = None
                
                pwd_hash = generate_password_hash(data['password'], method='pbkdf2:sha256')
                
                cur.execute('''
                    INSERT INTO usuarios_admin (restaurante_id, username, password_hash, nombre, email, rol, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, 1)
                ''', (
                    restaurante_id,
                    data['username'],
                    pwd_hash,
                    data['nombre'],
                    data.get('email', ''),
                    data.get('rol', 'admin')
                ))
                db.commit()
                return jsonify({'success': True, 'id': cur.lastrowid})

    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_usuarios: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/usuarios/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@superadmin_required
def api_usuario(user_id):
    """API para obtener, editar o eliminar un usuario."""
    db = get_db()
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute('''
                    SELECT id, restaurante_id, username, nombre, email, rol, activo 
                    FROM usuarios_admin WHERE id = %s
                ''', (user_id,))
                user = cur.fetchone()
                if not user:
                    return jsonify({'error': 'Usuario no encontrado'}), 404
                return jsonify(dict_from_row(user))
                
            if request.method == 'PUT':
                data = request.get_json()
                
                if data.get('password'):
                    pwd_hash = generate_password_hash(data['password'], method='pbkdf2:sha256')
                    cur.execute('''
                        UPDATE usuarios_admin SET 
                            restaurante_id = %s, username = %s, password_hash = %s, 
                            nombre = %s, email = %s, rol = %s, activo = %s
                        WHERE id = %s
                    ''', (
                        data.get('restaurante_id'),
                        data.get('username'),
                        pwd_hash,
                        data.get('nombre'),
                        data.get('email', ''),
                        data.get('rol', 'admin'),
                        data.get('activo', 1),
                        user_id
                    ))
                else:
                    cur.execute('''
                        UPDATE usuarios_admin SET 
                            restaurante_id = %s, username = %s, nombre = %s, 
                            email = %s, rol = %s, activo = %s
                        WHERE id = %s
                    ''', (
                        data.get('restaurante_id'),
                        data.get('username'),
                        data.get('nombre'),
                        data.get('email', ''),
                        data.get('rol', 'admin'),
                        data.get('activo', 1),
                        user_id
                    ))
                db.commit()
                return jsonify({'success': True})
                
            if request.method == 'DELETE':
                # No permitir eliminar superadmin
                cur.execute("SELECT username FROM usuarios_admin WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if user and user['username'] == 'superadmin':
                    return jsonify({'success': False, 'error': 'No se puede eliminar el superadmin'}), 400
                
                cur.execute("DELETE FROM usuarios_admin WHERE id = %s", (user_id,))
                db.commit()
                return jsonify({'success': True})

    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.error(f"Error en api_usuario: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# INICIALIZACIÓN DE BASE DE DATOS
# ============================================================

@app.route('/api/init-db')
def init_db_route():
    """Inicializa la base de datos creando las tablas si no existen."""
    try:
        db = get_db()
        messages = []
        
        with db.cursor() as cur:
            # Verificar si las tablas ya existen
            cur.execute("SHOW TABLES")
            existing_tables = [row[list(row.keys())[0]] for row in cur.fetchall()]
            messages.append(f"Tablas existentes: {existing_tables}")
            
            # Crear tabla planes si no existe
            if 'planes' not in existing_tables:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS planes (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        nombre VARCHAR(50) NOT NULL,
                        precio_mensual DECIMAL(10,2) DEFAULT 0,
                        max_platos INT DEFAULT 50,
                        max_categorias INT DEFAULT 10,
                        tiene_pdf TINYINT(1) DEFAULT 1,
                        tiene_qr_personalizado TINYINT(1) DEFAULT 0,
                        tiene_estadisticas TINYINT(1) DEFAULT 1,
                        activo TINYINT(1) DEFAULT 1,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                ''')
                db.commit()
                messages.append("✓ Tabla planes creada")
            
            # Insertar planes por defecto si no existen
            cur.execute("SELECT COUNT(*) as total FROM planes")
            if cur.fetchone()['total'] == 0:
                cur.execute('''
                    INSERT INTO planes (nombre, precio_mensual, max_platos, max_categorias, tiene_pdf, tiene_qr_personalizado, tiene_estadisticas) VALUES
                    ('Gratis', 0, 20, 5, 1, 0, 0),
                    ('Básico', 9990, 50, 10, 1, 0, 1),
                    ('Premium', 19990, 200, 50, 1, 1, 1)
                ''')
                db.commit()
                messages.append("✓ Planes por defecto insertados")
            
            # Crear superadmin si no existe
            cur.execute("SELECT id FROM usuarios_admin WHERE username = 'superadmin'")
            if not cur.fetchone():
                pwd = generate_password_hash('superadmin123', method='pbkdf2:sha256')
                cur.execute('''
                    INSERT INTO usuarios_admin (restaurante_id, username, password_hash, nombre, rol, activo)
                    VALUES (NULL, 'superadmin', %s, 'Super Admin Divergent Studio', 'superadmin', 1)
                ''', (pwd,))
                db.commit()
                messages.append("✓ Usuario superadmin creado")
            else:
                messages.append("✓ Usuario superadmin ya existe")
        
        return jsonify({
            'success': True,
            'message': '✓ Base de datos MySQL inicializada correctamente',
            'details': messages,
            'superadmin_user': 'superadmin',
            'superadmin_pass': 'superadmin123 (¡cambiar en producción!)'
        })
        
    except Exception as e:
        logger.error(f"Error en init-db: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


# ============================================================
# ENDPOINT DE DIAGNÓSTICO
# ============================================================

@app.route('/api/health')
def health_check():
    """Endpoint para verificar que la app está funcionando."""
    import sys
    
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
    
    # Intentar conexión a MySQL
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT 1")
            status['mysql_connection'] = 'ok'
            
            # Verificar tablas
            cur.execute("SHOW TABLES")
            tables = [row[list(row.keys())[0]] for row in cur.fetchall()]
            status['tables'] = tables
            
    except Exception as e:
        status['mysql_connection'] = f'error: {str(e)}'
        status['mysql_traceback'] = traceback.format_exc()
    
    return jsonify(status)


# ============================================================
# ARCHIVOS ESTÁTICOS
# ============================================================

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Sirve archivos subidos."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ============================================================
# EJECUTAR APLICACIÓN
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("🍽️  MENÚ DIGITAL SAAS - Divergent Studio")
    print("=" * 50)
    print(f"📦 MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
    print(f"🌐 Servidor: http://127.0.0.1:5000")
    print("=" * 50)
    print("⚠️  Antes de usar, ejecuta: GET /api/init-db")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
