-- ============================================================
-- MIGRACIÓN: Simplificar planes a solo 2 (Gratuito y Premium)
-- Fecha: 2026-01-29
-- ============================================================

-- Paso 1: Actualizar el plan "Gratis" o "Básico" a "Gratuito"
UPDATE planes SET nombre = 'Gratuito', precio_mensual = 0 WHERE nombre IN ('Gratis', 'Básico') OR precio_mensual = 0;

-- Paso 2: Actualizar el plan "Premium" con el precio correcto
UPDATE planes SET nombre = 'Premium', precio_mensual = 14990 WHERE nombre = 'Premium' OR precio_mensual > 10000;

-- Paso 3: Eliminar planes intermedios si existen (mantener solo 2)
-- Primero mover los restaurantes del plan "Básico" al plan "Premium" si existe
UPDATE restaurantes r
SET r.plan_id = (SELECT id FROM planes WHERE nombre = 'Premium' LIMIT 1)
WHERE r.plan_id IN (SELECT id FROM planes WHERE nombre NOT IN ('Gratuito', 'Premium'));

-- Ahora eliminar los planes que no sean Gratuito o Premium
DELETE FROM planes WHERE nombre NOT IN ('Gratuito', 'Premium');

-- Paso 4: Asegurar que existan los 2 planes
INSERT IGNORE INTO planes (nombre, precio_mensual, max_platos, max_categorias, tiene_pdf, tiene_qr_personalizado, tiene_estadisticas, activo) 
VALUES ('Gratuito', 0, 20, 5, 1, 0, 0, 1);

INSERT IGNORE INTO planes (nombre, precio_mensual, max_platos, max_categorias, tiene_pdf, tiene_qr_personalizado, tiene_estadisticas, activo) 
VALUES ('Premium', 14990, 200, 50, 1, 1, 1, 1);

-- Verificación final
SELECT id, nombre, precio_mensual, activo FROM planes ORDER BY precio_mensual;
