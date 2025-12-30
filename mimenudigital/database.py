# database.py

import pymysql
from pymysql.cursors import DictCursor
from flask import g, current_app

def get_db():
    """
    Obtiene una conexión a MySQL.
    Reutiliza la conexión existente si está activa en el contexto de la aplicación.
    """
    if 'db' not in g:
        try:
            g.db = pymysql.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                password=current_app.config['MYSQL_PASSWORD'],
                db=current_app.config['MYSQL_DB'],
                port=int(current_app.config.get('MYSQL_PORT', 3306)),
                charset='utf8mb4',
                cursorclass=DictCursor
            )
        except pymysql.Error as e:
            # You should probably log this error
            raise e
    return g.db

def close_db(e=None):
    """Cierra la conexión a la base de datos."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    """Registra la función de cierre de la base de datos con la aplicación Flask."""
    app.teardown_appcontext(close_db)