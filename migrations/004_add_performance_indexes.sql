-- ============================================================
-- MIGRACIÓN 004: Índices de Rendimiento para Producción
-- Creado: 2025
-- ============================================================

-- Índice compuesto para consulta frecuente: platos activos por restaurante y categoría
-- Usado en: ver_menu_publico(), api_platos()
CREATE INDEX IF NOT EXISTS idx_platos_rest_cat_activo 
ON platos (restaurante_id, categoria_id, activo);

-- Índice compuesto para ordenamiento de platos
CREATE INDEX IF NOT EXISTS idx_platos_rest_orden 
ON platos (restaurante_id, orden, nombre);

-- Índice compuesto para categorías activas ordenadas
CREATE INDEX IF NOT EXISTS idx_categorias_rest_activo_orden 
ON categorias (restaurante_id, activo, orden);

-- Índice para búsqueda de restaurante por slug (usado en cada vista de menú público)
-- Ya existe idx_url_slug pero lo hacemos más específico
CREATE INDEX IF NOT EXISTS idx_restaurantes_slug_activo 
ON restaurantes (url_slug, activo);

-- Índice para estadísticas: vistas por restaurante y fecha
CREATE INDEX IF NOT EXISTS idx_visitas_rest_fecha_movil 
ON visitas (restaurante_id, fecha, es_movil, es_qr);

-- Índice para auditoría por fecha (para limpieza periódica)
CREATE INDEX IF NOT EXISTS idx_audit_fecha_accion 
ON audit_log (fecha, accion);

-- Índice para suscripciones por estado y fecha
CREATE INDEX IF NOT EXISTS idx_suscripciones_estado_fecha 
ON suscripciones (estado, fecha_fin);

-- Índice para recuperación de contraseñas (limpieza de tokens expirados)
CREATE INDEX IF NOT EXISTS idx_password_resets_expiracion_usado 
ON password_resets (fecha_expiracion, utilizado);

-- Índice para imágenes pendientes (procesamiento batch)
CREATE INDEX IF NOT EXISTS idx_imagenes_pendientes_status_attempts 
ON imagenes_pendientes (status, attempts, created_at);

-- ============================================================
-- NOTA: Para ejecutar en MySQL/MariaDB, quitar "IF NOT EXISTS" 
-- y usar ALTER TABLE ADD INDEX en caso de que no soporte la sintaxis
-- ============================================================
