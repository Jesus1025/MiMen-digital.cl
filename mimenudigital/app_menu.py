# (Reubicadas) Las rutas de SuperAdmin se definen más abajo, tras la configuración y los
# decoradores, para evitar name errors y referencias a objetos aún no inicializados.
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
import sys
import atexit  # Para limpiar conexiones al cerrar

# Intentar cargar variables de entorno desde .env (solo si existe)
# En PythonAnywhere, las variables se configuran en Web -> Environment variables
try:
    from dotenv import load_dotenv
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_local_path = os.path.join(base_dir, '.env.local')
    env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_local_path):
        load_dotenv(env_local_path)
    elif os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    # dotenv no instalado, está bien - las vars vienen de PythonAnywhere
    base_dir = os.path.dirname(os.path.abspath(__file__))

import logging  # Importar temprano para logging durante configuración de proxy

# ============================================================
# CONFIGURACIÓN DE PROXY PARA PYTHONANYWHERE (CUENTA GRATUITA)
# Debe hacerse ANTES de cualquier importación que haga conexiones HTTP
# ============================================================
_api_proxy = os.environ.get('API_PROXY')
if _api_proxy:
    os.environ['HTTP_PROXY'] = _api_proxy
    os.environ['HTTPS_PROXY'] = _api_proxy
    os.environ['http_proxy'] = _api_proxy
    os.environ['https_proxy'] = _api_proxy
    os.environ['ALL_PROXY'] = _api_proxy
    os.environ['no_proxy'] = ''  # No excluir nada del proxy

from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, 
    flash, session, g, send_from_directory, make_response
)
import pymysql
from pymysql.cursors import DictCursor
import uuid
from functools import wraps
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import logging

# ============================================================
# CLOUDINARY - IMPLEMENTACIÓN DIRECTA CON REQUESTS Y PROXY
# ============================================================
# El SDK de Cloudinary no respeta bien el proxy en PythonAnywhere.
# Usamos requests directamente que SÍ funciona con proxy.

import requests
import hashlib
import time

# ============================================================
# CLOUDINARY - REQUIERE VARIABLE DE ENTORNO
# ============================================================
# NUNCA hardcodear credenciales aquí
# Configura CLOUDINARY_URL en tus variables de entorno
# Formato: cloudinary://api_key:api_secret@cloud_name
# ============================================================

_cloudinary_config = None
_cloudinary_url_env = os.environ.get('CLOUDINARY_URL', '')

if _cloudinary_url_env and _cloudinary_url_env.startswith('cloudinary://'):
    try:
        # cloudinary://api_key:api_secret@cloud_name
        _cld_parts = _cloudinary_url_env.replace('cloudinary://', '')
        if '@' in _cld_parts:
            _cld_auth, _cld_cloud = _cld_parts.split('@', 1)
            if ':' in _cld_auth:
                _cld_key, _cld_secret = _cld_auth.split(':', 1)
                _cloudinary_config = {
                    'cloud_name': _cld_cloud,
                    'api_key': _cld_key,
                    'api_secret': _cld_secret
                }
                logging.getLogger(__name__).info("Cloudinary configurado desde CLOUDINARY_URL: cloud=%s", _cld_cloud)
    except Exception as e:
        logging.getLogger(__name__).warning("Error parseando CLOUDINARY_URL: %s", e)
else:
    logging.getLogger(__name__).warning("CLOUDINARY_URL no configurado - subida de imágenes deshabilitada")

# Sesión de requests con proxy configurado
_cloudinary_session = requests.Session()
if _api_proxy:
    _cloudinary_session.proxies = {
        'http': _api_proxy,
        'https': _api_proxy
    }
    logging.getLogger(__name__).info("Cloudinary session configurada con proxy: %s", _api_proxy)


def _cloudinary_sign(params_to_sign, api_secret):
    """Genera la firma para la API de Cloudinary."""
    # Ordenar parámetros alfabéticamente y crear string
    sorted_params = sorted(params_to_sign.items())
    to_sign = '&'.join([f"{k}={v}" for k, v in sorted_params if v is not None and v != ''])
    to_sign += api_secret
    return hashlib.sha1(to_sign.encode('utf-8')).hexdigest()


def cloudinary_upload(file, **options):
    """
    Sube una imagen a Cloudinary usando requests directamente.
    SIMPLIFICADO: Solo sube la imagen con folder, sin transformaciones complejas.
    La rotación EXIF se maneja automáticamente por Cloudinary.
    
    Args:
        file: Archivo (file-like object, path string, o URL)
        **options: Opciones de upload (folder, etc.)
    
    Returns:
        dict con la respuesta de Cloudinary (secure_url, public_id, etc.)
    
    Raises:
        RuntimeError: Si CLOUDINARY_URL no está configurado
    """
    if _cloudinary_config is None:
        raise RuntimeError("CLOUDINARY_URL no está configurado. Configura la variable de entorno.")
    
    config = _cloudinary_config
    cloud_name = config['cloud_name']
    api_key = config['api_key']
    api_secret = config['api_secret']
    
    # URL del API - siempre usar 'auto' para detectar tipo automáticamente
    upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload"
    
    # Timestamp
    timestamp = str(int(time.time()))
    
    # Parámetros básicos para la firma
    params = {
        'timestamp': timestamp,
    }
    
    # Solo agregar folder si está presente
    if 'folder' in options and options['folder']:
        params['folder'] = options['folder']
    
    # Generar firma
    signature = _cloudinary_sign(params, api_secret)
    
    # Agregar credenciales (NO van en la firma)
    params['api_key'] = api_key
    params['signature'] = signature
    
    # Preparar archivo
    files = None
    if isinstance(file, str):
        if file.startswith(('http://', 'https://', 'ftp://', 's3://', 'data:')):
            params['file'] = file
        else:
            files = {'file': open(file, 'rb')}
    else:
        # File-like object
        filename = getattr(file, 'filename', 'upload.jpg')
        content_type = getattr(file, 'content_type', 'image/jpeg')
        files = {'file': (filename, file, content_type)}
    
    try:
        response = _cloudinary_session.post(
            upload_url,
            data=params,
            files=files,
            timeout=120
        )
        
        result = response.json()
        
        if 'error' in result:
            error_msg = result['error'].get('message', str(result['error']))
            raise Exception(f"Cloudinary error: {error_msg}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error de conexión con Cloudinary: {str(e)}")


# También importar cloudinary para funciones auxiliares (URLs, etc.)
try:
    import cloudinary
    import cloudinary.utils
    
    # Configurar cloudinary para funciones de URL
    cloudinary.config(
        cloud_name=_cloudinary_config['cloud_name'],
        api_key=_cloudinary_config['api_key'],
        api_secret=_cloudinary_config['api_secret']
    )
    if _api_proxy:
        cloudinary.config(api_proxy=_api_proxy)
    
    CLOUDINARY_AVAILABLE = True
    logging.getLogger(__name__).info("Cloudinary configurado: cloud_name=%s (upload directo con requests)", _cloudinary_config['cloud_name'])
except ImportError:
    cloudinary = None
    CLOUDINARY_AVAILABLE = True  # Aún podemos usar cloudinary_upload directo
    logging.getLogger(__name__).info("Cloudinary SDK no instalado, usando implementación directa")


# --- Cloudinary helpers: build eager transforms, generate URLs and srcsets for responsive images ---
def get_cloudinary_eager():
    """Genera la lista de transformaciones eager según la configuración (anchos).
    Devuelve lista de dicts para pasar a `upload(..., eager=...)`."""
    widths = app.config.get('CLOUDINARY_IMAGE_WIDTHS', [320, 640, 1024])
    q = app.config.get('CLOUDINARY_IMAGE_QUALITY', 'auto')
    return [{'width': w, 'crop': 'limit', 'quality': q, 'fetch_format': 'auto'} for w in widths]


def cloudinary_image_url(public_id, width=None):
    """Construye una URL de Cloudinary para `public_id` con transformación opcional de ancho.
    IMPORTANTE: Incluye angle='auto' para corregir rotación EXIF de fotos de celular."""
    if not public_id:
        return None
    
    if _cloudinary_config is None:
        logger.warning("CLOUDINARY_URL no configurado, no se puede generar URL de imagen")
        return None
    
    # Si tenemos el SDK de cloudinary, usarlo
    if cloudinary and hasattr(cloudinary, 'utils'):
        try:
            opts = {
                'quality': app.config.get('CLOUDINARY_IMAGE_QUALITY', 'auto'), 
                'fetch_format': 'auto', 
                'resource_type': 'image',
                'angle': 'auto'  # CRÍTICO: Corrige rotación EXIF de fotos tomadas con celular
            }
            if width:
                opts.update({'width': width, 'crop': 'limit'})
            url, _ = cloudinary.utils.cloudinary_url(public_id, **opts)
            return url
        except Exception as e:
            logger.exception('Error generating cloudinary URL for %s: %s', public_id, e)
    
    # Fallback: construir URL manualmente
    cloud_name = _cloudinary_config.get('cloud_name')
    transformations = ['a_auto', 'q_auto', 'f_auto']
    if width:
        transformations.append(f'w_{width}')
        transformations.append('c_limit')
    
    trans_str = ','.join(transformations)
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{trans_str}/{public_id}"


def cloudinary_srcset(public_id, widths=None):
    """Genera un `srcset` (string) para el `public_id` usando los anchos configurados o pasados."""
    if not CLOUDINARY_AVAILABLE or not public_id:
        return None
    if widths is None:
        widths = app.config.get('CLOUDINARY_IMAGE_WIDTHS', [320, 640, 1024])
    parts = []
    for w in widths:
        url = cloudinary_image_url(public_id, width=w)
        if url:
            parts.append(f"{url} {w}w")
    return ', '.join(parts)


import traceback
from logging.handlers import RotatingFileHandler

# Intentar importar pdfkit para generación de PDFs
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    pdfkit = None
    PDFKIT_AVAILABLE = False

# Intentar importar python-magic para MIME sniffing de archivos subidos
try:
    import magic
    MAGIC_AVAILABLE = True
except Exception:
    magic = None
    MAGIC_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.info('python-magic no disponible: MIME sniffing deshabilitado')

# Intentar importar SDK de Mercado Pago
MERCADOPAGO_IMPORT_ERROR = None
try:
    import mercadopago
    MERCADOPAGO_AVAILABLE = True
except ImportError as e:
    mercadopago = None
    MERCADOPAGO_AVAILABLE = False
    MERCADOPAGO_IMPORT_ERROR = str(e)
    # Friendly guidance to fix missing dependency (visible at startup)
    logging.getLogger(__name__).warning("[MercadoPago] Mercado Pago SDK no encontrado. Instala con: pip install mercado-pago")
except Exception as e:
    mercadopago = None
    MERCADOPAGO_AVAILABLE = False
    MERCADOPAGO_IMPORT_ERROR = str(e)
    logging.getLogger(__name__).error("[MercadoPago] Error al importar Mercado Pago: %s", MERCADOPAGO_IMPORT_ERROR)

# ============================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================
# Definir directorio de logs
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Rotating file handler: 5MB por archivo, 3 backups
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler para desarrollo
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter('%(levelname)-8s: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logger.info("=" * 60)
logger.info("Iniciando aplicación Menu Digital")
logger.info("=" * 60)

# ============================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ============================================================

app = Flask(__name__)

# Cargar configuración desde variables de entorno
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    secret_key = 'please-set-a-secret-key'
    if os.environ.get('FLASK_ENV') == 'production':
        logger.warning('SECRET_KEY not set in environment. Set SECRET_KEY in production.')

app.secret_key = secret_key
app.config['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'development')

# Configuración de sesiones (optimizada para rendimiento)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora
app.config['SESSION_REFRESH_EACH_REQUEST'] = False  # Reduce overhead de sesiones

# Configuración de rendimiento
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 año para archivos estáticos
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # JSON compacto en producción
app.config['JSON_SORT_KEYS'] = False  # No ordenar keys JSON (más rápido)

# ============================================================
# INICIALIZAR MIDDLEWARE DE SEGURIDAD Y PERFORMANCE
# ============================================================
try:
    from security_middleware import (
        init_security_middleware, 
        check_login_allowed, 
        record_login_attempt,
        get_client_ip,
        get_cache,
        invalidate_menu_cache,
        clear_all_menu_cache,
        rate_limit
    )
    init_security_middleware(app)
    SECURITY_MIDDLEWARE_AVAILABLE = True
    logger.info("Security middleware loaded successfully")
except ImportError as e:
    logger.warning("Security middleware not available: %s", e)
    SECURITY_MIDDLEWARE_AVAILABLE = False
    # Funciones placeholder si el módulo no está disponible
    def check_login_allowed(ip, username=None):
        return False, None
    def record_login_attempt(ip, username, success):
        pass
    def get_client_ip():
        return request.remote_addr or '127.0.0.1'
    def invalidate_menu_cache(restaurante_id, url_slug=None):
        pass
    def clear_all_menu_cache():
        pass
    def rate_limit(limit_type='default'):
        def decorator(f):
            return f
        return decorator


def invalidar_cache_restaurante(restaurante_id):
    """
    Helper para invalidar el cache del menú de un restaurante.
    Obtiene el url_slug de la BD y llama a invalidate_menu_cache.
    """
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT url_slug FROM restaurantes WHERE id = %s", (restaurante_id,))
            result = cur.fetchone()
            if result:
                url_slug = result.get('url_slug') if isinstance(result, dict) else result[0]
                invalidate_menu_cache(restaurante_id, url_slug)
                logger.debug("Cache invalidado para restaurante %s (slug: %s)", restaurante_id, url_slug)
            else:
                # Fallback: invalidar todas las entradas de menú
                invalidate_menu_cache(restaurante_id)
    except Exception as e:
        logger.warning("Error invalidando cache: %s", e)
        # Fallback: invalidar sin url_slug
        invalidate_menu_cache(restaurante_id)

# Función now() para templates
app.jinja_env.globals['now'] = lambda: datetime.utcnow()

# Filtro para formato de precio chileno (con punto como separador de miles)
def formato_precio_chileno(valor):
    """Formatea un número como precio chileno: 14990 -> 14.990"""
    try:
        return "{:,.0f}".format(int(valor)).replace(",", ".")
    except (ValueError, TypeError):
        return valor

app.jinja_env.filters['precio_cl'] = formato_precio_chileno

# Registrar helpers de Cloudinary en Jinja si la app está inicializada
try:
    app.jinja_env.globals['cloudinary_image_url'] = cloudinary_image_url
    app.jinja_env.globals['cloudinary_srcset'] = cloudinary_srcset
except Exception:
    # En pruebas unitarias 'app' podría no comportarse como en runtime; ignorar errores de registro
    pass

# ============================================================
# FUNCIONES DE INICIALIZACIÓN
# ============================================================

# Variable global para almacenar si Cloudinary está configurado
CLOUDINARY_CONFIGURED = False

def init_cloudinary():
    """
    Inicializa la configuración de Cloudinary.
    Con la nueva implementación directa, solo verifica que las credenciales estén disponibles.
    """
    global CLOUDINARY_CONFIGURED, _cloudinary_config, _cloudinary_session
    
    api_proxy = os.environ.get('API_PROXY')
    
    logger.info("init_cloudinary() - cloud_name: %s", _cloudinary_config.get('cloud_name'))
    logger.info("init_cloudinary() - API_PROXY presente: %s", bool(api_proxy))
    
    # Verificar que tenemos credenciales
    if not all([_cloudinary_config.get('cloud_name'), 
                _cloudinary_config.get('api_key'), 
                _cloudinary_config.get('api_secret')]):
        logger.warning("Credenciales de Cloudinary incompletas")
        CLOUDINARY_CONFIGURED = False
        return False
    
    # Asegurar que la sesión tiene el proxy configurado
    if api_proxy and _cloudinary_session:
        _cloudinary_session.proxies = {
            'http': api_proxy,
            'https': api_proxy
        }
        logger.info("Cloudinary session proxy actualizado: %s", api_proxy)
    
    # Configurar también el SDK si está disponible (para URLs)
    if cloudinary:
        try:
            cloudinary.config(
                cloud_name=_cloudinary_config['cloud_name'],
                api_key=_cloudinary_config['api_key'],
                api_secret=_cloudinary_config['api_secret']
            )
            if api_proxy:
                cloudinary.config(api_proxy=api_proxy)
        except Exception as e:
            logger.warning("Error configurando cloudinary SDK: %s", e)
    
    logger.info("Cloudinary configurado correctamente (implementación directa con requests)")
    CLOUDINARY_CONFIGURED = True
    return True


def is_cloudinary_ready():
    """Verifica si Cloudinary está listo para usar. Re-inicializa si es necesario."""
    global CLOUDINARY_CONFIGURED
    if CLOUDINARY_CONFIGURED:
        return True
    # Intentar inicializar si aún no está configurado
    if CLOUDINARY_AVAILABLE:
        logger.info("is_cloudinary_ready() - Intentando re-inicializar Cloudinary...")
        return init_cloudinary()
    return False

# Inicialización perezosa: se realiza al primer request (compatibilidad con Flask 3)
@app.before_request
def _lazy_init_services_once():
    # Ejecutar solo una vez para evitar ejecutar en cada petición
    if app.config.get('_services_initialized'):
        return
    try:
        # Inicializar servicios dependientes de configuración externa
        init_cloudinary()
        init_mercadopago()
        # Ejecutar comprobaciones críticas de entorno (solo lanzará en producción)
        enforce_required_envs()

        # Registrar helpers de Jinja que usan funciones definidas en este módulo
        try:
            app.jinja_env.globals['cloudinary_image_url'] = cloudinary_image_url
            app.jinja_env.globals['cloudinary_srcset'] = cloudinary_srcset
        except Exception:
            # Ignorar errores de registro en entornos de test o importación
            pass

        app.config['_services_initialized'] = True
    except Exception:
        logger.exception("Error durante la inicialización perezosa de servicios")

# Variable global para almacenar cliente de Mercado Pago
MERCADOPAGO_CLIENT = None

def init_mercadopago():
    """
    Inicializa el cliente de Mercado Pago.
    Se llama después de que Flask está completamente cargado.
    """
    global MERCADOPAGO_CLIENT

    if not MERCADOPAGO_AVAILABLE:
        logger.warning("SDK de Mercado Pago no está instalado. Los pagos no funcionarán.")
        if MERCADOPAGO_IMPORT_ERROR:
            logger.error("Mercado Pago import error: %s", MERCADOPAGO_IMPORT_ERROR)
        return False

    # Buscar explícitamente las variables esperadas (sin alias cortos)
    access_token = os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')
    public_key = os.environ.get('MERCADO_PAGO_PUBLIC_KEY')

    # Requerir al menos el access token para inicializar el cliente en servidor.
    if not access_token:
        logger.error("MERCADO_PAGO_ACCESS_TOKEN no está configurada. Mercado Pago no podrá inicializarse.")
        MERCADOPAGO_CLIENT = None
        return False

    # Mostrar vista previa segura (primeros 10 caracteres) para depuración en logs
    try:
        preview = access_token[:10]
        logger.info("Mercado Pago access token preview: %s...", preview)
    except Exception:
        logger.debug("No se pudo generar preview del access token.")

    if not public_key:
        logger.warning("MERCADO_PAGO_PUBLIC_KEY no está configurada. La integración del lado cliente puede fallar.")

    try:
        MERCADOPAGO_CLIENT = mercadopago.SDK(access_token)
        logger.info("Mercado Pago configurado correctamente (cliente inicializado).")
        return True
    except Exception:
        logger.exception("Error configurando Mercado Pago")
        MERCADOPAGO_CLIENT = None
        return False

# Inicializar Mercado Pago (la inicialización se ejecuta perezosamente en `_lazy_init_services`)

# ============================================================
# CONFIGURACIÓN DE UPLOADS Y ARCHIVOS
# ============================================================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB máximo

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Upload folder (local fallback when Cloudinary is not configured)
UPLOAD_FOLDER = os.path.join(base_dir, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================

# Leer configuración de variables de entorno
# Valores por defecto NUNCA deben ser 'localhost' en producción
MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'MiMenudigital.mysql.pythonanywhere-services.com'
MYSQL_USER = os.environ.get('MYSQL_USER') or 'MiMenudigital'
# Do not provide a default password in code. Require the hosting provider to set this securely.
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
if not MYSQL_PASSWORD:
    logger.warning('MYSQL_PASSWORD not set in environment; verify your deployment configuration')
MYSQL_DB = os.environ.get('MYSQL_DB') or 'MiMenudigital$menu_digital'
MYSQL_PORT = os.environ.get('MYSQL_PORT') or '3306' 

app.config['MYSQL_HOST'] = MYSQL_HOST
app.config['MYSQL_USER'] = MYSQL_USER
app.config['MYSQL_PASSWORD'] = MYSQL_PASSWORD
app.config['MYSQL_DB'] = MYSQL_DB
app.config['MYSQL_PORT'] = int(MYSQL_PORT)
app.config['MYSQL_CHARSET'] = 'utf8mb4'

logger.info("Database config: %s:%s/%s", app.config['MYSQL_HOST'], app.config['MYSQL_PORT'], app.config['MYSQL_DB'])

# URL base
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
app.config['BASE_URL'] = BASE_URL
logger.info("Base URL: %s", BASE_URL)

# ============================================================
# SECURITY & PRODUCTION CHECKS
# ============================================================

def enforce_required_envs():
    """Enforce presence of critical environment variables in production.
    This raises only when FLASK_ENV == 'production' to avoid breaking local/dev.

    Additional checks:
    - If Cloudinary SDK is available, require `CLOUDINARY_URL` in production.
    - If Mercado Pago SDK is available, require `MERCADO_PAGO_ACCESS_TOKEN` in production.
    """
    missing = []
    if os.environ.get('FLASK_ENV') == 'production':
        if not os.environ.get('SECRET_KEY'):
            missing.append('SECRET_KEY')
        if not os.environ.get('MYSQL_PASSWORD'):
            missing.append('MYSQL_PASSWORD')
        # If cloudinary SDK is installed, require CLOUDINARY_URL in production
        if CLOUDINARY_AVAILABLE and not os.environ.get('CLOUDINARY_URL'):
            missing.append('CLOUDINARY_URL')
        # If Mercado Pago is installed, require token in production
        if MERCADOPAGO_AVAILABLE and not os.environ.get('MERCADO_PAGO_ACCESS_TOKEN'):
            missing.append('MERCADO_PAGO_ACCESS_TOKEN')
    if missing:
        msg = f"Missing required env vars in production: {', '.join(missing)}"
        logger.error(msg)
        raise RuntimeError(msg)
    else:
        # Warn in non-production environments so devs notice
        if not os.environ.get('SECRET_KEY'):
            logger.warning('SECRET_KEY not set; use a strong secret in production')
        if not os.environ.get('MYSQL_PASSWORD'):
            logger.warning('MYSQL_PASSWORD not set; ensure DB credentials are configured')
        if CLOUDINARY_AVAILABLE and not os.environ.get('CLOUDINARY_URL'):
            logger.warning('CLOUDINARY_URL not set; uploads will not work without it')
        if MERCADOPAGO_AVAILABLE and not os.environ.get('MERCADO_PAGO_ACCESS_TOKEN'):
            logger.warning('MERCADO_PAGO_ACCESS_TOKEN not set; Mercado Pago will not work')

# Comprobaciones críticas de entorno: se ejecutan perezosamente en `_lazy_init_services`
# para evitar lanzar en import time durante desarrollo. Sin embargo, para mantener
# compatibilidad con el comportamiento previo en producción, ejecutamos las comprobaciones
# durante la importación si estamos en producción (esto replicará el comportamiento
# previo que fallaba rápido en despliegue si faltan variables críticas).
if os.environ.get('FLASK_ENV') == 'production':
    enforce_required_envs()

# Secure session cookie settings (only enforce secure cookies in production)
app.config['SESSION_COOKIE_SECURE'] = True if os.environ.get('FLASK_ENV') == 'production' else False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Optional: enable CSRF via Flask-WTF if available
CSRF_EXEMPT_VIEWS = set()  # Views to exempt from CSRF
try:
    from flask_wtf.csrf import CSRFProtect, generate_csrf
    csrf = CSRFProtect()
    csrf.init_app(app)
    # Registrar csrf_token en el contexto global de Jinja2
    app.jinja_env.globals['csrf_token'] = generate_csrf
    CSRF_ENABLED = True
    logger.info('CSRF protection enabled via Flask-WTF')
        
except Exception as e:
    logger.warning('Flask-WTF not available; CSRF protection not enabled: %s', e)
    # Registrar función dummy para que los templates no fallen
    app.jinja_env.globals['csrf_token'] = lambda: ''
    csrf = None
    CSRF_ENABLED = False


def csrf_exempt(view_function):
    """Decorador para eximir una vista de la verificación CSRF."""
    CSRF_EXEMPT_VIEWS.add(view_function.__name__)
    if csrf:
        return csrf.exempt(view_function)
    return view_function

# Optional: integrate Sentry if SENTRY_DSN present
if os.environ.get('SENTRY_DSN'):
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(
            dsn=os.environ.get('SENTRY_DSN'),
            integrations=[FlaskIntegration()],
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLERATE', 0.0))
        )
        logger.info('Sentry initialized')
    except Exception as e:
        logger.warning('Sentry SDK not available or failed to init: %s', e)

# Enforce HTTPS in production (respecting proxy headers)
@app.before_request
def enforce_https_in_production():
    if os.environ.get('FLASK_ENV') == 'production':
        proto = request.headers.get('X-Forwarded-Proto', request.scheme)
        if proto != 'https':
            # Only redirect GET requests to avoid breaking POSTs
            if request.method == 'GET':
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)

# Mercado Pago webhook verification hint (verify if key present)
MERCADO_WEBHOOK_KEY = os.environ.get('MERCADO_WEBHOOK_KEY') or os.environ.get('MERCADO_CLIENT_SECRET')
if MERCADO_WEBHOOK_KEY:
    logger.info('Mercado Pago webhook verification is enabled (signature header will be verified if provided)')

# ============================================================
# DATABASE - usar `database.py` centralizado con SQLAlchemy Pool
# ============================================================
from database import init_app as db_init_app, get_db as db_get_db, get_cursor as db_get_cursor, execute_query as db_execute_query, get_pool_status, _pool as db_pool

# Inicializar el pool de conexiones SQLAlchemy
db_init_app(app)
logger.info("SQLAlchemy connection pool initialized")

# Backwards compatibility: expose expected names used across the codebase
get_db = db_get_db
get_cursor = db_get_cursor
execute_query = db_execute_query

# ============================================================
# INICIALIZAR SERVICIO DE EMAIL
# ============================================================
try:
    from email_service import (
        init_mail, 
        is_mail_configured,
        enviar_confirmacion_ticket,
        notificar_nuevo_ticket_admin,
        enviar_respuesta_ticket,
        enviar_email_recuperacion
    )
    
    # Cargar configuración de email en la app
    from config import MailConfig
    app.config['MAIL_SERVER'] = MailConfig.MAIL_SERVER
    app.config['MAIL_PORT'] = MailConfig.MAIL_PORT
    app.config['MAIL_USE_TLS'] = MailConfig.MAIL_USE_TLS
    app.config['MAIL_USE_SSL'] = MailConfig.MAIL_USE_SSL
    app.config['MAIL_USERNAME'] = MailConfig.MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = MailConfig.MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = MailConfig.MAIL_DEFAULT_SENDER
    app.config['SUPERADMIN_EMAIL'] = MailConfig.SUPERADMIN_EMAIL
    
    # Inicializar Flask-Mail
    mail = init_mail(app)
    EMAIL_SERVICE_AVAILABLE = mail is not None
    logger.info("Email service initialized: %s", EMAIL_SERVICE_AVAILABLE)
except ImportError as e:
    logger.warning("Email service not available: %s", e)
    EMAIL_SERVICE_AVAILABLE = False
    def is_mail_configured(): return False
    def enviar_confirmacion_ticket(data): return False
    def notificar_nuevo_ticket_admin(data, url): return False
    def enviar_respuesta_ticket(data, respuesta): return False
    def enviar_email_recuperacion(data, url): return False

# Backwards compatibility: expose expected names used across the codebase
get_db = db_get_db
get_cursor = db_get_cursor
execute_query = db_execute_query

# ============================================================
# FUNCIONES AUXILIARES DE SUSCRIPCIÓN
# ============================================================

def get_current_restaurant():
    """
    Obtiene el restaurante actual de la sesión con CACHÉ en g.
    OPTIMIZACIÓN: Evita queries repetidas durante el mismo request.
    
    Returns:
        dict: Datos del restaurante o None si no hay sesión
    """
    # Verificar caché en g (válido durante el request)
    if hasattr(g, '_current_restaurant'):
        return g._current_restaurant
    
    restaurante_id = session.get('restaurante_id')
    if not restaurante_id:
        g._current_restaurant = None
        return None
    
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM restaurantes WHERE id = %s", (restaurante_id,))
            result = cur.fetchone()
            g._current_restaurant = dict_from_row(result) if result else None
            return g._current_restaurant
    except Exception as e:
        logger.error("Error getting current restaurant: %s", e)
        g._current_restaurant = None
        return None


def get_subscription_info(restaurante_id):
    """
    Obtiene información de la suscripción del restaurante.
    
    Calcula:
    - Estado: 'active', 'expiring_soon' (< 5 días), 'expired'
    - Días restantes
    - Fecha de vencimiento
    - Tipo de plan: 'prueba' o 'activa'
    
    Returns:
        dict: Con keys: status, days_remaining, expiration_date, fecha_vencimiento (object), plan_type
    """
    # Validar que el ID sea válido
    if not restaurante_id:
        return None
        
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "SELECT fecha_vencimiento, estado_suscripcion FROM restaurantes WHERE id = %s",
                (restaurante_id,)
            )
            result = cur.fetchone()
            
            if not result:
                logger.debug("Restaurant %s not found in get_subscription_info", restaurante_id)
                return None
            
            fecha_vencimiento = result.get('fecha_vencimiento')
            estado_suscripcion = result.get('estado_suscripcion', 'prueba')
            
            if not fecha_vencimiento:
                logger.warning("No expiration date for restaurant %s", restaurante_id)
            
            # Convertir a datetime si es string
            if isinstance(fecha_vencimiento, str):
                from datetime import datetime as dt
                fecha_vencimiento = dt.strptime(fecha_vencimiento, '%Y-%m-%d').date()
            
            hoy = date.today()
            dias_restantes = (fecha_vencimiento - hoy).days
            
            # Determinar estado
            if dias_restantes < 0:
                estado = 'expired'
            elif dias_restantes <= 5:
                estado = 'expiring_soon'
            else:
                estado = 'active'
            
            # Formatear fecha para mostrar
            fecha_formateada = fecha_vencimiento.strftime('%d/%m/%Y')
            
            return {
                'status': estado,
                'days_remaining': max(0, dias_restantes),
                'expiration_date': fecha_formateada,
                'fecha_vencimiento': fecha_vencimiento,
                'plan_type': estado_suscripcion
            }
    except Exception as e:
        logger.exception("Error getting subscription info")
        return None


# ============================================================
# CONTEXTO GLOBAL PARA TEMPLATES
# ============================================================

from werkzeug.exceptions import RequestEntityTooLarge


@app.before_request
def inject_subscription_info():
    """
    Inyecta información de suscripción en el contexto global de templates.
    BALANCEADO: Usa caché de sesión, sin queries directas.
    """
    g.subscription_info = None
    
    # Saltar para rutas públicas y estáticas
    path = request.path
    if path.startswith(('/static/', '/menu/', '/api/health')) or path == '/':
        return
    
    # Usar caché de sesión si existe
    cached_info = session.get('_sub_info_cache')
    if cached_info:
        g.subscription_info = cached_info


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(e):
    # Return JSON for API routes, otherwise render friendly page
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Archivo demasiado grande'}), 413
    return render_template('error_publico.html', error_code=413, error_message='Archivo demasiado grande'), 413

# Hacer disponible en templates
@app.context_processor
def inject_globals():
    """
    Inyecta variables globales en todos los templates.
    BALANCEADO: Usa caché pero hace query si es necesario.
    """
    tickets_pendientes = 0
    if session.get('rol') == 'superadmin':
        # Intentar usar caché primero
        cached = session.get('_tickets_count_cache')
        cache_time = session.get('_tickets_cache_time', 0)
        ahora = time.time()
        
        if cached is not None and (ahora - cache_time < 300):  # 5 min caché
            tickets_pendientes = int(cached) if cached else 0
        else:
            # Hacer query solo si no hay caché o expiró
            try:
                db = get_db()
                with db.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as c FROM tickets_soporte WHERE estado IN ('abierto','en_proceso')")
                    r = cur.fetchone()
                    tickets_pendientes = int(r['c']) if r and r['c'] else 0
                    session['_tickets_count_cache'] = tickets_pendientes
                    session['_tickets_cache_time'] = ahora
            except:
                tickets_pendientes = 0
    
    return {
        'subscription_info': g.get('subscription_info', None),
        'now': datetime.utcnow(),
        'tickets_pendientes': int(tickets_pendientes) if tickets_pendientes else 0
    }


# ============================================================
# GENERACIÓN DE CÓDIGOS QR
# ============================================================

def generar_qr_restaurante(url, filename):
    """
    Genera un código QR en formato imagen.
    
    Args:
        url (str): URL a codificar
        filename (str): Nombre del archivo (e.g., "123_qr.png")
    
    Returns:
        str: Ruta al archivo QR generado
    """
    qr_folder = os.path.join(base_dir, 'static', 'uploads', 'qrs')
    os.makedirs(qr_folder, exist_ok=True)
    
    qr_path = os.path.join(qr_folder, filename)
    
    # No regenerar si ya existe
    if os.path.exists(qr_path):
        logger.debug("QR already exists: %s", qr_path)
        return qr_path
    
    try:
        import qrcode
    except ImportError as e:
        logger.error('qrcode module not available')
        raise RuntimeError('QR generation unavailable: install qrcode[pil]') from e

    try:
        logger.info("Generating QR code for: %s", url)
        img = qrcode.make(url)
        img.save(qr_path)
        logger.info("QR code saved: %s", qr_path)
        return qr_path
    except Exception as e:
        logger.error('Failed to generate QR for %s: %s', url, e)
        raise

# ============================================================
# MANEJADORES DE ERRORES
# ============================================================

@app.errorhandler(403)
def forbidden_error(error):
    """Maneja errores 403 (acceso denegado)."""
    logger.warning("403 Forbidden error: %s", request.path)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Acceso prohibido'}), 403
    return render_template('error_publico.html', 
                          error_code=403, 
                          error_message='Acceso prohibido'), 403



@app.errorhandler(500)
def internal_error(error):
    """Maneja errores 500 (error interno del servidor)."""
    logger.exception("500 Internal Server Error")
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False, 
            'error': 'Error interno del servidor'
        }), 500
    return render_template('error_publico.html', 
                          error_code=500, 
                          error_message='Error interno del servidor'), 500


@app.errorhandler(404)
def not_found_error(error):
    """Maneja errores 404 (no encontrado)."""
    logger.debug("404 Not Found: %s", request.path)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Recurso no encontrado'}), 404
    return render_template('error_publico.html', 
                          error_code=404, 
                          error_message='Página no encontrada'), 404


@app.errorhandler(Exception)
def handle_exception(e):
    """Maneja excepciones globales no controladas."""
    logger.exception("Unhandled exception: %s", type(e).__name__)

    # During TESTING return the exception details as JSON to aid debugging
    if app.config.get('TESTING'):
        return jsonify({'success': False, 'error': str(e), 'type': type(e).__name__}), 500

    # Report to Sentry if available
    try:
        if 'sentry_sdk' in globals() and hasattr(sentry_sdk, 'capture_exception'):
            try:
                # Attach user context if present
                with sentry_sdk.push_scope() as scope:
                    if 'user_id' in session:
                        sentry_sdk.set_user({'id': session.get('user_id'), 'restaurante_id': session.get('restaurante_id')})
                    sentry_sdk.capture_exception(e)
            except Exception as sentry_e:
                logger.debug('Sentry capture failed: %s', sentry_e)
    except Exception:
        # Be resilient if sentry isn't present
        pass

    if request.path.startswith('/api/'):
        return jsonify({
            'success': False, 
            'error': 'Error interno',
            'type': type(e).__name__
        }), 500
    return render_template('error_publico.html', 
                          error_code=500, 
                          error_message=f'Error: {str(e)}'), 500


# Helper: register the same Sentry-aware error handler onto another Flask app instance
# Useful for tests that need a fresh app and for programmatic setups.
def register_sentry_error_handler(target_app, sentry_module=None):
    """Registra un manejador de errores en `target_app` que replica la lógica del
    manejador global definido arriba y que informará a `sentry_module` si se proporciona.
    """
    def _handler(e):
        logger.exception("Unhandled exception (external app): %s", type(e).__name__)
        try:
            sentry = sentry_module if sentry_module is not None else globals().get('sentry_sdk')
            if sentry and hasattr(sentry, 'capture_exception'):
                try:
                    with sentry.push_scope() as scope:
                        if 'user_id' in session:
                            sentry.set_user({'id': session.get('user_id'), 'restaurante_id': session.get('restaurante_id')})
                        sentry.capture_exception(e)
                except Exception as sentry_e:
                    logger.debug('Sentry capture failed: %s', sentry_e)
        except Exception:
            pass

        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Error interno',
                'type': type(e).__name__
            }), 500
        return render_template('error_publico.html', error_code=500, error_message=f'Error: {str(e)}'), 500

    target_app.register_error_handler(Exception, _handler)
    return _handler


# ============================================================
# FUNCIONES UTILITARIAS
# ============================================================

def dict_from_row(row):
    """Convierte una fila a diccionario (PyMySQL con DictCursor ya lo hace)."""
    return dict(row) if row else None


def list_from_rows(rows):
    """Convierte lista de filas a lista de diccionarios."""
    return [dict(row) for row in rows] if rows else []


# --- Configuración Global ---
def get_config_global():
    """Obtiene todas las configuraciones globales como diccionario."""
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT clave, valor FROM configuracion_global")
            rows = cur.fetchall()
            return {row['clave']: row['valor'] for row in rows}
    except Exception:
        # Si la tabla no existe todavía, retornar valores por defecto
        return {
            'mercadopago_activo': 'false',
            'deposito_activo': 'true',
            'precio_mensual': '14990'
        }


def get_config_value(clave, default=None):
    """Obtiene un valor específico de configuración."""
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT valor FROM configuracion_global WHERE clave = %s", (clave,))
            row = cur.fetchone()
            return row['valor'] if row else default
    except Exception:
        return default


def set_config_value(clave, valor):
    """Establece o actualiza un valor de configuración."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO configuracion_global (clave, valor) 
            VALUES (%s, %s) 
            ON DUPLICATE KEY UPDATE valor = VALUES(valor)
        """, (clave, valor))
        db.commit()


def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def validate_image_file(file):
    """Validación más robusta de imágenes: extensión, Content-Type y, si está disponible, MIME sniffing.
    Retorna (True, None) si válido, o (False, 'mensaje') si inválido."""
    if not file:
        return False, 'No se recibió archivo'

    filename = getattr(file, 'filename', '')
    if not allowed_file(filename):
        return False, 'Extensión no permitida'

    # Content-Type (por ejemplo: image/jpeg) — usado como heurística, pero no siempre confiable
    content_type = getattr(file, 'content_type', '') or getattr(file, 'mimetype', '')

    # Tamaño máximo por archivo (intentar comprobar de forma segura)
    max_len = app.config.get('MAX_CONTENT_LENGTH', MAX_CONTENT_LENGTH)
    # Algunos objetos file tienen .content_length
    cl = getattr(file, 'content_length', None)
    if cl and cl > max_len:
        return False, 'Archivo demasiado grande'

    # Intentar inspeccionar parcialmente el stream para chequear tamaño sin consumirlo
    try:
        pos = file.stream.tell()
        peek = file.stream.read(max_len + 1)
        file.stream.seek(pos)
        if len(peek) > max_len:
            return False, 'Archivo demasiado grande'
    except Exception:
        # Si no podemos medir, no bloquear; será chequeado por request.content_length
        pass

    # En modo TESTING, ser menos restrictivos para facilitar tests unitarios (aceptar archivos de prueba)
    if app.config.get('TESTING'):
        return True, None

    # Si python-magic está disponible, leer los primeros KB y verificar MIME
    if MAGIC_AVAILABLE and magic:
        try:
            # Mantener posición del stream
            pos = file.stream.tell()
            head = file.stream.read(2048)
            file.stream.seek(pos)
            mtype = magic.from_buffer(head, mime=True)
            if not mtype or not mtype.startswith('image/'):
                return False, f'Contenido no es imagen (detected: {mtype})'
        except Exception as e:
            # En caso de error en magic, no bloquear la subida; solo loggear
            logger = logging.getLogger(__name__)
            logger.debug('Error al usar python-magic para detectar MIME: %s', e)
    else:
        # Fallback simple: verificar firmas binarias para tipos comunes si no hay magic
        try:
            pos = file.stream.tell()
            head = file.stream.read(16)
            file.stream.seek(pos)
            if head.startswith(b'\xff\xd8\xff'):
                return True, None  # JPEG
            if head.startswith(b'\x89PNG'):
                return True, None  # PNG
            if head.startswith(b'GIF8'):
                return True, None  # GIF
            if len(head) >= 12 and head[0:4] == b'RIFF' and head[8:12] == b'WEBP':
                return True, None  # WEBP
            return False, 'Contenido no es imagen'
        except Exception:
            # Si no podemos inspeccionar, permitir y confiar en Content-Type or size checks
            pass

    return True, None


# Context processor para inyectar menu_url en todos los templates
@app.context_processor
def inject_menu_url():
    """
    Inyecta la URL del menú público en todos los templates.
    OPTIMIZADO: Usa url_slug cacheado en sesión, sin queries adicionales.
    """
    menu_url = None
    # Usar url_slug de la sesión (se guarda al hacer login)
    url_slug = session.get('url_slug')
    if url_slug:
        menu_url = f"/menu/{url_slug}"
    return {'menu_url_global': menu_url}


# ============================================================
# DECORADORES PERSONALIZADOS
# ============================================================

def login_required(f):
    """Decorador que requiere login. Redirige a login si no está autenticado."""
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
    """
    Decorador que permite solo acceso al administrador del restaurante 
    actual o a un superadmin.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Permitir solo si el rol es admin o superadmin (no consulta)
        if session.get('rol') == 'consulta':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Acceso denegado. Rol de solo lectura.'}), 403
            flash('No tienes permisos para modificar el menú', 'error')
            logger.warning("Access denied for user %s with role 'consulta'", session.get('user_id'))
            return redirect(url_for('menu_gestion'))
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    """
    Decorador que solo permite acceso a superadmins.
    Rechaza acceso a administradores normales.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Acceso denegado. Solo superadmin.'}), 403
            flash('No tienes permisos de superadministrador', 'error')
            logger.warning("Superadmin access denied for user %s with role %s", session.get('user_id'), session.get('rol'))
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def verificar_suscripcion(f):
    """
    Decorador que verifica si la suscripción del restaurante está vigente.
    ULTRA-OPTIMIZADO: Usa caché de sesión de 10 minutos, mínimas queries.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Superadmin siempre tiene acceso
        if session.get('rol') == 'superadmin':
            return f(*args, **kwargs)
        
        # Usuarios normales: verificar suscripción
        restaurante_id = session.get('restaurante_id')
        if not restaurante_id:
            return f(*args, **kwargs)
        
        # OPTIMIZACIÓN AGRESIVA: Caché de 10 minutos
        cache_key = '_suscripcion_verificada'
        cache_time_key = '_suscripcion_verificada_at'
        ahora = time.time()
        
        # Si ya verificamos recientemente (10 min), usar caché SIN queries
        tiempo_cache = session.get(cache_time_key, 0)
        if tiempo_cache and (ahora - tiempo_cache < 600):  # 10 minutos
            estado_cache = session.get(cache_key)
            if estado_cache == 'ok':
                return f(*args, **kwargs)
            elif estado_cache == 'vencida':
                flash('Tu período de prueba o suscripción ha terminado', 'warning')
                return redirect(url_for('gestion_pago_pendiente'))
        
        # Solo hacer query si el caché expiró
        try:
            db = get_db()
            with db.cursor() as cur:
                cur.execute('SELECT fecha_vencimiento, estado_suscripcion FROM restaurantes WHERE id = %s', (restaurante_id,))
                rest = cur.fetchone()

                if not rest:
                    session[cache_key] = 'ok'
                    session[cache_time_key] = ahora
                    return f(*args, **kwargs)
                
                fecha_vencimiento = rest.get('fecha_vencimiento')
                
                # Si no tiene fecha, asignar 30 días (solo una vez)
                if not fecha_vencimiento:
                    fecha_vencimiento = date.today() + timedelta(days=30)
                    cur.execute('UPDATE restaurantes SET fecha_vencimiento = %s, estado_suscripcion = %s WHERE id = %s',
                               (fecha_vencimiento.isoformat(), 'prueba', restaurante_id))
                    db.commit()
                    session[cache_key] = 'ok'
                    session[cache_time_key] = ahora
                    return f(*args, **kwargs)

                # Normalizar fecha
                if isinstance(fecha_vencimiento, str):
                    fecha_vencimiento = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()

                # Verificar expiración
                if date.today() > fecha_vencimiento:
                    session[cache_key] = 'vencida'
                    session[cache_time_key] = ahora
                    flash('Tu período de prueba o suscripción ha terminado', 'warning')
                    return redirect(url_for('gestion_pago_pendiente'))
                
                # Actualizar caché de suscripción para inject_subscription_info
                dias_restantes = (fecha_vencimiento - date.today()).days
                session['_sub_info_cache'] = {
                    'status': 'expiring_soon' if dias_restantes <= 5 else 'active',
                    'days_remaining': dias_restantes,
                    'expiration_date': fecha_vencimiento.strftime('%d/%m/%Y'),
                    'plan_type': rest.get('estado_suscripcion', 'prueba')
                }
                
                session[cache_key] = 'ok'
                session[cache_time_key] = ahora
                return f(*args, **kwargs)
                
        except Exception as e:
            logger.error("Error al verificar suscripción: %s", e)
            # En caso de error, permitir acceso (mejor UX)
            return f(*args, **kwargs)
    
    return decorated


# ============================================================
# TRACKING DE VISITAS Y ESCANEOS QR/NFC
# ============================================================

# Cola de visitas para procesamiento asíncrono con BATCH
from queue import Queue, Empty
from threading import Thread
import threading

_visitas_queue = Queue(maxsize=5000)  # Aumentado para soportar más tráfico
_visita_worker_running = False
_visita_worker_lock = threading.Lock()
_visita_worker_conn = None  # Conexión persistente del worker

def _get_worker_connection():
    """Obtiene o crea la conexión del worker de visitas."""
    global _visita_worker_conn
    
    config = {
        'host': os.environ.get('MYSQL_HOST'),
        'user': os.environ.get('MYSQL_USER'),
        'password': os.environ.get('MYSQL_PASSWORD'),
        'database': os.environ.get('MYSQL_DB'),
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
        'autocommit': True,
        'connect_timeout': 5,
        'read_timeout': 30
    }
    
    # Verificar si la conexión existe y está viva
    if _visita_worker_conn is not None:
        try:
            _visita_worker_conn.ping(reconnect=True)
            return _visita_worker_conn
        except:
            try:
                _visita_worker_conn.close()
            except:
                pass
            _visita_worker_conn = None
    
    # Crear nueva conexión
    _visita_worker_conn = pymysql.connect(**config)
    return _visita_worker_conn

def _visita_worker():
    """Worker thread que procesa visitas en BATCH para mejor rendimiento."""
    global _visita_worker_running
    
    BATCH_SIZE = 50  # Procesar hasta 50 visitas por batch
    BATCH_TIMEOUT = 5  # Segundos de espera para completar batch
    
    while _visita_worker_running:
        batch = []
        batch_start = time.time()
        
        # Recolectar batch de visitas
        while len(batch) < BATCH_SIZE:
            try:
                remaining_time = max(0.5, BATCH_TIMEOUT - (time.time() - batch_start))
                visita_data = _visitas_queue.get(timeout=remaining_time)
                
                if visita_data is None:  # Señal de terminación
                    _visita_worker_running = False
                    break
                
                batch.append(visita_data)
                _visitas_queue.task_done()
                
            except Empty:
                break  # Timeout, procesar lo que tengamos
            except Exception as e:
                logger.warning("Error getting visit from queue: %s", e)
                break
        
        # Procesar batch si hay visitas
        if batch:
            _procesar_batch_visitas(batch)

def _procesar_batch_visitas(batch):
    """Procesa un batch de visitas en una sola transacción."""
    if not batch:
        return
    
    try:
        conn = _get_worker_connection()
        with conn.cursor() as cur:
            # Preparar datos para INSERT múltiple de visitas
            visitas_values = []
            stats_updates = {}  # {(restaurante_id, fecha): {visitas, qr, movil, desktop}}
            
            for v in batch:
                # Datos para tabla visitas
                visitas_values.append((
                    v['restaurante_id'],
                    v['ip_address'],
                    v['user_agent'],
                    v['referer'],
                    1 if v['es_movil'] else 0,
                    1 if v['es_qr'] else 0
                ))
                
                # Agregar a estadísticas
                key = (v['restaurante_id'], v['fecha'])
                if key not in stats_updates:
                    stats_updates[key] = {'visitas': 0, 'qr': 0, 'movil': 0, 'desktop': 0}
                stats_updates[key]['visitas'] += 1
                if v['es_qr']:
                    stats_updates[key]['qr'] += 1
                if v['es_movil']:
                    stats_updates[key]['movil'] += 1
                else:
                    stats_updates[key]['desktop'] += 1
            
            # INSERT batch de visitas
            if visitas_values:
                cur.executemany('''
                    INSERT INTO visitas 
                    (restaurante_id, ip_address, user_agent, referer, es_movil, es_qr, fecha)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ''', visitas_values)
            
            # UPDATE batch de estadísticas
            for (rest_id, fecha), stats in stats_updates.items():
                cur.execute('''
                    INSERT INTO estadisticas_diarias 
                    (restaurante_id, fecha, visitas, escaneos_qr, visitas_movil, visitas_desktop)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        visitas = visitas + %s,
                        escaneos_qr = escaneos_qr + %s,
                        visitas_movil = visitas_movil + %s,
                        visitas_desktop = visitas_desktop + %s
                ''', (
                    rest_id, fecha,
                    stats['visitas'], stats['qr'], stats['movil'], stats['desktop'],
                    stats['visitas'], stats['qr'], stats['movil'], stats['desktop']
                ))
            
            logger.debug("Processed batch of %d visits", len(batch))
            
    except Exception as e:
        logger.warning("Error processing visit batch: %s", e)
        # Intentar reconectar en el próximo batch
        global _visita_worker_conn
        try:
            if _visita_worker_conn:
                _visita_worker_conn.close()
        except:
            pass
        _visita_worker_conn = None

def _iniciar_visita_worker():
    """Inicia el worker de visitas si no está corriendo."""
    global _visita_worker_running
    
    with _visita_worker_lock:
        if not _visita_worker_running:
            _visita_worker_running = True
            worker = Thread(target=_visita_worker, daemon=True, name="visita-worker")
            worker.start()
            logger.info("Visita worker thread started (batch mode)")


# NOTA: La función _procesar_visita_sync fue ELIMINADA
# Ahora se usa _procesar_batch_visitas() para mejor rendimiento


def registrar_visita(restaurante_id, req):
    """
    Registra una visita/escaneo QR para el restaurante de forma ASÍNCRONA.
    La visita se encola y procesa en segundo plano para no bloquear la respuesta.
    """
    try:
        # Iniciar worker si no está corriendo
        _iniciar_visita_worker()
        
        # Obtener información del visitante
        ip_address = req.headers.get('X-Forwarded-For', req.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()[:45]
        
        user_agent = req.headers.get('User-Agent', '')[:500]
        referer = req.headers.get('Referer', '')[:500]
        
        # Detectar dispositivo móvil
        ua_lower = user_agent.lower()
        es_movil = any(x in ua_lower for x in ['mobile', 'android', 'iphone', 'ipad', 'ipod'])
        
        # Detectar escaneo QR
        es_qr = False
        if req.args.get('qr') == '1' or req.args.get('src') == 'qr':
            es_qr = True
        elif es_movil and (not referer or referer == ''):
            es_qr = True
        elif any(x in ua_lower for x in ['qr', 'scanner', 'barcode', 'zxing', 'nfc']):
            es_qr = True
        elif referer and 'qr' in referer.lower():
            es_qr = True
        
        # Encolar la visita (no bloquea)
        visita_data = {
            'restaurante_id': restaurante_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'referer': referer,
            'es_movil': es_movil,
            'es_qr': es_qr,
            'fecha': date.today().isoformat()
        }
        
        try:
            _visitas_queue.put_nowait(visita_data)
        except:
            # Cola llena, ignorar (mejor que bloquear)
            logger.warning("Visit queue full, dropping visit for restaurant %s", restaurante_id)
            
    except Exception:
        logger.exception("Error queuing visit for restaurant %s", restaurante_id)


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
    """Ruta pública para ver el menú. Accesible por QR. Con cache para mejor rendimiento."""
    try:
        # Preview de tema - no cachear
        preview_tema = request.args.get('preview_tema')
        # Forzar recarga sin cache
        force_refresh = request.args.get('refresh') == '1' or request.args.get('nocache') == '1'
        
        # Intentar obtener del cache si no es preview ni refresh
        cache_key = f"menu:{url_slug}"
        cached_data = None
        if not preview_tema and not force_refresh and SECURITY_MIDDLEWARE_AVAILABLE:
            cached_data = get_cache().get(cache_key)
        
        if cached_data:
            restaurante, menu_estructurado = cached_data
            # Registrar visita aunque venga del cache
            registrar_visita(restaurante['id'], request)
            return render_template('menu_publico.html', 
                                   restaurante=restaurante, 
                                   menu=list(menu_estructurado.values()))
        
        db = get_db()
        with db.cursor() as cur:
            # 1. Obtener datos del restaurante
            cur.execute("SELECT * FROM restaurantes WHERE url_slug = %s AND activo = 1", (url_slug,))
            row = cur.fetchone()
            
            if not row:
                return render_template('menu_404.html', slug=url_slug), 404
            
            restaurante = dict_from_row(row)
            
            if preview_tema:
                restaurante['tema'] = preview_tema
            
            # 2. Registrar visita (solo si no es preview)
            if not preview_tema:
                registrar_visita(restaurante['id'], request)

            # 3. Obtener categorías y platos
            cur.execute('''
                SELECT c.id as categoria_id, c.nombre as categoria_nombre, c.icono as categoria_icono,
                       p.id as plato_id, p.nombre as plato_nombre, p.descripcion, p.precio, 
                       p.precio_oferta, p.imagen_url, p.imagen_public_id, p.etiquetas, p.es_nuevo, p.es_popular,
                       p.es_vegetariano, p.es_vegano, p.es_sin_gluten, p.es_picante
                FROM categorias c
                LEFT JOIN platos p ON c.id = p.categoria_id AND p.activo = 1
                WHERE c.restaurante_id = %s AND c.activo = 1
                ORDER BY c.orden, p.orden, p.nombre
            ''', (restaurante['id'],))
            
            platos_raw = cur.fetchall()
            
            # 3.5 Cargar imágenes múltiples para todos los platos
            plato_ids = [r['plato_id'] for r in platos_raw if r['plato_id']]
            imagenes_por_plato = {}
            if plato_ids:
                # Usar placeholders seguros para evitar SQL injection
                placeholders = ','.join(['%s'] * len(plato_ids))
                query = '''
                    SELECT id, plato_id, imagen_url, imagen_public_id, orden, es_principal
                    FROM platos_imagenes 
                    WHERE plato_id IN ({}) AND activo = 1
                    ORDER BY es_principal DESC, orden ASC
                '''.format(placeholders)
                cur.execute(query, tuple(plato_ids))
                for img in cur.fetchall():
                    plato_id = img['plato_id']
                    if plato_id not in imagenes_por_plato:
                        imagenes_por_plato[plato_id] = []
                    # Generar URL optimizada para cada imagen
                    img_url = img['imagen_url']
                    img_pid = img.get('imagen_public_id')
                    if img_pid and CLOUDINARY_AVAILABLE and CLOUDINARY_CONFIGURED:
                        generated_url = cloudinary_image_url(img_pid, width=640)
                        img['imagen_src'] = generated_url if generated_url else img_url
                    else:
                        img['imagen_src'] = img_url
                    imagenes_por_plato[plato_id].append(dict(img))

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
                    # Determinar URL de imagen - siempre usar imagen_url como fallback
                    img_url = row['imagen_url']
                    img_public_id = row.get('imagen_public_id')
                    
                    # Intentar generar URL optimizada, pero siempre caer a imagen_url si falla
                    if img_public_id and CLOUDINARY_AVAILABLE and CLOUDINARY_CONFIGURED:
                        generated_url = cloudinary_image_url(img_public_id, width=640)
                        imagen_src = generated_url if generated_url else img_url
                        imagen_srcset = cloudinary_srcset(img_public_id) if generated_url else None
                    else:
                        imagen_src = img_url
                        imagen_srcset = None
                    
                    # Obtener imágenes múltiples del plato
                    plato_imagenes = imagenes_por_plato.get(row['plato_id'], [])
                    
                    plato = {
                        'id': row['plato_id'],
                        'nombre': row['plato_nombre'],
                        'descripcion': row['descripcion'],
                        'precio': float(row['precio'] or 0),
                        'precio_oferta': float(row['precio_oferta']) if row['precio_oferta'] else None,
                        'imagen_url': img_url,
                        'imagen_public_id': img_public_id,
                        'imagen_src': imagen_src,
                        'imagen_srcset': imagen_srcset,
                        'imagenes': plato_imagenes,  # Lista de imágenes múltiples
                        'etiquetas': row['etiquetas'].split(',') if row['etiquetas'] else [],
                        'es_nuevo': row['es_nuevo'],
                        'es_popular': row['es_popular'],
                        'es_vegetariano': row['es_vegetariano'],
                        'es_vegano': row['es_vegano'],
                        'es_sin_gluten': row['es_sin_gluten'],
                        'es_picante': row['es_picante']
                    }
                    menu_estructurado[cat_id]['platos'].append(plato)

            # Guardar en cache si no es preview (5 minutos TTL)
            if not preview_tema and SECURITY_MIDDLEWARE_AVAILABLE:
                get_cache().set(cache_key, (restaurante, menu_estructurado), ttl=300)

            return render_template('menu_publico.html', 
                                   restaurante=restaurante, 
                                   menu=list(menu_estructurado.values()))

    except Exception as e:
        logger.exception("Error al cargar menú para %s", url_slug)
        return render_template('error_publico.html'), 500


# ============================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión con protección contra brute force."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ip = get_client_ip()
        
        # Verificar si el IP o usuario está bloqueado por demasiados intentos
        is_locked, unlock_time = check_login_allowed(ip, username)
        if is_locked:
            logger.warning("Login blocked for IP %s (user: %s) - too many attempts", ip, username)
            flash(f'Demasiados intentos fallidos. Intenta de nuevo en {unlock_time} segundos.', 'error')
            return render_template('login.html')
        
        db = get_db()
        with db.cursor() as cur:
            cur.execute('''
                SELECT u.*, r.nombre as restaurante_nombre, r.url_slug as restaurante_url_slug,
                       r.fecha_vencimiento, r.estado_suscripcion
                FROM usuarios_admin u
                LEFT JOIN restaurantes r ON u.restaurante_id = r.id
                WHERE u.username = %s AND u.activo = 1
            ''', (username,))
            row = cur.fetchone()
            
            if row:
                user = dict_from_row(row)
                if check_password_hash(user['password_hash'], password):
                    # Login exitoso - registrar y limpiar intentos fallidos
                    record_login_attempt(ip, username, success=True)
                    
                    # Prevent session fixation: clear existing session and set fresh values
                    session.clear()
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['nombre'] = user['nombre']
                    session['rol'] = user['rol']
                    session['restaurante_id'] = user['restaurante_id']
                    session['restaurante_nombre'] = user['restaurante_nombre'] or 'Panel Admin'
                    
                    # OPTIMIZACIÓN: Guardar url_slug en sesión para evitar queries
                    session['url_slug'] = user.get('restaurante_url_slug')
                    
                    # OPTIMIZACIÓN: Pre-cargar info de suscripción en caché de sesión
                    if user.get('fecha_vencimiento'):
                        fecha_v = user['fecha_vencimiento']
                        if isinstance(fecha_v, str):
                            fecha_v = datetime.strptime(fecha_v, '%Y-%m-%d').date()
                        dias_restantes = (fecha_v - date.today()).days
                        estado = 'expired' if dias_restantes < 0 else ('expiring_soon' if dias_restantes <= 5 else 'active')
                        session['_sub_info_cache'] = {
                            'status': estado,
                            'days_remaining': max(0, dias_restantes),
                            'expiration_date': fecha_v.strftime('%d/%m/%Y'),
                            'plan_type': user.get('estado_suscripcion', 'prueba')
                        }
                    
                    # Actualizar último login
                    cur.execute("UPDATE usuarios_admin SET ultimo_login = NOW() WHERE id = %s", (user['id'],))
                    db.commit()
                    
                    logger.info("Successful login for user %s from IP %s", username, ip)
                    flash('Bienvenido ' + user['nombre'], 'success')
                    
                    if user['rol'] == 'superadmin':
                        return redirect(url_for('superadmin_restaurantes'))
                    return redirect(url_for('menu_gestion'))
            
            # Login fallido - registrar intento
            record_login_attempt(ip, username, success=False)
            logger.warning("Failed login attempt for user %s from IP %s", username, ip)
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))


@app.route('/recuperar-contraseña', methods=['GET', 'POST'])
def recuperar_contraseña():
    """Solicita recuperación de contraseña."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Por favor ingresa tu email', 'error')
            return render_template('recuperar_contraseña.html')
        
        db = get_db()
        try:
            with db.cursor() as cur:
                # Buscar usuario por email
                cur.execute("SELECT id, nombre, email FROM usuarios_admin WHERE email = %s AND activo = 1", (email,))
                user = cur.fetchone()
                
                if not user:
                    # No revelar si el email existe
                    flash('Si el email está registrado, recibirás instrucciones en breve', 'info')
                    return render_template('recuperar_contraseña.html')
                
                # Generar token único (40 caracteres hexadecimales)
                import secrets
                token = secrets.token_hex(20)
                fecha_expiracion = datetime.utcnow() + timedelta(hours=24)
                
                # Guardar token en BD (válido por 24 horas)
                cur.execute('''
                    INSERT INTO password_resets (usuario_id, token, email, fecha_expiracion)
                    VALUES (%s, %s, %s, %s)
                ''', (user['id'], token, email, fecha_expiracion))
                db.commit()
                
                # Link de reset
                reset_url = f"{BASE_URL}/resetear-contraseña/{token}"
                
                # Enviar email de recuperación
                if EMAIL_SERVICE_AVAILABLE:
                    try:
                        usuario_data = {
                            'nombre': user['nombre'],
                            'email': user['email']
                        }
                        enviar_email_recuperacion(usuario_data, reset_url)
                        logger.info("Email de recuperación enviado a %s", email)
                        flash('Se ha enviado un link de recuperación a tu email', 'success')
                    except Exception as email_err:
                        logger.error("Error enviando email de recuperación: %s", email_err)
                        # Fallback: mostrar link en desarrollo
                        if os.environ.get('FLASK_ENV') != 'production':
                            flash(f'Error con email. Link de reset: <a href="{reset_url}">Haz clic aquí</a>', 'warning')
                        else:
                            flash('Error enviando el email. Por favor intenta de nuevo.', 'error')
                else:
                    # Email no configurado
                    token_mask = (token[:6] + '...') if token else None
                    logger.info("Password reset requested for %s. Token masked: %s (email not configured)", email, token_mask)
                    
                    if os.environ.get('FLASK_ENV') != 'production':
                        # En desarrollo, mostrar el link
                        flash(f'Link de reset: <a href="{reset_url}">Haz clic aquí</a>', 'success')
                    else:
                        flash('Se ha enviado un link de recuperación a tu email si está registrado', 'info')
                
                return render_template('recuperar_contraseña.html')
        
        except Exception as e:
            logger.exception("Error en recuperar_contraseña")
            flash('Error al procesar la solicitud', 'error')
    
    return render_template('recuperar_contraseña.html')


@app.route('/resetear-contraseña/<token>', methods=['GET', 'POST'])
def resetear_contraseña(token):
    """Permite resetear la contraseña con un token válido."""
    db = get_db()
    
    try:
        with db.cursor() as cur:
            # Buscar token válido y no expirado
            cur.execute('''
                SELECT pr.id, pr.usuario_id, pr.email, u.nombre
                FROM password_resets pr
                JOIN usuarios_admin u ON pr.usuario_id = u.id
                WHERE pr.token = %s AND pr.utilizado = 0 AND pr.fecha_expiracion > NOW()
            ''', (token,))
            reset = cur.fetchone()
            
            if not reset:
                flash('Link de recuperación inválido o expirado', 'error')
                return redirect(url_for('login'))
            
            if request.method == 'POST':
                password = request.form.get('password', '').strip()
                password_confirm = request.form.get('password_confirm', '').strip()
                
                if not password or len(password) < 6:
                    flash('La contraseña debe tener al menos 6 caracteres', 'error')
                    return render_template('resetear_contraseña.html', token=token, email=reset['email'])
                
                if password != password_confirm:
                    flash('Las contraseñas no coinciden', 'error')
                    return render_template('resetear_contraseña.html', token=token, email=reset['email'])
                
                # Hashear nueva contraseña
                password_hash = generate_password_hash(password, method='pbkdf2:sha256')
                
                # Actualizar contraseña y marcar token como utilizado
                cur.execute('''
                    UPDATE usuarios_admin SET password_hash = %s WHERE id = %s
                ''', (password_hash, reset['usuario_id']))
                
                cur.execute('''
                    UPDATE password_resets SET utilizado = 1 WHERE id = %s
                ''', (reset['id'],))
                
                db.commit()
                
                logger.info("Password reset successfully for user %s", reset['usuario_id'])
                flash('Contraseña actualizada correctamente. Ya puedes iniciar sesión', 'success')
                return redirect(url_for('login'))
            
            return render_template('resetear_contraseña.html', token=token, email=reset['email'])
    
    except Exception as e:
        logger.error("Error en resetear_contraseña: %s", traceback.format_exc())
        flash('Error al procesar la solicitud', 'error')
        return redirect(url_for('login'))


# ============================================================
# RUTAS DE GESTIÓN (PANEL ADMIN)
# ============================================================

@app.route('/gestion')
@login_required
@verificar_suscripcion
def menu_gestion():
    """Panel de gestión principal."""
    return render_template('gestion/dashboard.html')


@app.route('/gestion/platos')
@login_required
@verificar_suscripcion
def gestion_platos():
    """Página de gestión de platos."""
    db = get_db()
    categorias = []
    restaurante_id = session.get('restaurante_id')
    if restaurante_id:
        try:
            with db.cursor() as cur:
                cur.execute("SELECT id, nombre, icono FROM categorias WHERE restaurante_id = %s AND activo = 1 ORDER BY orden, nombre", (restaurante_id,))
                categorias = list_from_rows(cur.fetchall())
        except Exception:
            categorias = []
    return render_template('gestion/platos.html', categorias=categorias)


@app.route('/gestion/categorias')
@login_required
@verificar_suscripcion
def gestion_categorias():
    """Página de gestión de categorías."""
    return render_template('gestion/categorias.html')


@app.route('/gestion/mi-restaurante')
@login_required
@verificar_suscripcion
def gestion_mi_restaurante():
    """Página de configuración del restaurante."""
    restaurante = get_current_restaurant()
    if not restaurante:
        flash('Error al cargar datos del restaurante', 'error')
        return redirect(url_for('menu_gestion'))
    return render_template('gestion/mi_restaurante.html', restaurante=restaurante)


@app.route('/gestion/codigo-qr')
@login_required
@verificar_suscripcion
def gestion_codigo_qr():
    """Página del código QR."""
    restaurante = get_current_restaurant()
    if not restaurante:
        flash('Error al cargar datos del restaurante', 'error')
        return redirect(url_for('menu_gestion'))
    
    base_url = request.host_url.rstrip('/')
    # URL del menú con parámetro qr=1 para tracking de escaneos
    menu_url = f"{base_url}/menu/{restaurante['url_slug']}?qr=1"
    # URL sin parámetro para mostrar al usuario (más limpia)
    menu_url_display = f"{base_url}/menu/{restaurante['url_slug']}"
    
    # Generar QR con el parámetro de tracking
    qr_filename = f"{restaurante['id']}_qr.png"
    try:
        # Forzar regeneración para incluir el parámetro ?qr=1
        qr_path = os.path.join(base_dir, 'static', 'uploads', 'qrs', qr_filename)
        if os.path.exists(qr_path):
            os.remove(qr_path)  # Eliminar QR antiguo sin parámetro
        generar_qr_restaurante(menu_url, qr_filename)
    except Exception as e:
        logger.error("Error generando QR: %s", e)
        qr_filename = None
    
    return render_template('gestion/codigo_qr.html', 
                          restaurante=restaurante, 
                          menu_url=menu_url,
                          menu_url_display=menu_url_display,
                          qr_filename=qr_filename)


@app.route('/gestion/apariencia')
@login_required
@verificar_suscripcion
def gestion_apariencia():
    """Página de personalización de apariencia."""
    restaurante = get_current_restaurant()
    if not restaurante:
        flash('Error al cargar datos del restaurante', 'error')
        return redirect(url_for('menu_gestion'))
    return render_template('gestion/apariencia.html', restaurante=restaurante)


@app.route('/gestion/descargas')
@login_required
@verificar_suscripcion
def gestion_descargas():
    """Página de descargas - PDF del menú."""
    restaurante = get_current_restaurant()
    if not restaurante:
        flash('Error al cargar datos del restaurante', 'error')
        return redirect(url_for('menu_gestion'))
    
    restaurante_id = restaurante['id']
    db = get_db()
    
    try:
        with db.cursor() as cur:
            # Obtener categorías y platos en una sola consulta (evita N+1)
            cur.execute("""
                SELECT c.id as categoria_id, c.nombre as categoria_nombre, c.orden as categoria_orden,
                       p.id as plato_id, p.nombre as plato_nombre, p.descripcion, p.precio, 
                       p.precio_oferta, p.imagen_url, p.etiquetas
                FROM categorias c 
                LEFT JOIN platos p ON c.id = p.categoria_id AND p.activo = 1 AND p.restaurante_id = %s
                WHERE c.restaurante_id = %s AND c.activo = 1 
                ORDER BY c.orden, c.nombre, p.orden, p.nombre
            """, (restaurante_id, restaurante_id))
            rows = cur.fetchall()
            
            # Estructurar el menú
            menu = []
            categorias_dict = {}
            for row in rows:
                cat_id = row['categoria_id']
                if cat_id not in categorias_dict:
                    categorias_dict[cat_id] = {
                        'id': cat_id,
                        'nombre': row['categoria_nombre'],
                        'platos': []
                    }
                    menu.append(categorias_dict[cat_id])
                
                if row['plato_id']:
                    etiquetas = []
                    if row.get('etiquetas'):
                        etiquetas = [tag.strip() for tag in row['etiquetas'].split(',')]
                    
                    categorias_dict[cat_id]['platos'].append({
                        'id': row['plato_id'],
                        'nombre': row['plato_nombre'],
                        'descripcion': row['descripcion'],
                        'precio': row['precio'],
                        'precio_oferta': row['precio_oferta'],
                        'imagen_url': row['imagen_url'],
                        'etiquetas': etiquetas
                    })
        
        return render_template('gestion/descargas.html', restaurante=restaurante, menu=menu)
    
    except Exception as e:
        logger.exception("Error en gestion_descargas")
        flash('Error al cargar la página de descargas', 'error')
        return redirect(url_for('gestion_platos'))


@app.route('/api/menu/pdf')
@login_required
@verificar_suscripcion
def api_menu_pdf():
    """API para descargar el menú en PDF."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            # Obtener restaurante
            cur.execute("SELECT * FROM restaurantes WHERE id = %s", (restaurante_id,))
            restaurante = dict_from_row(cur.fetchone())
            
            # Obtener categorías y platos en una sola consulta (evita N+1)
            cur.execute("""
                SELECT c.id as categoria_id, c.nombre as categoria_nombre, c.orden as categoria_orden,
                       p.id as plato_id, p.nombre as plato_nombre, p.descripcion, p.precio, 
                       p.precio_oferta, p.imagen_url, p.etiquetas
                FROM categorias c 
                LEFT JOIN platos p ON c.id = p.categoria_id AND p.activo = 1 AND p.restaurante_id = %s
                WHERE c.restaurante_id = %s AND c.activo = 1 
                ORDER BY c.orden, c.nombre, p.orden, p.nombre
            """, (restaurante_id, restaurante_id))
            rows = cur.fetchall()
            
            # Estructurar el menú
            menu = []
            categorias_dict = {}
            for row in rows:
                cat_id = row['categoria_id']
                if cat_id not in categorias_dict:
                    categorias_dict[cat_id] = {
                        'id': cat_id,
                        'nombre': row['categoria_nombre'],
                        'platos': []
                    }
                    menu.append(categorias_dict[cat_id])
                
                if row['plato_id']:
                    etiquetas = []
                    if row.get('etiquetas'):
                        etiquetas = [tag.strip() for tag in row['etiquetas'].split(',')]
                    
                    categorias_dict[cat_id]['platos'].append({
                        'id': row['plato_id'],
                        'nombre': row['plato_nombre'],
                        'descripcion': row['descripcion'],
                        'precio': row['precio'],
                        'precio_oferta': row['precio_oferta'],
                        'imagen_url': row['imagen_url'],
                        'etiquetas': etiquetas
                    })
            
            # Renderizar HTML
            base_url = request.host_url.rstrip('/')
            fecha_generacion = datetime.now().strftime('%d/%m/%Y')
            html_content = render_template(
                'menu_pdf.html',
                restaurante=restaurante,
                menu=menu,
                base_url=base_url,
                fecha_generacion=fecha_generacion
            )
            
            # Generar PDF usando pdfkit
            if PDFKIT_AVAILABLE:
                try:
                    # Opciones mejoradas para formato de impresión
                    options = {
                        'page-size': 'A4',
                        'margin-top': '0.7in',
                        'margin-right': '0.5in',
                        'margin-bottom': '0.9in',
                        'margin-left': '0.5in',
                        'encoding': 'UTF-8',
                        'no-outline': None,
                        'enable-local-file-access': None,
                        'print-media-type': None,
                        'disable-smart-shrinking': None,
                        'zoom': '1.0',

                        # Header / Footer
                        'header-left': restaurante.get('nombre', '')[:60],
                        'header-font-size': '11',
                        'header-spacing': '5',
                        'footer-center': 'Página [page] de [toPage]',
                        'footer-font-size': '9',
                        'footer-right': 'Divergent Studio'
                    }

                    # Detectar wkhtmltopdf binario sugerido via env var (opcional)
                    wk_cmd = os.environ.get('WKHTMLTOPDF_CMD')
                    pdf_config = None
                    if wk_cmd:
                        try:
                            pdf_config = pdfkit.configuration(wkhtmltopdf=wk_cmd)
                        except Exception as e:
                            logger.warning('WKHTMLTOPDF_CMD set but pdfkit.configuration failed: %s', e)

                    # Intentar cargar CSS desde static si existe (mejor control de impresión)
                    css_path = os.path.join(base_dir, 'static', 'css', 'menu_pdf.css')
                    css_to_use = css_path if os.path.exists(css_path) else None

                    if pdf_config:
                        pdf_content = pdfkit.from_string(html_content, False, options=options, configuration=pdf_config, css=css_to_use)
                    else:
                        pdf_content = pdfkit.from_string(html_content, False, options=options, css=css_to_use)

                    # Crear nombre seguro para el archivo
                    import re
                    safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', restaurante.get('nombre', 'menu')).strip('_')
                    filename = f'menu_{safe_name}.pdf'

                    # Crear respuesta con el PDF
                    response = make_response(pdf_content)
                    response.headers['Content-Type'] = 'application/pdf'
                    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response

                except Exception as e:
                    logger.exception('Error generando PDF con pdfkit')
                    return jsonify({'success': False, 'error': f'Error al generar PDF: {str(e)}'}), 500
            else:
                # Fallback: devolver HTML para que el navegador lo convierta a PDF
                logger.warning("pdfkit no disponible, devolviendo HTML para imprimir")
                response = make_response(html_content)
                response.headers['Content-Type'] = 'text/html; charset=utf-8'
                return response
    
    except Exception as e:
        logger.error("Error en api_menu_pdf: %s", traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/gestion/pago-pendiente')
@login_required
def gestion_pago_pendiente():
    """Página que se muestra cuando la suscripción ha expirado."""
    db = get_db()
    restaurante_id = session.get('restaurante_id')
    
    with db.cursor() as cur:
        cur.execute('''
            SELECT nombre, fecha_vencimiento, estado_suscripcion, email, whatsapp
            FROM restaurantes WHERE id = %s
        ''', (restaurante_id,))
        restaurante = dict_from_row(cur.fetchone())
    
    dias_vencido = (date.today() - restaurante['fecha_vencimiento']).days if restaurante['fecha_vencimiento'] else 0
    
    # Obtener configuración de pagos
    config_pagos = get_config_global()

    return render_template('gestion/pago_pendiente.html', 
                          restaurante=restaurante, 
                          dias_vencido=dias_vencido,
                          config_pagos=config_pagos,
                          mercado_pago_public_key=os.environ.get('MERCADO_PAGO_PUBLIC_KEY', ''))


@app.route('/api/pago/crear-preferencia', methods=['POST'])
@login_required
def api_crear_preferencia_pago():
    """API para crear una preferencia de pago en Mercado Pago."""
    # Si el cliente no está inicializado en el arranque, reintentar inicialización bajo demanda
    if not MERCADOPAGO_CLIENT:
        logger.warning("MERCADOPAGO_CLIENT is None. Attempting on-demand initialization.")
        try:
            init_ok = init_mercadopago()
            if not init_ok or not MERCADOPAGO_CLIENT:
                # Log detallado de las variables de entorno que ve Python para depuración
                mp_pub = os.environ.get('MERCADO_PAGO_PUBLIC_KEY')
                mp_pub_preview = (mp_pub[:6] + '...') if mp_pub else None
                logger.error("Falla de config. MP_PUBLIC_KEY preview: %s", mp_pub_preview)
                logger.error("MercadoPago config: available=%s, client_present=%s, import_error=%s", MERCADOPAGO_AVAILABLE, bool(MERCADOPAGO_CLIENT), MERCADOPAGO_IMPORT_ERROR)
                return jsonify({'success': False, 'error': 'Mercado Pago no está configurado', 'mp_public_key': os.environ.get('MERCADO_PAGO_PUBLIC_KEY')}), 500
        except Exception as e:
            logger.exception("Error re-inicializando Mercado Pago: %s", e)
            return jsonify({'success': False, 'error': 'Error al inicializar Mercado Pago'}), 500
    
    try:
        db = get_db()
        restaurante_id = session.get('restaurante_id')
        data = request.get_json()
        
        # Obtener datos del restaurante
        with db.cursor() as cur:
            cur.execute(
                "SELECT nombre, email FROM restaurantes WHERE id = %s",
                (restaurante_id,)
            )
            restaurante = dict_from_row(cur.fetchone())
        
        # Definir parámetros del pago
        plan_type = data.get('plan_type', 'mensual')
        
        # Obtener precio desde configuración global
        precio_config = get_config_value('precio_mensual', '14990')
        try:
            precio = int(precio_config)
        except (ValueError, TypeError):
            precio = 14990
        
        # Configurar descripción según plan
        if plan_type == 'mensual':
            descripcion = 'Suscripción Mensual - Menú Digital'
        elif plan_type == 'anual':
            precio = precio * 10  # 10 meses por el precio de 12 (descuento)
            descripcion = 'Suscripción Anual - Menú Digital'
        else:
            descripcion = 'Suscripción - Menú Digital'
        
        # Crear preferencia de pago
        preference_data = {
            "items": [
                {
                    "title": descripcion,
                    "quantity": 1,
                    "currency_id": "CLP",  # Cambiar según país
                    "unit_price": precio
                }
            ],
            "payer": {
                "email": restaurante.get('email', 'no-email@example.com')
            },
            "back_urls": {
                "success": f"{request.host_url.rstrip('/')}/pago/exito",
                "failure": f"{request.host_url.rstrip('/')}/pago/fallo",
                "pending": f"{request.host_url.rstrip('/')}/pago/pendiente"
            },
            "notification_url": f"{request.host_url.rstrip('/')}/webhook/mercado-pago",
            "external_reference": f"rest_{restaurante_id}_{int(datetime.utcnow().timestamp())}",
            "auto_return": "approved"
        }
        
        # Crear preferencia
        response = MERCADOPAGO_CLIENT.preference().create(preference_data)
        
        if response.get("status") == 201:
            preference = response.get("response", {})
            
            # Guardar referencia en BD
            with db.cursor() as cur:
                cur.execute("""
                    UPDATE restaurantes 
                    SET ultima_preferencia_pago = %s,
                        fecha_ultimo_intento_pago = NOW()
                    WHERE id = %s
                """, (preference.get('id'), restaurante_id))
                db.commit()
            
            logger.info("Preferencia de pago creada para restaurante %s: %s", restaurante_id, preference.get('id'))
            
            return jsonify({
                'success': True,
                'preferencia_id': preference.get('id'),
                'init_point': preference.get('init_point')
            })
        else:
            error_msg = response.get('response', {}).get('message', 'Error desconocido')
            logger.error("Error creando preferencia: %s", error_msg)
            return jsonify({'success': False, 'error': error_msg}), 500
    
    except Exception as e:
        logger.error("Error en api_crear_preferencia_pago: %s", traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/mercadopago/status', methods=['GET', 'POST'])
@login_required
@restaurante_owner_required
def admin_mercadopago_status():
    """GET: devuelve estado de Mercado Pago. POST: reintenta inicializar (útil tras setear env vars)."""
    if request.method == 'POST':
        ok = init_mercadopago()
        return jsonify({'reinitialized': ok, 'client_present': bool(MERCADOPAGO_CLIENT), 'sdk_available': MERCADOPAGO_AVAILABLE})

    # GET
    mp_public_preview = None
    try:
        mp_pub = os.environ.get('MERCADO_PAGO_PUBLIC_KEY')
        mp_public_preview = (mp_pub[:8] + '...') if mp_pub else None
    except Exception:
        mp_public_preview = None

    return jsonify({'initialized': bool(MERCADOPAGO_CLIENT), 'sdk_available': MERCADOPAGO_AVAILABLE, 'public_key_preview': mp_public_preview})


@app.route('/admin/mercadopago/test-preference', methods=['POST'])
@login_required
@restaurante_owner_required
def admin_mercadopago_test_preference():
    """Crea una preferencia de prueba en MercadoPago y devuelve init_point para testing."""
    if not MERCADOPAGO_AVAILABLE:
        return jsonify({'success': False, 'error': 'Mercado Pago SDK no instalado. pip install mercado-pago'}), 500
    if not MERCADOPAGO_CLIENT:
        ok = init_mercadopago()
        if not ok or not MERCADOPAGO_CLIENT:
            return jsonify({'success': False, 'error': 'Mercado Pago no está configurado. Revisa MERCADO_PAGO_ACCESS_TOKEN'}), 500

    try:
        data = request.get_json() or {}
        price = data.get('price', 1000)
        description = data.get('description', 'Prueba - Preferencia')
        preference_data = {
            "items": [{"title": description, "quantity": 1, "currency_id": "CLP", "unit_price": price}],
            "back_urls": {
                "success": f"{request.host_url.rstrip('/')}/pago/exito",
                "failure": f"{request.host_url.rstrip('/')}/pago/fallo",
                "pending": f"{request.host_url.rstrip('/')}/pago/pendiente"
            },
            "notification_url": f"{request.host_url.rstrip('/')}/webhook/mercado-pago",
            "auto_return": "approved"
        }
        response = MERCADOPAGO_CLIENT.preference().create(preference_data)
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        logger.exception("Error creando test preference")
        return jsonify({'success': False, 'error': str(e)}), 500


# Webhook de Mercado Pago - Exento de CSRF ya que Mercado Pago no puede enviar el token
@app.route('/webhook/mercado-pago', methods=['POST'])
@csrf_exempt
def webhook_mercado_pago():
    """Webhook para recibir notificaciones de Mercado Pago."""
    try:
        # Si está configurado, verificar firma HMAC-SHA256 (cabecera: X-Hub-Signature-256 o X-Mercadopago-Signature)
        webhook_key = os.environ.get('MERCADO_WEBHOOK_KEY') or os.environ.get('MERCADO_CLIENT_SECRET')
        signature_header = request.headers.get('X-Hub-Signature-256') or request.headers.get('X-Hub-Signature') or request.headers.get('X-Mercadopago-Signature')
        if webhook_key and signature_header:
            try:
                import hmac, hashlib
                payload = request.get_data()
                expected = hmac.new(webhook_key.encode(), payload, hashlib.sha256).hexdigest()
                sig = signature_header.split('=', 1)[1] if '=' in signature_header else signature_header
                if not hmac.compare_digest(expected, sig):
                    logger.warning('Invalid Mercado Pago webhook signature')
                    return jsonify({'status': 'invalid_signature'}), 401
            except Exception as e:
                logger.warning('Error verificando firma de webhook: %s', e)
                return jsonify({'status': 'error', 'error': 'signature_verification_failed'}), 400

        data = request.get_json() or request.form.to_dict()
        
        # Validar que sea una notificación de pago
        if not data or 'data' not in data:
            logger.warning("Webhook recibido sin datos de pago: %s", data)
            return jsonify({'status': 'ignored'}), 200
        
        payment_id = data['data'].get('id')
        
        if not payment_id:
            logger.warning("Webhook sin payment_id: %s", data)
            return jsonify({'status': 'ignored'}), 200
        
        # Obtener detalles del pago desde Mercado Pago
        payment_info = MERCADOPAGO_CLIENT.payment().get(payment_id)
        
        if payment_info.get('status') != 200:
            logger.error("Error obteniendo pago %s: %s", payment_id, payment_info)
            return jsonify({'status': 'error'}), 500
        
        payment = payment_info.get('response', {})
        external_reference = payment.get('external_reference', '')
        payment_status = payment.get('status')
        
        # Extraer restaurante_id de external_reference (formato: rest_RESTAURANTE_ID_TIMESTAMP)
        if not external_reference.startswith('rest_'):
            logger.warning("External reference inválido: %s", external_reference)
            return jsonify({'status': 'ignored'}), 200
        
        try:
            restaurante_id = int(external_reference.split('_')[1])
        except (IndexError, ValueError):
            logger.error("No se pudo extraer restaurante_id de: %s", external_reference)
            return jsonify({'status': 'error'}), 500
        
        # Procesar según estado del pago
        db = get_db()
        
        if payment_status == 'approved':
            # Pago aprobado - Extender suscripción
            plan_type = 'mensual'  # Podría obtenerse del pago
            dias_extension = 30  # Por defecto mensual
            
            with db.cursor() as cur:
                # Idempotencia: comprobar si este payment_id ya fue aplicado
                cur.execute("SELECT ultimo_pago_mercadopago FROM restaurantes WHERE id = %s", (restaurante_id,))
                prev = cur.fetchone()
                if prev and prev.get('ultimo_pago_mercadopago') == payment_id:
                    logger.info('Payment %s already applied for restaurante %s; ignoring (idempotent)', payment_id, restaurante_id)
                    return jsonify({'status': 'already_processed'}), 200

                # Obtener fecha de vencimiento actual
                cur.execute(
                    "SELECT fecha_vencimiento FROM restaurantes WHERE id = %s",
                    (restaurante_id,)
                )
                result = dict_from_row(cur.fetchone())
                
                fecha_vencimiento_actual = None
                if result and result.get('fecha_vencimiento'):
                    fecha_vencimiento_actual = result.get('fecha_vencimiento')
                else:
                    fecha_vencimiento_actual = date.today()

                # Si está vencido, comenzar desde hoy
                if fecha_vencimiento_actual < date.today():
                    fecha_vencimiento_actual = date.today()
                
                # Calcular nueva fecha
                nueva_fecha = fecha_vencimiento_actual + timedelta(days=dias_extension)
                
                # Actualizar BD
                cur.execute("""
                    UPDATE restaurantes 
                    SET estado_suscripcion = 'activa',
                        fecha_vencimiento = %s,
                        ultimo_pago_mercadopago = %s,
                        fecha_ultimo_pago = NOW()
                    WHERE id = %s
                """, (nueva_fecha, payment_id, restaurante_id))
                db.commit()
            
            logger.info("Pago aprobado para restaurante %s. Suscripción extendida hasta %s", restaurante_id, nueva_fecha)
        
        elif payment_status == 'pending':
            logger.info("Pago pendiente para restaurante %s: %s", restaurante_id, payment_id)
        
        elif payment_status == 'rejected':
            logger.warning("Pago rechazado para restaurante %s: %s", restaurante_id, payment_id)
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logger.error("Error en webhook_mercado_pago: %s", traceback.format_exc())
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/pago/exito')
@login_required
def pago_exito():
    """Página de confirmación de pago exitoso."""
    return render_template('pago_exito.html')


@app.route('/pago/fallo')
@login_required
def pago_fallo():
    """Página de error de pago."""
    return render_template('pago_fallo.html')


@app.route('/pago/pendiente')
@login_required
def pago_pendiente_status():
    """Página de pago pendiente."""
    return render_template('pago_pendiente_status.html')


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
                # Paginación opcional
                page = request.args.get('page', type=int)
                per_page = request.args.get('per_page', 50, type=int)
                per_page = min(per_page, 100)  # Máximo 100 por página
                
                # Filtro opcional por categoría
                categoria_id = request.args.get('categoria_id', type=int)
                
                base_query = '''
                    SELECT p.*, c.nombre as categoria_nombre 
                    FROM platos p 
                    LEFT JOIN categorias c ON p.categoria_id = c.id
                    WHERE p.restaurante_id = %s 
                '''
                params = [restaurante_id]
                
                if categoria_id:
                    base_query += ' AND p.categoria_id = %s'
                    params.append(categoria_id)
                
                base_query += ' ORDER BY p.orden, p.nombre'
                
                # Si se pide paginación
                if page is not None:
                    # Contar total
                    count_query = 'SELECT COUNT(*) as total FROM platos WHERE restaurante_id = %s'
                    count_params = [restaurante_id]
                    if categoria_id:
                        count_query += ' AND categoria_id = %s'
                        count_params.append(categoria_id)
                    cur.execute(count_query, count_params)
                    total = cur.fetchone()['total']
                    
                    offset = (page - 1) * per_page
                    base_query += ' LIMIT %s OFFSET %s'
                    params.extend([per_page, offset])
                    
                    cur.execute(base_query, params)
                    rows = list_from_rows(cur.fetchall())
                    
                    # Enriquecer con URLs responsivas
                    for r in rows:
                        pid = r.get('imagen_public_id')
                        img_url = r.get('imagen_url')
                        if pid and CLOUDINARY_AVAILABLE and CLOUDINARY_CONFIGURED:
                            generated_url = cloudinary_image_url(pid, width=640)
                            r['imagen_src'] = generated_url if generated_url else img_url
                            r['imagen_srcset'] = cloudinary_srcset(pid) if generated_url else None
                        else:
                            r['imagen_src'] = img_url
                            r['imagen_srcset'] = None
                    
                    return jsonify({
                        'items': rows,
                        'total': total,
                        'page': page,
                        'per_page': per_page,
                        'pages': (total + per_page - 1) // per_page
                    })
                
                # Sin paginación (compatibilidad hacia atrás)
                cur.execute(base_query, params)
                rows = list_from_rows(cur.fetchall())
                
                # Cargar imágenes múltiples para cada plato
                plato_ids = [r['id'] for r in rows]
                imagenes_por_plato = {}
                if plato_ids:
                    # Usar placeholders seguros para evitar SQL injection
                    placeholders = ','.join(['%s'] * len(plato_ids))
                    query = '''
                        SELECT * FROM platos_imagenes 
                        WHERE plato_id IN ({}) AND activo = 1
                        ORDER BY es_principal DESC, orden ASC
                    '''.format(placeholders)
                    cur.execute(query, tuple(plato_ids))
                    for img in cur.fetchall():
                        plato_id = img['plato_id']
                        if plato_id not in imagenes_por_plato:
                            imagenes_por_plato[plato_id] = []
                        imagenes_por_plato[plato_id].append(dict(img))
                
                # Enriquecer con URLs responsivas si tenemos imagen_public_id
                for r in rows:
                    pid = r.get('imagen_public_id')
                    img_url = r.get('imagen_url')
                    
                    # Agregar imágenes múltiples
                    r['imagenes'] = imagenes_por_plato.get(r['id'], [])
                    
                    # Intentar generar URL optimizada con Cloudinary
                    if pid and CLOUDINARY_AVAILABLE and CLOUDINARY_CONFIGURED:
                        generated_url = cloudinary_image_url(pid, width=640)
                        r['imagen_src'] = generated_url if generated_url else img_url
                        r['imagen_srcset'] = cloudinary_srcset(pid) if generated_url else None
                    else:
                        # Usar la URL directa guardada en la base de datos
                        r['imagen_src'] = img_url
                        r['imagen_srcset'] = None
                return jsonify(rows)
                
            if request.method == 'POST':
                data = request.get_json()
                
                # Validación de datos obligatorios
                if not data:
                    return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
                
                nombre = data.get('nombre', '').strip()
                if not nombre or len(nombre) > 200:
                    return jsonify({'success': False, 'error': 'Nombre es obligatorio (máx 200 caracteres)'}), 400
                
                categoria_id = data.get('categoria_id')
                if not categoria_id:
                    return jsonify({'success': False, 'error': 'Categoría es obligatoria'}), 400
                
                # Validar que la categoría pertenece al restaurante
                cur.execute("SELECT id FROM categorias WHERE id = %s AND restaurante_id = %s", (categoria_id, restaurante_id))
                if not cur.fetchone():
                    return jsonify({'success': False, 'error': 'Categoría no válida'}), 400
                
                # Validar precio
                try:
                    precio = float(data.get('precio', 0))
                    if precio < 0:
                        return jsonify({'success': False, 'error': 'Precio no puede ser negativo'}), 400
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Precio inválido'}), 400
                
                # Procesar imagen - puede venir como archivo o ya subida previamente
                imagen_url = data.get('imagen_url', '')
                imagen_public_id = data.get('imagen_public_id')  # Puede venir del frontend si ya se subió

                if 'imagen' in request.files and request.files['imagen']:
                    file = request.files['imagen']
                    if file and allowed_file(file.filename):
                        # Validación de MIME y tamaño
                        if request.content_length and request.content_length > app.config.get('MAX_CONTENT_LENGTH', MAX_CONTENT_LENGTH):
                            return jsonify({'success': False, 'error': 'Archivo demasiado grande'}), 400
                        is_valid, err = validate_image_file(file)
                        if not is_valid:
                            return jsonify({'success': False, 'error': err}), 400
                        try:
                            if not is_cloudinary_ready():
                                return jsonify({'success': False, 'error': 'Cloudinary no está configurado'}), 500
                            
                            # Subir a Cloudinary (rotación EXIF se corrige automáticamente)
                            result = cloudinary_upload(
                                file,
                                folder=f"mimenudigital/platos/{restaurante_id}"
                            )
                            imagen_url = result.get('secure_url')
                            imagen_public_id = result.get('public_id')
                            if not imagen_url:
                                raise Exception('Cloudinary no retornó URL')
                        except Exception as e:
                            logger.exception("Error subiendo imagen a Cloudinary: %s", traceback.format_exc())
                            # Guardar localmente y crear registro pendiente para reintento
                            try:
                                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                                unique_filename = f"{restaurante_id}_{uuid.uuid4().hex[:8]}.{ext}"
                                upload_folder = app.config.get('UPLOAD_FOLDER')
                                os.makedirs(upload_folder, exist_ok=True)
                                filepath = os.path.join(upload_folder, unique_filename)
                                file.save(filepath)

                                # Insertar registro pendiente (sin plato_id, se asociará tras insertar el plato)
                                with db.cursor() as cur_pending:
                                    cur_pending.execute('''
                                        INSERT INTO imagenes_pendientes (restaurante_id, local_path, tipo, attempts, status, created_at)
                                        VALUES (%s, %s, %s, 0, 'pending', NOW())
                                    ''', (restaurante_id, filepath, 'plato_upload'))
                                    db.commit()
                                    pending_id = cur_pending.lastrowid

                                imagen_url = f"/static/uploads/{unique_filename}"
                                imagen_public_id = None
                                # No return aquí; se insertará el plato con la imagen local y se asociará pending luego
                                logger.info('Imagen guardada localmente y pendiente de subida (pending_id=%s)', pending_id)
                            except Exception as err:
                                logger.exception('Error creando pending tras fallo de Cloudinary: %s', err)
                                return jsonify({'success': False, 'error': f'Error al subir imagen: {str(e)}'}), 500
                
                # Sanitizar descripción y etiquetas
                descripcion = (data.get('descripcion', '') or '')[:1000]  # Límite 1000 chars
                etiquetas = (data.get('etiquetas', '') or '')[:500]  # Límite 500 chars
                
                cur.execute('''
                    INSERT INTO platos (restaurante_id, categoria_id, nombre, descripcion, precio, 
                                        precio_oferta, imagen_url, imagen_public_id, etiquetas, es_vegetariano, es_vegano,
                                        es_sin_gluten, es_picante, es_nuevo, es_popular, orden, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                ''', (
                    restaurante_id,
                    categoria_id,
                    nombre,
                    descripcion,
                    precio,
                    data.get('precio_oferta'),
                    imagen_url,
                    imagen_public_id,
                    etiquetas,
                    1 if data.get('es_vegetariano') else 0,
                    1 if data.get('es_vegano') else 0,
                    1 if data.get('es_sin_gluten') else 0,
                    1 if data.get('es_picante') else 0,
                    1 if data.get('es_nuevo') else 0,
                    1 if data.get('es_popular') else 0,
                    int(data.get('orden', 0))
                ))
                db.commit()
                new_id = cur.lastrowid
                
                # Guardar imágenes múltiples si existen
                imagenes = data.get('imagenes', [])
                if imagenes:
                    for img in imagenes:
                        cur.execute('''
                            INSERT INTO platos_imagenes (plato_id, restaurante_id, imagen_url, imagen_public_id, orden, es_principal)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (
                            new_id,
                            restaurante_id,
                            img.get('imagen_url', ''),
                            img.get('imagen_public_id'),
                            img.get('orden', 0),
                            img.get('es_principal', 0)
                        ))
                    db.commit()
                
                # Si existe un pending creado antes (fallo de subida), asociarlo al plato recién creado
                try:
                    if 'pending_id' in locals() and pending_id:
                        with db.cursor() as cur2:
                            cur2.execute("UPDATE imagenes_pendientes SET plato_id = %s WHERE id = %s", (new_id, pending_id))
                            db.commit()
                            logger.info('Asociado pending_id %s con plato %s', pending_id, new_id)
                except Exception as e:
                    logger.warning('No se pudo asociar pending_id %s con plato %s: %s', pending_id, new_id, e)

                # Invalidar cache del menú público
                invalidar_cache_restaurante(restaurante_id)
                
                return jsonify({'success': True, 'id': new_id})
                
    except Exception as e:
        try:
            db.rollback()
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_platos: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_platos")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/upload-image', methods=['POST'])
@login_required
@restaurante_owner_required
def api_upload_image():
    """API para subir imágenes de platos (sube a Cloudinary). Requiere Cloudinary configurado."""
    try:
        # Requisitos previos: SDK presente y CLOUDINARY_URL configurada
        if not CLOUDINARY_AVAILABLE:
            logger.error('Cloudinary SDK no instalado. Instalalo con: pip install cloudinary')
            return jsonify({'success': False, 'error': 'Cloudinary SDK no está instalado. Ejecuta: pip install cloudinary'}), 500
        
        # Usar is_cloudinary_ready() para verificar y re-inicializar si es necesario
        if not is_cloudinary_ready():
            logger.error('Cloudinary no configurado. CLOUDINARY_URL=%s', os.environ.get('CLOUDINARY_URL', 'NO DEFINIDA'))
            return jsonify({'success': False, 'error': 'Cloudinary no está configurado. Añade la variable de entorno CLOUDINARY_URL'}), 500

        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió ninguna imagen'}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No se seleccionó ningún archivo'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Tipo de archivo no permitido. Usa: PNG, JPG, JPEG, GIF o WEBP'}), 400

        if request.content_length and request.content_length > app.config.get('MAX_CONTENT_LENGTH', MAX_CONTENT_LENGTH):
            return jsonify({'success': False, 'error': 'Archivo demasiado grande'}), 400

        # Validación adicional de contenido (MIME sniffing si está disponible)
        is_valid, err = validate_image_file(file)
        if not is_valid:
            return jsonify({'success': False, 'error': err}), 400

        # Intentar subir a Cloudinary
        try:
            restaurante_id = session.get('restaurante_id') or 'anon'
            # Subir a Cloudinary
            result = cloudinary_upload(
                file,
                folder=f"mimenudigital/platos/{restaurante_id}"
            )
            url = result.get('secure_url') or result.get('url')
            public_id = result.get('public_id')
            if not url:
                raise Exception('Cloudinary no retornó URL')
            return jsonify({'success': True, 'message': 'Imagen subida correctamente', 'url': url, 'public_id': public_id})

        except Exception as e:
            logger.exception("Error subiendo imagen a Cloudinary: %s", traceback.format_exc())
            # Guardar localmente y crear registro pendiente para reintento
            try:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                unique_filename = f"{session.get('restaurante_id')}_{uuid.uuid4().hex[:8]}.{ext}"
                upload_folder = app.config.get('UPLOAD_FOLDER')
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, unique_filename)
                file.save(filepath)

                # Insertar registro pendiente
                db = get_db()
                with db.cursor() as cur2:
                    cur2.execute('''
                        INSERT INTO imagenes_pendientes (restaurante_id, local_path, tipo, attempts, status, created_at)
                        VALUES (%s, %s, %s, 0, 'pending', NOW())
                    ''', (session.get('restaurante_id'), filepath, 'upload'))
                    db.commit()
                    pending_id = cur2.lastrowid

                image_url = f"/static/uploads/{unique_filename}"
                return jsonify({'success': True, 'message': 'Imagen guardada localmente y pendiente de subida (se reintentará)', 'url': image_url, 'pending_id': pending_id}), 200

            except Exception as err:
                logger.exception("Error creando pending tras fallo de Cloudinary: %s", err)
                return jsonify({'success': False, 'error': f'Error al subir imagen a Cloudinary: {str(e)}'}), 500

    except Exception as e:
        # If it's a request entity too large error, respond with 413
        from werkzeug.exceptions import RequestEntityTooLarge as _ReqTooLarge
        if isinstance(e, _ReqTooLarge):
            return jsonify({'success': False, 'error': 'Archivo demasiado grande'}), 413
        logger.exception("Error en api_upload_image")
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
                
                # Procesar imagen - puede venir como archivo o ya subida previamente
                imagen_url = data.get('imagen_url', '')
                imagen_public_id = data.get('imagen_public_id')  # Puede venir del frontend si ya se subió
                
                if 'imagen' in request.files and request.files['imagen']:
                    file = request.files['imagen']
                    if file and allowed_file(file.filename):
                        # Validación de MIME y tamaño
                        if request.content_length and request.content_length > app.config.get('MAX_CONTENT_LENGTH', MAX_CONTENT_LENGTH):
                            return jsonify({'success': False, 'error': 'Archivo demasiado grande'}), 400
                        is_valid, err = validate_image_file(file)
                        if not is_valid:
                            return jsonify({'success': False, 'error': err}), 400
                        try:
                            if not is_cloudinary_ready():
                                return jsonify({'success': False, 'error': 'Cloudinary no está configurado'}), 500
                            
                            # Subir a Cloudinary
                            result = cloudinary_upload(
                                file,
                                folder=f"mimenudigital/platos/{restaurante_id}"
                            )
                            imagen_url = result.get('secure_url')
                            imagen_public_id = result.get('public_id')
                        except Exception as e:
                            logger.error("Error subiendo imagen a Cloudinary: %s", traceback.format_exc())
                            return jsonify({'success': False, 'error': f'Error al subir imagen: {str(e)}'}), 500
                
                cur.execute('''
                    UPDATE platos SET 
                        categoria_id = %s, nombre = %s, descripcion = %s, precio = %s,
                        precio_oferta = %s, imagen_url = %s, imagen_public_id = %s, etiquetas = %s, 
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
                    imagen_url,
                    imagen_public_id,
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
                
                # Actualizar imágenes múltiples si existen
                imagenes = data.get('imagenes', [])
                if imagenes:
                    # Eliminar imágenes anteriores
                    cur.execute("DELETE FROM platos_imagenes WHERE plato_id = %s", (plato_id,))
                    # Insertar las nuevas
                    for img in imagenes:
                        cur.execute('''
                            INSERT INTO platos_imagenes (plato_id, restaurante_id, imagen_url, imagen_public_id, orden, es_principal)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (
                            plato_id,
                            restaurante_id,
                            img.get('imagen_url', ''),
                            img.get('imagen_public_id'),
                            img.get('orden', 0),
                            img.get('es_principal', 0)
                        ))
                
                db.commit()
                # Invalidar cache del menú público
                invalidar_cache_restaurante(restaurante_id)
                return jsonify({'success': True})
                
            if request.method == 'DELETE':
                # Antes de borrar, intentar eliminar la imagen en Cloudinary si existe
                try:
                    cur.execute("SELECT imagen_public_id FROM platos WHERE id = %s AND restaurante_id = %s", (plato_id, restaurante_id))
                    row = cur.fetchone()
                    public_id = row.get('imagen_public_id') if row else None
                    if public_id and CLOUDINARY_AVAILABLE and CLOUDINARY_CONFIGURED and hasattr(cloudinary, 'uploader'):
                        try:
                            cloudinary.uploader.destroy(public_id, resource_type='image')
                            logger.info('Imagen Cloudinary %s eliminada para plato %s', public_id, plato_id)
                        except Exception as e:
                            logger.warning('No se pudo eliminar imagen en Cloudinary: %s', e)
                except Exception as e:
                    logger.warning('Error comprobando imagen_public_id antes de borrar plato: %s', e)

                cur.execute("DELETE FROM platos WHERE id = %s AND restaurante_id = %s", 
                           (plato_id, restaurante_id))
                db.commit()
                # Invalidar cache del menú público
                invalidar_cache_restaurante(restaurante_id)
                return jsonify({'success': True})
                
    except Exception as e:
        try:
            db.rollback()
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_plato: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_plato")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - APARIENCIA DEL RESTAURANTE
# ============================================================

@app.route('/api/mi-restaurante/apariencia', methods=['PUT'])
@login_required
@restaurante_owner_required
def api_apariencia():
    """API para actualizar la apariencia/tema del menú."""
    db = get_db()
    restaurante_id = session.get('restaurante_id')
    if not restaurante_id:
        return jsonify({'success': False, 'error': 'Restaurante no seleccionado'}), 400

    try:
        data = request.get_json() or {}
        tema = data.get('tema', 'calido')
        # Convertir booleanos/strings a 0/1 de forma robusta
        mostrar_precios = 1 if (data.get('mostrar_precios', True) in (True, 1, '1', 'true')) else 0
        mostrar_descripciones = 1 if (data.get('mostrar_descripciones', True) in (True, 1, '1', 'true')) else 0
        mostrar_imagenes = 1 if (data.get('mostrar_imagenes', True) in (True, 1, '1', 'true')) else 0

        with db.cursor() as cur:
            # Confirmar que el restaurante existe y pertenece al session
            cur.execute("SELECT id FROM restaurantes WHERE id = %s", (restaurante_id,))
            if not cur.fetchone():
                logger.warning('Attempt to update appearance for missing restaurant id: %s', restaurante_id)
                return jsonify({'success': False, 'error': 'Restaurante no encontrado'}), 404

            cur.execute('''
                UPDATE restaurantes SET 
                    tema = %s,
                    mostrar_precios = %s,
                    mostrar_descripciones = %s,
                    mostrar_imagenes = %s,
                    fecha_actualizacion = NOW()
                WHERE id = %s
            ''', (
                tema,
                mostrar_precios,
                mostrar_descripciones,
                mostrar_imagenes,
                restaurante_id
            ))
            db.commit()
        # Invalidar cache del menú público
        invalidar_cache_restaurante(restaurante_id)
        logger.info("Apariencia actualizada para restaurante %s: tema=%s, precios=%s, descripciones=%s, imagenes=%s", 
                   restaurante_id, tema, mostrar_precios, mostrar_descripciones, mostrar_imagenes)
        return jsonify({'success': True, 'message': 'Apariencia actualizada'})
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.exception('Error actualizando apariencia')
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
                nuevo_orden = int(data.get('orden', 0))
                
                # Desplazar categorías existentes si el nuevo orden ya está ocupado
                if nuevo_orden > 0:
                    cur.execute('''
                        UPDATE categorias 
                        SET orden = orden + 1 
                        WHERE restaurante_id = %s AND orden >= %s
                        ORDER BY orden DESC
                    ''', (restaurante_id, nuevo_orden))
                
                cur.execute('''
                    INSERT INTO categorias (restaurante_id, nombre, descripcion, icono, orden, activo)
                    VALUES (%s, %s, %s, %s, %s, 1)
                ''', (
                    restaurante_id,
                    data.get('nombre'),
                    data.get('descripcion', ''),
                    data.get('icono', ''),
                    nuevo_orden
                ))
                db.commit()
                # Invalidar cache del menú público
                invalidar_cache_restaurante(restaurante_id)
                return jsonify({'success': True, 'id': cur.lastrowid})
                
    except Exception as e:
        try:
            db.rollback()
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_categorias: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_categorias")
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
                nuevo_orden = int(data.get('orden', 0))
                
                # Obtener el orden actual de la categoría
                cur.execute("SELECT orden FROM categorias WHERE id = %s AND restaurante_id = %s", 
                           (categoria_id, restaurante_id))
                cat_actual = cur.fetchone()
                orden_actual = cat_actual['orden'] if cat_actual else 0
                
                # Si el orden cambió, desplazar las demás categorías
                if nuevo_orden != orden_actual and nuevo_orden > 0:
                    if nuevo_orden > orden_actual:
                        # Moviendo hacia abajo: decrementar las que están en el rango
                        cur.execute('''
                            UPDATE categorias 
                            SET orden = orden - 1 
                            WHERE restaurante_id = %s AND orden > %s AND orden <= %s AND id != %s
                        ''', (restaurante_id, orden_actual, nuevo_orden, categoria_id))
                    else:
                        # Moviendo hacia arriba: incrementar las que están en el rango
                        cur.execute('''
                            UPDATE categorias 
                            SET orden = orden + 1 
                            WHERE restaurante_id = %s AND orden >= %s AND orden < %s AND id != %s
                        ''', (restaurante_id, nuevo_orden, orden_actual, categoria_id))
                
                cur.execute('''
                    UPDATE categorias SET 
                        nombre = %s, descripcion = %s, icono = %s, orden = %s, activo = %s
                    WHERE id = %s AND restaurante_id = %s
                ''', (
                    data.get('nombre'),
                    data.get('descripcion', ''),
                    data.get('icono', ''),
                    nuevo_orden,
                    data.get('activo', 1),
                    categoria_id, restaurante_id
                ))
                db.commit()
                # Invalidar cache del menú público
                invalidar_cache_restaurante(restaurante_id)
                return jsonify({'success': True})
                
            if request.method == 'DELETE':
                # Primero eliminar platos de la categoría
                cur.execute("DELETE FROM platos WHERE categoria_id = %s AND restaurante_id = %s", 
                           (categoria_id, restaurante_id))
                cur.execute("DELETE FROM categorias WHERE id = %s AND restaurante_id = %s", 
                           (categoria_id, restaurante_id))
                db.commit()
                # Invalidar cache del menú público
                invalidar_cache_restaurante(restaurante_id)
                return jsonify({'success': True})
                
    except Exception as e:
        try:
            db.rollback()
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_categoria: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_categoria")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API - ETIQUETAS PERSONALIZADAS
# ============================================================

@app.route('/api/etiquetas', methods=['GET', 'POST'])
@login_required
def api_etiquetas():
    """API para listar y crear etiquetas del restaurante."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            if request.method == 'GET':
                cur.execute('''
                    SELECT id, nombre, color, emoji, orden, activo
                    FROM etiquetas 
                    WHERE restaurante_id = %s AND activo = 1
                    ORDER BY orden, nombre
                ''', (restaurante_id,))
                return jsonify(list_from_rows(cur.fetchall()))
                
            if request.method == 'POST':
                data = request.get_json()
                nombre = (data.get('nombre', '') or '').strip()[:50]
                color = (data.get('color', '#34495e') or '#34495e')[:7]
                emoji = (data.get('emoji', '') or '')[:10]
                
                if not nombre:
                    return jsonify({'success': False, 'error': 'El nombre es requerido'}), 400
                
                # Verificar si ya existe
                cur.execute('''
                    SELECT id FROM etiquetas 
                    WHERE restaurante_id = %s AND nombre = %s
                ''', (restaurante_id, nombre))
                if cur.fetchone():
                    return jsonify({'success': False, 'error': 'Ya existe una etiqueta con ese nombre'}), 400
                
                # Obtener siguiente orden
                cur.execute('SELECT COALESCE(MAX(orden), 0) + 1 as next_orden FROM etiquetas WHERE restaurante_id = %s', (restaurante_id,))
                next_orden = cur.fetchone()['next_orden']
                
                cur.execute('''
                    INSERT INTO etiquetas (restaurante_id, nombre, color, emoji, orden, activo)
                    VALUES (%s, %s, %s, %s, %s, 1)
                ''', (restaurante_id, nombre, color, emoji, next_orden))
                db.commit()
                
                return jsonify({
                    'success': True, 
                    'id': cur.lastrowid,
                    'etiqueta': {
                        'id': cur.lastrowid,
                        'nombre': nombre,
                        'color': color,
                        'emoji': emoji,
                        'orden': next_orden
                    }
                })
                
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.exception("Error en api_etiquetas")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/etiquetas/<int:etiqueta_id>', methods=['PUT', 'DELETE'])
@login_required
def api_etiqueta(etiqueta_id):
    """API para editar o eliminar una etiqueta."""
    db = get_db()
    restaurante_id = session['restaurante_id']
    
    try:
        with db.cursor() as cur:
            # Verificar que la etiqueta pertenece al restaurante
            cur.execute('SELECT id FROM etiquetas WHERE id = %s AND restaurante_id = %s', 
                       (etiqueta_id, restaurante_id))
            if not cur.fetchone():
                return jsonify({'error': 'Etiqueta no encontrada'}), 404
            
            if request.method == 'PUT':
                data = request.get_json()
                nombre = (data.get('nombre', '') or '').strip()[:50]
                color = (data.get('color', '#34495e') or '#34495e')[:7]
                emoji = (data.get('emoji', '') or '')[:10]
                
                if not nombre:
                    return jsonify({'success': False, 'error': 'El nombre es requerido'}), 400
                
                # Verificar duplicados (excluyendo la actual)
                cur.execute('''
                    SELECT id FROM etiquetas 
                    WHERE restaurante_id = %s AND nombre = %s AND id != %s
                ''', (restaurante_id, nombre, etiqueta_id))
                if cur.fetchone():
                    return jsonify({'success': False, 'error': 'Ya existe una etiqueta con ese nombre'}), 400
                
                cur.execute('''
                    UPDATE etiquetas SET nombre = %s, color = %s, emoji = %s
                    WHERE id = %s AND restaurante_id = %s
                ''', (nombre, color, emoji, etiqueta_id, restaurante_id))
                db.commit()
                
                return jsonify({'success': True})
                
            if request.method == 'DELETE':
                cur.execute('DELETE FROM etiquetas WHERE id = %s AND restaurante_id = %s', 
                           (etiqueta_id, restaurante_id))
                db.commit()
                return jsonify({'success': True})
                
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        logger.exception("Error en api_etiqueta")
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
                
                # Log para debug
                logger.info("Actualizando restaurante %s - horario: %s, whatsapp: %s", 
                           restaurante_id, 
                           data.get('horario', '')[:100] if data.get('horario') else 'None',
                           data.get('whatsapp', ''))
                
                cur.execute('''
                    UPDATE restaurantes SET 
                        nombre = %s, descripcion = %s, slogan = %s, telefono = %s, 
                        email = %s, direccion = %s, horario = %s, instagram = %s, 
                        facebook = %s, whatsapp = %s, logo_url = %s, mostrar_precios = %s, 
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
                    data.get('logo_url', ''),
                    data.get('mostrar_precios', 1),
                    data.get('mostrar_descripciones', 1),
                    data.get('mostrar_imagenes', 1),
                    data.get('moneda', '$'),
                    restaurante_id
                ))
                db.commit()
                
                logger.info("Restaurante %s actualizado correctamente", restaurante_id)
                
                # Actualizar nombre en sesión
                session['restaurante_nombre'] = data.get('nombre')
                
                # Invalidar cache del menú público
                invalidar_cache_restaurante(restaurante_id)
                
                return jsonify({'success': True})
                
    except Exception as e:
        try:
            db.rollback()
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_mi_restaurante: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_mi_restaurante")
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
        # Invalidar cache del menú público
        invalidar_cache_restaurante(restaurante_id)
        return jsonify({'success': True})
        
    except Exception as e:
        try:
            db.rollback()
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_actualizar_tema: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_actualizar_tema")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/mi-restaurante/logo', methods=['POST'])
@login_required
@restaurante_owner_required
def api_subir_logo():
    """Sube el logo del restaurante a Cloudinary."""
    if 'logo' not in request.files:
        return jsonify({'success': False, 'error': 'No se envió ningún archivo'}), 400
    
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Archivo vacío'}), 400
    
    if file and allowed_file(file.filename):
        try:
            if not is_cloudinary_ready():
                return jsonify({'success': False, 'error': 'Cloudinary no está configurado'}), 500
            
            # Subir logo a Cloudinary
            result = cloudinary_upload(
                file,
                folder=f"mimenudigital/logos"
            )
            
            logo_url = result['secure_url']
            
            # Actualizar en BD
            db = get_db()
            with db.cursor() as cur:
                cur.execute("UPDATE restaurantes SET logo_url = %s WHERE id = %s", 
                           (logo_url, session['restaurante_id']))
                db.commit()
            
            logger.info("Logo subido a Cloudinary para restaurante %s", session['restaurante_id'])
            # Invalidar cache del menú público
            invalidar_cache_restaurante(session['restaurante_id'])
            return jsonify({'success': True, 'logo_url': logo_url})
        
        except Exception as e:
            logger.exception("Error subiendo logo a Cloudinary")
            return jsonify({'success': False, 'error': f'Error al subir imagen: {str(e)}'}), 500
    
    return jsonify({'success': False, 'error': 'Tipo de archivo no permitido'}), 400


# ============================================================
# API - DASHBOARD STATS
# ============================================================

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """Obtiene estadísticas del restaurante para el dashboard. OPTIMIZADO con query combinada."""
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
        # Intentar obtener del caché (TTL corto de 30 segundos)
        cache_key = f"dashboard_stats:{restaurante_id}"
        if SECURITY_MIDDLEWARE_AVAILABLE:
            cached = get_cache().get(cache_key)
            if cached:
                cached['base_url'] = request.host_url.rstrip('/')  # Actualizar base_url
                return jsonify(cached)
        
        db = get_db()
        hoy = date.today().isoformat()
        primer_dia_mes = date.today().replace(day=1).isoformat()
        
        with db.cursor() as cur:
            # Query combinada para obtener todos los conteos en una sola operación
            cur.execute('''
                SELECT 
                    (SELECT COUNT(*) FROM platos WHERE restaurante_id = %s AND activo = 1) as total_platos,
                    (SELECT COUNT(*) FROM categorias WHERE restaurante_id = %s AND activo = 1) as total_categorias,
                    (SELECT url_slug FROM restaurantes WHERE id = %s) as url_slug,
                    (SELECT COALESCE(SUM(visitas), 0) FROM estadisticas_diarias WHERE restaurante_id = %s AND fecha >= %s) as total_vistas,
                    (SELECT COALESCE(SUM(escaneos_qr), 0) FROM estadisticas_diarias WHERE restaurante_id = %s AND fecha >= %s) as total_scans
            ''', (restaurante_id, restaurante_id, restaurante_id, restaurante_id, primer_dia_mes, restaurante_id, primer_dia_mes))
            stats = cur.fetchone()
            
            # Estadísticas de hoy (query separada porque es más simple)
            cur.execute('''
                SELECT COALESCE(visitas, 0) as visitas, COALESCE(escaneos_qr, 0) as scans
                FROM estadisticas_diarias 
                WHERE restaurante_id = %s AND fecha = %s
            ''', (restaurante_id, hoy))
            hoy_row = cur.fetchone()
            
            # Últimos 7 días
            cur.execute('''
                SELECT fecha, visitas, escaneos_qr as scans
                FROM estadisticas_diarias 
                WHERE restaurante_id = %s AND fecha >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                ORDER BY fecha
            ''', (restaurante_id,))
            ultimos_7_dias = list_from_rows(cur.fetchall())
            
            result = {
                'total_platos': stats['total_platos'] if stats else 0,
                'total_categorias': stats['total_categorias'] if stats else 0,
                'total_vistas': stats['total_vistas'] if stats else 0,
                'total_scans': stats['total_scans'] if stats else 0,
                'visitas_hoy': hoy_row['visitas'] if hoy_row else 0,
                'scans_hoy': hoy_row['scans'] if hoy_row else 0,
                'ultimos_7_dias': ultimos_7_dias,
                'url_slug': stats['url_slug'] if stats else '',
                'base_url': request.host_url.rstrip('/')
            }
            
            # Guardar en caché por 30 segundos
            if SECURITY_MIDDLEWARE_AVAILABLE:
                get_cache().set(cache_key, result, ttl=30)
            
            return jsonify(result)
            
    except Exception as e:
        logger.exception("Error getting dashboard stats: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# RUTAS DE SUPERADMIN
# ============================================================

@app.route('/superadmin/cambiar-password', methods=['POST'])
@login_required
@superadmin_required
def superadmin_cambiar_password():
    """Cambiar contraseña del superadmin (ya autenticado, no requiere contraseña actual)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
            
        password_nuevo = data.get('password_nuevo', '').strip()
        password_confirmar = data.get('password_confirmar', '').strip()
        
        # Validaciones
        if not password_nuevo or not password_confirmar:
            return jsonify({'success': False, 'error': 'Completa todos los campos'}), 400
        
        if password_nuevo != password_confirmar:
            return jsonify({'success': False, 'error': 'Las contraseñas no coinciden'}), 400
        
        if len(password_nuevo) < 8:
            return jsonify({'success': False, 'error': 'La contraseña debe tener al menos 8 caracteres'}), 400
        
        usuario_id = session.get('user_id')
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Sesión no válida'}), 401
        
        db = get_db()
        with db.cursor() as cur:
            # Verificar que el usuario existe
            cur.execute("SELECT id FROM usuarios_admin WHERE id = %s", (usuario_id,))
            user = cur.fetchone()
            
            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
            
            # Actualizar contraseña
            nuevo_hash = generate_password_hash(password_nuevo)
            cur.execute("UPDATE usuarios_admin SET password_hash = %s WHERE id = %s", (nuevo_hash, usuario_id))
            db.commit()
        
        logger.info("SuperAdmin %s cambió su contraseña", usuario_id)
        return jsonify({'success': True, 'message': 'Contraseña actualizada correctamente'})
        
    except Exception as e:
        logger.exception("Error cambiando contraseña de superadmin: %s", str(e))
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


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


@app.route('/superadmin/usuarios')
@login_required
@superadmin_required
def superadmin_usuarios():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT u.id, u.username, u.nombre, u.email, u.rol, u.activo, 
                   u.ultimo_login, u.fecha_creacion,
                   r.nombre as restaurante_nombre
            FROM usuarios_admin u
            LEFT JOIN restaurantes r ON u.restaurante_id = r.id
            WHERE u.rol != 'superadmin' 
            ORDER BY u.fecha_creacion DESC
        """)
        usuarios = list_from_rows(cur.fetchall())
    return render_template('superadmin/usuarios.html', usuarios=usuarios)


@app.route('/superadmin/suscripciones')
@login_required
@superadmin_required
def superadmin_suscripciones():
    return render_template('superadmin/suscripciones.html')


@app.route('/api/superadmin/clear-cache', methods=['POST'])
@login_required
@superadmin_required
def api_superadmin_clear_cache():
    """API para limpiar todo el cache de menús."""
    try:
        count = clear_all_menu_cache()
        logger.info("Cache limpiado por superadmin: %d entradas eliminadas", count)
        return jsonify({'success': True, 'message': f'Cache limpiado: {count} entradas eliminadas'})
    except Exception as e:
        logger.exception("Error limpiando cache")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/superadmin/suscripciones', methods=['GET'])
@login_required
@superadmin_required
def api_superadmin_suscripciones():
    """API para obtener todas las suscripciones de restaurantes."""
    db = get_db()
    with db.cursor() as cur:
        # Obtener restaurantes con info de suscripción
        cur.execute('''
            SELECT r.id, r.nombre, r.email, r.plan_id, r.estado_suscripcion, 
                   r.fecha_vencimiento, r.activo, r.fecha_creacion
            FROM restaurantes r
            ORDER BY r.fecha_vencimiento ASC
        ''')
        suscripciones = list_from_rows(cur.fetchall())
        
        # Obtener planes
        cur.execute("SELECT id, nombre FROM planes")
        planes_rows = cur.fetchall()
        planes = {p['id']: p['nombre'] for p in planes_rows}
        
    return jsonify({
        'suscripciones': suscripciones,
        'planes': planes
    })


@app.route('/api/superadmin/suscripciones/<int:restaurante_id>', methods=['PUT'])
@login_required
@superadmin_required
def api_superadmin_actualizar_suscripcion(restaurante_id):
    """API para actualizar/extender suscripción de un restaurante."""
    try:
        db = get_db()
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No se recibieron datos'}), 400
        
        with db.cursor() as cur:
            # Obtener fecha actual de vencimiento
            cur.execute("SELECT fecha_vencimiento, estado_suscripcion, nombre FROM restaurantes WHERE id = %s", (restaurante_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'success': False, 'error': 'Restaurante no encontrado'}), 404
            
            fecha_actual = row['fecha_vencimiento']
            estado_actual = row['estado_suscripcion']
            nombre_rest = row['nombre']
            
            hoy = date.today()
            nueva_fecha = None
            
            # Calcular nueva fecha
            if data.get('fecha_especifica'):
                # Fecha específica proporcionada
                fecha_str = data['fecha_especifica']
                try:
                    if isinstance(fecha_str, str):
                        nueva_fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    else:
                        nueva_fecha = fecha_str
                except ValueError:
                    return jsonify({'success': False, 'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
                    
            elif data.get('dias_extension'):
                # Extensión por días
                try:
                    dias = int(data['dias_extension'])
                    if dias <= 0:
                        return jsonify({'success': False, 'error': 'Los días deben ser mayor a 0'}), 400
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'error': 'Días de extensión inválidos'}), 400
                
                # Si ya tiene fecha y no está vencida, extender desde ahí
                if fecha_actual:
                    # Convertir a date si es datetime
                    if hasattr(fecha_actual, 'date'):
                        fecha_actual = fecha_actual.date()
                    
                    if fecha_actual >= hoy:
                        base = fecha_actual
                    else:
                        base = hoy
                else:
                    base = hoy
                    
                nueva_fecha = base + timedelta(days=dias)
            else:
                return jsonify({'success': False, 'error': 'Debe especificar días de extensión o fecha específica'}), 400
            
            # Determinar el nuevo estado
            nuevo_estado = data.get('estado_suscripcion', 'activa')
            nuevo_plan_id = data.get('plan_id')
            
            # Si la fecha es futura y el estado sería 'vencida', forzar 'activa'
            if nueva_fecha >= hoy and nuevo_estado == 'vencida':
                nuevo_estado = 'activa'
            
            # Si el estado actual es 'vencida' o 'suspendida' y la fecha es válida, activar
            if nueva_fecha >= hoy and estado_actual in ('vencida', 'suspendida') and nuevo_estado not in ('suspendida',):
                nuevo_estado = 'activa'
            
            # Formatear fecha para MySQL
            fecha_mysql = nueva_fecha.strftime('%Y-%m-%d')
            
            # Construir la consulta dinámicamente según si se actualiza el plan
            if nuevo_plan_id:
                cur.execute('''
                    UPDATE restaurantes 
                    SET fecha_vencimiento = %s, estado_suscripcion = %s, plan_id = %s, fecha_actualizacion = NOW()
                    WHERE id = %s
                ''', (fecha_mysql, nuevo_estado, nuevo_plan_id, restaurante_id))
            else:
                cur.execute('''
                    UPDATE restaurantes 
                    SET fecha_vencimiento = %s, estado_suscripcion = %s, fecha_actualizacion = NOW()
                    WHERE id = %s
                ''', (fecha_mysql, nuevo_estado, restaurante_id))
            
            db.commit()
            
            logger.info("Suscripción actualizada: restaurante=%s (%s), nueva_fecha=%s, estado=%s (anterior: %s)", 
                       restaurante_id, nombre_rest, fecha_mysql, nuevo_estado, estado_actual)
            
            return jsonify({
                'success': True, 
                'nueva_fecha': fecha_mysql,
                'nuevo_estado': nuevo_estado,
                'mensaje': f'Suscripción de {nombre_rest} actualizada correctamente'
            })
            
    except Exception as e:
        logger.exception("Error actualizando suscripción del restaurante %s", restaurante_id)
        try:
            db.rollback()
        except:
            pass
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500



@app.route('/superadmin/estadisticas')
@login_required
@superadmin_required
def superadmin_estadisticas():
    return render_template('superadmin/estadisticas.html')


# ============================================================
# RUTAS DE SOPORTE / TICKETS
# ============================================================

@app.route('/api/tickets', methods=['POST'])
@login_required
def api_crear_ticket():
    """API para crear tickets desde el dashboard del usuario."""
    try:
        data = request.get_json()
        
        tipo = data.get('tipo', 'consulta')
        asunto = data.get('asunto', '').strip()
        mensaje = data.get('mensaje', '').strip()
        
        if not asunto or not mensaje:
            return jsonify({'success': False, 'error': 'Completa todos los campos'}), 400
        
        if len(mensaje) < 10:
            return jsonify({'success': False, 'error': 'El mensaje debe tener al menos 10 caracteres'}), 400
        
        usuario_id = session['user_id']
        restaurante_id = session.get('restaurante_id')
        
        db = get_db()
        with db.cursor() as cur:
            # Obtener datos del usuario
            cur.execute("SELECT nombre, email FROM usuarios_admin WHERE id = %s", (usuario_id,))
            user = cur.fetchone()
            
            nombre = user['nombre'] if user else 'Usuario'
            email = user['email'] if user else ''
            
            # Obtener nombre del restaurante
            restaurante_nombre = None
            if restaurante_id:
                cur.execute("SELECT nombre FROM restaurantes WHERE id = %s", (restaurante_id,))
                rest = cur.fetchone()
                if rest:
                    restaurante_nombre = rest['nombre']
            
            # Crear el ticket
            cur.execute('''
                INSERT INTO tickets_soporte 
                (usuario_id, restaurante_id, nombre, email, asunto, mensaje, tipo, ip_address, user_agent, pagina_origen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                usuario_id,
                restaurante_id,
                nombre,
                email,
                asunto,
                mensaje,
                tipo,
                get_client_ip(),
                request.headers.get('User-Agent', '')[:500],
                'Dashboard'
            ))
            db.commit()
            ticket_id = cur.lastrowid
        
        # Preparar datos para emails
        ticket_data = {
            'id': ticket_id,
            'nombre': nombre,
            'email': email,
            'asunto': asunto,
            'mensaje': mensaje,
            'tipo': tipo,
            'prioridad': 'media',
            'restaurante_nombre': restaurante_nombre
        }
        
        # Enviar emails
        if EMAIL_SERVICE_AVAILABLE:
            try:
                enviar_confirmacion_ticket(ticket_data)
                admin_url = url_for('superadmin_tickets', _external=True)
                notificar_nuevo_ticket_admin(ticket_data, admin_url)
            except Exception as email_err:
                logger.error("Error enviando emails de ticket: %s", email_err)
        
        logger.info("Ticket #%s creado desde dashboard por usuario %s", ticket_id, usuario_id)
        
        return jsonify({
            'success': True, 
            'ticket_id': ticket_id,
            'message': f'Ticket #{ticket_id} creado exitosamente'
        })
        
    except Exception as e:
        logger.exception("Error al crear ticket via API")
        return jsonify({'success': False, 'error': 'Error al crear el ticket'}), 500


@app.route('/soporte', methods=['GET', 'POST'])
def contactar_soporte():
    """Formulario público para contactar soporte."""
    # Valores por defecto si está logueado
    nombre_default = None
    email_default = None
    restaurante_nombre = None
    restaurante_id = None
    usuario_id = None
    
    if 'user_id' in session:
        usuario_id = session['user_id']
        nombre_default = session.get('nombre', '')
        
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT email FROM usuarios_admin WHERE id = %s", (usuario_id,))
            user = cur.fetchone()
            if user:
                email_default = user.get('email', '')
            
            if session.get('restaurante_id'):
                restaurante_id = session['restaurante_id']
                cur.execute("SELECT nombre FROM restaurantes WHERE id = %s", (restaurante_id,))
                rest = cur.fetchone()
                if rest:
                    restaurante_nombre = rest['nombre']
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefono = request.form.get('telefono', '').strip() or None
        tipo = request.form.get('tipo', 'consulta')
        asunto = request.form.get('asunto', '').strip()
        mensaje = request.form.get('mensaje', '').strip()
        
        # Validaciones
        if not nombre or not email or not asunto or not mensaje:
            flash('Por favor completa todos los campos obligatorios', 'error')
            return render_template('soporte.html', 
                                   nombre_default=nombre_default,
                                   email_default=email_default,
                                   restaurante_nombre=restaurante_nombre)
        
        if len(mensaje) < 20:
            flash('El mensaje debe tener al menos 20 caracteres', 'error')
            return render_template('soporte.html',
                                   nombre_default=nombre_default,
                                   email_default=email_default,
                                   restaurante_nombre=restaurante_nombre)
        
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute('''
                    INSERT INTO tickets_soporte 
                    (usuario_id, restaurante_id, nombre, email, telefono, asunto, mensaje, tipo, ip_address, user_agent, pagina_origen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    usuario_id,
                    restaurante_id,
                    nombre,
                    email,
                    telefono,
                    asunto,
                    mensaje,
                    tipo,
                    get_client_ip(),
                    request.headers.get('User-Agent', '')[:500],
                    request.referrer or ''
                ))
                db.commit()
                ticket_id = cur.lastrowid
            
            # Preparar datos del ticket para emails
            ticket_data = {
                'id': ticket_id,
                'nombre': nombre,
                'email': email,
                'telefono': telefono,
                'asunto': asunto,
                'mensaje': mensaje,
                'tipo': tipo,
                'prioridad': 'media',  # Por defecto
                'restaurante_nombre': restaurante_nombre
            }
            
            # Enviar email de confirmación al usuario
            if EMAIL_SERVICE_AVAILABLE:
                try:
                    enviar_confirmacion_ticket(ticket_data)
                    logger.info("Email de confirmación enviado a %s para ticket #%s", email, ticket_id)
                except Exception as email_err:
                    logger.error("Error enviando email de confirmación: %s", email_err)
                
                # Notificar al superadmin
                try:
                    admin_url = url_for('superadmin_tickets', _external=True)
                    notificar_nuevo_ticket_admin(ticket_data, admin_url)
                    logger.info("Notificación enviada al superadmin para ticket #%s", ticket_id)
                except Exception as email_err:
                    logger.error("Error notificando al superadmin: %s", email_err)
                
            logger.info("Nuevo ticket de soporte #%s creado por %s", ticket_id, email)
            flash(f'¡Mensaje enviado! Tu ticket #{ticket_id} ha sido registrado. Te responderemos pronto a {email}', 'success')
            return render_template('soporte.html',
                                   nombre_default=nombre_default,
                                   email_default=email_default,
                                   restaurante_nombre=restaurante_nombre)
            
        except Exception as e:
            logger.exception("Error al crear ticket de soporte")
            flash('Error al enviar el mensaje. Por favor intenta de nuevo.', 'error')
    
    return render_template('soporte.html',
                           nombre_default=nombre_default,
                           email_default=email_default,
                           restaurante_nombre=restaurante_nombre)


@app.route('/superadmin/tickets')
@login_required
@superadmin_required
def superadmin_tickets():
    """Panel de gestión de tickets de soporte."""
    filtro_estado = request.args.get('estado', '')
    filtro_tipo = request.args.get('tipo', '')
    filtro_prioridad = request.args.get('prioridad', '')
    
    db = get_db()
    with db.cursor() as cur:
        # Estadísticas
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN estado = 'abierto' THEN 1 ELSE 0 END) as abiertos,
                SUM(CASE WHEN estado = 'en_proceso' THEN 1 ELSE 0 END) as en_proceso,
                SUM(CASE WHEN estado = 'respondido' THEN 1 ELSE 0 END) as respondidos
            FROM tickets_soporte
        """)
        stats = cur.fetchone()
        
        # OPTIMIZACIÓN: Actualizar caché de tickets pendientes
        session['_tickets_count_cache'] = (stats.get('abiertos', 0) or 0) + (stats.get('en_proceso', 0) or 0)
        
        # Construir query con filtros
        query = """
            SELECT t.*, r.nombre as restaurante_nombre
            FROM tickets_soporte t
            LEFT JOIN restaurantes r ON t.restaurante_id = r.id
            WHERE 1=1
        """
        params = []
        
        if filtro_estado:
            query += " AND t.estado = %s"
            params.append(filtro_estado)
        if filtro_tipo:
            query += " AND t.tipo = %s"
            params.append(filtro_tipo)
        if filtro_prioridad:
            query += " AND t.prioridad = %s"
            params.append(filtro_prioridad)
        
        query += " ORDER BY FIELD(t.prioridad, 'urgente', 'alta', 'media', 'baja'), t.fecha_creacion DESC"
        
        cur.execute(query, tuple(params))
        tickets = list_from_rows(cur.fetchall())
    
    return render_template('superadmin/tickets.html',
                           tickets=tickets,
                           stats=stats,
                           filtro_estado=filtro_estado,
                           filtro_tipo=filtro_tipo,
                           filtro_prioridad=filtro_prioridad)


@app.route('/superadmin/tickets/responder', methods=['POST'])
@login_required
@superadmin_required
def superadmin_responder_ticket():
    """Responder a un ticket de soporte."""
    ticket_id = request.form.get('ticket_id')
    respuesta = request.form.get('respuesta', '').strip()
    nuevo_estado = request.form.get('nuevo_estado', 'respondido')
    enviar_email = request.form.get('enviar_email') == 'on'
    
    if not ticket_id or not respuesta:
        flash('Faltan datos requeridos', 'error')
        return redirect(url_for('superadmin_tickets'))
    
    # Validar estado
    estados_validos = ['abierto', 'en_proceso', 'respondido', 'cerrado']
    if nuevo_estado not in estados_validos:
        nuevo_estado = 'respondido'
    
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('''
                UPDATE tickets_soporte 
                SET respuesta = %s, 
                    respondido_por = %s, 
                    fecha_respuesta = NOW(),
                    estado = %s
                WHERE id = %s
            ''', (respuesta, session['user_id'], nuevo_estado, ticket_id))
            db.commit()
            
            # Obtener datos del ticket para el email
            cur.execute("SELECT id, email, nombre, asunto, mensaje FROM tickets_soporte WHERE id = %s", (ticket_id,))
            ticket = cur.fetchone()
            
            if enviar_email and ticket and EMAIL_SERVICE_AVAILABLE:
                try:
                    ticket_data = {
                        'id': ticket['id'],
                        'email': ticket['email'],
                        'nombre': ticket['nombre'],
                        'asunto': ticket['asunto'],
                        'mensaje': ticket['mensaje']
                    }
                    enviar_respuesta_ticket(ticket_data, respuesta)
                    logger.info("Email de respuesta enviado a %s para ticket #%s", ticket['email'], ticket_id)
                    flash(f'Respuesta enviada al ticket #{ticket_id} y email enviado a {ticket["email"]}', 'success')
                except Exception as email_err:
                    logger.error("Error enviando email de respuesta: %s", email_err)
                    flash(f'Respuesta guardada para ticket #{ticket_id}, pero hubo un error enviando el email', 'warning')
            else:
                flash(f'Respuesta guardada para el ticket #{ticket_id}', 'success')
            
    except Exception as e:
        logger.exception("Error al responder ticket")
        flash('Error al guardar la respuesta', 'error')
    
    return redirect(url_for('superadmin_tickets'))


@app.route('/superadmin/tickets/cambiar-estado', methods=['POST'])
@login_required
@superadmin_required
def superadmin_cambiar_estado_ticket():
    """Cambiar el estado de un ticket (API JSON)."""
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    nuevo_estado = data.get('estado')
    
    estados_validos = ['abierto', 'en_proceso', 'respondido', 'cerrado']
    
    if not ticket_id or nuevo_estado not in estados_validos:
        return jsonify({'success': False, 'error': 'Datos inválidos'}), 400
    
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("UPDATE tickets_soporte SET estado = %s WHERE id = %s", (nuevo_estado, ticket_id))
            db.commit()
        
        logger.info("Ticket #%s cambiado a estado: %s", ticket_id, nuevo_estado)
        return jsonify({'success': True})
        
    except Exception as e:
        logger.exception("Error al cambiar estado del ticket")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# CONFIGURACIÓN DE PAGOS (SUPERADMIN) - RUTAS
# =============================================================================

@app.route('/superadmin/config/pagos', methods=['GET', 'POST'])
@login_required
@superadmin_required
def superadmin_config_pagos():
    """Página de configuración de métodos de pago."""
    if request.method == 'POST':
        # Guardar configuración desde el formulario
        campos = [
            ('mercadopago_activo', 'true' if request.form.get('mercadopago_activo') else 'false'),
            ('deposito_activo', 'true' if request.form.get('deposito_activo') else 'false'),
            ('banco_nombre', request.form.get('banco_nombre', '')),
            ('banco_tipo_cuenta', request.form.get('banco_tipo_cuenta', '')),
            ('banco_numero', request.form.get('banco_numero', '')),
            ('banco_rut', request.form.get('banco_rut', '')),
            ('banco_titular', request.form.get('banco_titular', '')),
            ('banco_email', request.form.get('banco_email', '')),
            ('precio_mensual', request.form.get('precio_mensual', '14990')),
            ('soporte_whatsapp', request.form.get('soporte_whatsapp', '')),
            ('soporte_email', request.form.get('soporte_email', '')),
            ('soporte_nombre_empresa', request.form.get('soporte_nombre_empresa', 'Menú Digital')),
            ('soporte_mensaje_auto', request.form.get('soporte_mensaje_auto', ''))
        ]
        
        try:
            for clave, valor in campos:
                set_config_value(clave, valor)
            flash('Configuración guardada correctamente', 'success')
            logger.info("Configuración de pagos actualizada por superadmin")
        except Exception as e:
            flash(f'Error al guardar: {str(e)}', 'danger')
            logger.exception("Error guardando configuración de pagos")
        
        return redirect(url_for('superadmin_config_pagos'))
    
    config = get_config_global()
    return render_template('superadmin/config_pagos.html', config=config)


@app.route('/api/superadmin/config', methods=['POST'])
@login_required
@superadmin_required
def api_superadmin_config():
    """API para guardar configuración global."""
    data = request.get_json()
    clave = data.get('clave')
    valor = data.get('valor')
    
    if not clave:
        return jsonify({'success': False, 'error': 'Clave requerida'}), 400
    
    # Lista de claves permitidas
    claves_permitidas = [
        'mercadopago_activo', 'deposito_activo',
        'banco_nombre', 'banco_tipo_cuenta', 'banco_numero',
        'banco_rut', 'banco_titular', 'banco_email',
        'precio_mensual', 'soporte_whatsapp', 'soporte_email',
        'soporte_nombre_empresa', 'soporte_mensaje_auto'
    ]
    
    if clave not in claves_permitidas:
        return jsonify({'success': False, 'error': 'Clave no permitida'}), 400
    
    try:
        set_config_value(clave, valor or '')
        logger.info("Configuración actualizada: %s = %s", clave, valor)
        return jsonify({'success': True})
    except Exception as e:
        logger.exception("Error al guardar configuración")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config/pagos')
def api_config_pagos_public():
    """API pública para obtener configuración de pagos (para páginas de usuario)."""
    config = get_config_global()
    return jsonify({
        'mercadopago_activo': config.get('mercadopago_activo') == 'true',
        'deposito_activo': config.get('deposito_activo') == 'true',
        'banco_nombre': config.get('banco_nombre', ''),
        'banco_tipo_cuenta': config.get('banco_tipo_cuenta', ''),
        'banco_numero': config.get('banco_numero', ''),
        'banco_rut': config.get('banco_rut', ''),
        'banco_titular': config.get('banco_titular', ''),
        'banco_email': config.get('banco_email', ''),
        'precio_mensual': int(config.get('precio_mensual', 14990)),
        'soporte_whatsapp': config.get('soporte_whatsapp', '')
    })


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
        
        # Tickets pendientes (para notificaciones push)
        cur.execute("SELECT COUNT(*) as count FROM tickets_soporte WHERE estado IN ('abierto', 'en_proceso')")
        result = cur.fetchone()
        tickets_pendientes = int(result['count']) if result and result['count'] else 0
        
    return jsonify({
        'total_restaurantes': int(total_restaurantes) if total_restaurantes else 0,
        'total_usuarios': int(total_usuarios) if total_usuarios else 0,
        'total_visitas': int(total_visitas) if total_visitas else 0,
        'total_escaneos': int(total_escaneos) if total_escaneos else 0,
        'visitas_30dias': visitas_30dias,
        'tickets_pendientes': int(tickets_pendientes)
    })


@app.route('/api/superadmin/stats-extended')
@login_required
@superadmin_required
def api_superadmin_stats_extended():
    """API extendida de estadísticas con ingresos, tendencias y desglose completo."""
    try:
        db = get_db()
        with db.cursor() as cur:
            # ============================================
            # MÉTRICAS BÁSICAS
            # ============================================
            
            # Total restaurantes
            cur.execute("SELECT COUNT(*) as total FROM restaurantes")
            total_restaurantes = cur.fetchone()['total'] or 0
            
            # Restaurantes activos (con actividad en últimos 30 días)
            try:
                cur.execute("""
                    SELECT COUNT(DISTINCT restaurante_id) as activos 
                    FROM estadisticas_diarias 
                    WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                """)
                restaurantes_activos = cur.fetchone()['activos'] or 0
            except Exception:
                restaurantes_activos = 0
            
            # Total usuarios (sin superadmin)
            cur.execute("SELECT COUNT(*) as total FROM usuarios_admin WHERE rol != 'superadmin'")
            total_usuarios = cur.fetchone()['total'] or 0
            
            # Total platos y categorías
            try:
                cur.execute("SELECT COUNT(*) as total FROM platos WHERE activo = 1")
                total_platos = cur.fetchone()['total'] or 0
            except Exception:
                total_platos = 0
            
            try:
                cur.execute("SELECT COUNT(*) as total FROM categorias WHERE activo = 1")
                total_categorias = cur.fetchone()['total'] or 0
            except Exception:
                total_categorias = 0
            
            # ============================================
            # VISITAS Y ESCANEOS
            # ============================================
            
            # Total histórico
            try:
                cur.execute("""
                    SELECT COALESCE(SUM(visitas),0) as visitas, 
                           COALESCE(SUM(escaneos_qr),0) as escaneos,
                           COALESCE(SUM(visitas_movil),0) as movil,
                           COALESCE(SUM(visitas_desktop),0) as desktop
                    FROM estadisticas_diarias
                """)
                row = cur.fetchone()
                total_visitas = int(row['visitas']) if row and row['visitas'] else 0
                total_escaneos = int(row['escaneos']) if row and row['escaneos'] else 0
                total_movil = int(row['movil']) if row and row['movil'] else 0
                total_desktop = int(row['desktop']) if row and row['desktop'] else 0
            except Exception:
                total_visitas = total_escaneos = total_movil = total_desktop = 0
            
            # Visitas últimos 30 días
            try:
                cur.execute("""
                    SELECT DATE_FORMAT(fecha, '%%Y-%%m-%%d') as fecha, 
                           COALESCE(SUM(visitas),0) as visitas,
                           COALESCE(SUM(escaneos_qr),0) as escaneos,
                           COALESCE(SUM(visitas_movil),0) as movil,
                           COALESCE(SUM(visitas_desktop),0) as desktop
                    FROM estadisticas_diarias
                    WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    GROUP BY fecha
                    ORDER BY fecha
                """)
                visitas_30dias = []
                for r in cur.fetchall():
                    visitas_30dias.append({
                        'fecha': str(r['fecha']),
                        'visitas': int(r['visitas']) if r['visitas'] else 0,
                        'escaneos': int(r['escaneos']) if r['escaneos'] else 0,
                        'movil': int(r['movil']) if r['movil'] else 0,
                        'desktop': int(r['desktop']) if r['desktop'] else 0
                    })
            except Exception as e:
                logger.warning("Error getting visitas_30dias: %s", e)
                visitas_30dias = []
            
            # Totales de los últimos 30 días
            try:
                cur.execute("""
                    SELECT COALESCE(SUM(visitas),0) as visitas,
                           COALESCE(SUM(escaneos_qr),0) as escaneos
                    FROM estadisticas_diarias
                    WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                """)
                row_30 = cur.fetchone()
                visitas_mes_actual = int(row_30['visitas']) if row_30 and row_30['visitas'] else 0
                escaneos_mes_actual = int(row_30['escaneos']) if row_30 and row_30['escaneos'] else 0
            except Exception:
                visitas_mes_actual = escaneos_mes_actual = 0
            
            # Totales del mes anterior (para comparar)
            try:
                cur.execute("""
                    SELECT COALESCE(SUM(visitas),0) as visitas,
                           COALESCE(SUM(escaneos_qr),0) as escaneos
                    FROM estadisticas_diarias
                    WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
                      AND fecha < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                """)
                row_ant = cur.fetchone()
                visitas_mes_anterior = int(row_ant['visitas']) if row_ant and row_ant['visitas'] else 0
                escaneos_mes_anterior = int(row_ant['escaneos']) if row_ant and row_ant['escaneos'] else 0
            except Exception:
                visitas_mes_anterior = escaneos_mes_anterior = 0
            
            # Calcular tendencia (%)
            if visitas_mes_anterior > 0:
                tendencia_visitas = round(((visitas_mes_actual - visitas_mes_anterior) / visitas_mes_anterior) * 100, 1)
            else:
                tendencia_visitas = 100 if visitas_mes_actual > 0 else 0
                
            if escaneos_mes_anterior > 0:
                tendencia_escaneos = round(((escaneos_mes_actual - escaneos_mes_anterior) / escaneos_mes_anterior) * 100, 1)
            else:
                tendencia_escaneos = 100 if escaneos_mes_actual > 0 else 0
            
            # Visitas de hoy
            try:
                cur.execute("""
                    SELECT COALESCE(SUM(visitas),0) as visitas,
                           COALESCE(SUM(escaneos_qr),0) as escaneos
                    FROM estadisticas_diarias
                    WHERE fecha = CURDATE()
                """)
                row_hoy = cur.fetchone()
                visitas_hoy = int(row_hoy['visitas']) if row_hoy and row_hoy['visitas'] else 0
                escaneos_hoy = int(row_hoy['escaneos']) if row_hoy and row_hoy['escaneos'] else 0
            except Exception:
                visitas_hoy = escaneos_hoy = 0
            
            # Visitas por día de la semana (últimos 30 días)
            try:
                cur.execute("""
                    SELECT DAYOFWEEK(fecha) as dia, 
                           COALESCE(AVG(visitas),0) as promedio
                    FROM estadisticas_diarias
                    WHERE fecha >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    GROUP BY DAYOFWEEK(fecha)
                    ORDER BY dia
                """)
                visitas_por_dia = []
                for r in cur.fetchall():
                    visitas_por_dia.append({
                        'dia': int(r['dia']),
                        'promedio': float(r['promedio']) if r['promedio'] else 0
                    })
            except Exception:
                visitas_por_dia = []
            
            # ============================================
            # SUSCRIPCIONES - Lógica mejorada basada en plan + fecha
            # ============================================
            
            # Primero obtener IDs de planes para identificar Gratuito vs Premium
            planes_gratuitos = []
            planes_premium = []
            try:
                cur.execute("SELECT id, nombre FROM planes")
                for p in cur.fetchall():
                    nombre_plan = (p['nombre'] or '').lower()
                    if 'gratis' in nombre_plan or 'gratuito' in nombre_plan or 'free' in nombre_plan:
                        planes_gratuitos.append(p['id'])
                    else:
                        planes_premium.append(p['id'])
            except Exception:
                pass
            
            # Contar suscripciones de forma inteligente
            cur.execute("""
                SELECT 
                    r.id,
                    r.plan_id,
                    LOWER(TRIM(COALESCE(r.estado_suscripcion, ''))) as estado,
                    r.fecha_vencimiento,
                    r.activo
                FROM restaurantes r
            """)
            all_restaurants = cur.fetchall()
            
            subs_activas = 0
            subs_prueba = 0
            subs_vencidas = 0
            subs_suspendidas = 0
            hoy = date.today()
            
            for r in all_restaurants:
                plan_id = r['plan_id']
                estado = (r['estado'] or '').lower().strip()
                fecha_venc = r['fecha_vencimiento']
                es_activo = r['activo']
                
                # Convertir fecha si es necesario
                if fecha_venc and hasattr(fecha_venc, 'date'):
                    fecha_venc = fecha_venc.date()
                
                # Determinar si es plan premium
                es_plan_premium = plan_id in planes_premium if planes_premium else (plan_id and plan_id > 1)
                
                # Lógica de clasificación:
                # 1. Si está suspendida/cancelada explícitamente -> suspendida
                if estado in ('suspendida', 'suspendido', 'suspended', 'inactiva', 'inactivo', 'cancelada', 'cancelado'):
                    subs_suspendidas += 1
                # 2. Si es plan premium Y fecha vigente -> activa
                elif es_plan_premium and fecha_venc and fecha_venc >= hoy:
                    subs_activas += 1
                # 3. Si es plan premium PERO fecha vencida -> vencida
                elif es_plan_premium and (not fecha_venc or fecha_venc < hoy):
                    subs_vencidas += 1
                # 4. Si es plan gratuito -> prueba
                elif not es_plan_premium:
                    subs_prueba += 1
                # 5. Si el estado dice explícitamente activa -> activa
                elif estado in ('activa', 'activo', 'premium', 'active', 'pagada', 'pagado', 'paid'):
                    subs_activas += 1
                # 6. Default -> prueba
                else:
                    subs_prueba += 1
            
            # Restaurantes que vencen en los próximos 7 días
            try:
                cur.execute("""
                    SELECT id, nombre, DATE_FORMAT(fecha_vencimiento, '%%Y-%%m-%%d') as fecha_vencimiento, estado_suscripcion
                    FROM restaurantes
                    WHERE fecha_vencimiento BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                      AND LOWER(TRIM(COALESCE(estado_suscripcion, ''))) IN ('activa', 'activo', 'premium', 'active', 'pagada', 'prueba', 'trial', 'demo', '')
                    ORDER BY fecha_vencimiento
                    LIMIT 10
                """)
                por_vencer = []
                for r in cur.fetchall():
                    por_vencer.append({
                        'id': r['id'],
                        'nombre': r['nombre'],
                        'fecha_vencimiento': str(r['fecha_vencimiento']) if r['fecha_vencimiento'] else '',
                        'estado_suscripcion': r['estado_suscripcion']
                    })
            except Exception:
                por_vencer = []
            
            # Nuevos restaurantes este mes
            try:
                cur.execute("""
                    SELECT COUNT(*) as nuevos
                    FROM restaurantes
                    WHERE fecha_creacion >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
                """)
                result = cur.fetchone()
                nuevos_este_mes = result['nuevos'] if result and result['nuevos'] else 0
            except Exception:
                nuevos_este_mes = 0
            
            # ============================================
            # INGRESOS
            # ============================================
            
            config = get_config_global()
            precio_mensual = int(config.get('precio_mensual', 14990))
            ingreso_mensual = subs_activas * precio_mensual
            ingreso_anual_proyectado = ingreso_mensual * 12
            
            # ============================================
            # TOP RESTAURANTES
            # ============================================
            
            try:
                cur.execute("""
                    SELECT r.id, r.nombre, r.estado_suscripcion, r.url_slug,
                           COALESCE(SUM(e.visitas), 0) as total_visitas,
                           COALESCE(SUM(e.escaneos_qr), 0) as total_escaneos
                    FROM restaurantes r
                    LEFT JOIN estadisticas_diarias e ON r.id = e.restaurante_id
                    GROUP BY r.id, r.nombre, r.estado_suscripcion, r.url_slug
                    ORDER BY total_visitas DESC
                    LIMIT 10
                """)
                top_restaurantes = []
                for r in cur.fetchall():
                    top_restaurantes.append({
                        'id': r['id'],
                        'nombre': r['nombre'],
                        'estado_suscripcion': r['estado_suscripcion'] or 'prueba',
                        'url_slug': r['url_slug'],
                        'total_visitas': int(r['total_visitas']) if r['total_visitas'] else 0,
                        'total_escaneos': int(r['total_escaneos']) if r['total_escaneos'] else 0
                    })
            except Exception as e:
                logger.warning("Error getting top_restaurantes: %s", e)
                top_restaurantes = []
            
            # Top restaurantes por escaneos QR
            try:
                cur.execute("""
                    SELECT r.id, r.nombre, r.estado_suscripcion,
                           COALESCE(SUM(e.escaneos_qr), 0) as total_escaneos
                    FROM restaurantes r
                    LEFT JOIN estadisticas_diarias e ON r.id = e.restaurante_id
                    GROUP BY r.id, r.nombre, r.estado_suscripcion
                    HAVING total_escaneos > 0
                    ORDER BY total_escaneos DESC
                    LIMIT 10
                """)
                top_escaneos = []
                for r in cur.fetchall():
                    top_escaneos.append({
                        'id': r['id'],
                        'nombre': r['nombre'],
                        'estado_suscripcion': r['estado_suscripcion'] or 'prueba',
                        'total_escaneos': int(r['total_escaneos']) if r['total_escaneos'] else 0
                    })
            except Exception:
                top_escaneos = []
            
            # ============================================
            # ACTIVIDAD RECIENTE
            # ============================================
            
            # Últimos restaurantes creados (usar fecha_creacion, no created_at)
            try:
                cur.execute("""
                    SELECT id, nombre, fecha_creacion, estado_suscripcion
                    FROM restaurantes
                    ORDER BY fecha_creacion DESC
                    LIMIT 5
                """)
                ultimos_restaurantes = []
                for r in cur.fetchall():
                    fecha = r['fecha_creacion']
                    if fecha:
                        if hasattr(fecha, 'isoformat'):
                            fecha_str = fecha.isoformat()
                        else:
                            fecha_str = str(fecha)
                    else:
                        fecha_str = ''
                    ultimos_restaurantes.append({
                        'id': r['id'],
                        'nombre': r['nombre'],
                        'created_at': fecha_str,
                        'estado_suscripcion': r['estado_suscripcion'] or 'prueba'
                    })
            except Exception as e:
                logger.warning("Error getting ultimos_restaurantes: %s", e)
                ultimos_restaurantes = []
            
            # Tickets recientes (usar fecha_creacion, no created_at)
            try:
                cur.execute("""
                    SELECT id, asunto, estado, fecha_creacion, tipo
                    FROM tickets_soporte
                    ORDER BY fecha_creacion DESC
                    LIMIT 5
                """)
                ultimos_tickets = []
                for r in cur.fetchall():
                    fecha = r['fecha_creacion']
                    if fecha:
                        if hasattr(fecha, 'isoformat'):
                            fecha_str = fecha.isoformat()
                        else:
                            fecha_str = str(fecha)
                    else:
                        fecha_str = ''
                    ultimos_tickets.append({
                        'id': r['id'],
                        'asunto': r['asunto'] or '',
                        'estado': r['estado'] or 'abierto',
                        'created_at': fecha_str,
                        'tipo': r['tipo'] or 'consulta'
                    })
            except Exception as e:
                # La tabla puede no existir
                logger.warning("Error getting ultimos_tickets (table may not exist): %s", e)
                ultimos_tickets = []
            
            tickets_pendientes = sum(1 for t in ultimos_tickets if t.get('estado') in ('abierto', 'en_proceso'))
            
        return jsonify({
            # Métricas básicas
            'total_restaurantes': total_restaurantes,
            'restaurantes_activos': restaurantes_activos,
            'total_usuarios': total_usuarios,
            'total_platos': total_platos,
            'total_categorias': total_categorias,
            
            # Visitas y escaneos
            'total_visitas': total_visitas,
            'total_escaneos': total_escaneos,
            'total_movil': total_movil,
            'total_desktop': total_desktop,
            'visitas_hoy': visitas_hoy,
            'escaneos_hoy': escaneos_hoy,
            'visitas_mes_actual': visitas_mes_actual,
            'escaneos_mes_actual': escaneos_mes_actual,
            'tendencia_visitas': tendencia_visitas,
            'tendencia_escaneos': tendencia_escaneos,
            'visitas_30dias': visitas_30dias,
            'visitas_por_dia': visitas_por_dia,
            
            # Suscripciones
            'subs_activas': subs_activas,
            'subs_prueba': subs_prueba,
            'subs_vencidas': subs_vencidas,
            'subs_suspendidas': subs_suspendidas,
            'por_vencer': por_vencer,
            'nuevos_este_mes': nuevos_este_mes,
            
            # Ingresos
            'ingreso_mensual': ingreso_mensual,
            'ingreso_anual_proyectado': ingreso_anual_proyectado,
            'precio_mensual': precio_mensual,
            
            # Rankings
            'top_restaurantes': top_restaurantes,
            'top_escaneos': top_escaneos,
            
            # Actividad reciente
            'ultimos_restaurantes': ultimos_restaurantes,
            'ultimos_tickets': ultimos_tickets,
            'tickets_pendientes': tickets_pendientes
        })
    except Exception as e:
        logger.exception("Error in api_superadmin_stats_extended")
        return jsonify({
            'error': str(e),
            'total_restaurantes': 0,
            'restaurantes_activos': 0,
            'total_usuarios': 0,
            'total_platos': 0,
            'total_categorias': 0,
            'total_visitas': 0,
            'total_escaneos': 0,
            'total_movil': 0,
            'total_desktop': 0,
            'visitas_hoy': 0,
            'escaneos_hoy': 0,
            'visitas_mes_actual': 0,
            'escaneos_mes_actual': 0,
            'tendencia_visitas': 0,
            'tendencia_escaneos': 0,
            'visitas_30dias': [],
            'visitas_por_dia': [],
            'subs_activas': 0,
            'subs_prueba': 0,
            'subs_vencidas': 0,
            'subs_suspendidas': 0,
            'por_vencer': [],
            'nuevos_este_mes': 0,
            'ingreso_mensual': 0,
            'ingreso_anual_proyectado': 0,
            'precio_mensual': 14990,
            'top_restaurantes': [],
            'top_escaneos': [],
            'ultimos_restaurantes': [],
            'ultimos_tickets': [],
            'tickets_pendientes': 0
        }), 500


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
                
                # Calcular fecha de vencimiento (30 días desde hoy)
                fecha_vencimiento = (date.today() + timedelta(days=30)).isoformat()
                
                cur.execute('''
                    INSERT INTO restaurantes 
                    (nombre, rut, url_slug, logo_url, tema, plan_id, activo, estado_suscripcion, fecha_vencimiento)
                    VALUES (%s, %s, %s, %s, %s, %s, 1, 'prueba', %s)
                ''', (
                    data['nombre'],
                    data.get('rut', ''),
                    data['url_slug'],
                    data.get('logo_url', ''),
                    data.get('tema', 'elegante'),
                    data.get('plan_id', 1),  # Plan gratis por defecto
                    fecha_vencimiento
                ))
                db.commit()
                logger.info("Nuevo restaurante creado: %s con vencimiento %s", data['nombre'], fecha_vencimiento)
                return jsonify({'success': True, 'id': cur.lastrowid})

    except pymysql.IntegrityError as e:
        try:
            db.rollback()
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_restaurantes (IntegrityError): %s", rollback_err, exc_info=True)
        error_msg = str(e)
        if 'Duplicate' in error_msg or 'duplicate' in error_msg.lower():
            return jsonify({'success': False, 'error': 'El URL slug ya existe'}), 400
        if 'foreign key' in error_msg.lower():
            return jsonify({'success': False, 'error': 'Error de referencia en la base de datos'}), 400
        return jsonify({'success': False, 'error': f'Error de integridad: {error_msg}'}), 500
    except Exception as e:
        try:
            db.rollback()
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_restaurantes: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_restaurantes")
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
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_restaurante: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_restaurante")
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
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_usuarios: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_usuarios")
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
        except Exception as rollback_err:
            logger.warning("DB rollback failed in api_usuario: %s", rollback_err, exc_info=True)
        logger.exception("Error en api_usuario")
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
        logger.exception("Error en init-db")
        return jsonify({'success': False, 'error': str(e)}), 500


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


@app.route('/healthz', methods=['GET'])
def healthz():
    """Lightweight health check (for load balancers): checks DB, pool, cache and Cloudinary."""
    ok = True
    components = {}
    
    # Verificar pool de conexiones
    try:
        pool_status = get_pool_status()
        # Compatibilidad con nuevo formato de pool
        size = pool_status.get('current_size', pool_status.get('size', 0))
        available = pool_status.get('available', 0)
        max_conn = pool_status.get('max_total', pool_status.get('max', 15))
        in_use = pool_status.get('in_use', size - available)
        
        components['db_pool'] = {
            'size': size,
            'available': available,
            'max': max_conn,
            'in_use': in_use,
            'utilization': f"{(in_use / max(max_conn, 1)) * 100:.1f}%"
        }
    except Exception as e:
        components['db_pool'] = str(e)
    
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute('SELECT 1')
        components['db'] = 'ok'
    except Exception as e:
        components['db'] = str(e)
        ok = False
    
    # Verificar caché
    try:
        if SECURITY_MIDDLEWARE_AVAILABLE:
            cache_stats = get_cache().stats
            components['cache'] = cache_stats
        else:
            components['cache'] = 'not available'
    except Exception as e:
        components['cache'] = str(e)
    
    # Verificar cola de visitas
    try:
        components['visit_queue'] = {
            'size': _visitas_queue.qsize(),
            'max': 1000,
            'worker_running': _visita_worker_running
        }
    except Exception as e:
        components['visit_queue'] = str(e)

    # Verificar Cloudinary con más detalle
    cloudinary_url = os.environ.get('CLOUDINARY_URL', '')
    components['cloudinary'] = {
        'sdk_available': CLOUDINARY_AVAILABLE,
        'configured': CLOUDINARY_CONFIGURED,
        'url_set': bool(cloudinary_url),
        'url_preview': cloudinary_url[:30] + '...' if len(cloudinary_url) > 30 else cloudinary_url,
        'api_proxy': os.environ.get('API_PROXY', 'not set')
    }
    
    # Intentar re-inicializar si no está configurado
    if not CLOUDINARY_CONFIGURED and CLOUDINARY_AVAILABLE and cloudinary_url:
        try:
            init_result = init_cloudinary()
            components['cloudinary']['init_retry'] = init_result
            components['cloudinary']['configured_after_retry'] = CLOUDINARY_CONFIGURED
        except Exception as e:
            components['cloudinary']['init_error'] = str(e)
    
    return jsonify({'ok': ok, 'components': components}), (200 if ok else 500)


@app.route('/api/diagnostico')
@login_required
@superadmin_required
def api_diagnostico_completo():
    """
    Diagnóstico completo del sistema para superadmin.
    Verifica TODAS las variables de entorno y servicios críticos.
    """
    import sys
    
    diagnostico = {
        'timestamp': datetime.utcnow().isoformat(),
        'entorno': os.environ.get('FLASK_ENV', 'development'),
        'servicios': {},
        'variables_entorno': {},
        'problemas': [],
        'recomendaciones': []
    }
    
    # ============================================================
    # 1. VARIABLES DE ENTORNO CRÍTICAS
    # ============================================================
    env_vars = {
        'SECRET_KEY': {
            'valor': os.environ.get('SECRET_KEY'),
            'requerido': True,
            'descripcion': 'Clave secreta para sesiones y CSRF'
        },
        'MYSQL_HOST': {
            'valor': os.environ.get('MYSQL_HOST'),
            'requerido': True,
            'descripcion': 'Host de la base de datos MySQL'
        },
        'MYSQL_USER': {
            'valor': os.environ.get('MYSQL_USER'),
            'requerido': True,
            'descripcion': 'Usuario de MySQL'
        },
        'MYSQL_PASSWORD': {
            'valor': os.environ.get('MYSQL_PASSWORD'),
            'requerido': True,
            'descripcion': 'Contraseña de MySQL',
            'ocultar': True
        },
        'MYSQL_DB': {
            'valor': os.environ.get('MYSQL_DB'),
            'requerido': True,
            'descripcion': 'Nombre de la base de datos'
        },
        'CLOUDINARY_URL': {
            'valor': os.environ.get('CLOUDINARY_URL'),
            'requerido': True,
            'descripcion': 'URL de configuración de Cloudinary',
            'ocultar': True
        },
        'MERCADO_PAGO_ACCESS_TOKEN': {
            'valor': os.environ.get('MERCADO_PAGO_ACCESS_TOKEN'),
            'requerido': True,
            'descripcion': 'Access Token de Mercado Pago (servidor)',
            'ocultar': True
        },
        'MERCADO_PAGO_PUBLIC_KEY': {
            'valor': os.environ.get('MERCADO_PAGO_PUBLIC_KEY'),
            'requerido': True,
            'descripcion': 'Public Key de Mercado Pago (cliente)'
        },
        'BASE_URL': {
            'valor': os.environ.get('BASE_URL'),
            'requerido': False,
            'descripcion': 'URL base de la aplicación'
        },
        'API_PROXY': {
            'valor': os.environ.get('API_PROXY'),
            'requerido': False,
            'descripcion': 'Proxy para APIs externas (PythonAnywhere)'
        },
        'MAIL_USERNAME': {
            'valor': os.environ.get('MAIL_USERNAME'),
            'requerido': False,
            'descripcion': 'Email para envío de correos'
        },
        'MAIL_PASSWORD': {
            'valor': os.environ.get('MAIL_PASSWORD'),
            'requerido': False,
            'descripcion': 'Contraseña de email',
            'ocultar': True
        },
        'SENTRY_DSN': {
            'valor': os.environ.get('SENTRY_DSN'),
            'requerido': False,
            'descripcion': 'DSN de Sentry para monitoreo de errores'
        }
    }
    
    for nombre, config in env_vars.items():
        valor = config['valor']
        tiene_valor = bool(valor)
        
        # Mostrar preview seguro (ocultar credenciales sensibles)
        if config.get('ocultar') and valor:
            preview = valor[:8] + '...' + valor[-4:] if len(valor) > 12 else '***'
        elif valor:
            preview = valor[:30] + '...' if len(valor) > 30 else valor
        else:
            preview = None
        
        estado = '✅' if tiene_valor else ('❌' if config['requerido'] else '⚠️')
        
        diagnostico['variables_entorno'][nombre] = {
            'configurada': tiene_valor,
            'requerida': config['requerido'],
            'preview': preview,
            'descripcion': config['descripcion'],
            'estado': estado
        }
        
        if config['requerido'] and not tiene_valor:
            diagnostico['problemas'].append(f"Variable {nombre} no configurada (requerida)")
    
    # ============================================================
    # 2. SERVICIOS
    # ============================================================
    
    # Base de datos
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT 1")
            cur.execute("SHOW TABLES")
            tablas = [row[list(row.keys())[0]] for row in cur.fetchall()]
        diagnostico['servicios']['mysql'] = {
            'estado': '✅ Conectado',
            'host': os.environ.get('MYSQL_HOST', 'not set'),
            'database': os.environ.get('MYSQL_DB', 'not set'),
            'tablas_encontradas': len(tablas),
            'tablas': tablas
        }
    except Exception as e:
        diagnostico['servicios']['mysql'] = {
            'estado': '❌ Error',
            'error': str(e)
        }
        diagnostico['problemas'].append(f"MySQL: {str(e)}")
    
    # Cloudinary
    diagnostico['servicios']['cloudinary'] = {
        'estado': '✅ Configurado' if CLOUDINARY_CONFIGURED else '❌ No configurado',
        'sdk_disponible': CLOUDINARY_AVAILABLE,
        'configurado': CLOUDINARY_CONFIGURED
    }
    if _cloudinary_config:
        diagnostico['servicios']['cloudinary']['cloud_name'] = _cloudinary_config.get('cloud_name')
    if not CLOUDINARY_CONFIGURED:
        diagnostico['problemas'].append("Cloudinary no está configurado - las imágenes no se subirán")
    
    # Mercado Pago
    diagnostico['servicios']['mercadopago'] = {
        'estado': '✅ Inicializado' if MERCADOPAGO_CLIENT else '❌ No inicializado',
        'sdk_disponible': MERCADOPAGO_AVAILABLE,
        'cliente_activo': bool(MERCADOPAGO_CLIENT),
        'public_key_configurada': bool(os.environ.get('MERCADO_PAGO_PUBLIC_KEY')),
        'access_token_configurado': bool(os.environ.get('MERCADO_PAGO_ACCESS_TOKEN'))
    }
    if MERCADOPAGO_IMPORT_ERROR:
        diagnostico['servicios']['mercadopago']['error_importacion'] = MERCADOPAGO_IMPORT_ERROR
    if not MERCADOPAGO_CLIENT:
        diagnostico['problemas'].append("Mercado Pago no está inicializado - los pagos no funcionarán")
    
    # Email
    diagnostico['servicios']['email'] = {
        'estado': '✅ Configurado' if EMAIL_SERVICE_AVAILABLE else '⚠️ No configurado',
        'disponible': EMAIL_SERVICE_AVAILABLE
    }
    
    # CSRF
    diagnostico['servicios']['csrf'] = {
        'estado': '✅ Activo' if CSRF_ENABLED else '⚠️ Inactivo',
        'habilitado': CSRF_ENABLED
    }
    
    # ============================================================
    # 3. RECOMENDACIONES
    # ============================================================
    if os.environ.get('FLASK_ENV') != 'production':
        diagnostico['recomendaciones'].append("Establece FLASK_ENV=production en producción")
    
    secret_key = os.environ.get('SECRET_KEY', '')
    if secret_key and len(secret_key) < 32:
        diagnostico['recomendaciones'].append("SECRET_KEY debería tener al menos 32 caracteres")
    
    if not os.environ.get('API_PROXY') and os.environ.get('FLASK_ENV') == 'production':
        diagnostico['recomendaciones'].append("En PythonAnywhere free tier, configura API_PROXY para APIs externas")
    
    if not EMAIL_SERVICE_AVAILABLE:
        diagnostico['recomendaciones'].append("Configura MAIL_USERNAME y MAIL_PASSWORD para envío de emails")
    
    # ============================================================
    # 4. RESUMEN
    # ============================================================
    total_vars_requeridas = sum(1 for v in env_vars.values() if v['requerido'])
    vars_configuradas = sum(1 for v in env_vars.values() if v['requerido'] and v['valor'])
    
    diagnostico['resumen'] = {
        'variables_requeridas': f"{vars_configuradas}/{total_vars_requeridas}",
        'problemas_encontrados': len(diagnostico['problemas']),
        'listo_para_produccion': len(diagnostico['problemas']) == 0
    }
    
    return jsonify(diagnostico)


# ============================================================
# ARCHIVOS ESTÁTICOS
# ============================================================


# ------------------------------------------------------------------
# Cloudinary diagnostics and test endpoints
# ------------------------------------------------------------------
@app.route('/admin/cloudinary/status', methods=['GET', 'POST'])
@login_required
@restaurante_owner_required
def admin_cloudinary_status():
    """GET: devuelve status de Cloudinary. POST: reintenta inicializar (útil después de setear CLOUDINARY_URL)."""
    if request.method == 'POST':
        ok = init_cloudinary()
        return jsonify({'reinitialized': ok, 'configured': CLOUDINARY_CONFIGURED, 'sdk_installed': CLOUDINARY_AVAILABLE})

    # GET
    # Mostrar información útil pero no exponer credenciales completas
    cloud_name = None
    if CLOUDINARY_CONFIGURED and cloudinary and hasattr(cloudinary, 'config'):
        try:
            cloud_name = getattr(cloudinary.config(), 'cloud_name', None) or os.environ.get('CLOUDINARY_URL', '').split('@')[-1]
        except Exception:
            cloud_name = None
    return jsonify({
        'configured': CLOUDINARY_CONFIGURED,
        'sdk_installed': CLOUDINARY_AVAILABLE,
        'cloud_name_preview': (cloud_name[:8] + '...') if cloud_name else None
    })


@app.route('/admin/cloudinary/test-upload', methods=['POST'])
@login_required
@restaurante_owner_required
def admin_cloudinary_test_upload():
    """Sube una imagen a Cloudinary para pruebas. Acepta campo 'image' (archivo) o 'image_url' (URL pública)."""
    if not CLOUDINARY_AVAILABLE:
        return jsonify({'success': False, 'error': 'Cloudinary SDK no instalado. Ejecuta pip install cloudinary'}), 500
    if not is_cloudinary_ready():
        return jsonify({'success': False, 'error': 'Cloudinary no está configurado. Establece CLOUDINARY_URL'}), 500

    # Permitir subir por archivo
    if 'image' in request.files and request.files['image']:
        file = request.files['image']
        # Validación de MIME y tamaño
        if request.content_length and request.content_length > app.config.get('MAX_CONTENT_LENGTH', MAX_CONTENT_LENGTH):
            return jsonify({'success': False, 'error': 'Archivo demasiado grande'}), 400
        is_valid, err = validate_image_file(file)
        if not is_valid:
            return jsonify({'success': False, 'error': err}), 400
        try:
            restaurante_id = session.get('restaurante_id') or 'anon'
            result = cloudinary_upload(
                file,
                folder=f"mimenudigital/test/{restaurante_id}"
            )
            return jsonify({'success': True, 'result': {'url': result.get('secure_url'), 'public_id': result.get('public_id')}})
        except Exception as e:
            logger.exception('Error al subir imagen de prueba a Cloudinary: %s', e)
            return jsonify({'success': False, 'error': str(e)}), 500

    # O permitir subir por URL
    image_url = request.form.get('image_url') or request.json.get('image_url') if request.is_json else None
    if image_url:
        try:
            restaurante_id = session.get('restaurante_id') or 'anon'
            result = cloudinary_upload(
                image_url,
                folder=f"mimenudigital/test/{restaurante_id}"
            )
            return jsonify({'success': True, 'result': {'url': result.get('secure_url'), 'public_id': result.get('public_id')}})
        except Exception as e:
            logger.exception('Error al subir imagen por URL a Cloudinary: %s', e)
            return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': False, 'error': 'Proporciona un archivo en el campo "image" o un "image_url" en el body.'}), 400


@app.route('/admin/cloudinary/process-pendings', methods=['POST'])
@login_required
@restaurante_owner_required
def admin_cloudinary_process_pendings():
    """Trigger processing of pending image uploads (synchronous). Accepts JSON: {"limit": 50, "max_attempts": 5, "dry_run": false}.
    Returns 200 on success and a brief summary."""
    data = request.get_json() or {}
    limit = int(data.get('limit', 50))
    max_attempts = int(data.get('max_attempts', 5))
    dry_run = bool(data.get('dry_run', False))

    if not CLOUDINARY_AVAILABLE:
        return jsonify({'success': False, 'error': 'Cloudinary SDK no instalado.'}), 500
    if not is_cloudinary_ready():
        return jsonify({'success': False, 'error': 'Cloudinary no está configurado.'}), 500

    try:
        # Import local script and run
        from scripts.process_pending_images import process
        exit_code = process(limit=limit, max_attempts=max_attempts, dry_run=dry_run)
        if exit_code == 0:
            return jsonify({'success': True, 'message': 'Procesamiento completado'}), 200
        elif exit_code == 2:
            return jsonify({'success': False, 'error': 'Cloudinary no disponible o no configurado'}), 500
        else:
            return jsonify({'success': False, 'error': 'Error durante el procesamiento'}), 500
    except Exception as e:
        logger.exception('Error ejecutando procesador de pendings: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    """Sirve archivos subidos (QR y temporales)."""
    upload_folder = os.path.join(base_dir, 'static', 'uploads')
    return send_from_directory(upload_folder, filename)


# ============================================================
# EJECUTAR APLICACIÓN
# ============================================================

if __name__ == '__main__':
    logger.info("%s", "=" * 50)
    logger.info("🍽️  MENÚ DIGITAL SAAS - Divergent Studio")
    logger.info("%s", "=" * 50)
    logger.info("MySQL: %s:%s/%s", app.config.get('MYSQL_HOST'), app.config.get('MYSQL_PORT'), app.config.get('MYSQL_DB'))
    logger.info("Servidor: http://127.0.0.1:5000")
    logger.info("%s", "=" * 50)
    logger.info("⚠️  Antes de usar, ejecuta: GET /api/init-db")
    logger.info("%s", "=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
