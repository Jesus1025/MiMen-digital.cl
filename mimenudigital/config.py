# ============================================================
# CONFIGURACIÓN - MENU DIGITAL SAAS
# ============================================================
import os

class Config:
    """Configuración base."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'menu_digital_divergent_secret_key_2025_prod')
    
    # Configuración de sesiones
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Base URL (se sobreescribe en producción)
    BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:5000')


class DevelopmentConfig(Config):
    """Configuración para desarrollo local."""
    DEBUG = True
    
    # MySQL local (XAMPP, WAMP, etc.)
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'menu_digital')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))


class ProductionConfig(Config):
    """Configuración para PythonAnywhere."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # MySQL en PythonAnywhere
    # Formato: tuusuario.mysql.pythonanywhere-services.com
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'tuusuario.mysql.pythonanywhere-services.com')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'tuusuario')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'tu_password_mysql')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'tuusuario$menu_digital')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    # Base URL en producción
    BASE_URL = os.environ.get('BASE_URL', 'https://tuusuario.pythonanywhere.com')


# Selector de configuración
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Obtiene la configuración según el entorno."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
