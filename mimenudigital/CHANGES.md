# CHANGES

## 2025-12-19 - Quick fixes
- Use RotatingFileHandler logging and write logs into `logs/app.log` (created directory).
- Lazy import `qrcode` inside `generar_qr_restaurante()` and add error logging if dependency missing.
- Move MySQL configuration into `app.config` and make `get_db()` build connection arguments dynamically.
- Use `secure_filename()` when extracting file extensions for uploads.
- Use UTC `now()` for Jinja2 `now` helper.

These are safe, minimal changes to improve reliability on PythonAnywhere and in development.
