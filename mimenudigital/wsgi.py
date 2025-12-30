# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================

import sys
import os

# 1. ESTABLECER VARIABLES DE ENTORNO
# Las variables de entorno (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, etc.)
# deben configurarse en la pestaña "Web" de PythonAnywhere.
# NO las dejes hardcodeadas en este fichero.

# 2. AÑADIR RUTA DEL PROYECTO
path = '/home/MiMenudigital/MiMen-digital.cl'
if path not in sys.path:
    sys.path.insert(0, path)

# 3. CARGAR .env si existe (desarrollo)
try:
    from dotenv import load_dotenv
    env_file = os.path.join(path, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
except ImportError:
    pass
except Exception:
    pass

# 4. IMPORTAR LA APP
try:
    from app_menu import app as application
except ImportError as e:
    import traceback
    from flask import Flask
    application = Flask(__name__)
    
    error_msg = f"Error importando app_menu: {str(e)}\n{traceback.format_exc()}"
    print(f"ERROR: {error_msg}")
    
    @application.route('/')
    def error():
        return f"<pre>Import Error:\n{error_msg}</pre>", 500
