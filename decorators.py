"""
decorators.py

Decoradores extraídos de `app_menu.py`.
Los decoradores usan `get_db` pasado como argumento a la función de registro
para evitar dependencias circulares cuando sea necesario.
"""
from functools import wraps
from flask import session, redirect, url_for, jsonify, flash, request
import logging

logger = logging.getLogger(__name__)


def make_login_required():
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
    return login_required


def make_restaurante_owner_required():
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
    return restaurante_owner_required


def make_superadmin_required():
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
    return superadmin_required


def make_verificar_suscripcion(get_db):
    """Devuelve el decorador verificar_suscripcion que usa get_db para consultar la BD."""
    def verificar_suscripcion(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Superadmin siempre tiene acceso
            if session.get('rol') == 'superadmin':
                return f(*args, **kwargs)

            restaurante_id = session.get('restaurante_id')
            if not restaurante_id:
                return f(*args, **kwargs)

            try:
                db = get_db()
                with db.cursor() as cur:
                    try:
                        cur.execute('''
                            SELECT fecha_vencimiento, estado_suscripcion 
                            FROM restaurantes WHERE id = %s
                        ''', (restaurante_id,))
                    except Exception as e:
                        logger.warning(f"No se pudo consultar fecha_vencimiento: {e}")
                        return f(*args, **kwargs)

                    rest = cur.fetchone()
                    if rest:
                        fecha_vencimiento = rest.get('fecha_vencimiento') if isinstance(rest, dict) else rest['fecha_vencimiento']
                        if not fecha_vencimiento:
                            return f(*args, **kwargs)

                        try:
                            from datetime import datetime as _dt
                            if isinstance(fecha_vencimiento, str):
                                fecha_vencimiento = _dt.strptime(fecha_vencimiento, '%Y-%m-%d').date()

                            if date.today() > fecha_vencimiento:
                                logger.warning(f"Suscripción expirada para restaurante {restaurante_id}")
                                flash('Tu período de prueba o suscripción ha terminado', 'warning')
                                return redirect(url_for('gestion_pago_pendiente'))
                        except Exception as e:
                            logger.warning(f"Formato de fecha_vencimiento inesperado: {e}")
                            return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"Error al verificar suscripción: {e}")
                return f(*args, **kwargs)

            return f(*args, **kwargs)
        return decorated
    return verificar_suscripcion
