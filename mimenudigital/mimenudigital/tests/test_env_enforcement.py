import os
import sys
import subprocess
import json

PY = sys.executable


def run_import_with_env(env_vars):
    # Build python -c script to import app_menu and explicitly call enforce_required_envs
    env = os.environ.copy()
    env.update(env_vars)
    cmd = [PY, '-c', "import os; os.environ.update({}); from app_menu import enforce_required_envs; enforce_required_envs(); print('OK')".format(repr(env_vars))]
    proc = subprocess.run(cmd, env=env, capture_output=True)
    return proc

# Note: we call enforce_required_envs explicitly to avoid depending on import-time side-effects
# which may vary between environments and Flask versions.


def test_enforce_required_envs_fails_in_production_when_missing(monkeypatch):
    # Simular entorno de producción sin SECRET_KEY ni MYSQL_PASSWORD
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.delenv('MYSQL_PASSWORD', raising=False)

    from app_menu import enforce_required_envs
    import pytest

    with pytest.raises(RuntimeError):
        enforce_required_envs()


def test_enforce_required_envs_passes_when_set():
    # Include CLOUDINARY_URL and MERCADO token to satisfy optional checks if SDKs are present
    env = {
        'FLASK_ENV': 'production',
        'SECRET_KEY': 'fake',
        'MYSQL_PASSWORD': 'pwd',
        'CLOUDINARY_URL': 'cloudinary://a:b@c',
        'MERCADO_PAGO_ACCESS_TOKEN': 'token'
    }
    proc = run_import_with_env(env)
    assert proc.returncode == 0
    out = proc.stdout.decode('utf-8', errors='ignore')
    assert 'OK' in out