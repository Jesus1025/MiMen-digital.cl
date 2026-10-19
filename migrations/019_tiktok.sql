-- ============================================================
-- MIGRACIÓN 019: TikTok del local (opcional)
-- Ejecutar UNA sola vez.
-- ============================================================

ALTER TABLE restaurantes ADD COLUMN tiktok VARCHAR(150) NULL;
