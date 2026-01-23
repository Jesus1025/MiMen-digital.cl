import pytest

import app_menu


def test_healthz_ok(monkeypatch, client):
    # Mock DB and Cloudinary flags
    class FakeCur:
        def execute(self, q):
            return None
    class FakeCtx:
        def __enter__(self):
            return FakeCur()
        def __exit__(self, *a):
            pass
    class FakeDB:
        def cursor(self):
            return FakeCtx()

    monkeypatch.setattr(app_menu, 'get_db', lambda: FakeDB())
    monkeypatch.setattr(app_menu, 'CLOUDINARY_AVAILABLE', True)
    monkeypatch.setattr(app_menu, 'CLOUDINARY_CONFIGURED', True)

    res = client.get('/healthz')
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    assert data['components']['cloudinary']['available'] is True


def test_healthz_db_down(monkeypatch, client):
    # Simulate DB error
    def bad_db():
        raise Exception('db down')
    monkeypatch.setattr(app_menu, 'get_db', bad_db)
    res = client.get('/healthz')
    assert res.status_code == 500
    data = res.get_json()
    assert data['ok'] is False
    assert 'db' in data['components']
