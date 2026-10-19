-- ============================================================
-- MIGRACIÓN 017: Planes Local y Tótem + tótems QR
-- Fecha: 2026-10-19
--   Local  $5.990/mes: carta digital + QR para que el local lo imprima.
--   Tótem  $9.990/mes: todo lo de Local + 5 tótems QR (cada uno con su propio código).
--   Tótem adicional: $3.000 cada uno (valor en configuracion_global).
-- Ejecutar UNA sola vez.
-- ============================================================

ALTER TABLE planes ADD COLUMN qr_totems INT NOT NULL DEFAULT 0;
ALTER TABLE planes ADD COLUMN descripcion VARCHAR(255) NULL;
ALTER TABLE restaurantes ADD COLUMN totems_extra INT NOT NULL DEFAULT 0;
ALTER TABLE visitas ADD COLUMN totem TINYINT UNSIGNED NULL;
ALTER TABLE visitas ADD INDEX idx_restaurante_totem (restaurante_id, totem);

-- Quitar planes duplicados que no usa ningún local (quedaban de init-db + migración 012)
DELETE p FROM planes p
JOIN planes q ON q.nombre = p.nombre AND q.id < p.id
WHERE NOT EXISTS (SELECT 1 FROM restaurantes r WHERE r.plan_id = p.id);

-- Premium pasa a ser el plan Tótem (los locales que lo tenían quedan en Tótem)
UPDATE planes SET nombre = 'Tótem', precio_mensual = 9990, qr_totems = 5,
    max_platos = 300, max_categorias = 50, tiene_pdf = 1, tiene_qr_personalizado = 1, tiene_estadisticas = 1,
    descripcion = 'Carta digital y 5 tótems QR para mesas, mostrador o vitrina', activo = 1
WHERE nombre = 'Premium';

-- Plan Local
INSERT INTO planes (nombre, precio_mensual, max_platos, max_categorias, tiene_pdf, tiene_qr_personalizado, tiene_estadisticas, activo, qr_totems, descripcion)
SELECT 'Local', 5990, 150, 30, 1, 0, 1, 1, 0, 'Carta digital y código QR para imprimir'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM planes WHERE nombre = 'Local');

-- El plan gratuito queda solo para cuentas antiguas o de prueba: no se ofrece
UPDATE planes SET activo = 0, descripcion = 'Solo cuentas de prueba' WHERE nombre IN ('Gratuito', 'Gratis');

INSERT INTO configuracion_global (clave, valor, descripcion) VALUES
('precio_totem_extra', '3000', 'Precio en CLP de cada tótem QR adicional (pago único)')
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

SELECT id, nombre, precio_mensual, qr_totems, activo FROM planes ORDER BY precio_mensual;
