# ============================================================
# MENU DIGITAL SAAS - DIVERGENT STUDIO
# Sistema Multi-Tenant para Menús Digitales
# ============================================================

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g, send_from_directory
import os
import sqlite3
import uuid
import logging
logger = logging.getLogger(__name__) 
from functools import wraps
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- CONFIGURACIÓN ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'menu_digital_divergent_secret_key_2025')

# Añadir función now() a Jinja2 para templates
app.jinja_env.globals['now'] = datetime.now

# Configuración para producción
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

# Configuración de SQLite (en producción usar MySQL)
DATABASE = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'menu_digital.db'))

# Dominio base para QR (cambiar en producción)
# En desarrollo usar tu IP local para que funcione el QR desde móvil
BASE_URL = os.environ.get('BASE_URL', 'http://192.168.100.19:5001')

def get_db():
    """Obtiene una conexión a la base de datos SQLite."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # Para acceder a columnas por nombre
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Cierra la conexión a la base de datos al terminar la request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def dict_from_row(row):
    """Convierte una fila de SQLite a diccionario."""
    if row is None:
        return None
    return dict(row)

def list_from_rows(rows):
    """Convierte una lista de filas de SQLite a lista de diccionarios."""
    return [dict(row) for row in rows]

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
            cur = db.cursor()
            cur.execute("SELECT url_slug FROM restaurantes WHERE id = ?", (session['restaurante_id'],))
            row = cur.fetchone()
            if row and row[0]:
                menu_url = f"/menu/{row[0]}"
        except Exception as e:
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug("Failed to inject menu_url (sqlite): %s", e, exc_info=True)
            except Exception:
                pass
    return {'menu_url_global': menu_url}

# ============================================================
# DECORADORES PERSONALIZADOS PARA EL MENÚ
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
        cur = db.cursor()
        
        # Obtener información del visitante
        ip_address = req.headers.get('X-Forwarded-For', req.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        user_agent = req.headers.get('User-Agent', '')[:500]  # Limitar tamaño
        referer = req.headers.get('Referer', '')[:255]
        
        # Detectar si es móvil (probablemente escaneo QR)
        es_movil = any(x in user_agent.lower() for x in ['mobile', 'android', 'iphone', 'ipad'])
        
        # Insertar registro de visita
        cur.execute('''
            INSERT INTO visitas (restaurante_id, fecha, ip_address, user_agent, referer, es_movil)
            VALUES (?, datetime('now'), ?, ?, ?, ?)
        ''', (restaurante_id, ip_address, user_agent, referer, 1 if es_movil else 0))
        
        # Actualizar contador diario en estadísticas
        hoy = date.today().isoformat()
        cur.execute('''
            INSERT INTO estadisticas_diarias (restaurante_id, fecha, visitas, escaneos_qr)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(restaurante_id, fecha) DO UPDATE SET
                visitas = visitas + 1,
                escaneos_qr = escaneos_qr + ?
        ''', (restaurante_id, hoy, 1 if es_movil else 0, 1 if es_movil else 0))
        
        db.commit()
    except Exception as e:
        # No fallar si hay error en tracking (no afectar experiencia del usuario)
        logger.exception("Error registrando visita: %s", e)

# ============================================================
# RUTAS PÚBLICAS (EL MENÚ QUE VE EL CLIENTE)
# ============================================================

@app.route('/')
def index():
    """Página de inicio."""
    return render_template('index.html')

@app.route('/menu/<string:url_slug>')
def ver_menu_publico(url_slug):
    """
    Ruta pública para ver el menú. Accesible por QR.
    Esta es la ruta crítica que debe ser ultra rápida.
    """
    try:
        db = get_db()
        cur = db.cursor()
        
        # 1. Obtener datos del restaurante por su slug
        cur.execute("SELECT * FROM restaurantes WHERE url_slug = ? AND activo = 1", (url_slug,))
        row = cur.fetchone()
        
        if not row:
            return render_template('menu_404.html', slug=url_slug), 404
        
        restaurante = dict_from_row(row)
        
        # Permitir preview de tema desde la página de apariencia
        preview_tema = request.args.get('preview_tema')
        if preview_tema:
            restaurante['tema'] = preview_tema
        
        # 2. TRACKING: Registrar visita/escaneo QR (solo si no es preview)
        if not preview_tema:
            registrar_visita(restaurante['id'], request)

        # 3. Obtener categorías y platos en una sola consulta optimizada
        cur.execute('''
            SELECT c.id as categoria_id, c.nombre as categoria_nombre, p.id as plato_id, p.nombre as plato_nombre, 
                   p.descripcion, p.precio, p.imagen_url, p.etiquetas, c.orden, p.activo
            FROM categorias c
            LEFT JOIN platos p ON c.id = p.categoria_id
            WHERE c.restaurante_id = ? AND c.activo = 1 AND (p.activo = 1 OR p.activo IS NULL)
            ORDER BY c.orden, p.nombre
        ''', (restaurante['id'],))
        
        platos_raw = cur.fetchall()

        # 4. Estructurar el menú para el template
        menu_estructurado = {}
        for row in platos_raw:
            row_dict = dict_from_row(row)
            cat_id = row_dict['categoria_id']
            if cat_id not in menu_estructurado:
                menu_estructurado[cat_id] = {
                    'nombre': row_dict['categoria_nombre'],
                    'platos': []
                }
            
            if row_dict['plato_id']:
                plato = {
                    'id': row_dict['plato_id'],
                    'nombre': row_dict['plato_nombre'],
                    'descripcion': row_dict['descripcion'],
                    'precio': float(row_dict['precio'] or 0),
                    'imagen_url': row_dict['imagen_url'],
                    'etiquetas': row_dict['etiquetas'].split(',') if row_dict['etiquetas'] else []
                }
                menu_estructurado[cat_id]['platos'].append(plato)

        return render_template('menu_publico.html', 
                               restaurante=restaurante, 
                               menu=list(menu_estructurado.values()))

    except Exception as e:
        logger.exception("Error al cargar menú para %s: %s", url_slug, e)
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
        cur = db.cursor()
        
        cur.execute('''
            SELECT u.*, r.nombre as restaurante_nombre 
            FROM usuarios_admin u
            LEFT JOIN restaurantes r ON u.restaurante_id = r.id
            WHERE u.username = ? AND u.activo = 1
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
# RUTAS DE GESTIÓN (BACKEND)
# ============================================================

@app.route('/gestion')
@login_required
def menu_gestion():
    """Página principal de gestión para el restaurante logueado."""
    return render_template('gestion/dashboard.html', 
                           restaurante_nombre=session.get('restaurante_nombre', 'Mi Restaurante'))

@app.route('/gestion/platos')
@login_required
def gestion_platos():
    """Vista de CRUD de Platos y Categorías."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM categorias WHERE restaurante_id = ? ORDER BY orden", (session['restaurante_id'],))
    categorias = list_from_rows(cur.fetchall())
    return render_template('gestion/platos.html', categorias=categorias)

@app.route('/gestion/categorias')
@login_required
def gestion_categorias():
    """Vista de CRUD de Categorías."""
    return render_template('gestion/categorias.html')

@app.route('/gestion/mi-restaurante')
@login_required
def gestion_mi_restaurante():
    """Vista para editar información del restaurante."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM restaurantes WHERE id = ?", (session['restaurante_id'],))
    restaurante = dict_from_row(cur.fetchone())
    return render_template('gestion/mi_restaurante.html', restaurante=restaurante, base_url=BASE_URL)

@app.route('/gestion/codigo-qr')
@login_required
def gestion_codigo_qr():
    """Vista para ver y descargar el código QR."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM restaurantes WHERE id = ?", (session['restaurante_id'],))
    restaurante = dict_from_row(cur.fetchone())
    menu_url = f"{BASE_URL}/menu/{restaurante['url_slug']}"
    return render_template('gestion/codigo_qr.html', restaurante=restaurante, menu_url=menu_url)

@app.route('/gestion/apariencia')
@login_required
def gestion_apariencia():
    """Vista para cambiar la apariencia del menú."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM restaurantes WHERE id = ?", (session['restaurante_id'],))
    restaurante = dict_from_row(cur.fetchone())
    return render_template('gestion/apariencia.html', restaurante=restaurante)

# ============================================================
# API DE GESTIÓN (CRUD)
# ============================================================

## API Platos
@app.route('/api/platos', methods=['GET', 'POST'])
@login_required
@restaurante_owner_required
def api_platos():
    db = get_db()
    cur = db.cursor()
    restaurante_id = session['restaurante_id']
    
    try:
        if request.method == 'GET':
            cur.execute("SELECT * FROM platos WHERE restaurante_id = ? ORDER BY nombre", (restaurante_id,))
            return jsonify(list_from_rows(cur.fetchall()))
            
        if request.method == 'POST':
            data = request.get_json()
            
            if not data.get('nombre') or not data.get('precio') or not data.get('categoria_id'):
                return jsonify({'success': False, 'error': 'Nombre, precio y categoría son obligatorios'}), 400
            
            cur.execute('''
                INSERT INTO platos (restaurante_id, categoria_id, nombre, descripcion, precio, imagen_url, etiquetas, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (
                restaurante_id,
                data['categoria_id'],
                data['nombre'],
                data.get('descripcion', ''),
                float(data['precio']),
                data.get('imagen_url', ''),
                data.get('etiquetas', '')
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Plato creado', 'id': cur.lastrowid})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/platos/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@restaurante_owner_required
def api_plato(id):
    db = get_db()
    cur = db.cursor()
    restaurante_id = session['restaurante_id']
    
    try:
        if request.method == 'GET':
            cur.execute("SELECT * FROM platos WHERE id = ? AND restaurante_id = ?", (id, restaurante_id))
            plato = cur.fetchone()
            if not plato:
                return jsonify({'error': 'Plato no encontrado'}), 404
            return jsonify(dict_from_row(plato))
            
        if request.method == 'PUT':
            data = request.get_json()
            cur.execute('''
                UPDATE platos SET 
                    categoria_id = ?, nombre = ?, descripcion = ?, 
                    precio = ?, imagen_url = ?, etiquetas = ?, activo = ?
                WHERE id = ? AND restaurante_id = ?
            ''', (
                data.get('categoria_id'),
                data.get('nombre'),
                data.get('descripcion', ''),
                float(data.get('precio', 0)),
                data.get('imagen_url', ''),
                data.get('etiquetas', ''),
                data.get('activo', 1),
                id,
                restaurante_id
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Plato actualizado'})
            
        if request.method == 'DELETE':
            cur.execute("DELETE FROM platos WHERE id = ? AND restaurante_id = ?", (id, restaurante_id))
            db.commit()
            return jsonify({'success': True, 'message': 'Plato eliminado'})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

## API Subida de Imágenes
@app.route('/api/upload-image', methods=['POST'])
@login_required
@restaurante_owner_required
def api_upload_image():
    """API para subir imágenes de platos o logo del restaurante."""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió ninguna imagen'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Tipo de archivo no permitido. Usa: PNG, JPG, JPEG, GIF o WEBP'}), 400
        
        # Generar nombre único para evitar colisiones
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{session['restaurante_id']}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # Guardar archivo
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Generar URL de la imagen
        image_url = f"/static/uploads/{unique_filename}"
        
        return jsonify({
            'success': True, 
            'message': 'Imagen subida correctamente',
            'url': image_url,
            'filename': unique_filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Sirve los archivos subidos."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

## API Mi Restaurante
@app.route('/api/mi-restaurante', methods=['GET', 'PUT'])
@login_required
@restaurante_owner_required
def api_mi_restaurante():
    """API para obtener/actualizar información del restaurante."""
    db = get_db()
    cur = db.cursor()
    restaurante_id = session['restaurante_id']
    
    try:
        if request.method == 'GET':
            cur.execute("SELECT * FROM restaurantes WHERE id = ?", (restaurante_id,))
            return jsonify(dict_from_row(cur.fetchone()))
        
        if request.method == 'PUT':
            data = request.get_json()
            
            cur.execute('''
                UPDATE restaurantes SET 
                    nombre = ?,
                    descripcion = ?,
                    telefono = ?,
                    email = ?,
                    direccion = ?,
                    horario = ?,
                    logo_url = ?,
                    instagram = ?,
                    facebook = ?,
                    whatsapp = ?
                WHERE id = ?
            ''', (
                data.get('nombre'),
                data.get('descripcion', ''),
                data.get('telefono', ''),
                data.get('email', ''),
                data.get('direccion', ''),
                data.get('horario', ''),
                data.get('logo_url', ''),
                data.get('instagram', ''),
                data.get('facebook', ''),
                data.get('whatsapp', ''),
                restaurante_id
            ))
            db.commit()
            
            # Actualizar nombre en sesión
            if data.get('nombre'):
                session['restaurante_nombre'] = data['nombre']
            
            return jsonify({'success': True, 'message': 'Restaurante actualizado'})
    
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mi-restaurante/apariencia', methods=['PUT'])
@login_required
@restaurante_owner_required
def api_apariencia():
    """API para actualizar la apariencia/tema del menú."""
    db = get_db()
    cur = db.cursor()
    restaurante_id = session['restaurante_id']
    
    try:
        data = request.get_json()
        
        cur.execute('''
            UPDATE restaurantes SET 
                tema = ?,
                mostrar_precios = ?,
                mostrar_descripciones = ?,
                mostrar_imagenes = ?
            WHERE id = ?
        ''', (
            data.get('tema', 'calido'),
            1 if data.get('mostrar_precios', True) else 0,
            1 if data.get('mostrar_descripciones', True) else 0,
            1 if data.get('mostrar_imagenes', True) else 0,
            restaurante_id
        ))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Apariencia actualizada'})
    
    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

## API Categorías
@app.route('/api/categorias', methods=['GET', 'POST'])
@login_required
@restaurante_owner_required
def api_categorias():
    db = get_db()
    cur = db.cursor()
    restaurante_id = session['restaurante_id']
    
    try:
        if request.method == 'GET':
            # Obtener categorías con cantidad de platos
            cur.execute('''
                SELECT c.*, COUNT(p.id) as cantidad_platos 
                FROM categorias c 
                LEFT JOIN platos p ON c.id = p.categoria_id
                WHERE c.restaurante_id = ? 
                GROUP BY c.id
                ORDER BY c.orden, c.nombre
            ''', (restaurante_id,))
            return jsonify(list_from_rows(cur.fetchall()))
            
        if request.method == 'POST':
            data = request.get_json()
            
            if not data.get('nombre'):
                return jsonify({'success': False, 'error': 'Nombre de la categoría es obligatorio'}), 400

            cur.execute("SELECT COALESCE(MAX(orden), 0) + 1 as next_orden FROM categorias WHERE restaurante_id = ?", (restaurante_id,))
            row = cur.fetchone()
            next_orden = data.get('orden', row[0] if row else 1)
            
            cur.execute('''
                INSERT INTO categorias (restaurante_id, nombre, orden, activo)
                VALUES (?, ?, ?, ?)
            ''', (
                restaurante_id,
                data['nombre'],
                next_orden,
                data.get('activo', 1)
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Categoría creada', 'id': cur.lastrowid})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categorias/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@restaurante_owner_required
def api_categoria(id):
    db = get_db()
    cur = db.cursor()
    restaurante_id = session['restaurante_id']
    
    try:
        if request.method == 'GET':
            cur.execute("SELECT * FROM categorias WHERE id = ? AND restaurante_id = ?", (id, restaurante_id))
            categoria = cur.fetchone()
            if not categoria:
                return jsonify({'error': 'Categoría no encontrada'}), 404
            return jsonify(dict_from_row(categoria))
            
        if request.method == 'PUT':
            data = request.get_json()
            cur.execute('''
                UPDATE categorias SET nombre = ?, orden = ?, activo = ?
                WHERE id = ? AND restaurante_id = ?
            ''', (
                data.get('nombre'),
                data.get('orden', 0),
                data.get('activo', 1),
                id,
                restaurante_id
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Categoría actualizada'})
            
        if request.method == 'DELETE':
            # Verificar si hay platos asociados
            cur.execute("SELECT COUNT(*) FROM platos WHERE categoria_id = ?", (id,))
            count = cur.fetchone()[0]
            if count > 0:
                return jsonify({'success': False, 'error': f'No puedes eliminar esta categoría porque tiene {count} platos asociados. Elimina o mueve los platos primero.'}), 400
            
            cur.execute("DELETE FROM categorias WHERE id = ? AND restaurante_id = ?", (id, restaurante_id))
            db.commit()
            return jsonify({'success': True, 'message': 'Categoría eliminada'})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# RUTAS DE ADMINISTRACIÓN SAAS (SUPERADMIN)
# ============================================================

@app.route('/superadmin/restaurantes')
@login_required
@superadmin_required
def superadmin_restaurantes():
    db = get_db()
    cur = db.cursor()
    
    # Obtener todos los restaurantes con estadísticas adicionales
    cur.execute("""
        SELECT r.*, 
               (SELECT COUNT(*) FROM categorias WHERE restaurante_id = r.id) as total_categorias,
               (SELECT COUNT(*) FROM platos WHERE restaurante_id = r.id) as total_platos,
               (SELECT COUNT(*) FROM usuarios_admin WHERE restaurante_id = r.id) as total_usuarios,
               (SELECT COUNT(*) FROM visitas_menu WHERE restaurante_id = r.id) as total_visitas
        FROM restaurantes r 
        ORDER BY r.nombre
    """)
    restaurantes = list_from_rows(cur.fetchall())
    
    # Contar nuevos restaurantes este mes
    primer_dia_mes = date.today().replace(day=1).isoformat()
    cur.execute("SELECT COUNT(*) FROM restaurantes WHERE fecha_creacion >= ?", (primer_dia_mes,))
    nuevos_este_mes = cur.fetchone()[0] or 0
    
    # Contar total de usuarios
    cur.execute("SELECT COUNT(*) FROM usuarios_admin WHERE rol != 'superadmin'")
    total_usuarios = cur.fetchone()[0] or 0
    
    return render_template('superadmin/restaurantes.html', 
                           restaurantes=restaurantes,
                           nuevos_este_mes=nuevos_este_mes,
                           total_usuarios=total_usuarios)

@app.route('/api/restaurantes', methods=['GET', 'POST'])
@login_required
@superadmin_required
def api_restaurantes():
    db = get_db()
    cur = db.cursor()
    
    try:
        if request.method == 'GET':
            cur.execute("SELECT * FROM restaurantes ORDER BY nombre")
            return jsonify(list_from_rows(cur.fetchall()))
            
        if request.method == 'POST':
            data = request.get_json()
            
            if not data.get('nombre') or not data.get('url_slug'):
                return jsonify({'success': False, 'error': 'Nombre y URL slug son obligatorios'}), 400
            
            cur.execute('''
                INSERT INTO restaurantes (nombre, rut, url_slug, logo_url, tema, activo)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (
                data['nombre'],
                data.get('rut', ''),
                data['url_slug'],
                data.get('logo_url', ''),
                data.get('tema', 'default')
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Restaurante creado', 'id': cur.lastrowid})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/restaurantes/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@superadmin_required
def api_restaurante(id):
    """API para obtener, editar o eliminar un restaurante."""
    db = get_db()
    cur = db.cursor()
    
    try:
        if request.method == 'GET':
            cur.execute("SELECT * FROM restaurantes WHERE id = ?", (id,))
            rest = cur.fetchone()
            if not rest:
                return jsonify({'error': 'Restaurante no encontrado'}), 404
            return jsonify(dict_from_row(rest))
            
        if request.method == 'PUT':
            data = request.get_json()
            cur.execute('''
                UPDATE restaurantes SET 
                    nombre = ?, rut = ?, url_slug = ?, logo_url = ?, tema = ?, activo = ?
                WHERE id = ?
            ''', (
                data.get('nombre'),
                data.get('rut', ''),
                data.get('url_slug'),
                data.get('logo_url', ''),
                data.get('tema', 'default'),
                data.get('activo', 1),
                id
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Restaurante actualizado'})
            
        if request.method == 'DELETE':
            # Eliminar usuarios asociados primero
            cur.execute("DELETE FROM usuarios_admin WHERE restaurante_id = ?", (id,))
            # Eliminar categorías y platos (cascade debería manejar esto)
            cur.execute("DELETE FROM platos WHERE restaurante_id = ?", (id,))
            cur.execute("DELETE FROM categorias WHERE restaurante_id = ?", (id,))
            cur.execute("DELETE FROM restaurantes WHERE id = ?", (id,))
            db.commit()
            return jsonify({'success': True, 'message': 'Restaurante eliminado'})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# API para crear usuarios de restaurantes
@app.route('/api/usuarios', methods=['GET', 'POST'])
@login_required
@superadmin_required
def api_usuarios():
    db = get_db()
    cur = db.cursor()
    
    try:
        if request.method == 'GET':
            cur.execute('''
                SELECT u.*, r.nombre as restaurante_nombre 
                FROM usuarios_admin u 
                LEFT JOIN restaurantes r ON u.restaurante_id = r.id
                ORDER BY u.nombre
            ''')
            usuarios = list_from_rows(cur.fetchall())
            # Eliminar password_hash de la respuesta
            for u in usuarios:
                u.pop('password_hash', None)
            return jsonify(usuarios)
            
        if request.method == 'POST':
            data = request.get_json()
            
            if not data.get('username') or not data.get('password') or not data.get('nombre'):
                return jsonify({'success': False, 'error': 'Username, password y nombre son obligatorios'}), 400
            
            # Verificar si el username ya existe
            cur.execute("SELECT id FROM usuarios_admin WHERE username = ?", (data['username'],))
            if cur.fetchone():
                return jsonify({'success': False, 'error': 'El nombre de usuario ya existe'}), 400
            
            pwd_hash = generate_password_hash(data['password'], method='pbkdf2:sha256')
            
            cur.execute('''
                INSERT INTO usuarios_admin (restaurante_id, username, password_hash, nombre, rol, activo)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (
                data.get('restaurante_id'),  # Puede ser NULL para superadmin
                data['username'],
                pwd_hash,
                data['nombre'],
                data.get('rol', 'admin')
            ))
            db.commit()
            return jsonify({'success': True, 'message': 'Usuario creado', 'id': cur.lastrowid})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/usuarios/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@superadmin_required
def api_usuario(id):
    """API para obtener, editar o eliminar un usuario."""
    db = get_db()
    cur = db.cursor()
    
    try:
        if request.method == 'GET':
            cur.execute("SELECT * FROM usuarios_admin WHERE id = ?", (id,))
            user = cur.fetchone()
            if not user:
                return jsonify({'error': 'Usuario no encontrado'}), 404
            user_dict = dict_from_row(user)
            user_dict.pop('password_hash', None)
            return jsonify(user_dict)
            
        if request.method == 'PUT':
            data = request.get_json()
            
            # Si se proporciona nueva contraseña, actualizarla
            if data.get('password'):
                pwd_hash = generate_password_hash(data['password'], method='pbkdf2:sha256')
                cur.execute('''
                    UPDATE usuarios_admin SET 
                        restaurante_id = ?, username = ?, password_hash = ?, nombre = ?, rol = ?, activo = ?
                    WHERE id = ?
                ''', (
                    data.get('restaurante_id'),
                    data.get('username'),
                    pwd_hash,
                    data.get('nombre'),
                    data.get('rol', 'admin'),
                    data.get('activo', 1),
                    id
                ))
            else:
                cur.execute('''
                    UPDATE usuarios_admin SET 
                        restaurante_id = ?, username = ?, nombre = ?, rol = ?, activo = ?
                    WHERE id = ?
                ''', (
                    data.get('restaurante_id'),
                    data.get('username'),
                    data.get('nombre'),
                    data.get('rol', 'admin'),
                    data.get('activo', 1),
                    id
                ))
            db.commit()
            return jsonify({'success': True, 'message': 'Usuario actualizado'})
            
        if request.method == 'DELETE':
            # No permitir eliminar al superadmin principal
            cur.execute("SELECT username FROM usuarios_admin WHERE id = ?", (id,))
            user = cur.fetchone()
            if user and user[0] == 'superadmin':
                return jsonify({'success': False, 'error': 'No se puede eliminar al superadmin principal'}), 400
            
            cur.execute("DELETE FROM usuarios_admin WHERE id = ?", (id,))
            db.commit()
            return jsonify({'success': True, 'message': 'Usuario eliminado'})

    except Exception as e:
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API ESTADÍSTICAS Y DASHBOARD
# ============================================================

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """Obtiene estadísticas del restaurante para el dashboard."""
    db = get_db()
    cur = db.cursor()
    restaurante_id = session.get('restaurante_id')
    
    # Si no hay restaurante_id (ej: superadmin), retornar valores vacíos
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
        # Contar platos activos
        cur.execute("SELECT COUNT(*) FROM platos WHERE restaurante_id = ? AND activo = 1", (restaurante_id,))
        total_platos = cur.fetchone()[0]
        
        # Contar categorías
        cur.execute("SELECT COUNT(*) FROM categorias WHERE restaurante_id = ? AND activo = 1", (restaurante_id,))
        total_categorias = cur.fetchone()[0]
        
        # Obtener url_slug del restaurante
        cur.execute("SELECT url_slug FROM restaurantes WHERE id = ?", (restaurante_id,))
        row = cur.fetchone()
        url_slug = row[0] if row else ''
        
        # Obtener visitas del mes actual
        primer_dia_mes = date.today().replace(day=1).isoformat()
        cur.execute('''
            SELECT COALESCE(SUM(visitas), 0), COALESCE(SUM(escaneos_qr), 0)
            FROM estadisticas_diarias 
            WHERE restaurante_id = ? AND fecha >= ?
        ''', (restaurante_id, primer_dia_mes))
        stats_row = cur.fetchone()
        total_vistas = stats_row[0] if stats_row else 0
        total_scans = stats_row[1] if stats_row else 0
        
        # Obtener visitas de hoy
        hoy = date.today().isoformat()
        cur.execute('''
            SELECT COALESCE(visitas, 0), COALESCE(escaneos_qr, 0)
            FROM estadisticas_diarias 
            WHERE restaurante_id = ? AND fecha = ?
        ''', (restaurante_id, hoy))
        hoy_row = cur.fetchone()
        visitas_hoy = hoy_row[0] if hoy_row else 0
        scans_hoy = hoy_row[1] if hoy_row else 0
        
        # Obtener últimos 7 días para gráfico
        cur.execute('''
            SELECT fecha, visitas, escaneos_qr
            FROM estadisticas_diarias 
            WHERE restaurante_id = ? AND fecha >= date('now', '-7 days')
            ORDER BY fecha
        ''', (restaurante_id,))
        ultimos_7_dias = [{'fecha': r[0], 'visitas': r[1], 'scans': r[2]} for r in cur.fetchall()]
        
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
# SCRIPTS DE CREACIÓN DE TABLAS (SQLite)
# ============================================================

@app.route('/api/crear-tablas-menu')
def crear_tablas_menu():
    """Crea todas las tablas necesarias para el sistema de menú."""
    try:
        db = get_db()
        cur = db.cursor()
        
        # 1. Tabla Restaurantes
        cur.execute('''
            CREATE TABLE IF NOT EXISTS restaurantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                rut TEXT UNIQUE,
                url_slug TEXT UNIQUE NOT NULL,
                logo_url TEXT,
                tema TEXT DEFAULT 'calido',
                descripcion TEXT,
                telefono TEXT,
                email TEXT,
                direccion TEXT,
                horario TEXT,
                instagram TEXT,
                facebook TEXT,
                whatsapp TEXT,
                mostrar_precios INTEGER DEFAULT 1,
                mostrar_descripciones INTEGER DEFAULT 1,
                mostrar_imagenes INTEGER DEFAULT 1,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Tabla Usuarios Admin
        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuarios_admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre TEXT,
                rol TEXT DEFAULT 'usuario',
                activo INTEGER DEFAULT 1,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
            )
        ''')
        
        # 3. Tabla Categorías
        cur.execute('''
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                orden INTEGER DEFAULT 0,
                activo INTEGER DEFAULT 1,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
            )
        ''')
        
        # 4. Tabla Platos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS platos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                categoria_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                imagen_url TEXT,
                etiquetas TEXT,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
            )
        ''')
        
        # Crear SuperAdmin inicial (verificar si ya existe)
        cur.execute("SELECT id FROM usuarios_admin WHERE username = 'superadmin'")
        if not cur.fetchone():
            pwd = generate_password_hash('superadmin123', method='pbkdf2:sha256')
            cur.execute('''
                INSERT INTO usuarios_admin (restaurante_id, username, password_hash, nombre, rol, activo)
                VALUES (NULL, 'superadmin', ?, 'Super Admin Divergent Studio', 'superadmin', 1)
            ''', (pwd,))
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Tablas del Menú Digital creadas correctamente (SQLite).',
            'superadmin_user': 'superadmin',
            'superadmin_pass': 'superadmin123'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# INICIALIZACIÓN DE BASE DE DATOS
# ============================================================

def init_db():
    """Inicializa la base de datos creando las tablas si no existen."""
    import sqlite3
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    
    # 1. Tabla Restaurantes
    cur.execute('''
        CREATE TABLE IF NOT EXISTS restaurantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            rut TEXT,
            url_slug TEXT UNIQUE NOT NULL,
            logo_url TEXT,
            tema TEXT DEFAULT 'calido',
            descripcion TEXT,
            telefono TEXT,
            email TEXT,
            direccion TEXT,
            horario TEXT,
            instagram TEXT,
            facebook TEXT,
            whatsapp TEXT,
            mostrar_precios INTEGER DEFAULT 1,
            mostrar_descripciones INTEGER DEFAULT 1,
            mostrar_imagenes INTEGER DEFAULT 1,
            activo INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Tabla Usuarios Admin
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios_admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurante_id INTEGER,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT,
            rol TEXT DEFAULT 'usuario',
            activo INTEGER DEFAULT 1,
            FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
        )
    ''')
    
    # 3. Tabla Categorías
    cur.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurante_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            orden INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
        )
    ''')
    
    # 4. Tabla Platos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS platos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurante_id INTEGER NOT NULL,
            categoria_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio REAL NOT NULL,
            imagen_url TEXT,
            etiquetas TEXT,
            activo INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
        )
    ''')
    
    # 5. Tabla Visitas (tracking de escaneos QR)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurante_id INTEGER NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            referer TEXT,
            es_movil INTEGER DEFAULT 0,
            FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
        )
    ''')
    
    # 6. Tabla Estadísticas Diarias (resumen para dashboard)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS estadisticas_diarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurante_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            visitas INTEGER DEFAULT 0,
            escaneos_qr INTEGER DEFAULT 0,
            UNIQUE(restaurante_id, fecha),
            FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
        )
    ''')
    
    # Índices para mejorar rendimiento
    cur.execute('CREATE INDEX IF NOT EXISTS idx_visitas_restaurante_fecha ON visitas(restaurante_id, fecha)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_estadisticas_restaurante_fecha ON estadisticas_diarias(restaurante_id, fecha)')
    
    # Crear SuperAdmin inicial (verificar si ya existe)
    cur.execute("SELECT id FROM usuarios_admin WHERE username = 'superadmin'")
    if not cur.fetchone():
        pwd = generate_password_hash('superadmin123', method='pbkdf2:sha256')
        cur.execute('''
            INSERT INTO usuarios_admin (restaurante_id, username, password_hash, nombre, rol, activo)
            VALUES (NULL, 'superadmin', ?, 'Super Admin Divergent Studio', 'superadmin', 1)
        ''', (pwd,))
    
    conn.commit()
    conn.close()
    logger.info("✓ Base de datos inicializada correctamente")

def crear_datos_demo():
    """Crea datos de demostración para probar el sistema."""
    import sqlite3
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    
    # Verificar si ya existe el restaurante demo
    cur.execute("SELECT id FROM restaurantes WHERE url_slug = 'pizzeria-don-luigi'")
    if cur.fetchone():
        conn.close()
        return  # Ya existe, no crear de nuevo
    
    # 1. Crear restaurante de ejemplo
    cur.execute('''
        INSERT INTO restaurantes (nombre, rut, url_slug, logo_url, tema, activo)
        VALUES ('Pizzería Don Luigi', '12.345.678-9', 'pizzeria-don-luigi', '', 'default', 1)
    ''')
    restaurante_id = cur.lastrowid
    
    # 2. Crear usuario admin para el restaurante
    pwd = generate_password_hash('demo123', method='pbkdf2:sha256')
    cur.execute('''
        INSERT INTO usuarios_admin (restaurante_id, username, password_hash, nombre, rol, activo)
        VALUES (?, 'demo', ?, 'Usuario Demo', 'admin', 1)
    ''', (restaurante_id, pwd))
    
    # 3. Crear categorías de ejemplo
    categorias = [
        ('Pizzas Clásicas', 1),
        ('Pizzas Especiales', 2),
        ('Pastas', 3),
        ('Bebidas', 4),
        ('Postres', 5)
    ]
    
    categoria_ids = {}
    for nombre, orden in categorias:
        cur.execute('''
            INSERT INTO categorias (restaurante_id, nombre, orden, activo)
            VALUES (?, ?, ?, 1)
        ''', (restaurante_id, nombre, orden))
        categoria_ids[nombre] = cur.lastrowid
    
    # 4. Crear platos de ejemplo con imágenes de Unsplash
    platos = [
        # Pizzas Clásicas
        (categoria_ids['Pizzas Clásicas'], 'Pizza Margherita', 'Salsa de tomate, mozzarella fresca y albahaca', 8500, 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400&h=300&fit=crop', 'popular'),
        (categoria_ids['Pizzas Clásicas'], 'Pizza Pepperoni', 'Salsa de tomate, mozzarella y pepperoni', 9500, 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=400&h=300&fit=crop', 'picante'),
        (categoria_ids['Pizzas Clásicas'], 'Pizza Hawaiana', 'Salsa de tomate, mozzarella, jamón y piña', 9000, 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400&h=300&fit=crop', ''),
        (categoria_ids['Pizzas Clásicas'], 'Pizza Cuatro Quesos', 'Mozzarella, gorgonzola, parmesano y fontina', 10500, 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&h=300&fit=crop', 'nuevo'),
        
        # Pizzas Especiales
        (categoria_ids['Pizzas Especiales'], 'Pizza Don Luigi', 'Nuestra especialidad: champiñones, jamón serrano, rúcula y parmesano', 12500, 'https://images.unsplash.com/photo-1593560708920-61dd98c46a4e?w=400&h=300&fit=crop', 'popular,nuevo'),
        (categoria_ids['Pizzas Especiales'], 'Pizza Vegetariana', 'Pimientos, champiñones, aceitunas, cebolla y tomate', 10000, 'https://images.unsplash.com/photo-1511689660979-10d2b1aada49?w=400&h=300&fit=crop', 'vegano'),
        (categoria_ids['Pizzas Especiales'], 'Pizza Diávola', 'Salami picante, jalapeños y aceite de chile', 11000, 'https://images.unsplash.com/photo-1458642849426-cfb724f15ef7?w=400&h=300&fit=crop', 'picante'),
        
        # Pastas
        (categoria_ids['Pastas'], 'Spaghetti Carbonara', 'Pasta con huevo, guanciale, pecorino y pimienta negra', 8000, 'https://images.unsplash.com/photo-1612874742237-6526221588e3?w=400&h=300&fit=crop', ''),
        (categoria_ids['Pastas'], 'Lasagna Clásica', 'Capas de pasta, ragú de carne, bechamel y queso gratinado', 9500, 'https://images.unsplash.com/photo-1619895092538-128341789043?w=400&h=300&fit=crop', 'popular'),
        (categoria_ids['Pastas'], 'Ravioli de Ricotta', 'Rellenos de ricotta y espinaca con salsa de tomate', 9000, 'https://images.unsplash.com/photo-1587740908075-9e245070dfaa?w=400&h=300&fit=crop', 'vegetariano'),
        
        # Bebidas
        (categoria_ids['Bebidas'], 'Coca-Cola', 'Lata 350ml', 2000, 'https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=400&h=300&fit=crop', ''),
        (categoria_ids['Bebidas'], 'Agua Mineral', 'Botella 500ml', 1500, 'https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=400&h=300&fit=crop', ''),
        (categoria_ids['Bebidas'], 'Limonada Natural', 'Preparada al momento', 2500, 'https://images.unsplash.com/photo-1621263764928-df1444c5e859?w=400&h=300&fit=crop', 'nuevo'),
        (categoria_ids['Bebidas'], 'Cerveza Artesanal', 'Variedad del día', 3500, 'https://images.unsplash.com/photo-1608270586620-248524c67de9?w=400&h=300&fit=crop', ''),
        
        # Postres
        (categoria_ids['Postres'], 'Tiramisú', 'Clásico italiano con mascarpone y café', 4500, 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400&h=300&fit=crop', 'popular'),
        (categoria_ids['Postres'], 'Panna Cotta', 'Con coulis de frutos rojos', 4000, 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400&h=300&fit=crop', ''),
        (categoria_ids['Postres'], 'Helado Artesanal', '2 bochas del sabor que prefieras', 3000, 'https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?w=400&h=300&fit=crop', ''),
    ]
    
    for cat_id, nombre, descripcion, precio, imagen, etiquetas in platos:
        cur.execute('''
            INSERT INTO platos (restaurante_id, categoria_id, nombre, descripcion, precio, imagen_url, etiquetas, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (restaurante_id, cat_id, nombre, descripcion, precio, imagen, etiquetas))
    
    conn.commit()
    conn.close()
    logger.info("✓ Datos de demostración creados")
    logger.info("  → Restaurante: Pizzería Don Luigi")
    logger.info("  → Usuario: demo | Contraseña: demo123")
    logger.info("  → Menú público: http://localhost:5001/menu/pizzeria-don-luigi")

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    # Inicializar la base de datos automáticamente al iniciar
    init_db()
    crear_datos_demo()
    logger.info("✓ Servidor iniciando en http://localhost:5001")
    logger.info("✓ Acceso desde red local: http://192.168.100.19:5001")
    logger.info("✓ SuperAdmin: superadmin | Contraseña: superadmin123")
    app.run(debug=True, port=5001, host='0.0.0.0')
