# ============================================================
# DATABASE - Conexión MySQL con SQLAlchemy QueuePool
# ============================================================
# Pool robusto para PythonAnywhere con 3 workers
# pool_size=5, max_overflow=10
# Liberación INMEDIATA de conexiones incluso en errores
# ============================================================

import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from flask import g, current_app
import logging
import time

# SQLAlchemy para pool de conexiones (mucho más robusto)
from sqlalchemy import create_engine, event, exc
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN GLOBAL DEL POOL
# ============================================================

_engine = None
_initialized = False


def _build_connection_url(app):
    """Construye la URL de conexión MySQL para SQLAlchemy."""
    host = app.config.get('MYSQL_HOST', 'localhost')
    user = app.config.get('MYSQL_USER', 'root')
    password = app.config.get('MYSQL_PASSWORD', '')
    database = app.config.get('MYSQL_DB', 'mimenudigital')
    port = app.config.get('MYSQL_PORT', 3306)
    
    # Escapar caracteres especiales en password
    from urllib.parse import quote_plus
    safe_password = quote_plus(str(password))
    
    return f"mysql+pymysql://{user}:{safe_password}@{host}:{port}/{database}?charset=utf8mb4"


def init_app(app):
    """
    Inicializa el pool de conexiones SQLAlchemy.
    
    CONFIGURACIÓN OPTIMIZADA PARA PYTHONANYWHERE (3 workers):
    - pool_size=5: Conexiones permanentes
    - max_overflow=10: Conexiones temporales extra (máximo total: 15)
    - pool_timeout=10: Máximo 10s esperando conexión
    - pool_recycle=60: Reciclar cada 60s (evita MySQL timeout)
    - pool_pre_ping=True: Verificar conexión antes de usarla
    """
    global _engine, _initialized
    
    if _initialized and _engine is not None:
        logger.debug("Pool already initialized")
        return
    
    try:
        connection_url = _build_connection_url(app)
        
        _engine = create_engine(
            connection_url,
            poolclass=QueuePool,
            pool_size=5,              # Conexiones base permanentes
            max_overflow=10,          # Conexiones adicionales temporales
            pool_timeout=10,          # Timeout esperando conexión (segundos)
            pool_recycle=60,          # Reciclar conexiones cada 60s
            pool_pre_ping=True,       # Verificar conexión está viva
            echo=False,               # No loggear SQL
            # Configuración de conexión PyMySQL - SIN DictCursor aquí
            connect_args={
                'autocommit': False,
                'connect_timeout': 5,
                'read_timeout': 30,
                'write_timeout': 30,
            }
        )
        
        # Configurar sesión MySQL al conectar
        @event.listens_for(_engine, "connect")
        def set_session_config(dbapi_connection, connection_record):
            """Configura la sesión MySQL al crear conexión."""
            cursor = dbapi_connection.cursor()
            cursor.execute("SET SESSION wait_timeout=120")
            cursor.execute("SET SESSION interactive_timeout=120")
            cursor.close()
        
        # Manejar conexiones inválidas
        @event.listens_for(_engine, "checkout")
        def checkout_listener(dbapi_connection, connection_record, connection_proxy):
            """Verifica conexión al sacarla del pool."""
            try:
                dbapi_connection.ping(reconnect=False)
            except Exception:
                raise exc.DisconnectionError()
        
        # Registrar teardown para liberar conexiones
        app.teardown_appcontext(_release_connection)
        
        _initialized = True
        logger.info("SQLAlchemy QueuePool initialized: pool_size=5, max_overflow=10")
        
    except Exception as e:
        logger.error("Failed to initialize connection pool: %s", e)
        raise


def _release_connection(exception=None):
    """
    Libera la conexión al terminar el request.
    Se llama automáticamente por Flask teardown_appcontext.
    GARANTIZA liberación incluso si hay error.
    """
    conn = g.pop('_db_connection', None)
    if conn is not None:
        try:
            if exception:
                conn.rollback()
            else:
                # Commit implícito si no hay error
                try:
                    conn.commit()
                except:
                    conn.rollback()
        except Exception as e:
            logger.debug("Error during connection cleanup: %s", e)
        finally:
            # SIEMPRE cerrar (devolver al pool)
            try:
                conn.close()
            except:
                pass


def get_db():
    """
    Obtiene una conexión del pool.
    La conexión se almacena en g y se libera AUTOMÁTICAMENTE al terminar el request.
    
    Returns:
        PyMySQL connection (raw connection from SQLAlchemy pool)
    """
    if '_db_connection' not in g:
        if not _initialized or _engine is None:
            raise RuntimeError("Database pool not initialized. Call init_app first.")
        
        # Obtener conexión raw del pool
        g._db_connection = _engine.raw_connection()
    
    return g._db_connection


@contextmanager
def get_connection():
    """
    Context manager para conexión con liberación INMEDIATA.
    Usa esto para operaciones fuera de un request Flask.
    
    La conexión se libera AL SALIR del bloque with, incluso si hay error.
    
    Ejemplo:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tabla")
                results = cur.fetchall()
        # Conexión ya liberada aquí
    """
    if not _initialized or _engine is None:
        raise RuntimeError("Database pool not initialized")
    
    conn = _engine.raw_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()  # SIEMPRE libera al pool


@contextmanager 
def get_cursor(commit=True):
    """
    Context manager para cursor con manejo automático de transacciones.
    La conexión se obtiene de g (request scope).
    Usa DictCursor para retornar diccionarios.
    
    Ejemplo:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM tabla")
            results = cur.fetchall()
    """
    conn = get_db()
    cursor = conn.cursor(DictCursor)  # Usar DictCursor explícitamente
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("Database error: %s", e)
        raise
    finally:
        cursor.close()


@contextmanager
def get_cursor_immediate():
    """
    Context manager para cursor con liberación INMEDIATA de conexión.
    Usa esto cuando necesites liberar la conexión rápidamente.
    Usa DictCursor para retornar diccionarios.
    
    Ejemplo:
        with get_cursor_immediate() as cur:
            cur.execute("SELECT * FROM tabla")
            results = cur.fetchall()
        # Conexión ya liberada aquí
    """
    if not _initialized or _engine is None:
        raise RuntimeError("Database pool not initialized")
    
    conn = _engine.raw_connection()
    cursor = conn.cursor(DictCursor)  # Usar DictCursor explícitamente
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()  # Libera INMEDIATAMENTE


def execute_query(query, params=None, commit=True):
    """
    Ejecuta una consulta SQL y retorna los resultados.
    Usa DictCursor para retornar diccionarios.
    
    Args:
        query (str): SQL query
        params (tuple): Parámetros para la query
        commit (bool): Si hacer commit (para INSERT/UPDATE/DELETE)
    
    Returns:
        list: Resultados para SELECT
        int: Filas afectadas para INSERT/UPDATE/DELETE
    """
    conn = get_db()
    cursor = conn.cursor(DictCursor)  # Usar DictCursor explícitamente
    try:
        cursor.execute(query, params or ())
        
        if query.strip().upper().startswith('SELECT'):
            result = cursor.fetchall()
        else:
            result = cursor.rowcount
        
        if commit:
            conn.commit()
        
        return result
    except Exception as e:
        conn.rollback()
        logger.error("Database error: %s", e)
        raise
    finally:
        cursor.close()


def get_pool_status():
    """Retorna estadísticas del pool de conexiones."""
    if _engine is None:
        return {'status': 'not_initialized'}
    
    pool = _engine.pool
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(), 
        'overflow': pool.overflow(),
        'total_connections': pool.checkedin() + pool.checkedout()
    }


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def dict_from_row(row):
    """Convierte fila a dict (DictCursor ya lo hace)."""
    return row if row else None


def list_from_rows(rows):
    """Convierte lista de filas a lista de dicts."""
    return list(rows) if rows else []


def close_db(error=None):
    """Alias para compatibilidad. Llamado por teardown."""
    _release_connection(error)


# Variable para compatibilidad con código que usa _pool
class _PoolCompat:
    """Wrapper de compatibilidad."""
    _initialized = False
    
    def init_app(self, app):
        init_app(app)
        self._initialized = True
    
    @property
    def status(self):
        return get_pool_status()

_pool = _PoolCompat()
