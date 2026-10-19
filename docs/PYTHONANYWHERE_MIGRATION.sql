-- ============================================================
-- SCRIPT SQL PARA PYTHONANYWHERE
-- Menu Digital - Actualizaciones de Base de Datos
-- Fecha: Diciembre 2025
-- ============================================================
-- INSTRUCCIONES:
-- 1. Copiar todo el contenido de este archivo
-- 2. Ir a PythonAnywhere → Databases → MySQL console
-- 3. Seleccionar la base de datos: MiMenudigital$menu_digital
-- 4. Pegar y ejecutar todo el código
-- ============================================================

USE `MiMenudigital$menu_digital`;

-- ============================================================
-- PASO 1: AGREGAR COLUMNAS DE PAGO A RESTAURANTES
-- ============================================================

-- Verificar y agregar columnas si no existen
ALTER TABLE restaurantes 
ADD COLUMN IF NOT EXISTS ultima_preferencia_pago VARCHAR(255) COMMENT 'ID de última preferencia de Mercado Pago';

ALTER TABLE restaurantes 
ADD COLUMN IF NOT EXISTS ultimo_pago_mercadopago VARCHAR(255) COMMENT 'ID del último pago en Mercado Pago';

ALTER TABLE restaurantes 
ADD COLUMN IF NOT EXISTS fecha_ultimo_pago TIMESTAMP NULL COMMENT 'Fecha del último pago procesado';

ALTER TABLE restaurantes 
ADD COLUMN IF NOT EXISTS fecha_ultimo_intento_pago TIMESTAMP NULL COMMENT 'Fecha del último intento de pago';

-- Agregar índices para optimizar búsquedas
ALTER TABLE restaurantes 
ADD INDEX IF NOT EXISTS idx_ultima_preferencia (ultima_preferencia_pago);

ALTER TABLE restaurantes 
ADD INDEX IF NOT EXISTS idx_ultimo_pago (ultimo_pago_mercadopago);

ALTER TABLE restaurantes 
ADD INDEX IF NOT EXISTS idx_fecha_pago (fecha_ultimo_pago);

-- ============================================================
-- PASO 2: CREAR TABLA DE TRANSACCIONES DE PAGO
-- ============================================================

CREATE TABLE IF NOT EXISTS transacciones_pago (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID único de transacción',
    
    restaurante_id INT NOT NULL COMMENT 'Restaurante que realizó el pago',
    
    payment_id VARCHAR(255) NOT NULL UNIQUE COMMENT 'ID de pago en Mercado Pago',
    
    preferencia_id VARCHAR(255) COMMENT 'ID de preferencia en Mercado Pago',
    
    monto DECIMAL(10, 2) COMMENT 'Monto del pago',
    
    moneda VARCHAR(10) COMMENT 'Moneda (CLP, ARS, etc)',
    
    estado VARCHAR(50) COMMENT 'Estado: approved, pending, rejected, cancelled',
    
    tipo_plan VARCHAR(50) COMMENT 'Tipo de plan: mensual, anual',
    
    descripcion TEXT COMMENT 'Descripción del pago/plan',
    
    respuesta_json LONGTEXT COMMENT 'Respuesta JSON completa de Mercado Pago',
    
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación del registro',
    
    fecha_procesamiento TIMESTAMP NULL COMMENT 'Fecha en que se procesó el pago',
    
    -- Índices para optimizar búsquedas
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_payment_id (payment_id),
    INDEX idx_estado (estado),
    INDEX idx_fecha (fecha_creacion),
    INDEX idx_fecha_procesamiento (fecha_procesamiento),
    
    -- Foreign key
    CONSTRAINT fk_transacciones_restaurante 
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Registro de todas las transacciones de pago en Mercado Pago';

-- ============================================================
-- PASO 3: CREAR TABLA DE NOTIFICACIONES (OPCIONAL)
-- ============================================================

CREATE TABLE IF NOT EXISTS notificaciones (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID único de notificación',
    
    restaurante_id INT NOT NULL COMMENT 'Restaurante asociado',
    
    tipo VARCHAR(50) NOT NULL COMMENT 'Tipo: pago, suscripcion, aviso, etc',
    
    titulo VARCHAR(255) NOT NULL COMMENT 'Título de la notificación',
    
    mensaje TEXT NOT NULL COMMENT 'Mensaje de la notificación',
    
    icono VARCHAR(50) COMMENT 'Icono (Font Awesome): check-circle, warning, etc',
    
    color VARCHAR(20) COMMENT 'Color: success, warning, danger, info',
    
    leida TINYINT(1) DEFAULT 0 COMMENT '1 si fue leída, 0 si no',
    
    url_accion VARCHAR(500) COMMENT 'URL a la que dirige la notificación',
    
    datos_json JSON COMMENT 'Datos adicionales en JSON',
    
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación',
    
    fecha_lectura TIMESTAMP NULL COMMENT 'Fecha en que fue leída',
    
    -- Índices
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_tipo (tipo),
    INDEX idx_leida (leida),
    INDEX idx_fecha (fecha_creacion),
    
    -- Foreign key
    CONSTRAINT fk_notificaciones_restaurante 
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Sistema de notificaciones para restaurantes';

-- ============================================================
-- PASO 4: VERIFICAR TABLAS EXISTENTES
-- ============================================================

-- Ver estructura de transacciones_pago
DESCRIBE transacciones_pago;

-- Ver estructura de notificaciones
DESCRIBE notificaciones;

-- Ver columnas agregadas a restaurantes
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'restaurantes' 
AND COLUMN_NAME IN ('ultima_preferencia_pago', 'ultimo_pago_mercadopago', 'fecha_ultimo_pago', 'fecha_ultimo_intento_pago')
ORDER BY ORDINAL_POSITION;

-- ============================================================
-- PASO 5: INSERTS DE EJEMPLO (OPCIONAL)
-- ============================================================

-- Insertar un registro de ejemplo de transacción
-- INSERT INTO transacciones_pago (
--     restaurante_id, 
--     payment_id, 
--     preferencia_id, 
--     monto, 
--     moneda, 
--     estado, 
--     tipo_plan, 
--     descripcion, 
--     respuesta_json
-- ) VALUES (
--     1,
--     'test_payment_123',
--     'test_preferencia_123',
--     9.99,
--     'CLP',
--     'approved',
--     'mensual',
--     'Suscripción Mensual - Menú Digital',
--     '{}'
-- );

-- ============================================================
-- PASO 6: VALIDACIÓN FINAL
-- ============================================================

-- Contar tablas creadas
SELECT COUNT(*) as total_tablas FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'MiMenudigital$menu_digital';

-- Confirmar migración completada
SELECT 'Migración completada exitosamente!' as status;
SELECT NOW() as timestamp;

-- ============================================================
-- FIN DEL SCRIPT
-- ============================================================
