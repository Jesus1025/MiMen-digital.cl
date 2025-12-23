# Resumen de Correcciones - Error log_dir

## ✅ Problema Identificado y Solucionado

### Error Original
```
NameError: name 'log_dir' is not defined
Línea 75 de app_menu.py: os.makedirs(log_dir, exist_ok=True)
```

### Causa
La variable `log_dir` no estaba definida antes de ser usada. El código intentaba crear un directorio sin haber declarado primero la ruta.

### Solución Aplicada
Se agregó la definición correcta de `log_dir` en las líneas 72-73:

```python
# Definir directorio de logs
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
```

**Beneficios:**
- ✅ Crea automáticamente la carpeta `logs/` en el directorio raíz del proyecto
- ✅ Usa rutas absolutas para evitar conflictos
- ✅ Compatible con PythonAnywhere
- ✅ Si la carpeta ya existe, no genera error

---

## 📋 Verificación de Variables de Mercado Pago

### Nombres Correctos Confirmados

En el código (`app_menu.py`):
```python
# Línea 176
access_token = os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')

# Línea 180
MERCADOPAGO_CLIENT = mercadopago.SDK(access_token)
```

### Variables a Configurar en PythonAnywhere

**Importante:** Los nombres deben coincidir exactamente.

```
MERCADO_PAGO_ACCESS_TOKEN = APP_USR-1259548247582305-122300-5d8c3d2581d2b1ec853e7a0a3b069882-3089095564
MERCADO_PAGO_PUBLIC_KEY = APP_USR-fd17b6ea-ef3b-4c7f-8f9d-2d94ae37b7c9
```

**Nota:** La `PUBLIC_KEY` se reserva para futuras integraciones (ej: Wallet, SDK de cliente).

---

## 📁 Estructura de Carpetas Generada

Después de ejecutar la aplicación, se crea automáticamente:

```
mimenudigital/
├── app_menu.py
├── wsgi.py
├── logs/                      ← SE CREA AUTOMÁTICAMENTE
│   └── app.log
├── static/
│   └── uploads/
│       └── qrs/
├── templates/
└── ...
```

---

## 🔄 Flujo de Inicialización Corregido

1. **Importaciones** (Línea 45-71)
   - Flask
   - Librerías estándar
   - pdfkit (opcional)
   - mercadopago (opcional)

2. **Logging Setup** (Línea 72-91) ✅ CORREGIDO
   - Define `log_dir` correctamente
   - Crea carpeta `logs/` si no existe
   - Configura rotación de logs (5MB, 3 backups)

3. **Inicialización de Flask** (Línea 93+)
   - Crea la app
   - Configura secret_key
   - Configura sesiones

4. **Inicialización de Servicios** (Línea 127+)
   - init_cloudinary()
   - init_mercadopago()

---

## 📊 Checklist de Despliegue en PythonAnywhere

- [ ] Copiar código corregido a PythonAnywhere
- [ ] Ejecutar PYTHONANYWHERE_MIGRATION.sql
- [ ] Agregar variables de entorno:
  - [ ] FLASK_ENV
  - [ ] SECRET_KEY
  - [ ] CLOUDINARY_URL
  - [ ] MERCADO_PAGO_ACCESS_TOKEN
  - [ ] MERCADO_PAGO_PUBLIC_KEY
  - [ ] DB_USER, DB_PASSWORD, DB_HOST, DB_NAME
- [ ] Reiniciar la aplicación (botón Reload)
- [ ] Verificar error.log
- [ ] Probar crear preferencia de pago
- [ ] Verificar que se crea directorio logs/

---

## 🧪 Test de Verificación

Ejecutar en la consola de PythonAnywhere (Bash):

```bash
# 1. Verificar que la carpeta logs se crea
ls -la ~/tu_aplicacion/logs/

# 2. Ver el contenido del log
tail -f ~/tu_aplicacion/logs/app.log

# 3. Verificar variables de entorno
env | grep MERCADO_PAGO

# 4. Probar importación del módulo
python -c "import app_menu; print('OK')"
```

---

## 📝 Cambios Realizados en app_menu.py

**Línea 72-73 (AGREGADO):**
```python
# Definir directorio de logs
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
```

**Línea 74 (MODIFICADO):**
```python
os.makedirs(log_dir, exist_ok=True)  # Ahora log_dir está definido
```

---

## 🚀 Estado Final

✅ Error `log_dir` solucionado
✅ Variables de Mercado Pago confirmadas  
✅ Estructura de archivos documentada
✅ Listo para despliegue en PythonAnywhere

---

**Fecha:** Diciembre 2025  
**Versión:** 2.0 - Production Ready
