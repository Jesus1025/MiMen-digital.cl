-- ============================================================
-- MIGRACIÓN 006: Índices de Performance Adicionales
-- ============================================================
-- Mejora el rendimiento de consultas frecuentes
-- Compatible con MySQL 5.7+
-- ============================================================

-- Índice compuesto para búsqueda de platos por restaurante y categoría
-- DROP INDEX si existe, luego crear (ignorar errores si no existe)
DROP INDEX idx_platos_rest_cat_activo ON platos;
CREATE INDEX idx_platos_rest_cat_activo ON platos(restaurante_id, categoria_id, activo);

-- Índice para ordenamiento de platos
DROP INDEX idx_platos_orden ON platos;
CREATE INDEX idx_platos_orden ON platos(restaurante_id, orden, nombre(50));

-- Índice para estadísticas diarias (muy consultado en dashboard)
DROP INDEX idx_estadisticas_rest_fecha ON estadisticas_diarias;
CREATE INDEX idx_estadisticas_rest_fecha ON estadisticas_diarias(restaurante_id, fecha);

-- Índice para visitas recientes
DROP INDEX idx_visitas_fecha ON visitas;
CREATE INDEX idx_visitas_fecha ON visitas(restaurante_id, fecha);

-- Índice para usuarios por restaurante (login y listados)
DROP INDEX idx_usuarios_rest_activo ON usuarios_admin;
CREATE INDEX idx_usuarios_rest_activo ON usuarios_admin(restaurante_id, activo, username);

-- Índice para categorías ordenadas
DROP INDEX idx_categorias_orden ON categorias;
CREATE INDEX idx_categorias_orden ON categorias(restaurante_id, activo, orden);

-- Índice para password_resets (recuperación de contraseña)
DROP INDEX idx_password_resets_token ON password_resets;
CREATE INDEX idx_password_resets_token ON password_resets(token, utilizado);

-- Índice para suscripciones próximas a vencer (superadmin)
DROP INDEX idx_restaurantes_vencimiento ON restaurantes;
CREATE INDEX idx_restaurantes_vencimiento ON restaurantes(fecha_vencimiento, activo);

-- ============================================================
-- NOTA: Los DROP INDEX pueden dar error si el índice no existe,
-- eso está bien, simplemente continúa con el siguiente.
-- ============================================================
