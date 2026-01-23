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

### Paso 5: Checklist de producción rápida (P0)
Antes de poner la aplicación en producción, asegúrate de:
- Establecer variables de entorno en Web -> Environment variables:
  - `SECRET_KEY`, `MYSQL_PASSWORD`, `BASE_URL`
  - Opcional: `SENTRY_DSN` (Sentry), `MERCADO_WEBHOOK_KEY` (webhook signature), `CLOUDINARY_URL`
  - Añadir health check (`/healthz` o `/api/health`) para balanceadores y uptime checks
  - Habilitar CI/Tests (incluí un ejemplo en `.github/workflows/ci.yml`) para ejecutar tests y auditoría de seguridad

  > Nota: para que las subidas funcionen en producción, configura `CLOUDINARY_URL` con el formato:
  > `cloudinary://<api_key>:<api_secret>@<cloud_name>`

  Para verificar localmente que Cloudinary está funcionando, ejecuta:

  ```bash
  pip install -r requirements.txt
  export CLOUDINARY_URL='cloudinary://<api_key>:<api_secret>@<cloud_name>'  # Windows: setx CLOUDINARY_URL "..."
  python scripts/cloudinary_check.py --url https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png
  ```

  La salida será JSON con `ok: true` y la `url` devuelta por Cloudinary.

  Para procesar subidas que quedaron pendientes (cuando Cloudinary falla o hay errores de red), hay un worker disponible:

  ```bash
  # Ejecutar manualmente (no en modo debug) para procesar hasta 100 registros pendientes
  python scripts/process_pending_images.py --limit 100

  # Ejemplo de cron (ejecutar cada 5 minutos)
  */5 * * * * /home/tuusuario/.virtualenvs/myenv/bin/python /home/tuusuario/menu-digital/scripts/process_pending_images.py --limit 50 >> /home/tuusuario/menu-digital/logs/pending_processor.log 2>&1
  ```

  El worker intentará subir cada `pending` al bucket de Cloudinary, actualizará `platos.imagen_public_id` y marcará el registro como `uploaded` o `failed` tras varios intentos.


### Variables y pruebas para Mercado Pago

Configura las variables de entorno en tu entorno (o en PythonAnywhere → Web → Environment variables):

```
MERCADO_PAGO_ACCESS_TOKEN = (tu_access_token_de_prueba)
MERCADO_PAGO_PUBLIC_KEY = (tu_public_key_de_prueba)
# Opcional (para validar firmas de webhook por HMAC)
MERCADO_WEBHOOK_KEY = (tu_clave_para_verificar_firmas)
```

Pasos rápidos para probar en servidor (autenticado como admin / propietario del restaurante):

1. Reinicia la app (Web → Reload) tras configurar variables.
2. Verifica estado del cliente:
   - GET `/admin/mercadopago/status` → muestra si SDK está instalado e initialized.
   - POST `/admin/mercadopago/status` → fuerza re-inicialización.
3. Crea una preferencia de prueba desde el servidor:
   - POST `/admin/mercadopago/test-preference` con JSON `{ "price": 1500, "description": "Prueba" }`.
   - Respuesta: `{ "success": true, "response": { ... } }` con `init_point` para abrir checkout en sandbox.
4. Para pruebas de fin a fin, usa las credenciales de prueba de Mercado Pago y verifica que el webhook (`/webhook/mercado-pago`) procese correctamente las notificaciones.

Revisa `logs/app.log` si algo falla y pásame la salida si necesitas ayuda."

- Instalar paquetes recomendados para producción (en tu virtualenv):
  - `pip install Flask-WTF sentry-sdk`
- Asegurar que `wkhtmltopdf` está disponible si usas PDFs (pdfkit)
- Configurar backups: usa `scripts/backup_mysql.sh` en un cron o tarea programada y, opcionalmente, sube a S3
- Recargar la aplicación desde el panel Web después de cambiar env vars


4. Inicializa el schema:
   - Abre la consola MySQL desde el dashboard
   - Copia y pega el contenido de `schema.sql`

### Paso 5: Configurar Web App
1. Ve a "Web" → "Add a new web app"
2. Selecciona "Manual configuration"
3. Selecciona Python 3.10

4. **Configurar WSGI** (editar `/var/www/tuusuario_pythonanywhere_com_wsgi.py`):

> Nota: **NO** pongas secrets (contraseñas, tokens) directamente en el archivo WSGI. En PythonAnywhere usa *Web -> Environment variables* para configurar `SECRET_KEY`, `MYSQL_PASSWORD`, etc.

```python
import sys
import os

# Ruta a tu proyecto
project_home = '/home/tuusuario/menu-digital'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Asegúrate de configurar variables sensibles en Web -> Environment variables
os.environ.setdefault('FLASK_ENV', 'production')
# NO establecer SECRET_KEY o MYSQL_PASSWORD aquí en el repo

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
