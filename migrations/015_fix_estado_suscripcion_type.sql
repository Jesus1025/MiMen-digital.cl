-- ============================================================
-- MIGRACIÓN: Corregir tipo de columna estado_suscripcion
-- Fecha: 2026-02-05
-- Descripción: Cambia estado_suscripcion de ENUM a VARCHAR(30) para permitir todos los estados
-- ============================================================

-- 1. Modificar la columna estado_suscripcion a VARCHAR(30)
-- Esto permite cualquier estado sin restricciones de ENUM
ALTER TABLE restaurantes 
MODIFY COLUMN estado_suscripcion VARCHAR(30) DEFAULT 'prueba';

-- 2. Verificar que no haya valores NULL
UPDATE restaurantes 
SET estado_suscripcion = 'prueba' 
WHERE estado_suscripcion IS NULL OR estado_suscripcion = '';

-- 3. Normalizar estados existentes a minúsculas
UPDATE restaurantes SET estado_suscripcion = LOWER(TRIM(estado_suscripcion));

-- 4. Verificar el resultado
SELECT estado_suscripcion, COUNT(*) as cantidad
FROM restaurantes
GROUP BY estado_suscripcion;
