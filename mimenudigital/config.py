# ============================================================
# CONFIGURACIÓN - MENU DIGITAL SAAS
# ============================================================
import os
import sys

class Config:
    """Configuración base para todos los entornos."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Mercado Pago y Cloudinary
    MERCADO_PAGO_ACCESS_TOKEN = os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
    

    # Configuración de sesiones - Seguridad mejorada y server-side
    SESSION_TYPE = os.environ.get('SESSION_TYPE', 'filesystem')  # filesystem, redis, etc.
    SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flask_session'))
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora de sesión
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Base URL
    BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000')
    
    # Database
    MYSQL_CHARSET = 'utf8mb4'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))


class DevelopmentConfig(Config):
    """Configuración para desarrollo local."""
    DEBUG = True
    TESTING = False
    
    # MySQL local (XAMPP, WAMP, Docker, etc.)
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'menu_digital')


class TestingConfig(Config):
    """Configuración para testing."""
    DEBUG = True
    TESTING = True
    
    # Base de datos de prueba
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB_TEST', 'menu_digital_test')


class ProductionConfig(Config):
    """Configuración para producción (ej. PythonAnywhere)."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # MySQL en producción - DEBEN ser configuradas como variables de entorno
    MYSQL_HOST = os.environ.get('MYSQL_HOST')
    MYSQL_USER = os.environ.get('MYSQL_USER')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
    MYSQL_DB = os.environ.get('MYSQL_DB')
    
    # Base URL en producción - DEBE ser HTTPS
    BASE_URL = os.environ.get('BASE_URL')


# Selector de configuración
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Obtiene la configuración según el entorno y la valida."""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config.get(env, config['default'])
    
    # --- Validación de variables críticas ---
    # En producción, ciertas variables son obligatorias.
    if env == 'production':
        required_vars = [
            'SECRET_KEY', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 
            'MYSQL_DB', 'BASE_URL', 'CLOUDINARY_URL', 'MERCADO_PAGO_ACCESS_TOKEN'
        ]
        missing_vars = [var for var in required_vars if not getattr(config_class, var, None)]
        
        if missing_vars:
            print("="*80, file=sys.stderr)
            print("FATAL ERROR: Faltan las siguientes variables de entorno en producción:", file=sys.stderr)
            for var in missing_vars:
                print(f" - {var}", file=sys.stderr)
            print("="*80, file=sys.stderr)
            sys.exit(1) # Detiene la aplicación si faltan variables clave
            
    return config_class

