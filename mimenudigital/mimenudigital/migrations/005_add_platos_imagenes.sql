-- ============================================================
-- MIGRACIÓN 005: Tabla para Múltiples Imágenes por Plato
-- ============================================================
-- Permite asociar múltiples imágenes a un mismo plato
-- para mostrar un carrusel/galería en el menú público
-- ============================================================

CREATE TABLE IF NOT EXISTS platos_imagenes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    plato_id INT NOT NULL,
    restaurante_id INT NOT NULL,
    imagen_url VARCHAR(500) NOT NULL,
    imagen_public_id VARCHAR(255),
    orden INT DEFAULT 0,
    es_principal TINYINT(1) DEFAULT 0,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_plato (plato_id),
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_orden (plato_id, orden),
    INDEX idx_principal (plato_id, es_principal),
    FOREIGN KEY (plato_id) REFERENCES platos(id) ON DELETE CASCADE,
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Migrar imágenes existentes de la tabla platos a la nueva tabla
-- (solo ejecutar si hay datos en platos con imagen_url)
INSERT INTO platos_imagenes (plato_id, restaurante_id, imagen_url, imagen_public_id, orden, es_principal)
SELECT id, restaurante_id, imagen_url, imagen_public_id, 0, 1
FROM platos 
WHERE imagen_url IS NOT NULL AND imagen_url != '';

-- ============================================================
-- NOTA: Después de verificar que la migración funcionó,
-- puedes considerar quitar imagen_url e imagen_public_id de platos
-- pero NO es necesario hacerlo inmediatamente.
-- El código será compatible con ambos esquemas.
-- ============================================================
