# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================
# COPIA ESTE CONTENIDO AL ARCHIVO WSGI DE PYTHONANYWHERE
# En el dashboard Web -> pestaña WSGI configuration file
# ============================================================


import sys
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ============================================================
# RUTA DEL PROYECTO - AJUSTAR SEGÚN TU ESTRUCTURA
# ============================================================
# Opción 1: Si clonaste directamente (sin carpeta anidada)
# project_home = '/home/MiMenudigital/MiMen-digital.cl'

# Opción 2: Si hay carpeta anidada con caracteres especiales
# Prueba estas variantes según tu estructura:
project_home = '/home/MiMenudigital/MiMen-digital.cl/mimenúdigital'

# Si la ruta con ú no funciona, intenta:
# project_home = '/home/MiMenudigital/MiMen-digital.cl/mimenudigital'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Cambiar al directorio del proyecto
try:
    os.chdir(project_home)
except Exception as e:
    # Si falla, intentar encontrar el directorio
    base_path = '/home/MiMenudigital/MiMen-digital.cl'
    if os.path.exists(base_path):
        for item in os.listdir(base_path):
            full_path = os.path.join(base_path, item)
            if os.path.isdir(full_path) and 'app_menu.py' in os.listdir(full_path):
                project_home = full_path
                sys.path.insert(0, project_home)
                os.chdir(project_home)
                break

# ============================================================
# VARIABLES DE ENTORNO - CONFIGURACIÓN MYSQL
# ============================================================
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'menu_digital_divergent_secret_2025_prod_key_muy_segura'

# MySQL en PythonAnywhere - AJUSTA ESTOS VALORES
os.environ['MYSQL_HOST'] = 'MiMenudigital.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'MiMenudigital'
os.environ['MYSQL_PASSWORD'] = '19101810Aa'
os.environ['MYSQL_DB'] = 'MiMenudigital$default'
os.environ['MYSQL_PORT'] = '3306'

os.environ['BASE_URL'] = 'https://MiMenudigital.pythonanywhere.com'

# ============================================================
# IMPORTAR APLICACIÓN
# ============================================================
from app_menu import app as application
