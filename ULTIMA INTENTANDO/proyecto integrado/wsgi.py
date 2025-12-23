# Archivo WSGI para PythonAnywhere
# Este archivo es el punto de entrada para el servidor web

import sys
import os

# Agregar el directorio del proyecto al path de Python
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Importar la aplicación Flask
from app import app as application

# Para PythonAnywhere, la variable debe llamarse 'application'
# Si prefieres usar otro nombre, puedes configurarlo en el panel de control
