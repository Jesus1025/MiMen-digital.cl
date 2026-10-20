"""Genera full_appetit.sql: la demo de Full Appetit (Av. Carrascal 4805, Quinta Normal) en MiMenú.
Carta y precios: los publicados en la ficha de Google Maps del local (sincronizada con su Uber Eats), 20 oct 2026.
Fotos: las del propio local en Google Maps (/static/uploads/fullappetit/); lo que no tiene foto lleva una de
referencia de Unsplash. Ejecutar: python full_appetit_generar.py > full_appetit.sql"""
import json

U = "/static/uploads/fullappetit/"
Q = "?w=1200&h=900&fit=crop&auto=format&q=75"
PAPAS = "https://images.unsplash.com/photo-1768215610440-fcb9631c7ee2" + Q
CRISPY = "https://images.unsplash.com/photo-1627662168223-7df99068099a" + Q
AROS = "https://images.unsplash.com/photo-1639024471283-03518883512d" + Q
VEGGIE = "https://images.unsplash.com/photo-1655279562015-047c3da9a271" + Q
CHAMPI = "https://images.unsplash.com/photo-1581771556488-da02d801966c" + Q
LATAS = "https://images.unsplash.com/photo-1761281137117-42da05306117" + Q

# (categoría, descripción de categoría, [(nombre, descripción, precio, foto, popular, vegetariano, picante)])
CARTA = [
    ("Promo churrasco 2x1", "Dos churrascos en pan frica", [
        ("Promo 2x1 Churrasco Italiano", "2 churrascos en pan frica con tomate, palta y mayo casera.", 9800, "churrasco_lechuga", 1, 0, 0),
        ("Promo 2x1 Churrasco Chacarero", "2 churrascos en pan frica con tomate, poroto verde, mayonesa casera y ají verde (opcional).", 9800, "chacarero_2x", 1, 0, 1),
        ("Promo 2x1 Churrasco Barros Luco", "2 churrascos en pan frica con queso fundido.", 9800, "barros_luco_2x", 0, 0, 0),
        ("Promo 2x1 Churrasco Dinámico", "2 churrascos en pan frica con palta, tomate, chucrut, americana y mayo casera.", 9800, "churrasco_lechuga", 0, 0, 0),
        ("Promo 2x1 Churrasco Completo", "2 churrascos en pan frica con tomate, chucrut, americana y mayo casera.", 9800, "completo_2x", 0, 0, 0),
    ]),
    ("Promo premium 2x1", "Dos churrascos de la casa con lo mejor", [
        ("Promo 2x1 Churrasco A Lo Pobre", "2 churrascos en pan frica con base de papas fritas, cebolla morada salteada y huevo frito.", 11800, "a_lo_pobre_2x", 1, 0, 0),
        ("Promo 2x1 Churrasco Full Appetit", "2 churrascos en pan frica con cebolla morada, tomate, queso fundido, lechuga y mayo casera.", 11800, "full_appetit_2x", 1, 0, 0),
        ("Promo 2x1 Churrasco Caribeña", "2 churrascos en pan frica con cebolla morada, lechuga, tomate, queso, papa hilo, tocino y mayo casera.", 11800, "caribena_2x", 0, 0, 0),
        ("Promo 2x1 Churrasco Full Bacon", "2 churrascos en pan frica con cebolla salteada, tocino, rúcula, tomate, queso fundido y mayonesa casera.", 11800, "caribena_2x", 0, 0, 0),
        ("Promo 2x1 Churrasco Rústico", "2 churrascos en pan frica con cebolla y champiñones salteados, queso fundido y mayonesa casera.", 11800, "rustico_2x", 0, 0, 0),
        ("Promo 2x1 Churrasco Champiñón Queso", "2 churrascos en pan frica con champiñones salteados y queso fundido.", 11800, "rustico_2x", 0, 0, 0),
        ("Promo 2x1 Churrasco Full Eiffel", "2 churrascos con champiñones salteados, choclo, queso fundido y mayonesa casera.", 11800, "rustico_2x", 0, 0, 0),
        ("Promo 2x1 Churrasco Turco", "2 churrascos en pan frica con carne, cebolla salteada, huevo y queso fundido.", 11800, "turco", 0, 0, 0),
        ("Promo 2x1 Churrascos Mongolianos", "2 churrascos en pan frica con cebollín salteado y queso fundido.", 11800, "turco", 0, 0, 0),
        ("Promo 2x1 Churrasco Full Pepo", "2 churrascos en pan frica con cebolla morada, pepinillo dill, queso fundido, tomate, lechuga y mayo casera.", 11800, "full_appetit_2x", 0, 0, 0),
        ("Promo 2x1 Churrasco Itaqueso", "2 churrascos en pan frica con tomate, palta, queso fundido y mayonesa casera.", 11800, "barros_luco_2x", 0, 0, 0),
    ]),
    ("Hamburguesas", "185 g de carne, con porción de papas fritas", [
        ("Terrible Burger + papas fritas", "185 g de carne, salsa BBQ, queso cheddar, cebolla crispy, tocino ahumado, jalapeños y queso gouda, con papas fritas.", 10500, "bacon_burger", 1, 0, 1),
        ("BBQ Burger + papas fritas", "185 g de carne, queso cheddar, aros de cebolla, tocino y salsa BBQ, con papas fritas.", 10500, "bacon_burger", 0, 0, 0),
        ("Full Appetit Burger + papas fritas", "185 g de carne, queso cheddar, lechuga, tomate, tocino, pepinillos, papa hilo, mayonesa casera y salsa Full Appetit, con papas fritas.", 10500, "bacon_burger", 0, 0, 0),
        ("Guacamole Burger + papas fritas", "185 g de carne, queso cheddar, lechuga, tocino, mayonesa casera y guacamole, con papas fritas.", 10500, "guacamole_burger", 0, 0, 0),
        ("Classic Burger + papas fritas", "185 g de carne, queso cheddar, lechuga, tomate, pepinillos, mayonesa casera y salsa Appetit, con papas fritas.", 10500, "bacon_burger", 0, 0, 0),
        ("Simple Burger + papas fritas", "185 g de carne con queso cheddar y salsa Appetit, con papas fritas.", 10500, "bacon_burger", 0, 0, 0),
    ]),
    ("As", "Carne en pan de completo", [
        ("As Italiano Grande", "Pan de completo grande con carne, tomate, palta y mayonesa casera.", 6000, "as_italiano_2", 0, 0, 0),
        ("As Dinámico Grande", "Pan de completo grande con carne, chucrut, americana, tomate, palta y mayonesa casera.", 6500, "as_italiano", 0, 0, 0),
        ("As Completo Grande", "Pan de completo grande con carne, chucrut, americana, tomate y mayonesa casera.", 6000, "as_italiano", 0, 0, 0),
        ("As Queso (Kayser) Grande", "Pan de completo grande con carne y queso fundido.", 6000, "as_queso", 0, 0, 0),
        ("As Italiano Jumbo", "Pan de completo jumbo con carne, tomate, palta y mayonesa casera.", 9500, "as_italiano_2", 0, 0, 0),
        ("As Dinámico Jumbo", "Pan de completo jumbo con carne, chucrut, americana, tomate, palta y mayonesa casera.", 9500, "as_italiano", 0, 0, 0),
        ("As Completo Jumbo", "Pan de completo jumbo con carne, chucrut, americana, tomate y mayonesa casera.", 9500, "as_italiano", 0, 0, 0),
        ("As Queso (Kayser) Jumbo", "Pan de completo jumbo con carne y queso fundido.", 9500, "as_queso", 0, 0, 0),
    ]),
    ("Vienesas", "Pequeña, grande o jumbo", [
        ("Vienesa Italiana Pequeña", "Vienesa, tomate, palta y mayo casera.", 3500, "vienesa_italiana", 0, 0, 0),
        ("Vienesa Completo Pequeña", "Vienesa, chucrut, americana, tomate y mayo casera.", 3500, "vienesa_dinamica", 0, 0, 0),
        ("Vienesa Dinámica Pequeña", "Vienesa, chucrut, americana, tomate, palta y mayonesa casera.", 3700, "vienesa_dinamica", 0, 0, 0),
        ("Vienesa Italiana Grande", "Vienesa, tomate, palta y mayonesa casera.", 4000, "vienesa_italiana", 0, 0, 0),
        ("Vienesa Completo Grande", "Vienesa, chucrut, americana, tomate y mayonesa casera.", 4000, "vienesa_dinamica", 0, 0, 0),
        ("Vienesa Dinámica Grande", "Vienesa, chucrut, americana, tomate, palta y mayonesa casera.", 4200, "vienesa_dinamica", 0, 0, 0),
        ("Vienesa Italiana Jumbo", "Vienesa, tomate, palta y mayonesa casera.", 4700, "vienesa_jumbo", 0, 0, 0),
        ("Vienesa Completo Jumbo", "Vienesa, chucrut, americana, tomate y mayonesa casera.", 4700, "vienesa_jumbo", 0, 0, 0),
        ("Vienesa Dinámica Jumbo", "Vienesa, chucrut, americana, tomate, palta y mayonesa casera.", 5000, "vienesa_jumbo", 0, 0, 0),
    ]),
    ("Chorrillanas", "Para compartir", [
        ("Chorrillana Clásica (2 personas)", "Papas fritas, salchichas, carne, cebolla morada salteada y huevos.", 18000, "chorrillana_huevos", 1, 0, 0),
        ("Chorrillana Champiñón Queso", "Papas fritas, salchichas, carne, champiñón, cebolla morada, queso fundido y huevos.", 16000, "chorrillana_queso", 0, 0, 0),
        ("Chorrillana Familiar", "Papas fritas, carne, cebolla frita, salchicha, champiñones, queso y huevos.", 26000, "chorrillana_sarten", 0, 0, 0),
    ]),
    ("Salchipapas", None, [
        ("Salchipapa Pequeña", "Salchicha y papas fritas, porción pequeña.", 3500, "salchipapas", 0, 0, 0),
        ("Salchipapa Grande", "Salchicha y papas fritas, porción grande.", 6500, "salchipapas", 0, 0, 0),
        ("Salchitalia", "Papas fritas, salchicha, tomate, palta y mayo casera.", 7200, "salchipapas", 0, 0, 0),
        ("Salchipapa Familiar", "Salchipapa tamaño familiar.", 11800, "salchipapas", 0, 0, 0),
    ]),
    ("Papas fritas", None, [
        ("Papas Fritas Pequeña", "Porción pequeña.", 2700, PAPAS, 0, 1, 0),
        ("Papas Fritas Mediana", "Porción mediana.", 4000, PAPAS, 0, 1, 0),
        ("Papas Fritas Grande", "Porción grande.", 6500, PAPAS, 0, 1, 0),
        ("Papas Fritas Familiar", "Tamaño familiar.", 11800, PAPAS, 0, 1, 0),
    ]),
    ("Pollo crispy", None, [
        ("Tutitos Crispy", "Siete tutitos de pollo apanado, con salsa BBQ.", 8500, CRISPY, 0, 0, 0),
        ("Combo Crispy Italiano", "Croqueta de pollo, tomate, palta y mayo casera, con porción de papas fritas.", 9000, CRISPY, 0, 0, 0),
        ("Aros de cebolla (12)", "12 aros de cebolla fritos.", 3900, AROS, 0, 1, 0),
    ]),
    ("Vegetarianos", None, [
        ("Frica Vegetariana", "Pan frica, champiñón, queso, tomate, cebolla morada, lechuga y mayo.", 5500, VEGGIE, 0, 1, 0),
        ("Champiñón Grande Italiano", "Champiñones salteados, tomate, palta y mayo.", 4000, CHAMPI, 0, 1, 0),
        ("Papapleto Grande", "Pan de completo grande con base de papas fritas.", 4000, PAPAS, 0, 1, 0),
        ("Chorrillana Vegetariana (2 personas)", "Papas fritas, champiñón, cebolla morada, cebollín, queso fundido, huevos, aceitunas y tomate.", 18000, "chorrillana_sarten", 0, 1, 0),
    ]),
    ("Bebidas", "Anota el sabor que quieres en tu pedido", [
        ("Bebida en lata 350 ml", "Coca-Cola, Coca-Cola sin azúcar, Pepsi, Pap o Bilz.", 1500, LATAS, 0, 0, 0),
        ("Bebida 2 litros", "Coca-Cola, Pepsi, Pap, Kem Piña o Limón Soda.", 5000, "bebida_2l", 0, 0, 0),
    ]),
    ("Agregados", None, [
        ("Vaso de mayo casera", "¡Agrégalo a tu pedido!", 2000, None, 0, 0, 0),
    ]),
]

HORARIO = {d: {"abierto": True, "apertura": "11:00", "cierre": "01:00"}
           for d in ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado")}
HORARIO["domingo"] = {"abierto": True, "apertura": "12:00", "cierre": "00:00"}


def s(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def foto(f):
    if not f:
        return None
    return f if f.startswith("http") else U + f + ".jpg"


print("""-- ============================================================
-- DEMO: Full Appetit (Av. Carrascal 4805, Quinta Normal)
-- Generado por full_appetit_generar.py. Carta y precios de su ficha de Google Maps
-- (sincronizada con Uber Eats, 20 oct 2026). Estado 'prueba' (30 días), plan Local vecino.
-- Ejecutar UNA sola vez. Para borrar: DELETE FROM restaurantes WHERE url_slug='fullappetit';
-- ============================================================
START TRANSACTION;""")
print(f"""INSERT INTO restaurantes
  (nombre, url_slug, tema, color_primario, color_secundario, slogan, descripcion, telefono, direccion, horario,
   instagram, whatsapp, logo_url, portada_url, mostrar_precios, mostrar_descripciones, mostrar_imagenes, moneda,
   plan_id, activo, estado_suscripcion, fecha_vencimiento, pagina_titulo, pagina_texto, pagina_destacados, galeria, pagina_activa)
SELECT 'Full Appetit', 'fullappetit', 'fuego', '#e3262f', '#141011', 'Juntos desde 2016 · Carrascal 4805',
  'Churrascos, hamburguesas, chorrillanas y completos en Quinta Normal. Terraza, delivery y retiro.',
  '+56 9 6285 7534', 'Av. Carrascal 4805, Quinta Normal', {s(json.dumps(HORARIO))},
  'full_appetit', '56962857534', {s(U + 'logo3.jpg')}, {s(U + 'chacarero_2x.jpg')}, 1, 1, 1, '$',
  (SELECT id FROM planes WHERE nombre = 'Local vecino' LIMIT 1), 1, 'prueba', DATE_ADD(CURDATE(), INTERVAL 30 DAY),
  'Churrascos, hamburguesas y chorrillanas en Quinta Normal',
  {s('Desde 2016 en Av. Carrascal 4805 preparamos churrascos en pan frica, hamburguesas de 185 g, chorrillanas para compartir y completos. Te esperamos de lunes a domingo con terraza, o pide por WhatsApp para retiro y delivery.')},
  {s(json.dumps(['Desde 2016', 'Terraza disponible', 'Abierto todos los días', 'Delivery y retiro', 'Pedidos por WhatsApp'], ensure_ascii=False))},
  {s(json.dumps([U + f + '.jpg' for f in ('full_appetit_2x', 'chacarero_2x', 'chorrillana_huevos', 'bacon_burger', 'a_lo_pobre_2x', 'salchipapas')]))},
  1
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM restaurantes WHERE url_slug = 'fullappetit');
SET @r := (SELECT id FROM restaurantes WHERE url_slug = 'fullappetit');""")
for orden, (cat, desc, platos) in enumerate(CARTA, 1):
    print(f"INSERT INTO categorias (restaurante_id, nombre, descripcion, orden) VALUES (@r, {s(cat)}, {s(desc)}, {orden});")
    print("SET @c := LAST_INSERT_ID();")
    for k, (nom, d, precio, f, pop, veg, pic) in enumerate(platos, 1):
        print(f"INSERT INTO platos (restaurante_id, categoria_id, nombre, descripcion, precio, imagen_url, es_popular, es_vegetariano, es_picante, orden) "
              f"VALUES (@r, @c, {s(nom)}, {s(d)}, {precio}, {s(foto(f))}, {pop}, {veg}, {pic}, {k});")
print("COMMIT;")
print("SELECT COUNT(DISTINCT c.id) categorias, COUNT(p.id) platos, SUM(p.imagen_url IS NOT NULL) con_foto FROM categorias c "
      "JOIN platos p ON p.categoria_id = c.id WHERE c.restaurante_id = @r;")
