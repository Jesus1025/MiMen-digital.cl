# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================
# Este archivo es necesario para desplegar en PythonAnywhere
# 
# INSTRUCCIONES:
# 1. Sube todo el proyecto a PythonAnywhere (Git o manual)
# 2. Crea la base de datos MySQL en el dashboard
# 3. En la pestaña "Web", configura el WSGI con estos valores
# ============================================================

import sys
import os

# Agregar el directorio del proyecto al path
# CAMBIAR 'tuusuario' por tu usuario de PythonAnywhere
project_home = '/home/MiMenudigital/menu-digital'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ============================================================
# VARIABLES DE ENTORNO - CONFIGURAR ANTES DE USAR
# ============================================================
os.environ['FLASK_ENV'] = 'production'

# Clave secreta - CAMBIAR por una cadena larga y aleatoria
os.environ['SECRET_KEY'] = 'CAMBIAR_POR_CLAVE_SECRETA_MUY_LARGA_Y_SEGURA_2025'

# MySQL en PythonAnywhere
# CAMBIAR 'tuusuario' por tu usuario real
os.environ['MYSQL_HOST'] = 'MiMenudigital.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'MiMenudigital'
os.environ['MYSQL_PASSWORD'] = '19101810Aa'
os.environ['MYSQL_DB'] = 'tuusuario$menu_digital'
os.environ['MYSQL_PORT'] = '3306'

# URL base de tu sitio
os.environ['BASE_URL'] = 'https://MiMenudigital.pythonanywhere.com'

# ============================================================
# IMPORTAR APLICACIÓN
# ============================================================
from app_menu import app as application
