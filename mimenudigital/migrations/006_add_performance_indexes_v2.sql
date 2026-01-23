-- ============================================================
-- MIGRACIÓN 006: Índices de Performance Adicionales
-- ============================================================
-- Mejora el rendimiento de consultas frecuentes
-- Compatible con MySQL 5.7+ / PythonAnywhere
-- ============================================================

-- Nota: Usamos procedimiento para evitar errores si el índice ya existe

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
    END IF;
END//

DELIMITER ;

-- Crear índices usando el procedimiento
CALL create_index_if_not_exists('platos', 'idx_platos_rest_cat_activo', 'restaurante_id, categoria_id, activo');
CALL create_index_if_not_exists('platos', 'idx_platos_orden', 'restaurante_id, orden');
CALL create_index_if_not_exists('estadisticas_diarias', 'idx_estadisticas_rest_fecha', 'restaurante_id, fecha');
CALL create_index_if_not_exists('visitas', 'idx_visitas_fecha', 'restaurante_id, fecha');
CALL create_index_if_not_exists('usuarios_admin', 'idx_usuarios_rest_activo', 'restaurante_id, activo');
CALL create_index_if_not_exists('categorias', 'idx_categorias_orden', 'restaurante_id, activo, orden');
CALL create_index_if_not_exists('password_resets', 'idx_password_resets_token', 'token, utilizado');
CALL create_index_if_not_exists('restaurantes', 'idx_restaurantes_vencimiento', 'fecha_vencimiento, activo');

-- Limpiar procedimiento temporal
DROP PROCEDURE IF EXISTS create_index_if_not_exists;

-- ============================================================
-- MIGRACIÓN COMPLETADA
-- ============================================================
