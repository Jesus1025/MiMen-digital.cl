-- ============================================================
-- MIGRACIÓN: Crear tabla de etiquetas personalizadas por restaurante
-- Fecha: 2026-02-03
-- ============================================================

-- Tabla de etiquetas personalizadas
CREATE TABLE IF NOT EXISTS etiquetas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    color VARCHAR(7) NOT NULL DEFAULT '#34495e',
    emoji VARCHAR(10) DEFAULT NULL,
    orden INT DEFAULT 0,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY idx_restaurante_nombre (restaurante_id, nombre),
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_orden (orden),
    INDEX idx_activo (activo),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Aumentar el tamaño del campo etiquetas en platos para JSON
ALTER TABLE platos MODIFY COLUMN etiquetas TEXT;
