# ============================================================
# SECURITY & PERFORMANCE MIDDLEWARE
# ============================================================
# Módulo centralizado para mejoras de seguridad y rendimiento
# - Rate Limiting
# - Security Headers
# - GZIP Compression
# - Simple In-Memory Cache
# - Login Attempt Limiting
# ============================================================

import time
import hashlib
import functools
import gzip
import io
from collections import defaultdict
from threading import Lock
from flask import request, jsonify, g, make_response
import logging

logger = logging.getLogger(__name__)

# ============================================================
# RATE LIMITING - Previene ataques DDoS y abuso
# ============================================================

class RateLimiter:
    """
    Rate limiter en memoria con sliding window.
    Limita requests por IP y por endpoint.
    """
    
    def __init__(self, default_limit=100, default_window=60):
        self.default_limit = default_limit  # requests por ventana
        self.default_window = default_window  # segundos
        self._requests = defaultdict(list)  # {key: [timestamps]}
        self._lock = Lock()
        self._cleanup_interval = 60  # limpiar cada 60 segundos
        self._last_cleanup = time.time()
        
    def _get_key(self, ip, endpoint=None):
        """Genera una key única para el rate limit."""
        if endpoint:
            return f"{ip}:{endpoint}"
        return ip
    
    def _cleanup(self):
        """Limpia entradas expiradas del diccionario."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
            
        with self._lock:
            expired_keys = []
            for key, timestamps in self._requests.items():
                # Filtrar timestamps viejos
                self._requests[key] = [t for t in timestamps if now - t < self.default_window * 2]
                if not self._requests[key]:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._requests[key]
            
            self._last_cleanup = now
    
    def is_allowed(self, ip, endpoint=None, limit=None, window=None):
        """
        Verifica si el request está permitido.
        
        Returns:
            tuple: (allowed: bool, remaining: int, reset_time: int)
        """
        self._cleanup()
        
        limit = limit or self.default_limit
        window = window or self.default_window
        key = self._get_key(ip, endpoint)
        now = time.time()
        
        with self._lock:
            # Filtrar timestamps dentro de la ventana
            self._requests[key] = [t for t in self._requests[key] if now - t < window]
            
            count = len(self._requests[key])
            remaining = max(0, limit - count - 1)
            
            if count >= limit:
                # Calcular cuándo se resetea
                oldest = min(self._requests[key]) if self._requests[key] else now
                reset_time = int(oldest + window - now)
                return False, 0, reset_time
            
            # Registrar este request
            self._requests[key].append(now)
            return True, remaining, window


# Instancia global del rate limiter
_rate_limiter = RateLimiter(default_limit=100, default_window=60)

# Límites específicos por tipo de endpoint
RATE_LIMITS = {
    'login': (5, 60),        # 5 intentos por minuto
    'api_write': (30, 60),   # 30 writes por minuto
    'api_read': (120, 60),   # 120 reads por minuto
    'upload': (10, 60),      # 10 uploads por minuto
    'public': (200, 60),     # 200 requests por minuto para menús públicos
    'default': (100, 60)     # 100 requests por minuto por defecto
}


def get_client_ip():
    """Obtiene la IP real del cliente considerando proxies."""
    # X-Forwarded-For puede tener múltiples IPs: client, proxy1, proxy2
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


def rate_limit(limit_type='default'):
    """
    Decorador para aplicar rate limiting a una ruta.
    
    Args:
        limit_type: Tipo de límite ('login', 'api_write', 'api_read', 'upload', 'public', 'default')
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            ip = get_client_ip()
            limit, window = RATE_LIMITS.get(limit_type, RATE_LIMITS['default'])
            endpoint = f"{limit_type}:{request.endpoint}"
            
            allowed, remaining, reset_time = _rate_limiter.is_allowed(ip, endpoint, limit, window)
            
            # Agregar headers de rate limit
            g.rate_limit_remaining = remaining
            g.rate_limit_reset = reset_time
            
            if not allowed:
                logger.warning("Rate limit exceeded for IP %s on %s", ip, request.endpoint)
                response = jsonify({
                    'success': False,
                    'error': 'Demasiadas solicitudes. Intenta de nuevo más tarde.',
                    'retry_after': reset_time
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(reset_time)
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = '0'
                response.headers['X-RateLimit-Reset'] = str(int(time.time()) + reset_time)
                return response
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# LOGIN ATTEMPT LIMITING - Previene brute force
# ============================================================

class LoginAttemptLimiter:
    """
    Limita intentos de login por IP y por username.
    Implementa lockout progresivo.
    """
    
    def __init__(self):
        self._attempts = defaultdict(list)  # {key: [(timestamp, success)]}
        self._lockouts = {}  # {key: unlock_time}
        self._lock = Lock()
        
    def _get_keys(self, ip, username):
        """Genera keys para IP y username."""
        return f"ip:{ip}", f"user:{username.lower()}" if username else None
    
    def record_attempt(self, ip, username, success):
        """Registra un intento de login."""
        ip_key, user_key = self._get_keys(ip, username)
        now = time.time()
        
        with self._lock:
            # Limpiar intentos viejos (últimos 15 minutos)
            cutoff = now - 900
            
            self._attempts[ip_key] = [(t, s) for t, s in self._attempts[ip_key] if t > cutoff]
            if user_key:
                self._attempts[user_key] = [(t, s) for t, s in self._attempts[user_key] if t > cutoff]
            
            # Registrar el intento
            self._attempts[ip_key].append((now, success))
            if user_key:
                self._attempts[user_key].append((now, success))
            
            # Si el intento falló, verificar si hay que aplicar lockout
            if not success:
                self._check_lockout(ip_key)
                if user_key:
                    self._check_lockout(user_key)
    
    def _check_lockout(self, key):
        """Verifica si se debe aplicar lockout basado en intentos fallidos."""
        failed = sum(1 for _, success in self._attempts[key] if not success)
        
        # Lockout progresivo
        if failed >= 10:
            # 10+ intentos: lockout de 30 minutos
            self._lockouts[key] = time.time() + 1800
        elif failed >= 5:
            # 5-9 intentos: lockout de 5 minutos
            self._lockouts[key] = time.time() + 300
        elif failed >= 3:
            # 3-4 intentos: lockout de 1 minuto
            self._lockouts[key] = time.time() + 60
    
    def is_locked(self, ip, username=None):
        """
        Verifica si el IP o username está bloqueado.
        
        Returns:
            tuple: (locked: bool, unlock_time: int or None)
        """
        ip_key, user_key = self._get_keys(ip, username)
        now = time.time()
        
        with self._lock:
            # Verificar lockout por IP
            if ip_key in self._lockouts:
                if now < self._lockouts[ip_key]:
                    return True, int(self._lockouts[ip_key] - now)
                else:
                    del self._lockouts[ip_key]
            
            # Verificar lockout por username
            if user_key and user_key in self._lockouts:
                if now < self._lockouts[user_key]:
                    return True, int(self._lockouts[user_key] - now)
                else:
                    del self._lockouts[user_key]
        
        return False, None
    
    def clear_on_success(self, ip, username):
        """Limpia los intentos fallidos tras un login exitoso."""
        ip_key, user_key = self._get_keys(ip, username)
        
        with self._lock:
            if ip_key in self._attempts:
                del self._attempts[ip_key]
            if ip_key in self._lockouts:
                del self._lockouts[ip_key]
            if user_key:
                if user_key in self._attempts:
                    del self._attempts[user_key]
                if user_key in self._lockouts:
                    del self._lockouts[user_key]


# Instancia global
_login_limiter = LoginAttemptLimiter()

def check_login_allowed(ip, username=None):
    """Verifica si se permite intentar login."""
    return _login_limiter.is_locked(ip, username)

def record_login_attempt(ip, username, success):
    """Registra un intento de login."""
    _login_limiter.record_attempt(ip, username, success)
    if success:
        _login_limiter.clear_on_success(ip, username)


# ============================================================
# SECURITY HEADERS - Previene XSS, clickjacking, etc.
# ============================================================

def add_security_headers(response):
    """
    Añade headers de seguridad a la respuesta.
    Llamar desde after_request.
    """
    # Prevenir clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Prevenir MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Habilitar XSS filter del navegador
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer policy - más permisivo para navegadores in-app (Instagram, Facebook, TikTok)
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    
    # Permissions policy (reemplaza Feature-Policy)
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # Cross-Origin headers para navegadores in-app de redes sociales
    response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    response.headers['Cross-Origin-Opener-Policy'] = 'unsafe-none'
    
    # Content Security Policy básica (ajustar según necesidades)
    # Permite scripts y estilos inline necesarios para la app
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://sdk.mercadopago.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https: blob: https://res.cloudinary.com; "
        "connect-src 'self' https://api.mercadopago.com https://api.cloudinary.com https://res.cloudinary.com; "
        "frame-src 'self' https://www.mercadopago.com https://www.mercadopago.cl; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Strict Transport Security (solo en producción con HTTPS)
    # El servidor ya debería estar en HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Cache control para contenido dinámico
    if 'Cache-Control' not in response.headers:
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        elif request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'  # 1 año para estáticos + immutable
        elif request.path.startswith('/menu/'):
            # Cache público de menús por 5 minutos para mejorar rendimiento móvil
            response.headers['Cache-Control'] = 'public, max-age=300, s-maxage=300'
    
    # Añadir headers de rate limit si están disponibles
    if hasattr(g, 'rate_limit_remaining'):
        response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
    
    return response


# ============================================================
# GZIP COMPRESSION - Reduce ancho de banda
# ============================================================

def gzip_response(response):
    """
    Comprime la respuesta con GZIP si el cliente lo acepta.
    Llamar desde after_request.
    """
    # No comprimir si ya está comprimido o es muy pequeño
    if (response.status_code < 200 or 
        response.status_code >= 300 or
        response.direct_passthrough or
        'gzip' not in request.accept_encodings or
        'Content-Encoding' in response.headers or
        len(response.get_data()) < 500):  # No comprimir respuestas < 500 bytes
        return response
    
    # Solo comprimir ciertos tipos de contenido
    content_type = response.content_type or ''
    compressible_types = ('text/', 'application/json', 'application/javascript', 'application/xml')
    if not any(ct in content_type for ct in compressible_types):
        return response
    
    try:
        data = response.get_data()
        
        # Comprimir con gzip
        buffer = io.BytesIO()
        with gzip.GzipFile(mode='wb', fileobj=buffer, compresslevel=6) as gz:
            gz.write(data)
        
        compressed = buffer.getvalue()
        
        # Solo usar si la compresión vale la pena (al menos 10% de reducción)
        if len(compressed) < len(data) * 0.9:
            response.set_data(compressed)
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = len(compressed)
            response.headers['Vary'] = 'Accept-Encoding'
    except Exception as e:
        logger.debug("GZIP compression failed: %s", e)
    
    return response


# ============================================================
# SIMPLE IN-MEMORY CACHE - Para menús públicos
# ============================================================

class SimpleCache:
    """
    Cache simple en memoria con TTL.
    Para menús públicos que no cambian frecuentemente.
    """
    
    def __init__(self, default_ttl=300, max_size=1000):
        self.default_ttl = default_ttl  # 5 minutos por defecto
        self.max_size = max_size
        self._cache = {}  # {key: (value, expire_time)}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key):
        """Obtiene un valor del cache."""
        with self._lock:
            if key in self._cache:
                value, expire_time = self._cache[key]
                if time.time() < expire_time:
                    self._hits += 1
                    return value
                else:
                    # Expirado, eliminar
                    del self._cache[key]
            self._misses += 1
            return None
    
    def set(self, key, value, ttl=None):
        """Guarda un valor en el cache."""
        ttl = ttl or self.default_ttl
        expire_time = time.time() + ttl
        
        with self._lock:
            # Limpiar si excedemos el tamaño máximo
            if len(self._cache) >= self.max_size:
                self._cleanup()
            
            self._cache[key] = (value, expire_time)
    
    def delete(self, key):
        """Elimina un valor del cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def invalidate_pattern(self, pattern):
        """Invalida todas las keys que contienen el patrón."""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)
    
    def _cleanup(self):
        """Limpia entradas expiradas y las más viejas si es necesario."""
        now = time.time()
        
        # Primero eliminar expirados
        expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for key in expired:
            del self._cache[key]
        
        # Si aún estamos llenos, eliminar los más viejos
        if len(self._cache) >= self.max_size:
            # Ordenar por tiempo de expiración y eliminar el 20% más viejo
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            to_remove = len(sorted_items) // 5
            for key, _ in sorted_items[:to_remove]:
                del self._cache[key]
    
    def clear(self):
        """Limpia todo el cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    @property
    def stats(self):
        """Retorna estadísticas del cache."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }


# Instancia global del cache
_cache = SimpleCache(default_ttl=300, max_size=500)


def cache_key(*args):
    """Genera una key de cache a partir de argumentos."""
    return hashlib.md5(':'.join(str(a) for a in args).encode()).hexdigest()


def cached(ttl=300, key_prefix=''):
    """
    Decorador para cachear el resultado de una función.
    
    Args:
        ttl: Tiempo de vida en segundos
        key_prefix: Prefijo para la key de cache
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Generar key de cache
            cache_key_str = f"{key_prefix}:{f.__name__}:{hash(str(args))}:{hash(str(sorted(kwargs.items())))}"
            
            # Intentar obtener del cache
            result = _cache.get(cache_key_str)
            if result is not None:
                return result
            
            # Ejecutar función y cachear resultado
            result = f(*args, **kwargs)
            _cache.set(cache_key_str, result, ttl)
            return result
        
        # Añadir método para invalidar el cache de esta función
        wrapper.invalidate = lambda: _cache.invalidate_pattern(f"{key_prefix}:{f.__name__}")
        return wrapper
    return decorator


def get_cache():
    """Retorna la instancia del cache."""
    return _cache


def invalidate_menu_cache(restaurante_id, url_slug=None):
    """
    Invalida el cache del menú de un restaurante específico.
    
    Args:
        restaurante_id: ID del restaurante (para logging)
        url_slug: URL slug del restaurante. Si no se proporciona, 
                  se invalidan todas las entradas que empiecen con 'menu:'
    """
    if url_slug:
        # Invalidar por url_slug específico
        key = f"menu:{url_slug}"
        _cache.delete(key)
        logger.debug("Invalidated cache for menu:%s (restaurant %s)", url_slug, restaurante_id)
        return 1
    else:
        # Invalidar todas las entradas de menú (fallback)
        pattern = "menu:"
        count = _cache.invalidate_pattern(pattern)
        logger.debug("Invalidated %d menu cache entries (restaurant %s)", count, restaurante_id)
        return count


def clear_all_menu_cache():
    """Limpia todo el cache de menús."""
    pattern = "menu:"
    count = _cache.invalidate_pattern(pattern)
    logger.info("Cleared all menu cache: %d entries removed", count)
    return count


# ============================================================
# INIT FUNCTION - Registra middleware con la app
# ============================================================

def init_security_middleware(app):
    """
    Inicializa todos los middleware de seguridad y performance.
    Llamar después de crear la app Flask.
    """
    
    @app.after_request
    def apply_security_and_compression(response):
        """Aplica headers de seguridad y compresión GZIP."""
        response = add_security_headers(response)
        
        # Aplicar GZIP siempre - importante para rendimiento móvil
        response = gzip_response(response)
        
        return response
    
    @app.before_request
    def apply_global_rate_limit():
        """Aplica rate limit global."""
        # Excluir health checks y estáticos
        if request.path in ('/healthz', '/api/health') or request.path.startswith('/static/'):
            return
        
        ip = get_client_ip()
        
        # Determinar tipo de límite
        if request.path.startswith('/api/') and request.method in ('POST', 'PUT', 'DELETE'):
            limit_type = 'api_write'
        elif request.path.startswith('/api/'):
            limit_type = 'api_read'
        elif request.path.startswith('/menu/'):
            limit_type = 'public'
        else:
            limit_type = 'default'
        
        limit, window = RATE_LIMITS.get(limit_type, RATE_LIMITS['default'])
        allowed, remaining, reset_time = _rate_limiter.is_allowed(ip, limit_type, limit, window)
        
        g.rate_limit_remaining = remaining
        
        if not allowed:
            logger.warning("Global rate limit exceeded for IP %s (type: %s)", ip, limit_type)
            return jsonify({
                'success': False,
                'error': 'Demasiadas solicitudes. Intenta de nuevo más tarde.',
                'retry_after': reset_time
            }), 429
    
    logger.info("Security and performance middleware initialized")
    logger.info("  - Rate limiting: enabled")
    logger.info("  - Security headers: enabled")
    logger.info("  - GZIP compression: enabled (production only)")
    logger.info("  - Response cache: enabled")
