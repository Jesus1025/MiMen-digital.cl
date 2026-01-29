-- ============================================================
-- MIGRACIÓN: Corregir estados de suscripción
-- Fecha: 2026-01-29
-- Descripción: Corrige los estados de suscripción que no coinciden con la fecha de vencimiento
-- ============================================================

-- 1. Corregir restaurantes con fecha válida (futura) pero estado 'vencida'
UPDATE restaurantes 
SET estado_suscripcion = 'activa',
    fecha_actualizacion = NOW()
WHERE fecha_vencimiento >= CURDATE() 
AND estado_suscripcion = 'vencida';

-- 2. Corregir restaurantes con fecha vencida pero estado 'activa' o 'prueba'
UPDATE restaurantes 
SET estado_suscripcion = 'vencida',
    fecha_actualizacion = NOW()
WHERE fecha_vencimiento < CURDATE() 
AND estado_suscripcion IN ('activa', 'prueba');

-- 3. Verificar el resultado
SELECT id, nombre, estado_suscripcion, fecha_vencimiento,
       CASE 
           WHEN fecha_vencimiento >= CURDATE() THEN 'VÁLIDA'
           ELSE 'VENCIDA'
       END as fecha_estado,
       DATEDIFF(fecha_vencimiento, CURDATE()) as dias_restantes
FROM restaurantes
ORDER BY fecha_vencimiento DESC;
