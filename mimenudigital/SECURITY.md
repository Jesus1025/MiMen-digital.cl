# Seguridad crítica (resumen de cambios)

Estos son los cambios de seguridad aplicados y recomendaciones para producción:

- Webhooks de Mercado Pago: ahora se verifica HMAC-SHA256 cuando `MERCADO_WEBHOOK_KEY` o `MERCADO_CLIENT_SECRET` está configurado. Si la firma no coincide, el webhook devuelve 401 y se ignoran los datos.
- Idempotencia en webhooks: se comprueba `ultimo_pago_mercadopago` antes de aplicar una actualización para evitar duplicados o re-procesamiento accidental.
- Validación de archivos subidos: `validate_image_file()` ahora rechaza archivos con extensiones no permitidas, MIME no coincidente (si `python-magic` está instalado) y archivos mayores a `MAX_CONTENT_LENGTH` (5 MB por defecto).
- Requerimientos de entorno: `enforce_required_envs()` valida la presencia de variables críticas en producción y levanta un error si faltan (`SECRET_KEY`, `MYSQL_PASSWORD`), evitando arranques inseguros.

Recomendaciones operativas:
- En producción, configura `MERCADO_WEBHOOK_KEY` (o `MERCADO_CLIENT_SECRET`) y `SECRET_KEY` con valores fuertes y protegidos.
- Habilita Sentry (`SENTRY_DSN`) para recibir errores en producción.
- Revisa las migraciones y backups antes de aplicar cambios en la base de datos.

Si quieres, puedo añadir un pequeño script para rotar las claves y una sección en el runbook de deploy con estos pasos.
