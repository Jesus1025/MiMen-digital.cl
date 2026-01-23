# ============================================================
# CONFIGURACIÓN DE EMAIL Y NOTIFICACIONES
# Menú Digital SaaS - Divergent Studio
# ============================================================

## 📧 Configuración de Email (SMTP)

### 🆓 Para Plan GRATUITO de PythonAnywhere (sin más env vars):

Edita directamente el archivo `config.py` y descomenta estas líneas:

```python
# En config.py, busca la clase MailConfig y descomenta:

_EMAIL_USERNAME = 'tu_email@gmail.com'
_EMAIL_PASSWORD = 'xxxx xxxx xxxx xxxx'  # Contraseña de aplicación
_SUPERADMIN_EMAIL = 'tu_email@gmail.com'
```

### 💰 Para Plan PAGO (con variables de entorno):

Ve a **Web > Environment Variables** y agrega:

```bash
# Servidor SMTP (ejemplos)
MAIL_SERVER=smtp.gmail.com          # Para Gmail
# MAIL_SERVER=smtp.office365.com    # Para Outlook/Hotmail
# MAIL_SERVER=smtp-mail.outlook.com # Para Outlook alternativo

# Puerto (587 para TLS, 465 para SSL)
MAIL_PORT=587

# TLS/SSL
MAIL_USE_TLS=true
MAIL_USE_SSL=false

# Credenciales
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion  # Ver instrucciones abajo

# Remitente por defecto
MAIL_DEFAULT_SENDER=Menú Digital <soporte@divergent.studio>

# Email del superadmin (recibe notificaciones de tickets)
SUPERADMIN_EMAIL=admin@divergent.studio
```

### Para Gmail:

1. Ve a [Google Account Security](https://myaccount.google.com/security)
2. Activa **Verificación en 2 pasos** si no está activa
3. Ve a **Contraseñas de aplicación** (App Passwords)
4. Genera una contraseña de aplicación para "Mail"
5. Usa esa contraseña de 16 caracteres en `MAIL_PASSWORD`

### Para Outlook/Hotmail:

1. Ve a [Microsoft Account Security](https://account.live.com/proofs/Manage)
2. Genera una contraseña de aplicación
3. Usa esa contraseña en `MAIL_PASSWORD`

---

## 🔔 Notificaciones Push al SuperAdmin

El sistema de notificaciones push está integrado automáticamente:

### Características:
- **Notificaciones en el navegador**: El superadmin recibe notificaciones nativas del navegador
- **Badge de notificaciones**: Icono de campana con contador de notificaciones no leídas
- **Polling automático**: Verifica nuevos tickets cada 30 segundos
- **Sonido de notificación**: Alerta sonora cuando llegan nuevos tickets
- **Historial de notificaciones**: Las últimas 50 notificaciones se guardan en localStorage

### Primera vez:
El navegador pedirá permiso para mostrar notificaciones. El superadmin debe **Permitir** para recibir alertas.

---

## 📨 Emails que se envían automáticamente:

1. **Nuevo ticket creado** (al usuario)
   - Confirmación con número de ticket
   - Resumen del mensaje enviado
   - Tiempo estimado de respuesta

2. **Nuevo ticket** (al superadmin)
   - Notificación inmediata del nuevo ticket
   - Datos del usuario y mensaje
   - Link directo al panel de tickets

3. **Respuesta a ticket** (al usuario)
   - Respuesta del soporte
   - Referencia al ticket original

4. **Recuperación de contraseña** (al usuario)
   - Link seguro para resetear contraseña
   - Expira en 24 horas

---

## 🧪 Verificar configuración

Para verificar que el email está configurado:

```python
# En la consola de Python de PythonAnywhere:
from app_menu import app
with app.app_context():
    print("MAIL_SERVER:", app.config.get('MAIL_SERVER'))
    print("MAIL_USERNAME:", app.config.get('MAIL_USERNAME'))
    print("EMAIL CONFIGURADO:", bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD')))
```

---

## 🐛 Troubleshooting

### El email no se envía:
1. Verifica que `MAIL_USERNAME` y `MAIL_PASSWORD` estén configurados
2. Revisa los logs: `tail -f /var/log/menu_digital.log`
3. Verifica que el puerto 587 esté permitido (en PythonAnywhere sí lo está)

### Notificaciones no aparecen:
1. Verifica que el navegador tenga permisos de notificación
2. Revisa la consola del navegador (F12 > Console)
3. Asegúrate de estar en el panel de SuperAdmin

### Gmail bloquea el acceso:
1. Verifica que uses "Contraseña de aplicación" NO tu contraseña normal
2. Revisa si hay alertas de seguridad en tu cuenta de Google
