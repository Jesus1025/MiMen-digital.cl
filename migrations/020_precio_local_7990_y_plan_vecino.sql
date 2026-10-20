-- ============================================================
-- MIGRACIÓN 020: nuevos precios (decisión de Jesús, 20 oct 2026)
--   Local (carta + QR)       $7.990/mes  (antes $5.990)
--   Tótem (5 tótems QR+NFC)  $9.990/mes  (sin cambio)
--   Local vecino             $5.990/mes  precio especial que se asigna a mano
--                            a locales puntuales (La Comarca). No se muestra
--                            en la página de venta (activo = 0).
-- Ejecutar UNA sola vez.
-- ============================================================

UPDATE planes SET precio_mensual = 7990 WHERE nombre = 'Local';

INSERT INTO planes (nombre, precio_mensual, max_platos, max_categorias, tiene_pdf, tiene_qr_personalizado,
                    tiene_estadisticas, activo, qr_totems, descripcion)
SELECT 'Local vecino', 5990, max_platos, max_categorias, tiene_pdf, tiene_qr_personalizado,
       tiene_estadisticas, 0, 0, 'Precio especial: carta digital y código QR para imprimir'
FROM planes WHERE nombre = 'Local'
  AND NOT EXISTS (SELECT 1 FROM planes WHERE nombre = 'Local vecino')
LIMIT 1;

UPDATE restaurantes SET plan_id = (SELECT id FROM planes WHERE nombre = 'Local vecino' LIMIT 1)
WHERE url_slug = 'lacomarca';

-- Valor de respaldo cuando un local no tiene plan con precio
UPDATE configuracion_global SET valor = '7990' WHERE clave = 'precio_mensual';

SELECT p.nombre, p.precio_mensual, p.activo, COUNT(r.id) AS locales
FROM planes p LEFT JOIN restaurantes r ON r.plan_id = p.id
GROUP BY p.id ORDER BY p.precio_mensual;
