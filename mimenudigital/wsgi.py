import sys
import os

# ============================================================ 
# CONFIGURACIÓN DE VARIABLES DE ENTORNO
# ============================================================ 
# CREDENCIALES DE MERCADO PAGO (LIMPIO Y FUNCIONAL)
# ============================================================ 
os.environ['MERCADO_PAGO_PUBLIC_KEY'] = 'APP_USR-56d00f49-c4e2-4b01-8670-d17bf4b841ad'
os.environ['MERCADO_PAGO_ACCESS_TOKEN'] = 'APP_USR-130838446303286-122321-7a32fce25e8565b16490762a1b0f2254-3090066666'
# Base de datos
os.environ['MYSQL_HOST'] = 'MiMenudigital.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'MiMenudigital'
os.environ['MYSQL_PASSWORD'] = '19101810Aa'
os.environ['MYSQL_DB'] = 'MiMenudigital$menu_digital'
os.environ['MYSQL_PORT'] = '3306'

# Configuración de la App
os.environ['FLASK_ENV'] = 'production'
os.environ['BASE_URL'] = 'https://mimenudigital.pythonanywhere.com'

# Credenciales de Cloudinary
os.environ['CLOUDINARY_URL'] = 'cloudinary://211225241664362:CV4Q_UfQR9A1GqKUmK02SzE4YiQ@dtrjravmg'

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