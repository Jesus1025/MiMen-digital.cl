import pytest
from types import SimpleNamespace

import app_menu


def test_cloudinary_image_url_and_srcset(monkeypatch):
    # Fake cloudinary.utils.cloudinary_url
    def fake_cloudinary_url(public_id, **opts):
        w = opts.get('width')
        if w:
            return (f"https://res.cloudinary.com/demo/image/upload/w_{w}/{public_id}.jpg", {})
        return (f"https://res.cloudinary.com/demo/image/upload/{public_id}.jpg", {})

    monkeypatch.setattr(app_menu, 'cloudinary', SimpleNamespace(utils=SimpleNamespace(cloudinary_url=fake_cloudinary_url)))
    monkeypatch.setattr(app_menu, 'CLOUDINARY_AVAILABLE', True)

    url = app_menu.cloudinary_image_url('folder/image_123', width=640)
    assert 'w_640' in url and 'folder/image_123' in url

    srcset = app_menu.cloudinary_srcset('folder/image_123', widths=[320, 640])
    assert 'w_320' in srcset and 'w_640' in srcset


def test_api_platos_returns_imagen_src(client, monkeypatch):
    # Fake DB cursor to return rows with imagen_public_id
    class FakeCursor:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def execute(self, q, params=None):
            pass
        def fetchall(self):
            return [{'id': 1, 'imagen_public_id': 'demo/public_1', 'imagen_url': '/static/uploads/1.jpg'}]

    class FakeDB:
        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(app_menu, 'get_db', lambda: FakeDB())

    # Fake cloudinary URL generator
    def fake_cloudinary_url(public_id, **opts):
        w = opts.get('width')
        if w:
            return (f"https://res.cloudinary.com/demo/image/upload/w_{w}/{public_id}.jpg", {})
        return (f"https://res.cloudinary.com/demo/image/upload/{public_id}.jpg", {})

    monkeypatch.setattr(app_menu, 'cloudinary', SimpleNamespace(utils=SimpleNamespace(cloudinary_url=fake_cloudinary_url)))
    monkeypatch.setattr(app_menu, 'CLOUDINARY_AVAILABLE', True)

    # Login as owner
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['restaurante_id'] = 1
        sess['rol'] = 'admin'

    res = client.get('/api/platos')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert data[0].get('imagen_src') is not None
    assert data[0].get('imagen_srcset') is not None
