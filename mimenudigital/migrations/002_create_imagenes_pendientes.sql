-- Migration: create imagenes_pendientes table to store pending image uploads
-- Run this in your MySQL database after taking a backup:

CREATE TABLE IF NOT EXISTS `imagenes_pendientes` (
  `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `restaurante_id` INT DEFAULT NULL,
  `plato_id` INT DEFAULT NULL,
  `local_path` VARCHAR(1024) DEFAULT NULL,
  `source_url` TEXT DEFAULT NULL,
  `attempts` INT DEFAULT 0,
  `max_attempts` INT DEFAULT 5,
  `status` ENUM('pending','processing','failed','uploaded') NOT NULL DEFAULT 'pending',
  `last_error` TEXT DEFAULT NULL,
  `public_id` VARCHAR(255) DEFAULT NULL,
  `url` TEXT DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `processed_at` DATETIME DEFAULT NULL,
  INDEX (`restaurante_id`),
  INDEX (`status`),
  INDEX (`attempts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
