-- ============================================================
-- MIGRACIÓN 016: Tablas faltantes para funcionamiento completo
-- Menú Digital SaaS - Divergent Studio
-- ============================================================

-- ============================================================
-- TABLA: PASSWORD_RESETS (Recuperación de contraseña)
-- ============================================================
CREATE TABLE IF NOT EXISTS password_resets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT NOT NULL,
    token VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    fecha_expiracion DATETIME NOT NULL,
    utilizado TINYINT(1) DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_token (token),
    INDEX idx_usuario (usuario_id),
    INDEX idx_email (email),
    INDEX idx_expiracion (fecha_expiracion),
    FOREIGN KEY (usuario_id) REFERENCES usuarios_admin(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: VISITAS (Tracking de visitas al menú)
-- ============================================================
CREATE TABLE IF NOT EXISTS visitas (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    referer VARCHAR(500),
    es_movil TINYINT(1) DEFAULT 0,
    es_qr TINYINT(1) DEFAULT 0,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_restaurante_fecha (restaurante_id, fecha),
    INDEX idx_fecha (fecha),
    INDEX idx_es_qr (es_qr),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: ESTADISTICAS_DIARIAS (Resumen diario de visitas)
-- ============================================================
CREATE TABLE IF NOT EXISTS estadisticas_diarias (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    fecha DATE NOT NULL,
    visitas INT DEFAULT 0,
    escaneos_qr INT DEFAULT 0,
    visitas_movil INT DEFAULT 0,
    visitas_desktop INT DEFAULT 0,
    platos_vistos INT DEFAULT 0,
    tiempo_promedio_segundos INT DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_restaurante_fecha (restaurante_id, fecha),
    INDEX idx_fecha (fecha),
    INDEX idx_restaurante (restaurante_id),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: ETIQUETAS (Etiquetas personalizadas por restaurante)
-- ============================================================
CREATE TABLE IF NOT EXISTS etiquetas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#34495e',
    emoji VARCHAR(10) DEFAULT '',
    orden INT DEFAULT 0,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_restaurante_nombre (restaurante_id, nombre),
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_orden (orden),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: IMAGENES_PENDIENTES (Cola de subidas a Cloudinary)
-- ============================================================
CREATE TABLE IF NOT EXISTS imagenes_pendientes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    plato_id INT NULL,
    local_path VARCHAR(500) NOT NULL,
    tipo VARCHAR(50) DEFAULT 'upload',
    cloudinary_url VARCHAR(500) NULL,
    cloudinary_public_id VARCHAR(255) NULL,
    attempts INT DEFAULT 0,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_plato (plato_id),
    INDEX idx_created (created_at),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE,
    FOREIGN KEY (plato_id) REFERENCES platos(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- INDICES ADICIONALES DE RENDIMIENTO
-- ============================================================

-- Índice para búsqueda rápida de tickets por estado
CREATE INDEX IF NOT EXISTS idx_tickets_estado_fecha 
ON tickets_soporte(estado, fecha_creacion DESC);

-- Índice para búsqueda de platos por restaurante y categoría
CREATE INDEX IF NOT EXISTS idx_platos_rest_cat_orden 
ON platos(restaurante_id, categoria_id, orden);

-- Índice para categorías por restaurante y orden
CREATE INDEX IF NOT EXISTS idx_categorias_rest_orden 
ON categorias(restaurante_id, orden);

-- ============================================================
-- PROCEDIMIENTO: Limpiar tokens expirados (ejecutar con cron)
-- ============================================================
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS cleanup_expired_tokens()
BEGIN
    DELETE FROM password_resets WHERE fecha_expiracion < NOW() OR utilizado = 1;
END //
DELIMITER ;

-- ============================================================
-- PROCEDIMIENTO: Agregar estadísticas diarias (ejecutar con cron)
-- ============================================================
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS aggregate_daily_stats()
BEGIN
    INSERT INTO estadisticas_diarias (restaurante_id, fecha, visitas, escaneos_qr, visitas_movil, visitas_desktop)
    SELECT 
        restaurante_id,
        DATE(fecha) as fecha,
        COUNT(*) as visitas,
        SUM(CASE WHEN es_qr = 1 THEN 1 ELSE 0 END) as escaneos_qr,
        SUM(CASE WHEN es_movil = 1 THEN 1 ELSE 0 END) as visitas_movil,
        SUM(CASE WHEN es_movil = 0 THEN 1 ELSE 0 END) as visitas_desktop
    FROM visitas
    WHERE DATE(fecha) = DATE(NOW() - INTERVAL 1 DAY)
    GROUP BY restaurante_id, DATE(fecha)
    ON DUPLICATE KEY UPDATE
        visitas = VALUES(visitas),
        escaneos_qr = VALUES(escaneos_qr),
        visitas_movil = VALUES(visitas_movil),
        visitas_desktop = VALUES(visitas_desktop);
END //
DELIMITER ;
