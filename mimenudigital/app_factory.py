"""
app_factory.py

Small compatibility shim created after a failed refactor attempt.
It exposes `get_db()` and `limiter` if the main app defines them (imported from `app_menu`).
This file exists to avoid import errors from partial blueprints left behind.
"""

try:
    from app_menu import get_db, limiter
except Exception:
    # app_menu not fully available; provide safe fallbacks
    def get_db():
        raise RuntimeError('get_db not available: app_menu not initialized')
    limiter = None
