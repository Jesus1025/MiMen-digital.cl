-- Migration: 003_create_imagenes_pendientes.sql
-- Crea tabla para almacenar imágenes pendientes de subida a Cloudinary

CREATE TABLE IF NOT EXISTS imagenes_pendientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    restaurante_id INT NULL,
    plato_id INT NULL,
    tipo VARCHAR(50) DEFAULT 'plato',
    local_path VARCHAR(1000) NULL,
    source_url VARCHAR(1000) NULL,
    public_id_desired VARCHAR(255) NULL,
    public_id_result VARCHAR(255) NULL,
    attempts INT DEFAULT 0,
    status ENUM('pending','processing','failed','done') DEFAULT 'pending',
    last_error TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_attempt_at DATETIME NULL
);

-- Index para consultas rápidas
CREATE INDEX idx_imagenes_pendientes_status ON imagenes_pendientes (status);
CREATE INDEX idx_imagenes_pendientes_restaurante ON imagenes_pendientes (restaurante_id);
CREATE INDEX idx_imagenes_pendientes_plato ON imagenes_pendientes (plato_id);
