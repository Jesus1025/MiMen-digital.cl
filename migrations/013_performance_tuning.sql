-- ============================================================
-- MIGRACIÓN 013: Optimización de Performance Final
-- ============================================================
-- Fecha: Febrero 2026
-- Propósito: Agregar índices faltantes y optimizar queries críticas
-- ============================================================

DELIMITER //

-- Procedimiento helper para crear índice si no existe
DROP PROCEDURE IF EXISTS create_index_if_not_exists//
CREATE PROCEDURE create_index_if_not_exists(
    IN p_table VARCHAR(64),
    IN p_index VARCHAR(64),
    IN p_columns VARCHAR(255)
)
BEGIN
    DECLARE index_exists INT DEFAULT 0;
    
    SELECT COUNT(*) INTO index_exists
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
    AND table_name = p_table
    AND index_name = p_index;
    
    IF index_exists = 0 THEN
        SET @sql = CONCAT('CREATE INDEX ', p_index, ' ON ', p_table, '(', p_columns, ')');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SELECT CONCAT('Created index: ', p_index, ' on ', p_table) as result;
    ELSE
        SELECT CONCAT('Index already exists: ', p_index, ' on ', p_table) as result;
    END IF;
END//

DELIMITER ;

-- ============================================================
-- ÍNDICES PARA QUERIES CRÍTICAS
-- ============================================================

-- 1. Índice para la query combinada del dashboard (subqueries)
CALL create_index_if_not_exists('estadisticas_diarias', 'idx_stats_rest_fecha_visitas', 'restaurante_id, fecha, visitas, escaneos_qr');

-- 2. Índice para la tabla platos_imagenes (galería de imágenes)
CALL create_index_if_not_exists('platos_imagenes', 'idx_platos_img_plato_activo', 'plato_id, activo, es_principal');

-- 3. Índice para búsqueda de tickets por estado
CALL create_index_if_not_exists('tickets_soporte', 'idx_tickets_estado_fecha', 'estado, fecha_creacion');

-- 4. Índice para visitas por fecha (limpieza de datos viejos)
CALL create_index_if_not_exists('visitas', 'idx_visitas_fecha_sola', 'fecha');

-- 5. Índice para restaurantes por fecha de vencimiento (alertas de suscripción)
CALL create_index_if_not_exists('restaurantes', 'idx_rest_vencimiento_estado', 'fecha_vencimiento, estado_suscripcion, activo');

-- 6. Índice para usuarios por restaurante y activo (login)
CALL create_index_if_not_exists('usuarios_admin', 'idx_usuarios_email_activo', 'email, activo');

-- Limpiar procedimiento temporal
DROP PROCEDURE IF EXISTS create_index_if_not_exists;

-- ============================================================
-- OPTIMIZACIONES DE TABLA (solo para MyISAM, ignorar en InnoDB)
-- ============================================================

-- Analizar tablas para actualizar estadísticas del optimizador
ANALYZE TABLE platos;
ANALYZE TABLE categorias;
ANALYZE TABLE restaurantes;
ANALYZE TABLE estadisticas_diarias;
ANALYZE TABLE visitas;

-- ============================================================
-- MIGRACIÓN COMPLETADA
-- ============================================================
SELECT 'Migration 013 completed successfully' as status;
