# ============================================================
# DATABASE - Conexión MySQL con manejo robusto
# ============================================================
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from flask import g, current_app
import logging

logger = logging.getLogger(__name__)


def get_db_config():
    """Obtiene la configuración de la base de datos desde app.config."""
    return {
        'host': current_app.config.get('MYSQL_HOST'),
        'user': current_app.config.get('MYSQL_USER'),
        'password': current_app.config.get('MYSQL_PASSWORD'),
        'database': current_app.config.get('MYSQL_DB'),
        'port': int(current_app.config.get('MYSQL_PORT', 3306)),
        'charset': current_app.config.get('MYSQL_CHARSET', 'utf8mb4'),
        'cursorclass': DictCursor,
        'autocommit': False  # Mejor control de transacciones
    }


def get_db():
    """
    Obtiene una conexión a MySQL con reconexión automática.
    Si la conexión existe y está activa, la reutiliza.
    """
    if 'db' not in g:
        try:
            config = get_db_config()
            g.db = pymysql.connect(**config)
            logger.info(f"Connected to MySQL at {config['host']}:{config['port']}")
        except pymysql.Error as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            raise
    else:
        # Verificar si la conexión sigue activa
        try:
            g.db.ping(reconnect=True)
        except pymysql.Error as e:
            logger.warning(f"Lost MySQL connection, reconnecting: {e}")
            try:
                config = get_db_config()
                g.db = pymysql.connect(**config)
            except pymysql.Error as e:
                logger.error(f"Failed to reconnect to MySQL: {e}")
                raise
    
    return g.db


def close_db(error=None):
    """Cierra la conexión al terminar la request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
            logger.debug("MySQL connection closed")
        except Exception as e:
            logger.warning(f"Error closing MySQL connection: {e}")


def init_app(app):
    """Registra el cierre de conexión con la app."""
    app.teardown_appcontext(close_db)
    logger.info("Database module initialized")


@contextmanager
def get_cursor(commit=True):
    """
    Context manager para obtener un cursor con manejo de transacciones.
    
    Args:
        commit (bool): Si True, hace commit automático. Si False, hace rollback.
    """
    db = get_db()
    cursor = db.cursor()
    try:
        yield cursor
        if commit:
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error in cursor context: {e}")
        raise
    finally:
        cursor.close()


def execute_query(query, params=None, commit=True):
    """
    Ejecuta una consulta SQL y retorna los resultados.
    
    Args:
        query (str): SQL query
        params (tuple): Parámetros para la query
        commit (bool): Si True, hace commit después de INSERT/UPDATE/DELETE
    
    Returns:
        list: Lista de diccionarios con los resultados (para SELECT)
        int: Número de filas afectadas (para INSERT/UPDATE/DELETE)
    """
    with get_cursor(commit=commit) as cursor:
        try:
            cursor.execute(query, params or ())
            
            # Si es SELECT, retornar resultados
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            
            # Para INSERT/UPDATE/DELETE, retornar número de filas afectadas
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error executing query: {e}\nQuery: {query}\nParams: {params}")
            raise


def dict_from_row(row):
    """Convierte una fila a diccionario (PyMySQL con DictCursor ya lo hace)."""
    return row if row else None


def list_from_rows(rows):
    """Convierte lista de filas a lista de diccionarios."""
    return list(rows) if rows else []
