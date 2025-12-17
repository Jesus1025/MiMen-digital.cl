import os
from app import app
from waitress import serve

# Lee la variable de entorno para determinar el modo de ejecución.
# Por defecto, se usa 'development'.
env = os.environ.get('FLASK_CONFIG', 'development')

if env == 'production':
    # En producción, usa Waitress, un servidor WSGI para Windows.
    # Escucha en todas las interfaces de red en el puerto 8080.
    print("Iniciando servidor en modo PRODUCCIÓN en http://0.0.0.0:8080")
    serve(app, host='0.0.0.0', port=8080)
else:
    # En desarrollo, usa el servidor de desarrollo de Flask.
    # Esto permite el modo de depuración y recarga automática.
    print("Iniciando servidor en modo DESARROLLO en http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000)
