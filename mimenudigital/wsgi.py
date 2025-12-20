# ============================================================
# WSGI CONFIGURATION FOR PYTHONANYWHERE
# ============================================================
# PythonAnywhere - Producción
# Las variables de entorno se configuran en:
# Web -> Environment variables
# ============================================================

import sys
import os

# 1. AÑADIR RUTA DEL PROYECTO
path = '/home/Jesus1025/MiMen-digital.cl'
if path not in sys.path:
    sys.path.insert(0, path)

# 2. IMPORTAR VARIABLES DE ENTORNO (solo en desarrollo si existe .env)
try:
    from dotenv import load_dotenv
    env_file = os.path.join(path, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
except ImportError:
    pass
except Exception:
    pass

# 3. IMPORTAR LA APP
try:
    from app_menu import app as application
except ImportError as e:
    # Si falla, mostrar error útil
    import traceback
    error_msg = f"Error importando app_menu: {str(e)}\n{traceback.format_exc()}"
    print(error_msg)
    
    # Crear una app dummy que muestre el error
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error():
        return f"<pre>Error: {error_msg}</pre>", 500
