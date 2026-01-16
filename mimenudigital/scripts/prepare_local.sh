#!/usr/bin/env bash
# Prepares local dev environment: create venv, install deps, create .env from example
set -euo pipefail

if [ ! -d ".venv" ]; then
  python -m venv .venv
  echo "Created .venv"
fi

source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit .env with your local credentials"
fi

echo "Local environment prepared. Run 'source .venv/bin/activate' (or .venv\Scripts\Activate.ps1 on Windows) and 'python -m pytest' to run tests."