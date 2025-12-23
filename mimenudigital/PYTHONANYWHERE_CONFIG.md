# Configuración de Variables de Entorno en PythonAnywhere

## Paso 1: Acceder a PythonAnywhere

1. Entra a [PythonAnywhere](https://www.pythonanywhere.com)
2. Ve a **Web** → Haz clic en tu sitio web
3. Baja hasta **Environment variables**

## Paso 2: Configurar Variables de Entorno

Agrega las siguientes variables (haciendo clic en "Add a new variable"):

### Variables de Flask
```
FLASK_ENV = production
SECRET_KEY = (tu_clave_secreta_aqui)
FLASK_APP = app_menu.py
```

### Variables de Cloudinary
```
CLOUDINARY_URL = (tu_url_de_cloudinary_aqui)
```

### Variables de Mercado Pago
**Importante:** Los nombres deben coincidir exactamente con los del código.

```
MERCADO_PAGO_ACCESS_TOKEN = APP_USR-1259548247582305-122300-5d8c3d2581d2b1ec853e7a0a3b069882-3089095564
MERCADO_PAGO_PUBLIC_KEY = APP_USR-fd17b6ea-ef3b-4c7f-8f9d-2d94ae37b7c9
```

### Variables de Base de Datos
```
DB_USER = tu_usuario_mysql
DB_PASSWORD = tu_contraseña_mysql
DB_HOST = tu_servidor_mysql.mysql.pythonanywhere-services.com
DB_NAME = tu_base_de_datos
```

## Paso 3: Verificar el Código

El archivo `app_menu.py` ya está configurado para:

✅ Leer variables de entorno correctamente
✅ Definir correctamente `log_dir` (línea 75)
✅ Usar `MERCADO_PAGO_ACCESS_TOKEN` para inicializar el SDK
✅ Usar `MERCADO_PAGO_PUBLIC_KEY` para futuras integraciones (reservado)

## Paso 4: Reiniciar la Aplicación

Después de configurar las variables:

1. Ve a **Web** 
2. Haz clic en el botón **Reload** (parte superior)
3. Espera a que reinicie (30-60 segundos)

## Paso 5: Verificar Logs

1. Ve a **Web** → **Log files**
2. Abre **error.log**
3. Busca cualquier error relacionado con:
   - `log_dir` (debe estar resuelto)
   - Mercado Pago
   - Cloudinary

## Estructura de Carpetas Esperada

```
/home/tu_usuario/tu_aplicacion/
├── app_menu.py
├── wsgi.py
├── requirements.txt
├── schema.sql
├── config.py
├── database.py
├── logs/              ← Se crea automáticamente
│   └── app.log
├── static/
│   └── uploads/
├── templates/
└── ...
```

## Troubleshooting

### Error: NameError: name 'log_dir' is not defined
✅ **Solucionado:** Se definió correctamente en línea 75 como:
```python
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
```

### Error: MERCADO_PAGO_ACCESS_TOKEN not found
⚠️ **Solución:** 
1. Verifica que el nombre sea exacto: `MERCADO_PAGO_ACCESS_TOKEN`
2. No uses espacios antes/después del valor
3. Reinicia la aplicación

### Los pagos no funcionan
⚠️ **Verificar:**
1. ✅ `MERCADO_PAGO_ACCESS_TOKEN` está configurada
2. ✅ La base de datos tiene la tabla `transacciones_pago`
3. ✅ La aplicación se ha reiniciado
4. ✅ Revisa el error.log en PythonAnywhere

## Notas Importantes

- **NUNCA** compartas tu `MERCADO_PAGO_ACCESS_TOKEN` públicamente
- Usa la consola MySQL de PythonAnywhere para ejecutar el archivo `PYTHONANYWHERE_MIGRATION.sql`
- Los logs se guardan en `/logs/app.log` y rotan automáticamente cada 5MB
- Las carpetas `logs/` y `static/uploads/` se crean automáticamente

## Comandos Útiles en PythonAnywhere

```bash
# Ver logs en tiempo real
tail -f /home/tu_usuario/tu_aplicacion/logs/app.log

# Verificar versión de Python
python --version

# Verificar paquetes instalados
pip list
```

---

**Fecha de última actualización:** Diciembre 2025
**Versión:** 2.0 - Production Ready
