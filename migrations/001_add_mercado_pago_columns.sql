-- ============================================================
-- MIGRACIÓN: Agregar columnas para Mercado Pago
-- MENU DIGITAL SAAS - 2025
-- ============================================================

-- Agregar columnas de pago a tabla restaurantes
ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS ultima_preferencia_pago VARCHAR(255);
ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS ultimo_pago_mercadopago VARCHAR(255);
ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS fecha_ultimo_pago TIMESTAMP NULL;
ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS fecha_ultimo_intento_pago TIMESTAMP NULL;

-- Crear tabla para registrar transacciones de pago
CREATE TABLE IF NOT EXISTS transacciones_pago (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    payment_id VARCHAR(255) NOT NULL UNIQUE,
    preferencia_id VARCHAR(255),
    monto DECIMAL(10, 2),
    moneda VARCHAR(10),
    estado VARCHAR(50),
    tipo_plan VARCHAR(50),
    descripcion TEXT,
    respuesta_json LONGTEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_payment_id (payment_id),
    INDEX idx_estado (estado),
    INDEX idx_fecha (fecha_creacion),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- VERIFICACIÓN
-- ============================================================
-- Verificar que las columnas fueron creadas
SELECT 'Migración completada. Columnas agregadas a restaurantes:' AS status;
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'restaurantes' AND COLUMN_NAME LIKE '%pago%';
