-- ============================================================
-- MENU DIGITAL SAAS - SCHEMA MySQL
-- Divergent Studio - 2025
-- ============================================================

-- Crear base de datos (ejecutar solo si tienes permisos)
-- CREATE DATABASE IF NOT EXISTS menu_digital CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE menu_digital;

-- ============================================================
-- TABLA: PLANES DE SUSCRIPCIÓN
-- ============================================================
CREATE TABLE IF NOT EXISTS planes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL,
    precio_mensual DECIMAL(10,2) DEFAULT 0,
    max_platos INT DEFAULT 50,
    max_categorias INT DEFAULT 10,
    tiene_pdf TINYINT(1) DEFAULT 1,
    tiene_qr_personalizado TINYINT(1) DEFAULT 0,
    tiene_estadisticas TINYINT(1) DEFAULT 1,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar planes por defecto
INSERT INTO planes (nombre, precio_mensual, max_platos, max_categorias, tiene_pdf, tiene_qr_personalizado, tiene_estadisticas) VALUES
('Gratis', 0, 20, 5, 1, 0, 0),
('Básico', 9990, 50, 10, 1, 0, 1),
('Premium', 19990, 200, 50, 1, 1, 1);

-- ============================================================
-- TABLA: RESTAURANTES
-- ============================================================
CREATE TABLE IF NOT EXISTS restaurantes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(200) NOT NULL,
    rut VARCHAR(20),
    url_slug VARCHAR(100) UNIQUE NOT NULL,
    logo_url VARCHAR(500),
    tema VARCHAR(50) DEFAULT 'elegante',
    color_primario VARCHAR(7) DEFAULT '#c0392b',
    color_secundario VARCHAR(7) DEFAULT '#2c3e50',
    descripcion TEXT,
    slogan VARCHAR(255),
    telefono VARCHAR(20),
    email VARCHAR(100),
    direccion VARCHAR(300),
    horario VARCHAR(200),
    instagram VARCHAR(100),
    facebook VARCHAR(100),
    whatsapp VARCHAR(20),
    mostrar_precios TINYINT(1) DEFAULT 1,
    mostrar_descripciones TINYINT(1) DEFAULT 1,
    mostrar_imagenes TINYINT(1) DEFAULT 1,
    moneda VARCHAR(10) DEFAULT '$',
    plan_id INT DEFAULT 1,
    activo TINYINT(1) DEFAULT 1,
    estado_suscripcion VARCHAR(20) DEFAULT 'prueba',
    fecha_vencimiento DATE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_url_slug (url_slug),
    INDEX idx_activo (activo),
    INDEX idx_plan (plan_id),
    INDEX idx_estado_suscripcion (estado_suscripcion),
    INDEX idx_fecha_vencimiento (fecha_vencimiento),
    FOREIGN KEY (plan_id) REFERENCES planes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: USUARIOS ADMIN
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios_admin (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(100),
    email VARCHAR(100),
    rol ENUM('superadmin', 'admin', 'editor', 'consulta') DEFAULT 'admin',
    activo TINYINT(1) DEFAULT 1,
    ultimo_login TIMESTAMP NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_username (username),
    INDEX idx_rol (rol),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: CATEGORÍAS
-- ============================================================
CREATE TABLE IF NOT EXISTS categorias (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255),
    icono VARCHAR(50),
    orden INT DEFAULT 0,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_orden (orden),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: PLATOS
-- ============================================================
CREATE TABLE IF NOT EXISTS platos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    categoria_id INT NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL DEFAULT 0,
    precio_oferta DECIMAL(10,2),
    imagen_url VARCHAR(500),
    imagen_public_id VARCHAR(255),
    etiquetas VARCHAR(255),
    es_vegetariano TINYINT(1) DEFAULT 0,
    es_vegano TINYINT(1) DEFAULT 0,
    es_sin_gluten TINYINT(1) DEFAULT 0,
    es_picante TINYINT(1) DEFAULT 0,
    es_nuevo TINYINT(1) DEFAULT 0,
    es_popular TINYINT(1) DEFAULT 0,
    orden INT DEFAULT 0,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_categoria (categoria_id),
    INDEX idx_activo (activo),
    INDEX idx_orden (orden),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: IMÁGENES PENDIENTES DE CLOUDINARY
-- Mantiene archivos locales que fallaron al subir para reintentos.
-- ============================================================
CREATE TABLE IF NOT EXISTS imagenes_pendientes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT DEFAULT NULL,
    plato_id INT DEFAULT NULL,
    tipo VARCHAR(50) DEFAULT 'plato',
    local_path VARCHAR(1024) DEFAULT NULL,
    source_url TEXT DEFAULT NULL,
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 5,
    status ENUM('pending','processing','failed','uploaded') NOT NULL DEFAULT 'pending',
    last_error TEXT DEFAULT NULL,
    public_id VARCHAR(255) DEFAULT NULL,
    url TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    processed_at DATETIME DEFAULT NULL,
    INDEX idx_imagenes_pendientes_restaurante (restaurante_id),
    INDEX idx_imagenes_pendientes_status (status),
    INDEX idx_imagenes_pendientes_plato (plato_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: VISITAS (Tracking detallado)
-- ============================================================
CREATE TABLE IF NOT EXISTS visitas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    referer VARCHAR(500),
    es_movil TINYINT(1) DEFAULT 0,
    es_qr TINYINT(1) DEFAULT 0,
    pais VARCHAR(50),
    ciudad VARCHAR(100),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_restaurante_fecha (restaurante_id, fecha),
    INDEX idx_fecha (fecha),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: ESTADÍSTICAS DIARIAS (Resumen para dashboard)
-- ============================================================
CREATE TABLE IF NOT EXISTS estadisticas_diarias (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    fecha DATE NOT NULL,
    visitas INT DEFAULT 0,
    escaneos_qr INT DEFAULT 0,
    visitas_movil INT DEFAULT 0,
    visitas_desktop INT DEFAULT 0,
    
    UNIQUE KEY unique_rest_fecha (restaurante_id, fecha),
    INDEX idx_restaurante_fecha (restaurante_id, fecha),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: SUSCRIPCIONES
-- ============================================================
CREATE TABLE IF NOT EXISTS suscripciones (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurante_id INT NOT NULL,
    plan_id INT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    estado ENUM('activa', 'cancelada', 'vencida', 'pendiente') DEFAULT 'activa',
    metodo_pago VARCHAR(50),
    referencia_pago VARCHAR(100),
    monto DECIMAL(10,2),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_estado (estado),
    FOREIGN KEY (restaurante_id) REFERENCES restaurantes(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES planes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: LOG DE AUDITORÍA
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT,
    restaurante_id INT,
    accion VARCHAR(50) NOT NULL,
    tabla_afectada VARCHAR(50),
    registro_id INT,
    datos_anteriores JSON,
    datos_nuevos JSON,
    ip_address VARCHAR(45),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_usuario (usuario_id),
    INDEX idx_restaurante (restaurante_id),
    INDEX idx_fecha (fecha),
    INDEX idx_accion (accion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TABLA: RECUPERACIÓN DE CONTRASEÑA
-- ============================================================
CREATE TABLE IF NOT EXISTS password_resets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    usuario_id INT NOT NULL,
    token VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(100) NOT NULL,
    fecha_expiracion TIMESTAMP NOT NULL,
    utilizado TINYINT(1) DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_usuario (usuario_id),
    INDEX idx_token (token),
    INDEX idx_expiracion (fecha_expiracion),
    FOREIGN KEY (usuario_id) REFERENCES usuarios_admin(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- USUARIO SUPERADMIN INICIAL
-- El usuario superadmin se crea automáticamente al visitar /api/init-db
-- Password por defecto: superadmin123 (cambiar en producción!)
-- ============================================================
-- NOTA: No insertar aquí - el hash se genera dinámicamente en /api/init-db
