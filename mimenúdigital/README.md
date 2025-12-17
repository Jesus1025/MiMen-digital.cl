# ============================================================
# 🍽️ MENÚ DIGITAL SAAS - GUÍA DE DESPLIEGUE
# Divergent Studio - 2025
# ============================================================

## 📋 ÍNDICE
1. [Requisitos Previos](#requisitos-previos)
2. [Configuración Local](#configuración-local)
3. [Despliegue en PythonAnywhere](#despliegue-en-pythonanywhere)
4. [Configuración de MySQL](#configuración-de-mysql)
5. [Variables de Entorno](#variables-de-entorno)
6. [Troubleshooting](#troubleshooting)

---

## 🔧 REQUISITOS PREVIOS

### Local (Desarrollo)
- Python 3.10+
- MySQL 8.0+ (XAMPP, WAMP, o MySQL Server)
- Git

### Producción (PythonAnywhere)
- Cuenta en PythonAnywhere (gratis funciona para empezar)
- Plan pagado si necesitas dominio personalizado

---

## 💻 CONFIGURACIÓN LOCAL

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/menu-digital.git
cd menu-digital
```

### 2. Crear entorno virtual
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Crear base de datos MySQL local
```sql
-- En MySQL (phpMyAdmin o consola)
CREATE DATABASE menu_digital CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Configurar variables de entorno
Crear archivo `.env` en la raíz:
```env
FLASK_ENV=development
SECRET_KEY=tu_clave_secreta_muy_larga_y_segura
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=menu_digital
MYSQL_PORT=3306
```

### 6. Inicializar base de datos
```bash
python app_menu_mysql.py
```
Luego visitar: `http://127.0.0.1:5000/api/init-db`

### 7. Acceder al sistema
- URL: `http://127.0.0.1:5000`
- Usuario: `superadmin`
- Password: `superadmin123`

---

## 🚀 DESPLIEGUE EN PYTHONANYWHERE

### Paso 1: Crear cuenta
1. Ve a [pythonanywhere.com](https://www.pythonanywhere.com)
2. Crea una cuenta gratuita (o pagada para dominio personalizado)
3. Tu usuario será parte de tu URL: `tuusuario.pythonanywhere.com`

### Paso 2: Subir código
**Opción A: Desde GitHub (recomendado)**
```bash
# En la consola Bash de PythonAnywhere
cd ~
git clone https://github.com/tu-usuario/menu-digital.git
```

**Opción B: Subir archivos manualmente**
1. Ve a "Files" en PythonAnywhere
2. Sube los archivos a `/home/tuusuario/menu-digital/`

### Paso 3: Crear entorno virtual
```bash
# En consola Bash de PythonAnywhere
cd ~/menu-digital
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Paso 4: Crear base de datos MySQL
1. Ve a "Databases" en el dashboard
2. Crea una nueva base de datos MySQL
3. Anota los datos:
   - Host: `tuusuario.mysql.pythonanywhere-services.com`
   - User: `tuusuario`
   - Password: (el que elijas)
   - Database: `tuusuario$menu_digital`

4. Inicializa el schema:
   - Abre la consola MySQL desde el dashboard
   - Copia y pega el contenido de `schema.sql`

### Paso 5: Configurar Web App
1. Ve a "Web" → "Add a new web app"
2. Selecciona "Manual configuration"
3. Selecciona Python 3.10

4. **Configurar WSGI** (editar `/var/www/tuusuario_pythonanywhere_com_wsgi.py`):
```python
import sys
import os

# Ruta a tu proyecto
project_home = '/home/tuusuario/menu-digital'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Variables de entorno
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'tu_clave_secreta_muy_segura_y_larga_2025'
os.environ['MYSQL_HOST'] = 'tuusuario.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'tuusuario'
os.environ['MYSQL_PASSWORD'] = 'tu_password_mysql'
os.environ['MYSQL_DB'] = 'tuusuario$menu_digital'
os.environ['BASE_URL'] = 'https://tuusuario.pythonanywhere.com'

# Importar la app
from app_menu_mysql import app as application
```

5. **Configurar Virtual Environment**:
   - En la sección "Virtualenv", poner: `/home/tuusuario/menu-digital/venv`

6. **Configurar Static Files**:
   | URL | Directory |
   |-----|-----------|
   | /static | /home/tuusuario/menu-digital/static |

### Paso 6: Inicializar base de datos
Visita: `https://tuusuario.pythonanywhere.com/api/init-db`

### Paso 7: ¡Listo!
Tu menú digital estará disponible en:
- Panel: `https://tuusuario.pythonanywhere.com/login`
- Menús: `https://tuusuario.pythonanywhere.com/menu/nombre-restaurante`

---

## 🔐 VARIABLES DE ENTORNO

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `FLASK_ENV` | Entorno (development/production) | `production` |
| `SECRET_KEY` | Clave secreta para sesiones | `abc123...xyz789` |
| `MYSQL_HOST` | Host de MySQL | `localhost` o `user.mysql.pythonanywhere-services.com` |
| `MYSQL_USER` | Usuario MySQL | `root` o `tuusuario` |
| `MYSQL_PASSWORD` | Contraseña MySQL | `tu_password` |
| `MYSQL_DB` | Nombre de la BD | `menu_digital` |
| `MYSQL_PORT` | Puerto MySQL | `3306` |
| `BASE_URL` | URL base del sitio | `https://tudominio.com` |

---

## 🐛 TROUBLESHOOTING

### Error: "Can't connect to MySQL"
- Verifica que MySQL esté corriendo
- Verifica host, user, password y database
- En PythonAnywhere, usa el host `.mysql.pythonanywhere-services.com`

### Error: "Table doesn't exist"
- Ejecuta `/api/init-db` para crear las tablas
- O ejecuta `schema.sql` manualmente en MySQL

### Error: "Module not found"
- Activa el entorno virtual: `source venv/bin/activate`
- Reinstala dependencias: `pip install -r requirements.txt`

### Los estilos no cargan
- Verifica la configuración de Static Files en PythonAnywhere
- Asegúrate que `/static` apunte al directorio correcto

### 502 Bad Gateway
- Revisa los logs de error en PythonAnywhere
- Generalmente es un error de sintaxis en Python o WSGI

---

## 📱 PRIMER USO

1. **Login como SuperAdmin**
   - Usuario: `superadmin`
   - Password: `superadmin123`
   - ⚠️ ¡Cambiar inmediatamente en producción!

2. **Crear primer restaurante**
   - Ve a "Gestión de Restaurantes"
   - Click en "Nuevo Restaurante"
   - Ingresa nombre y URL slug (ej: `mi-restaurante`)

3. **Crear usuario para el restaurante**
   - Click en "Crear Usuario"
   - Asigna el restaurante creado
   - Comparte credenciales con el cliente

4. **El cliente puede:**
   - Iniciar sesión con sus credenciales
   - Agregar categorías y platos
   - Personalizar apariencia
   - Descargar código QR

---

## 📞 SOPORTE

**Divergent Studio**
- Email: soporte@divergentstudio.cl
- WhatsApp: +56 9 XXXX XXXX

---

*Última actualización: Diciembre 2025*
