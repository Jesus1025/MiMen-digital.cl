# Runbook: Deploying MiMenudigital to PythonAnywhere

This runbook summarizes the manual steps to prepare and deploy the application on PythonAnywhere (or a systemd host).

## Preconditions
- You have SSH or web access to the host and a virtualenv with the project.
- DB credentials are available and a backup has been taken.
- Environment variables for production are stored in PythonAnywhere Web -> Environment variables.

## Environment variables (required)
- SECRET_KEY (mandatory)
- MYSQL_PASSWORD (mandatory)
- CLOUDINARY_URL (if using Cloudinary uploads)
- SENTRY_DSN (optional, recommended)
- MERCADO_PAGO_ACCESS_TOKEN (if using Mercado Pago)
- BASE_URL (optional, set to production URL)

## Steps
1. Backup DB
   - `mysqldump -u <user> -p <database> > backup-$(date +%F).sql`
   - Copy the backup off-server (S3 or local)

2. Pull latest code (if using git):
   - `git pull origin main`

3. Activate virtualenv and install deps
   - `.venv\Scripts\activate` (Windows/local) or `workon <virtualenv>` (PythonAnywhere)
   - `pip install -r requirements.txt`

4. Apply migrations (after backup)
   - Run SQL scripts (via `mysql` client or your admin UI):
     - `mysql -u <user> -p <db> < migrations/002_create_imagenes_pendientes.sql`
   - Verify table created: `SELECT COUNT(*) FROM imagenes_pendientes LIMIT 1;`

5. Configure scheduled worker (PythonAnywhere):
   - Web -> Tasks -> Add new scheduled task:
     - Command: `/home/<user>/.venv/bin/python /home/<user>/mimenudigital/scripts/process_pending_images.py --limit 50 --max-attempts 5`
     - Frequency: every 5 minutes (or adjust)
   - For systemd hosts: create a unit file (see example below)

6. Restart web app
   - On PythonAnywhere: Web -> Reload
   - On systemd: `systemctl restart myapp` or `gunicorn` service

7. Smoke checks
   - `curl -sS $BASE_URL/healthz` -> should return OK
   - `curl -sS -X POST -F 'image=@tests/fixtures/test.jpg' $BASE_URL/admin/cloudinary/test-upload` -> if Cloudinary configured and you are admin, returns success
   - `curl -sS -X POST $BASE_URL/admin/sentry/test` -> returns success if Sentry configured

8. Monitoring and Alerts
   - Ensure Sentry DSN is set and you can see events from staging before prod.
   - Configure uptime monitor (UptimeRobot) against `/healthz`.

## systemd unit example (for self-hosted servers)
```
[Unit]
Description=MiMenuDigital worker
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/mimenudigital
ExecStart=/var/www/mimenudigital/.venv/bin/python scripts/process_pending_images.py --limit 50 --max-attempts 5
Restart=on-failure
RestartSec=30s

[Install]
WantedBy=multi-user.target
```

## Rollback plan
- If something goes wrong, stop the worker and web app, restore DB from backup: `mysql -u <user> -p <db> < backup.sql` and roll back code to previous commit.

## Notes
- Always test worker in dry-run mode before enabling (use `--dry-run`).
- Verify logs at `/home/<user>/mimenudigital/logs/app.log` or wherever configured.
