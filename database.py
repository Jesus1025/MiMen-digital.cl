# ============================================================
# DATABASE - Pool de Conexiones MySQL de Alto Rendimiento
# ============================================================
# Versión: 2.0.0 - Production Ready
# Optimizado para PythonAnywhere con 3 workers
# 
# Características:
# - Pool thread-safe con queue.Queue
# - Reconexión automática en caso de fallo
# - Health checks con ping antes de entregar conexión
# - Reciclaje automático de conexiones antiguas
# - Métricas de uso en tiempo real
# - Liberación GARANTIZADA incluso en errores
# - Zero dependency (solo PyMySQL + Flask)
# ============================================================

import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from flask import g, has_request_context
import logging
import threading
import queue
import time
from functools import wraps

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN DEL POOL - OPTIMIZADA PARA PYTHONANYWHERE
# ============================================================

POOL_SIZE = 5           # Conexiones permanentes en el pool
MAX_OVERFLOW = 10       # Conexiones adicionales bajo demanda (max total: 15)
POOL_TIMEOUT = 10       # Segundos máximo esperando una conexión
POOL_RECYCLE = 55       # Reciclar conexiones cada 55s (MySQL timeout = 60s)
CONNECT_TIMEOUT = 5     # Timeout al crear conexión
READ_TIMEOUT = 30       # Timeout para lecturas
WRITE_TIMEOUT = 30      # Timeout para escrituras
MAX_RETRIES = 2         # Reintentos en caso de conexión perdida


# ============================================================
# EXCEPCIONES PERSONALIZADAS
# ============================================================

class PoolExhaustedError(Exception):
    """Se lanza cuando el pool está lleno y no hay conexiones disponibles."""
    pass


class ConnectionError(Exception):
    """Se lanza cuando no se puede establecer conexión con la base de datos."""
    pass


# ============================================================
# POOL DE CONEXIONES THREAD-SAFE
# ============================================================

class ConnectionPool:
    """
    Pool de conexiones MySQL thread-safe y de alto rendimiento.
    
    Características:
    - Conexiones verificadas con ping antes de entregarlas
    - Reciclaje automático de conexiones antiguas
    - Manejo robusto de errores y reconexión
    - Métricas de uso en tiempo real
    - Liberación garantizada con Flask teardown
    """
    
    def __init__(self):
        self._pool = queue.Queue(maxsize=POOL_SIZE + MAX_OVERFLOW)
        self._size = 0
        self._overflow = 0
        self._lock = threading.RLock()  # RLock para evitar deadlocks
        self._config = None
        self._initialized = False
        self._app = None
        
        # Métricas
        self._stats = {
            'connections_created': 0,
            'connections_recycled': 0,
            'connections_failed': 0,
            'gets': 0,
            'releases': 0,
            'timeouts': 0,
        }
    
    def init_app(self, app):
        """
        Inicializa el pool con la configuración de Flask.
        
        Args:
            app: Aplicación Flask con configuración de base de datos
        """
        if self._initialized:
            logger.debug("Pool already initialized, skipping")
            return
        
        self._app = app
        self._config = {
            'host': app.config.get('MYSQL_HOST', 'localhost'),
            'user': app.config.get('MYSQL_USER', 'root'),
            'password': app.config.get('MYSQL_PASSWORD', ''),
            'database': app.config.get('MYSQL_DB', 'mimenudigital'),
            'port': int(app.config.get('MYSQL_PORT', 3306)),
            'charset': 'utf8mb4',
            'cursorclass': DictCursor,
            'autocommit': False,
            'connect_timeout': CONNECT_TIMEOUT,
            'read_timeout': READ_TIMEOUT,
            'write_timeout': WRITE_TIMEOUT,
        }
        
        # Registrar teardown para liberar conexiones automáticamente
        app.teardown_appcontext(self._teardown)
        
        self._initialized = True
        logger.info(
            f"Connection pool initialized: "
            f"pool_size={POOL_SIZE}, max_overflow={MAX_OVERFLOW}, "
            f"recycle={POOL_RECYCLE}s, timeout={POOL_TIMEOUT}s"
        )
    
    def _create_connection(self):
        """
        Crea una nueva conexión MySQL con configuración optimizada.
        
        Returns:
            PyMySQL connection object
            
        Raises:
            ConnectionError: Si no se puede conectar
        """
        if not self._config:
            raise RuntimeError("Pool not initialized. Call init_app() first.")
        
        try:
            conn = pymysql.connect(**self._config)
            
            # Configurar sesión MySQL para mejor rendimiento
            with conn.cursor() as cur:
                cur.execute("SET SESSION wait_timeout=120")
                cur.execute("SET SESSION interactive_timeout=120")
                cur.execute("SET SESSION sql_mode='TRADITIONAL'")
            
            # Metadata para tracking
            conn._pool_created_at = time.time()
            conn._pool_last_used = time.time()
            
            with self._lock:
                self._stats['connections_created'] += 1
            
            return conn
            
        except pymysql.Error as e:
            with self._lock:
                self._stats['connections_failed'] += 1
            logger.error(f"Failed to create MySQL connection: {e}")
            raise ConnectionError(f"Cannot connect to database: {e}")
    
    def _is_connection_healthy(self, conn):
        """
        Verifica si una conexión está sana y lista para usar.
        
        Args:
            conn: Conexión a verificar
            
        Returns:
            bool: True si la conexión es válida
        """
        if conn is None:
            return False
        
        try:
            # Verificar si la conexión está viva
            conn.ping(reconnect=False)
            
            # Verificar edad de la conexión
            if hasattr(conn, '_pool_created_at'):
                age = time.time() - conn._pool_created_at
                if age > POOL_RECYCLE:
                    logger.debug(f"Connection recycled (age: {age:.1f}s)")
                    with self._lock:
                        self._stats['connections_recycled'] += 1
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _close_connection(self, conn):
        """Cierra una conexión de forma segura."""
        if conn is None:
            return
        try:
            conn.close()
        except Exception:
            pass
    
    def get_connection(self):
        """
        Obtiene una conexión del pool.
        
        Primero intenta obtener una conexión existente del pool.
        Si no hay disponibles, crea una nueva (si no se excede el límite).
        Si el pool está lleno, espera hasta POOL_TIMEOUT segundos.
        
        Returns:
            PyMySQL connection
            
        Raises:
            PoolExhaustedError: Si no hay conexiones disponibles
            ConnectionError: Si no se puede crear conexión
        """
        with self._lock:
            self._stats['gets'] += 1
        
        # Fase 1: Intentar obtener del pool (sin bloqueo)
        attempts = 0
        while attempts < 3:
            try:
                conn = self._pool.get_nowait()
                if self._is_connection_healthy(conn):
                    conn._pool_last_used = time.time()
                    return conn
                else:
                    self._close_connection(conn)
                    with self._lock:
                        if self._overflow > 0:
                            self._overflow -= 1
                        elif self._size > 0:
                            self._size -= 1
                    attempts += 1
            except queue.Empty:
                break
        
        # Fase 2: Crear nueva conexión si hay espacio
        with self._lock:
            total = self._size + self._overflow
            can_create = total < (POOL_SIZE + MAX_OVERFLOW)
            
            if can_create:
                if self._size < POOL_SIZE:
                    self._size += 1
                    is_overflow = False
                else:
                    self._overflow += 1
                    is_overflow = True
        
        if can_create:
            try:
                return self._create_connection()
            except Exception:
                with self._lock:
                    if is_overflow:
                        self._overflow -= 1
                    else:
                        self._size -= 1
                raise
        
        # Fase 3: Esperar por conexión disponible
        try:
            conn = self._pool.get(timeout=POOL_TIMEOUT)
            if self._is_connection_healthy(conn):
                conn._pool_last_used = time.time()
                return conn
            else:
                self._close_connection(conn)
                with self._lock:
                    if self._overflow > 0:
                        self._overflow -= 1
                    elif self._size > 0:
                        self._size -= 1
                # Último intento: crear nueva
                return self._create_connection()
                
        except queue.Empty:
            with self._lock:
                self._stats['timeouts'] += 1
            raise PoolExhaustedError(
                f"Connection pool exhausted. "
                f"Waited {POOL_TIMEOUT}s. Pool status: {self.status}"
            )
    
    def release_connection(self, conn, error=False):
        """
        Devuelve una conexión al pool.
        
        Args:
            conn: Conexión a devolver
            error: Si True, hace rollback; si False, hace commit
        """
        if conn is None:
            return
        
        with self._lock:
            self._stats['releases'] += 1
        
        try:
            # Manejar transacción
            if error:
                try:
                    conn.rollback()
                except Exception:
                    pass
            else:
                try:
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
            
            # Devolver al pool si está sana
            if self._is_connection_healthy(conn):
                try:
                    self._pool.put_nowait(conn)
                    return
                except queue.Full:
                    pass
            
            # Cerrar si no está sana o pool lleno
            self._close_connection(conn)
            with self._lock:
                if self._overflow > 0:
                    self._overflow -= 1
                elif self._size > 0:
                    self._size -= 1
                    
        except Exception as e:
            logger.debug(f"Error releasing connection: {e}")
            self._close_connection(conn)
    
    def _teardown(self, exception=None):
        """Flask teardown handler - libera conexión del request actual."""
        conn = g.pop('_db_connection', None)
        if conn is not None:
            self.release_connection(conn, error=exception is not None)
    
    @property
    def status(self):
        """Retorna métricas del pool en tiempo real."""
        with self._lock:
            available = self._pool.qsize()
            in_use = (self._size + self._overflow) - available
            return {
                'pool_size': POOL_SIZE,
                'max_overflow': MAX_OVERFLOW,
                'max_total': POOL_SIZE + MAX_OVERFLOW,
                'current_size': self._size,
                'overflow': self._overflow,
                'available': available,
                'in_use': max(0, in_use),
                'stats': self._stats.copy()
            }
    
    @property
    def is_healthy(self):
        """Verifica si el pool está funcionando correctamente."""
        try:
            conn = self.get_connection()
            self.release_connection(conn)
            return True
        except Exception:
            return False
    
    def close_all(self):
        """Cierra todas las conexiones del pool (para shutdown)."""
        closed = 0
        while True:
            try:
                conn = self._pool.get_nowait()
                self._close_connection(conn)
                closed += 1
            except queue.Empty:
                break
        
        with self._lock:
            self._size = 0
            self._overflow = 0
        
        logger.info(f"Connection pool closed ({closed} connections)")


# ============================================================
# INSTANCIA GLOBAL DEL POOL
# ============================================================

_pool = ConnectionPool()


def init_app(app):
    """Inicializa el pool de conexiones con la aplicación Flask."""
    _pool.init_app(app)


# ============================================================
# FUNCIONES DE ACCESO A BASE DE DATOS
# ============================================================

def get_db():
    """
    Obtiene una conexión del pool para el request actual.
    
    La conexión se almacena en Flask g y se libera AUTOMÁTICAMENTE
    al terminar el request gracias al teardown_appcontext.
    
    Returns:
        PyMySQL connection con DictCursor configurado
        
    Example:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
    """
    if '_db_connection' not in g:
        g._db_connection = _pool.get_connection()
    return g._db_connection


@contextmanager
def get_connection():
    """
    Context manager para conexión con liberación INMEDIATA.
    
    Usa esto para operaciones fuera de un request Flask o cuando
    necesites liberar la conexión antes de que termine el request.
    
    Example:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tabla")
                results = cur.fetchall()
        # Conexión ya liberada aquí
    """
    conn = _pool.get_connection()
    error = False
    try:
        yield conn
    except Exception:
        error = True
        raise
    finally:
        _pool.release_connection(conn, error=error)


@contextmanager 
def get_cursor(commit=True):
    """
    Context manager para cursor con transacción automática.
    
    La conexión se obtiene del request scope (Flask g).
    Hace commit automático al salir (a menos que haya error).
    
    Args:
        commit: Si True, hace commit al salir exitosamente
        
    Example:
        with get_cursor() as cur:
            cur.execute("INSERT INTO users (name) VALUES (%s)", ('John',))
            # Commit automático al salir
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error in get_cursor: {e}")
        raise
    finally:
        cursor.close()


@contextmanager
def get_cursor_immediate():
    """
    Context manager para cursor con liberación INMEDIATA de conexión.
    
    Ideal para operaciones rápidas donde quieres liberar la conexión
    lo antes posible para que otros requests puedan usarla.
    
    Example:
        with get_cursor_immediate() as cur:
            cur.execute("SELECT COUNT(*) as total FROM users")
            count = cur.fetchone()['total']
        # Conexión ya liberada aquí
    """
    conn = _pool.get_connection()
    cursor = conn.cursor()
    error = False
    try:
        yield cursor
        conn.commit()
    except Exception:
        error = True
        conn.rollback()
        raise
    finally:
        cursor.close()
        _pool.release_connection(conn, error=error)


def execute_query(query, params=None, commit=True):
    """
    Ejecuta una consulta SQL y retorna los resultados.
    
    Función de conveniencia para queries simples. Para operaciones
    más complejas o múltiples queries, usa get_cursor().
    
    Args:
        query: SQL query string
        params: Parámetros para la query (tuple o dict)
        commit: Si True, hace commit para INSERT/UPDATE/DELETE
        
    Returns:
        list[dict]: Para SELECT - lista de diccionarios
        int: Para INSERT/UPDATE/DELETE - número de filas afectadas
        
    Example:
        # SELECT
        users = execute_query("SELECT * FROM users WHERE active = %s", (True,))
        
        # INSERT
        rows = execute_query(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            ('John', 'john@example.com')
        )
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        
        # Detectar tipo de query
        query_type = query.strip().upper().split()[0] if query.strip() else ''
        
        if query_type == 'SELECT':
            result = cursor.fetchall()
        else:
            result = cursor.rowcount
            if commit:
                conn.commit()
        
        return result
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Query error: {e} | Query: {query[:100]}...")
        raise
    finally:
        cursor.close()


def execute_many(query, params_list, commit=True):
    """
    Ejecuta una query múltiples veces con diferentes parámetros.
    
    Más eficiente que llamar execute_query() múltiples veces.
    
    Args:
        query: SQL query string
        params_list: Lista de tuplas con parámetros
        commit: Si True, hace commit al final
        
    Returns:
        int: Total de filas afectadas
        
    Example:
        users = [('John', 'john@example.com'), ('Jane', 'jane@example.com')]
        rows = execute_many(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            users
        )
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.executemany(query, params_list)
        result = cursor.rowcount
        if commit:
            conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        logger.error(f"ExecuteMany error: {e}")
        raise
    finally:
        cursor.close()


# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def get_pool_status():
    """Retorna estadísticas completas del pool de conexiones."""
    return _pool.status


def is_pool_healthy():
    """Verifica si el pool está funcionando correctamente."""
    return _pool.is_healthy


def dict_from_row(row):
    """Convierte una fila a diccionario (DictCursor ya lo hace)."""
    return dict(row) if row else None


def list_from_rows(rows):
    """Convierte lista de filas a lista de diccionarios."""
    return [dict(row) for row in rows] if rows else []


def close_db(error=None):
    """Alias para compatibilidad con código legacy."""
    pass  # El teardown se encarga de esto automáticamente


# ============================================================
# DECORADORES DE UTILIDAD
# ============================================================

def with_retry(max_retries=MAX_RETRIES):
    """
    Decorador que reintenta operaciones de base de datos en caso de error de conexión.
    
    Example:
        @with_retry(max_retries=3)
        def get_user(user_id):
            return execute_query("SELECT * FROM users WHERE id = %s", (user_id,))
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (pymysql.OperationalError, pymysql.InterfaceError) as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}")
                        time.sleep(0.1 * (attempt + 1))  # Backoff exponencial
                    continue
                except Exception:
                    raise
            raise last_error
        return wrapper
    return decorator


# ============================================================
# HEALTH CHECK ENDPOINT HELPER
# ============================================================

def health_check():
    """
    Realiza un health check completo de la base de datos.
    
    Returns:
        dict: Estado de salud con métricas
        
    Example:
        @app.route('/health/db')
        def db_health():
            return jsonify(health_check())
    """
    start = time.time()
    try:
        with get_cursor_immediate() as cur:
            cur.execute("SELECT 1 as ping")
            result = cur.fetchone()
        
        latency = (time.time() - start) * 1000  # ms
        
        return {
            'status': 'healthy',
            'latency_ms': round(latency, 2),
            'pool': get_pool_status()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'pool': get_pool_status()
        }
