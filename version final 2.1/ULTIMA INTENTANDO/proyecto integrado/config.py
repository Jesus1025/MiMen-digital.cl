import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', '..', 'database'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'teknetau-dev-key-2025'
    DATABASE = os.path.join(DB_DIR, 'teknetau.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Configuración para producción
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
