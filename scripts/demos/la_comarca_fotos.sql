-- ============================================================
-- DEMO La Comarca: fotos de cada producto, logo, portada y galería.
-- Fotos reales del local (Instagram/Facebook) en /static/uploads/lacomarca/.
-- Lo que el local nunca fotografió (completos, chorrillanas, empanadas,
-- papas, salchipapas, nuggets, sopaipillas, bebidas) lleva foto de
-- referencia de Unsplash hasta que el dueño suba las suyas.
-- ============================================================

SET @r := (SELECT id FROM restaurantes WHERE url_slug = 'lacomarca');
SET @u := '/static/uploads/lacomarca/';
SET @q := '?w=1200&h=900&fit=crop&auto=format&q=75';

UPDATE restaurantes SET
  logo_url = CONCAT(@u, 'logo.jpg'),
  portada_url = CONCAT(@u, 'chacarero.jpg'),
  pagina_titulo = 'Sanguchería al paso en Quinta Normal desde 2019',
  galeria = CONCAT('["', @u, 'equipo.jpg","', @u, 'churrasco.jpg","', @u, 'hamburguesa_bacon.jpg","',
                   @u, 'pollo.jpg","', @u, 'gordita.jpg","', @u, 'ensalada.jpg"]')
WHERE id = @r;

-- Fotos reales
UPDATE platos SET imagen_url = CONCAT(@u, 'churrasco.jpg')
  WHERE restaurante_id = @r AND nombre IN ('Churrasco italiano', 'Churrasco luco', 'Mechada italiana', 'Mechada luco');
UPDATE platos SET imagen_url = CONCAT(@u, 'chacarero.jpg')
  WHERE restaurante_id = @r AND nombre IN ('Churrasco chacarero', 'Mechada chacarera');
UPDATE platos SET imagen_url = CONCAT(@u, 'hamburguesa_bacon.jpg')
  WHERE restaurante_id = @r AND nombre LIKE 'Hamburguesa %';
UPDATE platos SET imagen_url = CONCAT(@u, 'pollo.jpg')
  WHERE restaurante_id = @r AND nombre IN ('Pollo italiano', 'Pollo luco', 'Agrega a tu sánguche');
UPDATE platos SET imagen_url = CONCAT(@u, 'gordita.jpg')
  WHERE restaurante_id = @r AND nombre LIKE 'Gordita %';
UPDATE platos SET imagen_url = CONCAT(@u, 'ensalada.jpg')
  WHERE restaurante_id = @r AND nombre LIKE 'Ensalada %';
UPDATE platos SET imagen_url = CONCAT(@u, 'yogurt.jpg')
  WHERE restaurante_id = @r AND nombre = 'Yogurt con frutas';

-- Fotos de referencia (Unsplash)
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1627662168223-7df99068099a', @q)
  WHERE restaurante_id = @r AND nombre IN ('Promo 1', 'Nuggets de pollo (5)');
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1696935309723-207afc5a8228', @q)
  WHERE restaurante_id = @r AND nombre = 'Promo 2';
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1627054248949-21f77275a15f', @q)
  WHERE restaurante_id = @r AND nombre IN ('Promo 3', 'Completo');
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1678033391562-6ff8c834d1d5', @q)
  WHERE restaurante_id = @r AND nombre IN ('Italiano', 'Dinámico');
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1767065627047-e9251244c3ad', @q)
  WHERE restaurante_id = @r AND nombre = 'Chorrillana clásica';
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1684815495679-f6e6bc0634ec', @q)
  WHERE restaurante_id = @r AND nombre = 'Chorrillana vegetariana';
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1624128082323-beb6b8b508db', @q)
  WHERE restaurante_id = @r AND nombre LIKE 'Empanada %';
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1769254870299-338bfd99aabd', @q)
  WHERE restaurante_id = @r AND nombre LIKE 'Mini empanaditas%';
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1768215610440-fcb9631c7ee2', @q)
  WHERE restaurante_id = @r AND nombre LIKE 'Papas fritas%';
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1762284513031-3d7ad15562bc', @q)
  WHERE restaurante_id = @r AND nombre LIKE 'Salchipapas%';
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1759302307623-0ed463b8a9b9', @q)
  WHERE restaurante_id = @r AND nombre = 'Sopaipilla';
UPDATE platos SET imagen_url = CONCAT('https://images.unsplash.com/photo-1527960471264-932f39eb5846', @q)
  WHERE restaurante_id = @r AND nombre = 'Bebida en lata';

SELECT COUNT(*) total, SUM(imagen_url IS NOT NULL AND imagen_url <> '') con_foto
FROM platos WHERE restaurante_id = @r;

-- "Lo más pedido" solo con platos que tienen foto real del local
UPDATE platos SET es_popular = 0 WHERE restaurante_id = @r;
UPDATE platos SET es_popular = 1 WHERE restaurante_id = @r
  AND nombre IN ('Churrasco italiano', 'Hamburguesa bacon', 'Churrasco chacarero', 'Gordita italiana', 'Pollo italiano');
