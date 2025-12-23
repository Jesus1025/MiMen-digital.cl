# 🚀 GUÍA COMPLETA DE DESPLIEGUE EN PYTHONANYWHERE

## 📌 Resumen de la Solución

**Problema:** `NameError: name 'log_dir' is not defined` en línea 75
**Solución:** ✅ Variable `log_dir` ya fue definida correctamente en app_menu.py (línina 76)

---

## 🔧 PASO 1: Actualizar Código en PythonAnywhere

1. Entra a **PythonAnywhere** → **Files**
2. Navega a tu carpeta de aplicación
3. Reemplaza el archivo `app_menu.py` con la versión corregida que ya está en tu proyecto local

**O usa Git:**
```bash
cd /home/tu_usuario/tu_aplicacion
git pull origin main
```

---

## 🗄️ PASO 2: Ejecutar Migraciones SQL

1. Ve a **PythonAnywhere** → **Databases** → **MySQL console**
2. Selecciona tu base de datos: `MiMenudigital$menu_digital`
3. Copia TODO el contenido de `PYTHONANYWHERE_MIGRATION.sql` (en tu proyecto local)
4. Pégalo en la consola y presiona **Enter**

**Resultado esperado:**
```
Query OK, 0 rows affected
...
Migración completada exitosamente!
```

---

## 🔐 PASO 3: Configurar Variables de Entorno

1. Ve a **PythonAnywhere** → **Web** → Tu sitio web
2. Baja hasta **Environment variables**
3. Haz clic en **Add a new variable**

### 3.1 Variables de Flask
```
FLASK_ENV = production
SECRET_KEY = tu_clave_super_secreta_aqui_minimo_32_caracteres
FLASK_APP = app_menu.py
```

### 3.2 Variables de Cloudinary
```
CLOUDINARY_URL = cloudinary://tu_clave:tu_secreto@tu_cloudname
```
(Si no lo tienes, obtén uno en [Cloudinary](https://cloudinary.com))

### 3.3 Variables de Mercado Pago
```
MERCADO_PAGO_ACCESS_TOKEN = APP_USR-1259548247582305-122300-5d8c3d2581d2b1ec853e7a0a3b069882-3089095564
MERCADO_PAGO_PUBLIC_KEY = APP_USR-fd17b6ea-ef3b-4c7f-8f9d-2d94ae37b7c9
```

### 3.4 Variables de Base de Datos
```
DB_USER = MiMenudigital$usuario
DB_PASSWORD = tu_contraseña_mysql
DB_HOST = MiMenudigital.mysql.pythonanywhere-services.com
DB_NAME = MiMenudigital$menu_digital
```

**Nota:** Obtén estos valores de la configuración de tu BD en PythonAnywhere → Databases

---

## 🔄 PASO 4: Actualizar WSGI

1. Ve a **Web** → Haz clic en tu sitio
2. En **Code** → **WSGI configuration file**, haz clic en el enlace
3. Verifica que incluya:

```python
import sys
path = '/home/tu_usuario/tu_aplicacion'
if path not in sys.path:
    sys.path.append(path)

from app_menu import app
application = app
```

---

## 🔄 PASO 5: Instalar Dependencias

En **PythonAnywhere** → **Bash console:**

```bash
cd /home/tu_usuario/tu_aplicacion
pip install -r requirements.txt --user
```

Verifica que se instalen:
- ✅ Flask 3.0+
- ✅ pdfkit 1.0+
- ✅ mercado-pago 2.0+
- ✅ Pillow (para imágenes)
- ✅ PyMySQL

---

## 🔃 PASO 6: Reiniciar Aplicación

1. Ve a **Web** 
2. Haz clic en el botón **Reload** (parte superior)
3. Espera 30-60 segundos a que termine

---

## ✅ PASO 7: Verificar que Todo Funciona

### 7.1 Revisar Logs
1. Ve a **Web** → **Log files**
2. Abre **error.log**
3. Busca por "log_dir", "Mercado Pago" o cualquier error

**Líneas que deberías ver:**
```
INFO: Iniciando aplicación Menu Digital
INFO: Cloudinary configurado correctamente
INFO: Mercado Pago configurado correctamente
```

### 7.2 Probar en el Navegador
1. Ve a tu aplicación: `https://tu_usuario.pythonanywhere.com`
2. Intenta hacer login
3. Navega a panel de pago
4. Haz clic en "Pagar con Mercado Pago"

### 7.3 Verificar Carpeta de Logs
En **Bash console:**
```bash
ls -la /home/tu_usuario/tu_aplicacion/logs/
cat /home/tu_usuario/tu_aplicacion/logs/app.log
```

---

## 🐛 Troubleshooting

### Error: "NameError: name 'log_dir' is not defined"
✅ **SOLUCIONADO** - Ya está definido en las líneas 76-77 de app_menu.py

### Error: "MERCADO_PAGO_ACCESS_TOKEN not found"
- [ ] Verifica que el nombre sea EXACTO: `MERCADO_PAGO_ACCESS_TOKEN`
- [ ] Sin espacios antes/después
- [ ] Reinicia la app después de agregar

### Error: "Table 'transacciones_pago' doesn't exist"
- [ ] Ejecuta `PYTHONANYWHERE_MIGRATION.sql` en MySQL console
- [ ] Verifica que la BD seleccionada sea correcta

### Los pagos no redireccionan a Mercado Pago
- [ ] Verifica que `MERCADO_PAGO_ACCESS_TOKEN` esté configurada
- [ ] Revisa error.log
- [ ] Prueba crear una preferencia manualmente en la consola

### Carpeta logs/ no se crea
- [ ] Verifica permisos: `chmod 755 /home/tu_usuario/tu_aplicacion`
- [ ] La carpeta debería crearse automáticamente en el primer inicio

---

## 📊 Estructura Final Esperada

```
/home/tu_usuario/tu_aplicacion/
├── app_menu.py              ✅ Corregido (log_dir definido)
├── wsgi.py                  ✅ Apunta a app_menu.app
├── requirements.txt         ✅ Todas las dependencias
├── schema.sql               ✅ Para referencia
├── config.py
├── database.py
│
├── logs/                    ✅ SE CREA AUTOMÁTICAMENTE
│   └── app.log              (Rotación: 5MB, máx 3 backups)
│
├── static/
│   └── uploads/
│       └── qrs/             (Códigos QR generados)
│
├── templates/
│   ├── gestion/
│   ├── superadmin/
│   └── ...
│
└── .env.local               (OPCIONAL - valores locales)
```

---

## 🎯 Test Final

Ejecuta esto en **Bash console** de PythonAnywhere:

```bash
# 1. Verificar que log_dir se define correctamente
python -c "from app_menu import log_dir; print(f'log_dir: {log_dir}')"

# 2. Verificar importación de Mercado Pago
python -c "from app_menu import MERCADOPAGO_CLIENT; print('Mercado Pago OK')"

# 3. Verificar tabla de transacciones
mysql -u MiMenudigital\$usuario -p -h MiMenudigital.mysql.pythonanywhere-services.com MiMenudigital\$menu_digital -e "DESCRIBE transacciones_pago;"
```

**Salida esperada:**
```
log_dir: /home/tu_usuario/tu_aplicacion/logs
Mercado Pago OK
(Descripción de tabla con todas las columnas)
```

---

## 🚀 ¡Listo!

Si todo pasó las verificaciones, tu aplicación está completamente lista para producción:

✅ Logging configurado (sin errores de log_dir)
✅ Mercado Pago conectado
✅ Base de datos migrada
✅ PDFs funcionando
✅ QR generándose

---

## 📞 Soporte

Si algo falla:

1. Revisa **error.log**
2. Verifica todas las **Environment variables**
3. Confirma que **SQL migration** se ejecutó
4. Reinicia con el botón **Reload**

---

**Última actualización:** Diciembre 2025  
**Estado:** ✅ Listo para producción
**Versión:** 2.0 - Production Ready
