from flask import Flask, g
import sqlite3
import os
from werkzeug.security import generate_password_hash

from config import config

app = Flask(__name__)
# Selecciona la configuración a usar, con 'default' como opción predeterminada.
config_name = os.environ.get('FLASK_CONFIG') or 'default'
app.config.from_object(config[config_name])

# Crear directorios
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ===== GESTIÓN DE BASE DE DATOS =====
def get_db():
    """Abrir una nueva conexión a la base de datos si no existe una para el contexto actual."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row  # Devolver filas como diccionarios
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Cerrar la conexión a la base de datos."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_database():
    """Inicializar base de datos completa y asegurar que el usuario admin exista."""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            nombre TEXT,
            email TEXT,
            rol TEXT DEFAULT 'admin',
            activo BOOLEAN DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Asegurar que el usuario admin exista y tenga la contraseña predeterminada
    password_hash = generate_password_hash('admin123')
    
    # Verificar si el usuario 'admin' ya existe
    cursor.execute("SELECT id FROM usuarios WHERE username = 'admin'")
    admin_exists = cursor.fetchone()

    if admin_exists:
        # Si el usuario existe, actualizar su contraseña y otros campos
        cursor.execute('''
            UPDATE usuarios SET
                password_hash = ?,
                nombre = 'Administrador',
                email = 'admin@teknetau.cl',
                rol = 'admin',
                activo = 1
            WHERE username = 'admin'
        ''', (password_hash,))
    else:
        # Si el usuario no existe, insertarlo
        cursor.execute('''
            INSERT INTO usuarios (username, password_hash, nombre, email, rol, activo) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', password_hash, 'Administrador', 'admin@teknetau.cl', 'admin', 1))
    
    # Crear el resto de las tablas si no existen.
    # Esto no sobreescribirá las tablas existentes ni sus datos.
    
    # Tabla de clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rut TEXT UNIQUE,
            razon_social TEXT,
            giro TEXT,
            direccion TEXT,
            comuna TEXT,
            ciudad TEXT,
            telefono TEXT,
            email TEXT,
            activo BOOLEAN DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de proyectos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            nombre TEXT,
            descripcion TEXT,
            cliente_rut TEXT,
            fecha_inicio DATE,
            fecha_termino DATE,
            presupuesto REAL,
            estado TEXT DEFAULT 'Activo',
            FOREIGN KEY (cliente_rut) REFERENCES clientes(rut)
        )
    ''')
    
    # Tabla de facturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_doc INTEGER,
            tipo_doc TEXT, -- FAC, BOL, NC, ND
            folio TEXT,
            fecha_emision DATE,
            fecha_vencimiento DATE,
            cliente_rut TEXT,
            proyecto_codigo TEXT,
            descripcion TEXT,
            valor_neto REAL,
            iva REAL,
            valor_total REAL,
            estado TEXT DEFAULT 'Pendiente',
            forma_pago TEXT,
            observaciones TEXT,
            factura_referencia_id INTEGER,
            motivo_nc_nd TEXT,
            usuario_creacion TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_rut) REFERENCES clientes(rut),
            FOREIGN KEY (proyecto_codigo) REFERENCES proyectos(codigo),
            FOREIGN KEY (factura_referencia_id) REFERENCES facturas(id)
        )
    ''')
    
    # Tabla de items de facturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS factura_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER,
            codigo_producto TEXT,
            descripcion TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            descuento REAL DEFAULT 0,
            total_linea REAL,
            FOREIGN KEY (factura_id) REFERENCES facturas(id)
        )
    ''')
    
    # Tabla de motivos NC/ND
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS motivos_nc_nd (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo INTEGER,
            descripcion TEXT,
            tipo TEXT,
            activo BOOLEAN DEFAULT 1
        )
    ''')
    
    # Insertar datos de ejemplo solo si la tabla de clientes está vacía
    cursor.execute("SELECT COUNT(*) FROM clientes")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT OR IGNORE INTO clientes (rut, razon_social, giro, ciudad) VALUES ('76660180-4', 'WINPY SPA', 'Tecnología', 'Santiago')")
        cursor.execute("INSERT OR IGNORE INTO clientes (rut, razon_social, giro, ciudad) VALUES ('78138410-0', 'APLICACIONES COMPUTACIONALES SPA', 'Software', 'Santiago')")
        
    # Insertar motivos NC/ND solo si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM motivos_nc_nd")
    if cursor.fetchone()[0] == 0:
        motivos_nc = [
            (1, 'Anulación de factura de venta', 'NC'),
            (2, 'Rebaja o descuento otorgado', 'NC'),
            (3, 'Devolución de productos', 'NC'),
            (4, 'Descuento por pronto pago', 'NC'),
            (5, 'Corrección de montos', 'NC')
        ]
        
        motivos_nd = [
            (1, 'Intereses por mora', 'ND'),
            (2, 'Gastos por cobranza', 'ND'),
            (3, 'Ajuste de precios', 'ND'),
            (4, 'Otros cargos', 'ND')
        ]
        
        for motivo in motivos_nc + motivos_nd:
            cursor.execute(
                "INSERT OR IGNORE INTO motivos_nc_nd (codigo, descripcion, tipo) VALUES (?, ?, ?)",
                motivo
            )
            
    conn.commit()
    conn.close()

init_database()
