# api_gestion_blueprint.py

from flask import (
    Blueprint, request, jsonify, session, current_app, make_response
)
from functools import wraps
from datetime import date, timedelta

# Cloudinary y PDFKit (opcional, no crítico para API de platos)
try:
    from cloudinary.uploader import upload as cloudinary_upload
    CLOUDINARY_AVAILABLE = True
except Exception:
    cloudinary_upload = None
    CLOUDINARY_AVAILABLE = False
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    pdfkit = None
    PDFKIT_AVAILABLE = False

# Import original: get_db y limiter desde app_factory (como antes de la refactorización)
from app_factory import get_db, limiter

# Blueprint setup for APIs
api_gestion_bp = Blueprint('api_gestion', __name__, url_prefix='/api')


def register_api_gestion(app):
    """Register this blueprint on the given app."""
    app.register_blueprint(api_gestion_bp)
    app.logger.info('Registered api_gestion blueprint')
    return app


# ============================================================
# HELPER FUNCTIONS and DECORATORS
# ============================================================

def list_from_rows(rows):
    return [dict(row) for row in rows] if rows else []

def dict_from_row(row):
    return dict(row) if row else None

def allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated

def restaurante_owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') == 'consulta':
            return jsonify({'error': 'Acceso denegado. Rol de solo lectura.'}), 403
        return f(*args, **kwargs)
    return decorated

# ============================================================
# API ROUTES
# ============================================================

@api_gestion_bp.route('/platos', methods=['GET', 'POST'])
@login_required
@limiter.limit("30 per minute")
def api_platos():
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                # --- Filtros y paginación ---
                page = int(request.args.get('page', 1))
                per_page = int(request.args.get('per_page', 20))
                search = request.args.get('search', '').strip().lower()
                categoria_id = request.args.get('categoria_id')

                params = [restaurante_id]
                where_clauses = ['p.restaurante_id = %s']

                if categoria_id:
                    where_clauses.append('p.categoria_id = %s')
                    params.append(categoria_id)

                if search:
                    where_clauses.append('(LOWER(p.nombre) LIKE %s OR LOWER(p.descripcion) LIKE %s)')
                    params.extend([f'%{search}%', f'%{search}%'])

                where_sql = ' AND '.join(where_clauses)

                # Count total
                count_sql = f'SELECT COUNT(1) as total FROM platos p WHERE {where_sql}'
                cur.execute(count_sql, tuple(params))
                total = cur.fetchone()['total']

                # Pagination
                offset = (page - 1) * per_page
                sql = f'''
                    SELECT p.id, p.categoria_id, p.nombre, p.descripcion, p.precio, p.precio_oferta, p.imagen_url, p.etiquetas, p.es_vegetariano, p.es_vegano, p.es_sin_gluten, p.es_picante, p.es_nuevo, p.es_popular, p.orden, p.activo, c.nombre as categoria_nombre
                    FROM platos p
                    LEFT JOIN categorias c ON p.categoria_id = c.id
                    WHERE {where_sql}
                    ORDER BY p.orden, p.nombre
                    LIMIT %s OFFSET %s
                '''
                cur.execute(sql, tuple(params) + (per_page, offset))
                platos = list_from_rows(cur.fetchall())
                return jsonify({
                    'results': platos,
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'total_pages': (total + per_page - 1) // per_page
                })

            if request.method == 'POST':
                data = request.get_json()
                # ... (logic to insert plato)
                cur.execute("INSERT INTO platos (restaurante_id, categoria_id, nombre) VALUES (%s, %s, %s)", (restaurante_id, data.get('categoria_id'), data.get('nombre')))
                db.commit()
                return jsonify({'success': True, 'id': cur.lastrowid})
    except Exception as e:
        current_app.logger.error(f"Error en api_platos: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@api_gestion_bp.route('/platos/<int:plato_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@restaurante_owner_required
def api_plato(plato_id):
    db = get_db()
    restaurante_id = session['restaurante_id']

    try:
        with db.cursor() as cur:
            # Check if plato exists and belongs to the restaurant
            cur.execute("SELECT id FROM platos WHERE id = %s AND restaurante_id = %s", (plato_id, restaurante_id))
            if not cur.fetchone():
                return jsonify({'error': 'Plato no encontrado'}), 404

            if request.method == 'GET':
                cur.execute("""
                    SELECT p.id, p.categoria_id, p.nombre, p.descripcion, p.precio, p.precio_oferta, p.imagen_url, p.etiquetas, p.es_vegetariano, p.es_vegano, p.es_sin_gluten, p.es_picante, p.es_nuevo, p.es_popular, p.orden, p.activo, c.nombre as categoria_nombre
                    FROM platos p
                    LEFT JOIN categorias c ON p.categoria_id = c.id
                    WHERE p.id = %s
                """, (plato_id,))
                return jsonify(dict_from_row(cur.fetchone()))

            if request.method == 'PUT':
                data = request.get_json()
                # ... (logic to update plato)
                return jsonify({'success': True})

            if request.method == 'DELETE':
                cur.execute("DELETE FROM platos WHERE id = %s", (plato_id,))
                db.commit()
                return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error en api_plato {plato_id}: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# APARIENCIA DEL RESTAURANTE (TEMA, OPCIONES VISUALES)
# ============================================================

@api_gestion_bp.route('/mi-restaurante/apariencia', methods=['PUT'])
@login_required
@restaurante_owner_required
def api_apariencia_restaurante():
    db = get_db()
    restaurante_id = session.get('restaurante_id')
    if not restaurante_id:
        return jsonify({'success': False, 'error': 'Restaurante no encontrado en sesión'}), 400


    data = request.get_json() or {}

    # Validar tema
    temas_validos = {'clasico', 'moderno', 'elegante', 'natural', 'marino', 'calido'}
    tema = str(data.get('tema', '')).strip().lower()
    if tema not in temas_validos:
        return jsonify({'success': False, 'error': 'Tema inválido'}), 400

    # Validar booleanos
    def to_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return val != 0
        if isinstance(val, str):
            return val.lower() in ('1', 'true', 'si', 'yes', 'on')
        return False

    mostrar_precios = 1 if to_bool(data.get('mostrar_precios', True)) else 0
    mostrar_descripciones = 1 if to_bool(data.get('mostrar_descripciones', True)) else 0
    mostrar_imagenes = 1 if to_bool(data.get('mostrar_imagenes', True)) else 0

    try:
        with db.cursor() as cur:
            cur.execute("""
                UPDATE restaurantes
                SET tema = %s,
                    mostrar_precios = %s,
                    mostrar_descripciones = %s,
                    mostrar_imagenes = %s,
                    fecha_actualizacion = NOW()
                WHERE id = %s
            """, (tema, mostrar_precios, mostrar_descripciones, mostrar_imagenes, restaurante_id))
            db.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error actualizando apariencia restaurante: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
