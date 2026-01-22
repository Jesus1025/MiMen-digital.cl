# ============================================================
# DATABASE - Conexión MySQL con Connection Pool
# ============================================================
# MEJORA: Connection pooling para soportar cientos de usuarios simultáneos
# ============================================================
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from flask import g, current_app
import logging
import threading
import time
from queue import Queue, Empty

logger = logging.getLogger(__name__)

# ============================================================
# CONNECTION POOL - Reutiliza conexiones en lugar de crear nuevas
# ============================================================

class ConnectionPool:
    """
    Pool de conexiones MySQL thread-safe.
    Reutiliza conexiones existentes para evitar el overhead de crear nuevas.
    """
    
    def __init__(self, min_connections=2, max_connections=10, max_idle_time=300):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time  # segundos antes de cerrar conexión inactiva
        self._pool = Queue(maxsize=max_connections)
        self._size = 0
        self._lock = threading.Lock()
        self._config = None
        self._initialized = False
        
    def init_app(self, app):
        """Inicializa el pool con la configuración de la app."""
        self._config = {
            'host': app.config.get('MYSQL_HOST'),
            'user': app.config.get('MYSQL_USER'),
            'password': app.config.get('MYSQL_PASSWORD'),
            'database': app.config.get('MYSQL_DB'),
            'port': int(app.config.get('MYSQL_PORT', 3306)),
            'charset': app.config.get('MYSQL_CHARSET', 'utf8mb4'),
            'cursorclass': DictCursor,
            'autocommit': False,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30
        }
        
        # Pre-crear conexiones mínimas
        for _ in range(self.min_connections):
            try:
                conn = self._create_connection()
                self._pool.put((conn, time.time()))
            except Exception as e:
                logger.warning("Could not pre-create connection: %s", e)
        
        self._initialized = True
        logger.info("Connection pool initialized: min=%d, max=%d", self.min_connections, self.max_connections)
        
    def _create_connection(self):
        """Crea una nueva conexión MySQL."""
        if not self._config:
            raise RuntimeError("Connection pool not initialized. Call init_app first.")
        
        conn = pymysql.connect(**self._config)
        with self._lock:
            self._size += 1
        logger.debug("Created new MySQL connection (pool size: %d)", self._size)
        return conn
    
    def get_connection(self):
        """
        Obtiene una conexión del pool o crea una nueva si es necesario.
        """
        # Intentar obtener del pool
        while True:
            try:
                conn, last_used = self._pool.get_nowait()
                
                # Verificar si la conexión es muy vieja
                if time.time() - last_used > self.max_idle_time:
                    try:
                        conn.close()
                    except:
                        pass
                    with self._lock:
                        self._size -= 1
                    continue
                
                # Verificar que la conexión siga activa
                try:
                    conn.ping(reconnect=False)
                    return conn
                except pymysql.Error:
                    try:
                        conn.close()
                    except:
                        pass
                    with self._lock:
                        self._size -= 1
                    continue
                    
            except Empty:
                break
        
        # No hay conexiones disponibles, crear una nueva si no excedemos el máximo
        with self._lock:
            if self._size < self.max_connections:
                return self._create_connection()
        
        # Pool lleno, esperar por una conexión
        try:
            conn, _ = self._pool.get(timeout=10)
            try:
                conn.ping(reconnect=True)
                return conn
            except pymysql.Error:
                with self._lock:
                    self._size -= 1
                return self._create_connection()
        except Empty:
            raise RuntimeError("Connection pool exhausted and timeout reached")
    
    def return_connection(self, conn):
        """Devuelve una conexión al pool."""
        if conn is None:
            return
            
        try:
            # Rollback cualquier transacción pendiente
            conn.rollback()
            
            # Verificar que siga activa
            conn.ping(reconnect=False)
            
            # Devolver al pool
            try:
                self._pool.put_nowait((conn, time.time()))
            except:
                # Pool lleno, cerrar la conexión
                conn.close()
                with self._lock:
                    self._size -= 1
        except Exception as e:
            # Conexión corrupta, cerrar y decrementar
            logger.debug("Closing corrupted connection: %s", e)
            try:
                conn.close()
            except:
                pass
            with self._lock:
                self._size -= 1
    
    def close_all(self):
        """Cierra todas las conexiones del pool."""
        while True:
            try:
                conn, _ = self._pool.get_nowait()
                try:
                    conn.close()
                except:
                    pass
            except Empty:
                break
        with self._lock:
            self._size = 0
        logger.info("Connection pool closed")

    @property
    def status(self):
        """Retorna el estado actual del pool."""
        return {
            'size': self._size,
            'available': self._pool.qsize(),
            'max': self.max_connections,
            'min': self.min_connections
        }


# Instancia global del pool
_pool = ConnectionPool(min_connections=2, max_connections=10)


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
    Obtiene una conexión a MySQL del pool.
    La conexión se almacena en g para reutilizarla durante el request.
    """
    if 'db' not in g:
        try:
            if _pool._initialized:
                g.db = _pool.get_connection()
                g._db_from_pool = True
            else:
                # Fallback si el pool no está inicializado
                config = get_db_config()
                g.db = pymysql.connect(**config)
                g._db_from_pool = False
                logger.debug("Using direct connection (pool not initialized)")
        except Exception as e:
            logger.error("Failed to get MySQL connection: %s", e)
            raise
    else:
        # Verificar si la conexión sigue activa
        try:
            g.db.ping(reconnect=True)
        except pymysql.Error as e:
            logger.warning("Lost MySQL connection, getting new one: %s", e)
            if g.get('_db_from_pool') and _pool._initialized:
                g.db = _pool.get_connection()
            else:
                config = get_db_config()
                g.db = pymysql.connect(**config)
    
    return g.db


def close_db(error=None):
    """Devuelve la conexión al pool al terminar el request."""
    db = g.pop('db', None)
    from_pool = g.pop('_db_from_pool', False)
    
    if db is not None:
        if from_pool and _pool._initialized:
            _pool.return_connection(db)
        else:
            try:
                db.close()
            except Exception as e:
                logger.warning("Error closing MySQL connection: %s", e)


def init_app(app):
    """Registra el cierre de conexión con la app e inicializa el pool."""
    app.teardown_appcontext(close_db)
    
    # Inicializar pool después de que la config esté lista
    @app.before_request
    def _init_pool_once():
        if not _pool._initialized and app.config.get('MYSQL_HOST'):
            try:
                _pool.init_app(app)
            except Exception as e:
                logger.warning("Could not initialize connection pool: %s", e)
    
    logger.info("Database module initialized with connection pool")


def get_pool_status():
    """Retorna el estado del pool de conexiones."""
    return _pool.status


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
        logger.error("Database error in cursor context: %s", e)
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
            logger.error("Error executing query: %s | Query: %s | Params: %s", e, query, params)
            raise


def dict_from_row(row):
    """Convierte una fila a diccionario (PyMySQL con DictCursor ya lo hace)."""
    return row if row else None


def list_from_rows(rows):
    """Convierte lista de filas a lista de diccionarios."""
    return list(rows) if rows else []
