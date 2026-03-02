# ============================================================
# CHECKLIST DE PRODUCCIÓN - Menú Digital SaaS
# Divergent Studio - Última actualización: Marzo 2026
# ============================================================

## 🔴 CRÍTICO - Antes de ir a producción

### Variables de Entorno (Obligatorias)
- [ ] SECRET_KEY - Clave aleatoria de al menos 32 caracteres
- [ ] MYSQL_HOST - Host de la base de datos
- [ ] MYSQL_USER - Usuario de MySQL
- [ ] MYSQL_PASSWORD - Contraseña de MySQL
- [ ] MYSQL_DB - Nombre de la base de datos
- [ ] CLOUDINARY_URL - URL completa de Cloudinary
- [ ] MERCADO_PAGO_ACCESS_TOKEN - Token de acceso de Mercado Pago
- [ ] MERCADO_PAGO_PUBLIC_KEY - Clave pública de Mercado Pago
- [ ] BASE_URL - URL de producción (https://tudominio.com)
- [ ] FLASK_ENV=production - Modo producción

### Variables de Entorno (Recomendadas)
- [ ] MAIL_USERNAME - Email para envío de correos
- [ ] MAIL_PASSWORD - Contraseña de aplicación de Gmail
- [ ] API_PROXY - Proxy para PythonAnywhere (free tier)
- [ ] SENTRY_DSN - Monitoreo de errores (opcional)
- [ ] MERCADO_WEBHOOK_KEY - Verificación de webhooks

### Base de Datos
- [ ] Ejecutar schema.sql inicial
- [ ] Ejecutar TODAS las migraciones en orden (001 a 016)
- [ ] Verificar que existe usuario superadmin
- [ ] Cambiar contraseña del superadmin

### Seguridad
- [ ] HTTPS habilitado en el servidor
- [ ] SECRET_KEY única y no expuesta
- [ ] Contraseñas de BD no en código
- [ ] Credenciales de servicios solo en variables de entorno
- [ ] Verificar que DEBUG=False

---

## 🟡 IMPORTANTE - Para funcionamiento óptimo

### Migraciones a ejecutar
```bash
# En orden:
mysql -u usuario -p database < migrations/016_add_missing_tables.sql
```

### Configuración de Email (Gmail)
1. Habilitar verificación en 2 pasos en tu cuenta Google
2. Generar contraseña de aplicación: https://myaccount.google.com/apppasswords
3. Usar esa contraseña en MAIL_PASSWORD

### Configuración de Cloudinary
1. Crear cuenta en cloudinary.com
2. Copiar CLOUDINARY_URL del dashboard
3. Formato: cloudinary://API_KEY:API_SECRET@CLOUD_NAME

### Configuración de Mercado Pago
1. Crear aplicación en developers.mercadopago.com
2. Obtener credenciales de producción (no sandbox)
3. Configurar webhook URL: https://tudominio.com/webhook/mercado-pago

---

## 🔵 VERIFICACIÓN POST-DEPLOY

### Endpoints a probar
- [ ] GET /api/health - Debe retornar status OK
- [ ] GET /healthz - Verificar todos los componentes
- [ ] GET /login - Página de login carga correctamente
- [ ] POST /login - Login funciona con superadmin
- [ ] GET /api/diagnostico (como superadmin) - Verificar configuración

### Funcionalidades a probar
- [ ] Login/Logout funciona
- [ ] Crear restaurante funciona
- [ ] Crear categoría funciona
- [ ] Crear plato con imagen funciona
- [ ] Subida de imágenes a Cloudinary funciona
- [ ] Ver menú público funciona
- [ ] Generar código QR funciona
- [ ] Descargar PDF funciona
- [ ] Envío de emails funciona (recuperar contraseña)
- [ ] Crear ticket de soporte funciona
- [ ] Pago con Mercado Pago funciona

---

## 📊 MONITOREO RECOMENDADO

### Logs a revisar
- /logs/app.log - Log principal de la aplicación
- Errores de Cloudinary
- Errores de Mercado Pago
- Rate limiting activado

### Métricas a monitorear
- Pool de conexiones MySQL (via /healthz)
- Uso de caché (hit rate)
- Cola de visitas pendientes
- Tiempo de respuesta de APIs

### Alertas recomendadas
- Pool de conexiones > 80% utilización
- Errores 5xx > 10 por hora
- Fallos de Cloudinary consecutivos
- Fallos de pago en Mercado Pago

---

## 🔧 MANTENIMIENTO PERIÓDICO

### Diario (automático con cron)
```sql
CALL cleanup_expired_tokens();  -- Limpiar tokens expirados
CALL aggregate_daily_stats();   -- Agregar estadísticas
```

### Semanal
- Revisar logs de errores
- Verificar uso de Cloudinary
- Revisar tickets pendientes
- Backup de base de datos

### Mensual
- Actualizar dependencias de seguridad
- Revisar métricas de uso
- Limpiar imágenes huérfanas en Cloudinary
- Optimizar tablas MySQL

---

## 📁 ESTRUCTURA DE ARCHIVOS ESPERADA

```
mimenudigital/
├── app_menu.py          # Aplicación principal
├── config.py            # Configuración
├── database.py          # Pool de conexiones
├── security_middleware.py # Seguridad y caché
├── email_service.py     # Servicio de email
├── validators.py        # Validaciones (NUEVO)
├── wsgi.py             # Entrada WSGI
├── requirements.txt     # Dependencias
├── schema.sql          # Schema inicial
├── migrations/         # Migraciones SQL
├── templates/          # Templates Jinja2
├── static/             # Archivos estáticos
│   ├── css/
│   └── uploads/
└── logs/               # Logs de la aplicación
```

---

## 🚀 COMANDOS ÚTILES

### Iniciar en desarrollo
```bash
python app_menu.py
```

### Inicializar BD
```bash
curl http://localhost:5000/api/init-db
```

### Verificar salud
```bash
curl http://localhost:5000/healthz
```

### Procesar imágenes pendientes
```bash
python scripts/process_pending_images.py
```

### Backup MySQL
```bash
./scripts/backup_mysql.sh
```

---

## ⚠️ PROBLEMAS COMUNES

### "Cloudinary no está configurado"
- Verificar CLOUDINARY_URL en variables de entorno
- Formato correcto: cloudinary://API_KEY:API_SECRET@CLOUD_NAME
- En PythonAnywhere, configurar API_PROXY

### "Mercado Pago no inicializado"
- Verificar MERCADO_PAGO_ACCESS_TOKEN
- Asegurar que el token es de producción, no sandbox
- Verificar que mercadopago está instalado: pip install mercado-pago

### "Error de conexión MySQL"
- Verificar credenciales de BD
- En PythonAnywhere, usar formato: usuario.mysql.pythonanywhere-services.com
- Verificar que la BD existe y el usuario tiene permisos

### "Emails no se envían"
- Verificar MAIL_USERNAME y MAIL_PASSWORD
- Para Gmail, usar contraseña de aplicación (no la normal)
- Verificar que TLS está habilitado (puerto 587)

### "Rate limit exceeded"
- Comportamiento normal si hay muchas requests
- Ajustar límites en security_middleware.py si es necesario
- Verificar que no hay un bot atacando

---

## 📞 SOPORTE

- Email: soporte@divergentstudio.cl
- Web: https://divergentstudio.cl/
