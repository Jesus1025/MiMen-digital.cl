# ============================================================
# CONFIGURACIÓN - MENU DIGITAL SAAS
# ============================================================
import os

class Config:
    """Configuración base para todos los entornos."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'menu_digital_divergent_secret_key_2025_prod')
    
    # Configuración de sesiones - Seguridad mejorada
    SESSION_COOKIE_SECURE = False  # Se sobreescribe en ProductionConfig
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora de sesión
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Base URL (se sobreescribe en producción)
    BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000')
    
    # Database defaults (se sobreescriben en subclases)
    MYSQL_CHARSET = 'utf8mb4'
    MYSQL_PORT = 3306


class DevelopmentConfig(Config):
    """Configuración para desarrollo local."""
    DEBUG = True
    TESTING = False
    
    # MySQL local (XAMPP, WAMP, etc.)
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'menu_digital')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))


class TestingConfig(Config):
    """Configuración para testing."""
    DEBUG = True
    TESTING = True
    
    # Base de datos de prueba
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'menu_digital_test')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))


class ProductionConfig(Config):
    """Configuración para PythonAnywhere (producción)."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # MySQL en PythonAnywhere
    # Formato: tuusuario.mysql.pythonanywhere-services.com
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'tuusuario.mysql.pythonanywhere-services.com')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'tuusuario')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'tu_password_mysql')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'tuusuario$menu_digital')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    # Base URL en producción - DEBE ser HTTPS
    BASE_URL = os.environ.get('BASE_URL', 'https://tuusuario.pythonanywhere.com')


# Selector de configuración
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Obtiene la configuración según el entorno."""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config.get(env, config['default'])
    
    # Validación básica en producción
    if env == 'production':
        if config_class.SECRET_KEY == 'menu_digital_divergent_secret_key_2025_prod':
            import warnings
            warnings.warn(
                "Using default SECRET_KEY in production! Set SECRET_KEY environment variable.",
                RuntimeWarning
            )
    
    return config_class
