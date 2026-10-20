-- ============================================================
-- DEMO: La Comarca Sanguchería al paso (Quinta Normal)
-- Carta armada con la lista de precios que el local publicó en Facebook
-- (14 ago 2020) e Instagram @lacomarcasangucheria. Precios referenciales:
-- el local los actualiza desde su panel.
-- Queda en estado 'prueba' (30 días), plan Local, sin usuario admin.
-- Ejecutar UNA sola vez. Para borrar: DELETE FROM restaurantes WHERE url_slug='lacomarca';
-- ============================================================

START TRANSACTION;

INSERT INTO restaurantes
  (nombre, url_slug, tema, color_primario, color_secundario, slogan, descripcion,
   telefono, direccion, horario, instagram, facebook, whatsapp,
   mostrar_precios, mostrar_descripciones, mostrar_imagenes, moneda,
   plan_id, activo, estado_suscripcion, fecha_vencimiento,
   pagina_titulo, pagina_texto, pagina_destacados, pagina_activa)
SELECT
  'La Comarca', 'lacomarca', 'vintage', '#9b1c1f', '#c98a2b',
  'Sanguchería al paso desde 2019',
  'Churrascos, completos, hamburguesas, empanadas y chorrillanas hechos al momento en Quinta Normal.',
  '+56 9 4985 0860', 'Eduardo Charme 1504, Quinta Normal',
  '{"lunes":{"abierto":true,"apertura":"08:00","cierre":"15:00"},"martes":{"abierto":true,"apertura":"08:00","cierre":"15:00"},"miercoles":{"abierto":true,"apertura":"08:00","cierre":"15:00"},"jueves":{"abierto":true,"apertura":"08:00","cierre":"15:00"},"viernes":{"abierto":true,"apertura":"08:00","cierre":"15:00"},"sabado":{"abierto":false,"apertura":"","cierre":""},"domingo":{"abierto":false,"apertura":"","cierre":""}}',
  'lacomarcasangucheria', 'profile.php?id=100062956224673', '56949850860',
  1, 1, 1, '$',
  (SELECT id FROM planes WHERE nombre = 'Local' LIMIT 1), 1, 'prueba', DATE_ADD(CURDATE(), INTERVAL 30 DAY),
  'La Comarca, sanguchería al paso',
  'Desde 2019 en Eduardo Charme 1504 preparamos sánguches contundentes, completos y frituras para el desayuno y la colación del barrio. Pide por WhatsApp y te lo tenemos listo para retirar.',
  '["Desde 2019 en Quinta Normal","Pedidos por WhatsApp","Retiro en el local","Desayunos y colaciones","Opciones vegetarianas"]',
  1
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM restaurantes WHERE url_slug = 'lacomarca');

SET @r := (SELECT id FROM restaurantes WHERE url_slug = 'lacomarca');

INSERT INTO categorias (restaurante_id, nombre, descripcion, orden) VALUES
  (@r, 'Promociones',    'Combos para compartir o para la colación', 1),
  (@r, 'Churrascos',     'Carne de vacuno a la plancha en pan amasado', 2),
  (@r, 'Hamburguesas',   'Hamburguesa casera a la plancha', 3),
  (@r, 'Mechadas',       'Carne mechada jugosa, cocinada lento', 4),
  (@r, 'Pollo',          'Pechuga de pollo desmenuzada', 5),
  (@r, 'Gordas',         'Nuestro pan gordito relleno', 6),
  (@r, 'Completos',      'Vienesa en pan de completo', 7),
  (@r, 'Chorrillanas',   'Individual, alcanza hasta para 2 personas', 8),
  (@r, 'Empanadas',      'Fritas, doraditas y bien rellenas', 9),
  (@r, 'Para picar',     'Papas, salchipapas y algo más', 10),
  (@r, 'Ensaladas y yogurt', 'Opciones frescas', 11),
  (@r, 'Bebidas',        NULL, 12);

SET @promo := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Promociones');
SET @chu   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Churrascos');
SET @ham   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Hamburguesas');
SET @mec   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Mechadas');
SET @pol   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Pollo');
SET @gor   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Gordas');
SET @com   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Completos');
SET @cho   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Chorrillanas');
SET @emp   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Empanadas');
SET @pic   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Para picar');
SET @ens   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Ensaladas y yogurt');
SET @beb   := (SELECT id FROM categorias WHERE restaurante_id=@r AND nombre='Bebidas');

INSERT INTO platos (restaurante_id, categoria_id, nombre, descripcion, precio, es_vegetariano, es_picante, es_popular, orden) VALUES
  -- Promociones
  (@r, @promo, 'Promo 1', 'Papas fritas + 5 nuggets de pollo + 2 mini empanaditas de queso.', 2000, 0, 0, 1, 1),
  (@r, @promo, 'Promo 2', '2 italianos + papas fritas, o 4 nuggets, o 3 mini empanaditas de queso.', 3000, 0, 0, 1, 2),
  (@r, @promo, 'Promo 3', '2 completos + papas fritas, o 4 nuggets, o 3 mini empanaditas de queso.', 2600, 0, 0, 0, 3),
  (@r, @promo, 'Agrega a tu sánguche', 'A cualquier sánguche súmale papas fritas, o 4 nuggets, o 3 mini empanaditas de queso.', 600, 0, 0, 0, 4),
  -- Churrascos
  (@r, @chu, 'Churrasco italiano', 'Palta, tomate y mayonesa. De los más pedidos de la casa.', 3000, 0, 0, 1, 1),
  (@r, @chu, 'Churrasco luco', 'Con queso derretido.', 3000, 0, 0, 0, 2),
  (@r, @chu, 'Churrasco chacarero', 'Tomate, poroto verde, ají y mayonesa.', 3000, 0, 1, 0, 3),
  -- Hamburguesas
  (@r, @ham, 'Hamburguesa bacon', 'Queso cheddar, pepinillos, tocino y salsa barbecue.', 4000, 0, 0, 1, 1),
  (@r, @ham, 'Hamburguesa italiana', 'Palta, tomate y mayonesa.', 3500, 0, 0, 0, 2),
  (@r, @ham, 'Hamburguesa clásica', 'Lechuga, tomate y mayonesa.', 3200, 0, 0, 0, 3),
  -- Mechadas
  (@r, @mec, 'Mechada italiana', 'Palta, tomate y mayonesa.', 3000, 0, 0, 0, 1),
  (@r, @mec, 'Mechada luco', 'Con queso derretido.', 3000, 0, 0, 0, 2),
  (@r, @mec, 'Mechada chacarera', 'Tomate, poroto verde, ají y mayonesa.', 3000, 0, 1, 0, 3),
  -- Pollo
  (@r, @pol, 'Pollo italiano', 'Palta, tomate y mayonesa.', 2000, 0, 0, 0, 1),
  (@r, @pol, 'Pollo luco', 'Con queso derretido.', 2000, 0, 0, 0, 2),
  -- Gordas
  (@r, @gor, 'Gordita italiana', 'Palta, tomate y mayonesa. La favorita de nuestros regalones.', 1500, 0, 0, 1, 1),
  (@r, @gor, 'Gordita luco', 'Con queso derretido.', 1500, 0, 0, 0, 2),
  -- Completos
  (@r, @com, 'Italiano', 'Palta, tomate y mayonesa.', 1200, 0, 0, 1, 1),
  (@r, @com, 'Completo', 'Tomate y mayonesa.', 1000, 0, 0, 0, 2),
  (@r, @com, 'Dinámico', 'Salsa americana, tomate y mayonesa.', 1500, 0, 0, 0, 3),
  -- Chorrillanas
  (@r, @cho, 'Chorrillana clásica', 'Papas fritas, cebolla caramelizada, chorizo, carne y huevo frito.', 4500, 0, 0, 1, 1),
  (@r, @cho, 'Chorrillana vegetariana', 'Papas fritas, tomate, palta, huevo duro, aceitunas, pepinillos, queso y champiñones.', 5000, 1, 0, 0, 2),
  -- Empanadas
  (@r, @emp, 'Empanada de queso', NULL, 800, 1, 0, 0, 1),
  (@r, @emp, 'Empanada queso choclo', NULL, 1200, 1, 0, 0, 2),
  (@r, @emp, 'Empanada queso champiñón', NULL, 1300, 1, 0, 0, 3),
  (@r, @emp, 'Empanada queso pollo', NULL, 1400, 0, 0, 0, 4),
  (@r, @emp, 'Empanada queso camarón', NULL, 1500, 0, 0, 0, 5),
  (@r, @emp, 'Empanada queso mechada', NULL, 1600, 0, 0, 0, 6),
  (@r, @emp, 'Mini empanaditas de queso (4)', 'Cuatro mini empanaditas fritas de queso.', 1000, 1, 0, 0, 7),
  -- Para picar
  (@r, @pic, 'Papas fritas mediana', NULL, 1000, 1, 0, 0, 1),
  (@r, @pic, 'Papas fritas grande', NULL, 2000, 1, 0, 0, 2),
  (@r, @pic, 'Salchipapas mediana', NULL, 1500, 0, 0, 0, 3),
  (@r, @pic, 'Salchipapas grande', NULL, 2500, 0, 0, 0, 4),
  (@r, @pic, 'Nuggets de pollo (5)', NULL, 1000, 0, 0, 0, 5),
  (@r, @pic, 'Sopaipilla', 'Precio por unidad.', 200, 1, 0, 0, 6),
  -- Ensaladas y yogurt
  (@r, @ens, 'Ensalada surtida con carne', 'Ensalada surtida con proteína de carne.', 3300, 0, 0, 0, 1),
  (@r, @ens, 'Ensalada surtida con pollo, atún o champiñón', 'Elige tu proteína.', 3000, 0, 0, 0, 2),
  (@r, @ens, 'Yogurt con frutas', 'Yogurt con frutilla, arándanos, plátano y avena.', 1200, 1, 0, 0, 3),
  -- Bebidas
  (@r, @beb, 'Bebida en lata', NULL, 800, 0, 0, 0, 1);

COMMIT;

SELECT r.id, r.url_slug, COUNT(DISTINCT c.id) categorias, COUNT(p.id) platos
FROM restaurantes r
LEFT JOIN categorias c ON c.restaurante_id = r.id
LEFT JOIN platos p ON p.categoria_id = c.id
WHERE r.url_slug = 'lacomarca' GROUP BY r.id;
