-- ============================================================
-- Migración 008: Tabla de configuración global
-- ============================================================

CREATE TABLE IF NOT EXISTS configuracion_global (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT,
    descripcion VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar configuraciones iniciales
INSERT INTO configuracion_global (clave, valor, descripcion) VALUES
('mercadopago_activo', 'false', 'Habilitar/deshabilitar pagos con Mercado Pago'),
('deposito_activo', 'true', 'Habilitar/deshabilitar pagos por depósito bancario'),
('banco_nombre', 'Banco Estado', 'Nombre del banco para depósitos'),
('banco_tipo_cuenta', 'Cuenta Vista', 'Tipo de cuenta bancaria'),
('banco_numero', '12345678', 'Número de cuenta bancaria'),
('banco_rut', '12.345.678-9', 'RUT del titular de la cuenta'),
('banco_titular', 'Tu Nombre', 'Nombre del titular de la cuenta'),
('banco_email', 'tu@email.com', 'Email para confirmar depósitos'),
('precio_mensual', '14990', 'Precio mensual de suscripción en CLP')
ON DUPLICATE KEY UPDATE updated_at = NOW();
