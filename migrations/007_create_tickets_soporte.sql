-- ============================================================
-- Migración: Crear tabla de tickets de soporte
-- Fecha: 2026-01-22
-- ============================================================

CREATE TABLE IF NOT EXISTS tickets_soporte (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- Puede ser de un usuario registrado o anónimo
    usuario_id INT NULL,
    restaurante_id INT NULL,
    
    -- Datos del solicitante (para anónimos o para mostrar)
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    telefono VARCHAR(30) NULL,
    
    -- Contenido del ticket
    asunto VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    tipo ENUM('consulta', 'problema_tecnico', 'facturacion', 'otro') DEFAULT 'consulta',
    prioridad ENUM('baja', 'media', 'alta', 'urgente') DEFAULT 'media',
    
    -- Estado y gestión
    estado ENUM('abierto', 'en_proceso', 'respondido', 'cerrado') DEFAULT 'abierto',
    respuesta TEXT NULL,
    respondido_por INT NULL,
    fecha_respuesta TIMESTAMP NULL,
    
    -- Metadatos
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    pagina_origen VARCHAR(255) NULL,
    
    -- Timestamps
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Índices
    INDEX idx_usuario (usuario_id),
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_email (email),
    INDEX idx_estado (estado),
    INDEX idx_tipo (tipo),
    INDEX idx_prioridad (prioridad),
    INDEX idx_fecha (fecha_creacion),
    
    -- Foreign keys (opcionales, permiten tickets anónimos)
    FOREIGN KEY (usuario_id) REFERENCES usuarios_admin(id) ON DELETE SET NULL,
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE SET NULL,
    FOREIGN KEY (respondido_por) REFERENCES usuarios_admin(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Índice compuesto para listar tickets pendientes
CREATE INDEX idx_tickets_pendientes ON tickets_soporte (estado, prioridad DESC, fecha_creacion DESC);
