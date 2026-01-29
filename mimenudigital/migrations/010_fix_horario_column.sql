-- ============================================================
-- MIGRACIÓN 010: Cambiar columna horario a TEXT
-- El JSON de horarios puede exceder los 200 caracteres de VARCHAR
-- ============================================================

-- Cambiar el tipo de la columna horario de VARCHAR(200) a TEXT
ALTER TABLE restaurantes MODIFY COLUMN horario TEXT;

-- Verificación
-- SELECT column_name, data_type, character_maximum_length 
-- FROM information_schema.columns 
-- WHERE table_name = 'restaurantes' AND column_name = 'horario';
