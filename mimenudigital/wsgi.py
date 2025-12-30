import sys
import os

# ============================================================ 
# CONFIGURACIÓN DE VARIABLES DE ENTORNO
# ============================================================ 
# CREDENCIALES DE MERCADO PAGO (LIMPIO Y FUNCIONAL)
# ============================================================ 
os.environ['MERCADO_PAGO_PUBLIC_KEY'] = '***REMOVED***'
os.environ['MERCADO_PAGO_ACCESS_TOKEN'] = '***REMOVED***'
# Base de datos
os.environ['MYSQL_HOST'] = 'MiMenudigital.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'MiMenudigital'
os.environ['MYSQL_PASSWORD'] = '***REMOVED***'
os.environ['MYSQL_DB'] = 'MiMenudigital$menu_digital'
os.environ['MYSQL_PORT'] = '3306'

# Configuración de la App
os.environ['FLASK_ENV'] = 'production'
os.environ['BASE_URL'] = 'https://mimenudigital.pythonanywhere.com'

# Credenciales de Cloudinary
os.environ['CLOUDINARY_URL'] = 'cloudinary://***REMOVED***:***REMOVED***@tu_cloud_name'

# ============================================================ 


# ============================================================ 
# CARGA DE LA APLICACIÓN
# ============================================================ 
path = '/home/MiMenudigital/mimenudigital'

if path not in sys.path:
    sys.path.insert(0, path)

# Cambiamos al directorio del proyecto para que Flask encuentre las carpetas static/templates
os.chdir(path)

try:
    from app_factory import create_app
    application = create_app()
except ImportError as e:
    import traceback
    from flask import Flask
    application = Flask(__name__)

    error_msg = f"Error de Importación: {str(e)}\n\n{traceback.format_exc()}"

    @application.route('/')
    def error():
        return f"&lt;h1&gt;Error de Configuración&lt;/h1&gt;&lt;pre&gt;{error_msg}&lt;/pre&gt;", 500