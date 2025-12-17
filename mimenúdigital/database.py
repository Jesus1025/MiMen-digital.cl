# ============================================================
# DATABASE - Conexión MySQL con Pool
# ============================================================
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from flask import g, current_app

# Pool de conexiones simple
_connection_pool = []
_max_pool_size = 5


def get_db_config():
    """Obtiene la configuración de la base de datos."""
    return {
        'host': current_app.config['MYSQL_HOST'],
        'user': current_app.config['MYSQL_USER'],
        'password': current_app.config['MYSQL_PASSWORD'],
        'database': current_app.config['MYSQL_DB'],
        'port': current_app.config['MYSQL_PORT'],
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
        'autocommit': True
    }


def get_db():
    """Obtiene una conexión a MySQL."""
    if 'db' not in g:
        config = get_db_config()
        try:
            g.db = pymysql.connect(**config)
        except pymysql.Error as e:
            print(f"Error conectando a MySQL: {e}")
            raise
    return g.db


def close_db(error=None):
    """Cierra la conexión al terminar la request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except:
            pass


def init_app(app):
    """Registra el cierre de conexión con la app."""
    app.teardown_appcontext(close_db)


@contextmanager
def get_cursor():
    """Context manager para obtener un cursor."""
    db = get_db()
    cursor = db.cursor()
    try:
        yield cursor
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()


def dict_from_row(row):
    """Convierte una fila a diccionario (PyMySQL con DictCursor ya lo hace)."""
    return row if row else None


def list_from_rows(rows):
    """Convierte lista de filas a lista de diccionarios."""
    return list(rows) if rows else []
