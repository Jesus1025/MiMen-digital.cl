-- ============================================================
-- MIGRACIÓN 018: Página de presentación de cada local
-- Fecha: 2026-10-19
-- Cada local tiene, además de su carta (/menu/<slug>), una página de
-- presentación (/local/<slug>) que edita desde su panel.
-- Ejecutar UNA sola vez.
-- ============================================================

ALTER TABLE restaurantes ADD COLUMN portada_url VARCHAR(500) NULL;
ALTER TABLE restaurantes ADD COLUMN pagina_titulo VARCHAR(160) NULL;
ALTER TABLE restaurantes ADD COLUMN pagina_texto TEXT NULL;
ALTER TABLE restaurantes ADD COLUMN pagina_destacados TEXT NULL;   -- JSON: lista de frases cortas ("Terraza", "Delivery")
ALTER TABLE restaurantes ADD COLUMN galeria TEXT NULL;             -- JSON: lista de URLs de fotos (máximo 8)
ALTER TABLE restaurantes ADD COLUMN pagina_activa TINYINT(1) NOT NULL DEFAULT 1;
