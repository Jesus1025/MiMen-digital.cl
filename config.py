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

    # Cloudinary image defaults: widths (used to build srcset) and quality
    CLOUDINARY_IMAGE_WIDTHS = [320, 640, 1024]
    CLOUDINARY_IMAGE_QUALITY = 'auto'
    
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


# ============================================================
# CONFIGURACIÓN DE EMAIL (SMTP)
# ============================================================
# OPCIÓN 1: Variables de entorno (recomendado en producción con plan pago)
# OPCIÓN 2: Valores directos aquí (para plan gratuito sin más env vars)
#
# Para Gmail: usa "Contraseña de aplicación" (no tu contraseña normal)
# https://myaccount.google.com/apppasswords

class MailConfig:
    """Configuración de email compartida."""
    # ============================================================
    # 📧 CONFIGURA TUS CREDENCIALES AQUÍ (plan gratuito)
    # ============================================================
    # Descomenta y completa con tus datos:
    
    # _EMAIL_USERNAME = 'tu_email@gmail.com'
    # _EMAIL_PASSWORD = 'xxxx xxxx xxxx xxxx'  # Contraseña de aplicación de Gmail
    # _SUPERADMIN_EMAIL = 'tu_email@gmail.com'
    
    # ============================================================
    # (No tocar lo de abajo - usa env vars si existen, si no usa los de arriba)
    # ============================================================
    
    # Intentar obtener de variables de entorno primero, luego de valores locales
    _LOCAL_USERNAME = locals().get('_EMAIL_USERNAME', '')
    _LOCAL_PASSWORD = locals().get('_EMAIL_PASSWORD', '')
    _LOCAL_SUPERADMIN = locals().get('_SUPERADMIN_EMAIL', '')
    
    # Servidor SMTP
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    
    # Credenciales (prioridad: env var > valor local > vacío)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or _LOCAL_USERNAME
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or _LOCAL_PASSWORD
    
    # Remitente por defecto
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'Menú Digital <noreply@menudigital.com>')
    
    # Email del superadmin para notificaciones
    SUPERADMIN_EMAIL = os.environ.get('SUPERADMIN_EMAIL') or _LOCAL_SUPERADMIN or MAIL_USERNAME
    
    # Nombre de la aplicación para emails
    APP_NAME = 'Menú Digital - Divergent Studio'


# Agregar configuración de mail a las clases de config
DevelopmentConfig.MAIL_SERVER = MailConfig.MAIL_SERVER
DevelopmentConfig.MAIL_PORT = MailConfig.MAIL_PORT
DevelopmentConfig.MAIL_USE_TLS = MailConfig.MAIL_USE_TLS
DevelopmentConfig.MAIL_USE_SSL = MailConfig.MAIL_USE_SSL
DevelopmentConfig.MAIL_USERNAME = MailConfig.MAIL_USERNAME
DevelopmentConfig.MAIL_PASSWORD = MailConfig.MAIL_PASSWORD
DevelopmentConfig.MAIL_DEFAULT_SENDER = MailConfig.MAIL_DEFAULT_SENDER
DevelopmentConfig.SUPERADMIN_EMAIL = MailConfig.SUPERADMIN_EMAIL
DevelopmentConfig.APP_NAME = MailConfig.APP_NAME

ProductionConfig.MAIL_SERVER = MailConfig.MAIL_SERVER
ProductionConfig.MAIL_PORT = MailConfig.MAIL_PORT
ProductionConfig.MAIL_USE_TLS = MailConfig.MAIL_USE_TLS
ProductionConfig.MAIL_USE_SSL = MailConfig.MAIL_USE_SSL
ProductionConfig.MAIL_USERNAME = MailConfig.MAIL_USERNAME
ProductionConfig.MAIL_PASSWORD = MailConfig.MAIL_PASSWORD
ProductionConfig.MAIL_DEFAULT_SENDER = MailConfig.MAIL_DEFAULT_SENDER
ProductionConfig.SUPERADMIN_EMAIL = MailConfig.SUPERADMIN_EMAIL
ProductionConfig.APP_NAME = MailConfig.APP_NAME


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
