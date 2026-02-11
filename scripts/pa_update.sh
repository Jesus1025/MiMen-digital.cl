#!/usr/bin/env bash
# Usage: run on PythonAnywhere console in project dir
# Pull latest changes, install deps, apply migrations and reload webapp
set -euo pipefail

echo "Pulling latest from origin/main (you can change branch)..."
git fetch origin
git checkout --quiet -- .
# Optionally, switch branch: git checkout MAIN_BRANCH

echo "Installing requirements..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Apply SQL migration files if any (manual step, review before running)
# This assumes mysql client is configured or you use your own DB migration process
if [ -d migrations ]; then
  echo "Applying SQL migrations from migrations/"
  for f in migrations/*.sql; do
    [ -e "$f" ] || continue
    echo "Would apply $f - manual step: run via mysql client or admin console"
  done
fi

# If you use a manage script to run migrations, call it here (example):
# python3 manage.py migrate

# Restart web app on PythonAnywhere by touching WSGI file
PA_WSGI="/var/www/your_pythonanywhere_username_pythonanywhere_com_wsgi.py"
if [ -f "$PA_WSGI" ]; then
  echo "Touching WSGI file to reload web app"
  touch "$PA_WSGI"
else
  echo "Note: WSGI file path ($PA_WSGI) not found. If on PythonAnywhere, touch your WSGI file or use the web UI to reload."
fi

echo "Update script finished. Review migration steps if needed."