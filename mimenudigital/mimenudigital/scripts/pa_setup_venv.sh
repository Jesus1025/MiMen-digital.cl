#!/usr/bin/env bash
# Script to create / recreate a PythonAnywhere virtualenv and install requirements
# Usage on PythonAnywhere:
# bash ~/MiMen-digital.cl/scripts/pa_setup_venv.sh

set -euo pipefail

USER_HOME="/home/$(whoami)"
VENV_DIR="$USER_HOME/.virtualenvs/mimen-venv"
REPO_DIR="$USER_HOME/MiMen-digital.cl"
REQ_PATH="$REPO_DIR/mimenudigital/requirements.txt"

echo "-- pa_setup_venv.sh --"
echo "User home: $USER_HOME"
echo "Virtualenv dir: $VENV_DIR"
echo "Repo dir: $REPO_DIR"

# If repo directory doesn't exist, abort
if [ ! -d "$REPO_DIR" ]; then
  echo "ERROR: Repo directory $REPO_DIR not found. Clone your repo first."
  echo "Run: git clone https://github.com/Jesus1025/MiMen-digital.cl.git $REPO_DIR"
  exit 1
fi

# Backup existing venv if present
if [ -d "$VENV_DIR" ]; then
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP="$VENV_DIR.bak_$TIMESTAMP"
  echo "Virtualenv already exists at $VENV_DIR -> moving to $BACKUP"
  mv "$VENV_DIR" "$BACKUP"
fi

# Choose Python executable available on PA
PYTHON_CMD=""
for py in python3.10 python3.9 python3.8 python3.11 python3; do
  if command -v $py >/dev/null 2>&1; then
    PYTHON_CMD=$py
    break
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  echo "ERROR: No suitable python3 found on this system." >&2
  exit 1
fi

echo "Creating virtualenv with $PYTHON_CMD..."
$PYTHON_CMD -m venv "$VENV_DIR"

echo "Activating virtualenv and upgrading pip..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel

# Install requirements if file exists
if [ -f "$REQ_PATH" ]; then
  echo "Installing requirements from $REQ_PATH"
  pip install -r "$REQ_PATH"
else
  echo "WARNING: requirements file not found at $REQ_PATH"
  echo "You may need to run: pip install --user PyMySQL \"qrcode[pil]\" python-dotenv"
fi

echo
echo "DONE. Virtualenv created at: $VENV_DIR"
echo "Next steps:" 
echo "1) In PythonAnywhere web UI -> Web -> Virtualenv, set the Virtualenv path to:" 
echo "   $VENV_DIR"
echo "2) Ensure WSGI file points to your project path (MiMen-digital.cl/mimenudigital) and imports the app as 'mimenudigital.app_menu' or 'app_menu' depending on your setup." 
echo "3) Reload the web app from the Web tab (or run: touch /var/www/mimenudigital_pythonanywhere_com_wsgi.py)"

echo
# Print a quick import test command user can run
echo "To test the import inside the venv now run:" 
echo "source $VENV_DIR/bin/activate && python - <<'PY'"
echo "import traceback" 
echo "try:" 
echo "    import mimenudigital.app_menu as m" 
echo "    print('IMPORT_OK')" 
echo "except Exception:" 
echo "    traceback.print_exc()" 
echo "PY"

exit 0
