# Guía de Integración - Mercado Pago

## Estado: ✅ Implementado

Se ha integrado completamente Mercado Pago para la gestión de pagos de suscripciones.

---

## 📋 Requisitos Previos

1. **Cuenta en Mercado Pago**: [https://www.mercadopago.com.ar/](https://www.mercadopago.com.ar/)
2. **Access Token**: Obtenerlo de las credenciales de tu aplicación
3. **SDK instalado**: `pip install mercado-pago>=2.0.0`

---

## 🔧 Configuración en PythonAnywhere (WSGI)

En el archivo `wsgi.py`, agregar la variable de entorno:

```python
# En la sección "1. ESTABLECER VARIABLES DE ENTORNO"
os.environ['MERCADO_PAGO_ACCESS_TOKEN'] = 'tu_access_token_aqui'
```

**Ejemplo completo:**
```python
os.environ['MYSQL_HOST'] = 'MiMenudigital.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'MiMenudigital'
os.environ['MYSQL_PASSWORD'] = '19101810Aa'
os.environ['MYSQL_DB'] = 'MiMenudigital$menu_digital'
os.environ['MYSQL_PORT'] = '3306'
os.environ['FLASK_ENV'] = 'production'
os.environ['BASE_URL'] = 'https://mimenudigital.pythonanywhere.com'
os.environ['MERCADO_PAGO_ACCESS_TOKEN'] = 'APP_USR-1234567890-XXXXX'  # ← AGREGAR ESTA LÍNEA
```

---

## 🚀 Flujo de Pago

### 1. **Usuario accede a página de pago expirada**
```
GET /gestion/pago-pendiente
```

### 2. **Usuario hace clic en "Pagar con Mercado Pago"**
```
POST /api/pago/crear-preferencia
{
  "plan_type": "mensual"  // o "anual"
}
```

**Respuesta:**
```json
{
  "success": true,
  "preferencia_id": "123456789",
  "init_point": "https://www.mercadopago.com/checkout/v1/redirect?preference-id=123456789"
}
```

### 3. **Sistema redirige a Mercado Pago**
- Usuario completa el pago
- Mercado Pago redirige a `/pago/exito` o `/pago/fallo`

### 4. **Webhook de confirmación**
```
POST /webhook/mercado-pago
```

El webhook:
- Valida el pago con Mercado Pago
- Actualiza la tabla `restaurantes` (fecha_vencimiento, estado_suscripcion)
- Registra la transacción en `transacciones_pago`
- Responde con `{"status": "success"}`

---

## 🔑 Rutas Implementadas

### Públicas (sin autenticación):
- `POST /webhook/mercado-pago` - Recibe notificaciones de Mercado Pago

### Protegidas (requieren login + suscripción activa):
- `GET /gestion/descargas` - Página de descargas
- `GET /gestion/pago-pendiente` - Página de pago cuando expira

### Protegidas (requieren login):
- `POST /api/pago/crear-preferencia` - Crear preferencia de pago
- `GET /pago/exito` - Confirmación de pago exitoso
- `GET /pago/fallo` - Error de pago
- `GET /pago/pendiente` - Pago pendiente

---

## 📊 Estructura de Datos

### Tabla: `transacciones_pago`
```sql
id                  INT PRIMARY KEY
restaurante_id      INT (Foreign Key)
payment_id          VARCHAR(255) UNIQUE
preferencia_id      VARCHAR(255)
monto               DECIMAL(10,2)
moneda              VARCHAR(10)
estado              VARCHAR(50)
tipo_plan           VARCHAR(50)
descripcion         TEXT
respuesta_json      LONGTEXT
fecha_creacion      TIMESTAMP
```

### Nuevas columnas en `restaurantes`:
```sql
ultima_preferencia_pago    VARCHAR(255)
ultimo_pago_mercadopago   VARCHAR(255)
fecha_ultimo_pago         TIMESTAMP
fecha_ultimo_intento_pago TIMESTAMP
```

---

## 🔍 Estados de Pago

| Estado | Descripción | Acción |
|--------|-------------|--------|
| `approved` | Pago confirmado | Extender suscripción |
| `pending` | Pendiente de procesamiento | Esperar confirmación |
| `rejected` | Pago rechazado | Mostrar error al usuario |
| `cancelled` | Pago cancelado | No hacer nada |

---

## 💡 Ejemplo de Implementación Completa

### 1. Instalar dependencias:
```bash
pip install mercado-pago>=2.0.0
```

### 2. Ejecutar migración de BD:
```bash
mysql -h MiMenudigital.mysql.pythonanywhere-services.com \
  -u MiMenudigital \
  -p'19101810Aa' \
  MiMenudigital\$menu_digital < migrations/001_add_mercado_pago_columns.sql
```

### 3. Configurar WSGI (en PythonAnywhere):
```python
os.environ['MERCADO_PAGO_ACCESS_TOKEN'] = 'APP_USR-...'
```

### 4. Recargar aplicación (en PythonAnywhere Web):
- Web → Reload [tu_app]

---

## 🧪 Testing

### Modo Sandbox (Pruebas)
Mercado Pago proporciona credenciales de sandbox para testing:

1. Obtener access token de sandbox en:
   - https://www.mercadopago.com.ar/developers/es/docs

2. Usar tarjetas de prueba:
   - Visa: 4111 1111 1111 1111
   - Mastercard: 5555 5555 5555 4444

### Validar Webhook:
```bash
curl -X POST http://localhost:5000/webhook/mercado-pago \
  -H "Content-Type: application/json" \
  -d '{"data":{"id":"123456789"}}'
```

---

## 🔐 Seguridad

1. **Access Token**: Nunca compartir o exponer en código público
2. **Validación de webhook**: El código valida el pago con Mercado Pago
3. **HTTPS**: Requerido en producción (PythonAnywhere lo provee)
4. **External Reference**: Formato: `rest_{restaurante_id}_{timestamp}`
   - Previene duplicados
   - Identifica restaurante automáticamente

---

## 📝 Logs

Los pagos se registran en `/logs/app.log`:

```
2025-12-23 10:15:32 | INFO | Mercado Pago configurado correctamente
2025-12-23 10:20:15 | INFO | Preferencia de pago creada para restaurante 5: 123456789
2025-12-23 10:25:00 | INFO | Pago aprobado para restaurante 5. Suscripción extendida hasta 2026-01-23
```

---

## 🐛 Troubleshooting

### "Mercado Pago no está configurado"
- ✅ Verificar que `MERCADO_PAGO_ACCESS_TOKEN` está en WSGI
- ✅ Recargar aplicación en PythonAnywhere
- ✅ Verificar que el token no está vencido

### "Error al crear preferencia"
- ✅ Validar que los datos de restaurante existen en BD
- ✅ Revisar logs en `/logs/app.log`
- ✅ Verificar permisos de la API en Mercado Pago

### "Webhook no recibe notificaciones"
- ✅ Verificar URL de notificación en Mercado Pago (debe ser `https://`)
- ✅ Revisar logs para ver si se llama a `/webhook/mercado-pago`
- ✅ Usar herramientas como Webhook.site para testing

---

## 📱 Monitoreo

### Ver transacciones:
```sql
SELECT * FROM transacciones_pago 
WHERE restaurante_id = 5 
ORDER BY fecha_creacion DESC;
```

### Ver último pago de restaurante:
```sql
SELECT id, nombre, ultima_preferencia_pago, ultimo_pago_mercadopago, fecha_ultimo_pago
FROM restaurantes 
WHERE id = 5;
```

---

## ✅ Checklist de Implementación

- [x] SDK de Mercado Pago instalado
- [x] Rutas de pago implementadas
- [x] Webhook implementado
- [x] Plantillas de confirmación creadas
- [x] Migración de BD creada
- [x] Variables de entorno configuradas
- [x] Logging implementado
- [ ] Testing en producción
- [ ] Monitoreo activo

---

## 📞 Soporte

Para más información, consultar:
- Documentación oficial: https://www.mercadopago.com.ar/developers/es
- Dashboard: https://www.mercadopago.com.ar/dashboard
- Credenciales: https://www.mercadopago.com.ar/developers/panel/app
