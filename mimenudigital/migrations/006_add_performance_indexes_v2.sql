-- ============================================================
-- MIGRACIÓN 006: Índices de Performance Adicionales
-- ============================================================
-- Mejora el rendimiento de consultas frecuentes
-- ============================================================

-- Índice compuesto para búsqueda de platos por restaurante y categoría
-- Usado en: api_platos GET con filtro de categoría
CREATE INDEX IF NOT EXISTS idx_platos_rest_cat_activo 
ON platos(restaurante_id, categoria_id, activo);

-- Índice para ordenamiento de platos
CREATE INDEX IF NOT EXISTS idx_platos_orden 
ON platos(restaurante_id, orden, nombre);

-- Índice para estadísticas diarias (muy consultado en dashboard)
CREATE INDEX IF NOT EXISTS idx_estadisticas_rest_fecha 
ON estadisticas_diarias(restaurante_id, fecha DESC);

-- Índice para visitas recientes
CREATE INDEX IF NOT EXISTS idx_visitas_fecha 
ON visitas(restaurante_id, fecha DESC);

-- Índice para usuarios por restaurante (login y listados)
CREATE INDEX IF NOT EXISTS idx_usuarios_rest_activo 
ON usuarios_admin(restaurante_id, activo, username);

-- Índice para categorías ordenadas
CREATE INDEX IF NOT EXISTS idx_categorias_orden 
ON categorias(restaurante_id, activo, orden);

-- Índice para password_resets (recuperación de contraseña)
CREATE INDEX IF NOT EXISTS idx_password_resets_token 
ON password_resets(token, utilizado, fecha_expiracion);

-- Índice para suscripciones próximas a vencer (superadmin)
CREATE INDEX IF NOT EXISTS idx_restaurantes_vencimiento 
ON restaurantes(fecha_vencimiento, activo);

-- ============================================================
-- NOTA: Ejecutar estos índices en horario de bajo tráfico
-- ya que pueden bloquear la tabla temporalmente en tablas grandes
-- ============================================================
