-- Migration: 002_add_imagen_public_id.sql
-- Añade columna imagen_public_id a la tabla platos para almacenar public_id de Cloudinary

ALTER TABLE platos
ADD COLUMN imagen_public_id VARCHAR(255) NULL;

-- Opcional: crear índice para búsquedas rápidas por public_id (no estrictamente necesario)
CREATE INDEX IF NOT EXISTS idx_platos_imagen_public_id ON platos (imagen_public_id);
