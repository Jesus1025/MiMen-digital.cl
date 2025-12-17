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
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_url_slug (url_slug),
    INDEX idx_activo (activo),
    INDEX idx_plan (plan_id),
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
-- USUARIO SUPERADMIN INICIAL
-- Password: superadmin123 (cambiar en producción!)
-- Hash generado con werkzeug.security.generate_password_hash
-- ============================================================
INSERT INTO usuarios_admin (restaurante_id, username, password_hash, nombre, rol, activo) VALUES
(NULL, 'superadmin', 'pbkdf2:sha256:600000$salt$hash_placeholder', 'Super Admin Divergent Studio', 'superadmin', 1);

-- NOTA: El hash real se genera al iniciar la app si no existe el usuario
