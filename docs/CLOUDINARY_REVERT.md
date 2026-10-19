# Reversion: Cloudinary Obligatorio

## Cambios Realizados

✅ **Cloudinary ahora es obligatorio** - La aplicación fallará al iniciar si no está configurado.

### 1. Configuración de Cloudinary (Líneas 145-157)
**Antes:**
```python
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
if CLOUDINARY_URL:
    cloudinary.config_from_url(CLOUDINARY_URL)
    logger.info("Cloudinary configurado correctamente")
else:
    logger.warning("CLOUDINARY_URL no está configurada. Las imágenes no se subirán a la nube.")
```

**Después:**
```python
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
if not CLOUDINARY_URL:
    raise ValueError(
        "CLOUDINARY_URL no está configurada. Es requerida para el funcionamiento de la aplicación. "
        "Configúrala en las variables de entorno del servidor."
    )

cloudinary.config_from_url(CLOUDINARY_URL)
logger.info("Cloudinary configurado correctamente")
```

### 2. api_platos POST (Línea 920-938)
- ✅ Eliminado check `if not CLOUDINARY_URL`
- ✅ Solo usa Cloudinary para guardar imágenes
- ✅ Siempre guarda `secure_url` en BD

### 3. api_plato PUT (Línea 1000-1014)
- ✅ Eliminado check `if not CLOUDINARY_URL`
- ✅ Solo usa Cloudinary para actualizar imágenes
- ✅ Siempre guarda `secure_url` en BD

### 4. api_subir_logo (Línea 1268-1276)
- ✅ Eliminado check `if not CLOUDINARY_URL`
- ✅ Solo usa Cloudinary para guardar logos
- ✅ Siempre guarda `secure_url` en BD

## Comportamiento

### ✅ Con Cloudinary configurado correctamente:
1. App inicia sin problemas
2. Las imágenes se suben a Cloudinary
3. Se guardan `secure_url` en la base de datos
4. Se aplican transformaciones automáticas (quality="auto", fetch_format="auto")

### ❌ Sin Cloudinary configurado:
1. App falla al iniciar con error claro
2. Usuario ve: `"CLOUDINARY_URL no está configurada. Es requerida..."`
3. Debe configurar la variable de entorno antes de continuar

## Requisitos

- **cloudinary** debe estar instalado en el servidor
- **CLOUDINARY_URL** debe estar configurada como variable de entorno
  - Formato: `cloudinary://key:secret@cloud`

## Testing

```bash
# Verificar que CLOUDINARY_URL está configurada
echo $CLOUDINARY_URL

# Si no sale nada, configurarla en PythonAnywhere:
# Web → Environment variables → Add CLOUDINARY_URL
```

## Resumen

✅ Cloudinary es ahora **obligatorio** y no opcional
✅ La app **falla al iniciar** si no está configurado  
✅ Todos los uploads van **directamente a Cloudinary**
✅ Se guardan siempre las **secure_url** en BD
✅ No hay fallback a almacenamiento local
