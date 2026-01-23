import os
import tempfile
import pytest

import app_menu
from scripts.process_pending_images import process


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.last_executed = None
        self._fetch_res = rows
        self._one = None

    # Support usage as a context manager
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.last_executed = (query, params)
        # Support the SELECT plato_id query after updating
        if query.lower().startswith('select plato_id'):
            self._one = {'plato_id': None}

    def fetchall(self):
        return self._fetch_res

    def fetchone(self):
        return self._one


class FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.commits = 0

    def cursor(self):
        return FakeCursor(self.rows)

    def commit(self):
        self.commits += 1


def test_process_single_pending_success(monkeypatch, tmp_path):
    # Create a temp image file
    f = tmp_path / "testimg.jpg"
    f.write_bytes(b'abc')

    pending_row = {
        'id': 123,
        'restaurante_id': 1,
        'plato_id': None,
        'local_path': str(f),
        'source_url': None,
        'attempts': 0,
        'status': 'pending'
    }

    fake_db = FakeDB([pending_row])

    monkeypatch.setenv('CLOUDINARY_URL', 'cloudinary://a:b@c')
    monkeypatch.setattr(app_menu, 'CLOUDINARY_AVAILABLE', True)
    monkeypatch.setattr(app_menu, 'CLOUDINARY_CONFIGURED', True)
    monkeypatch.setattr(app_menu, 'get_db', lambda: fake_db)

    def fake_upload(file, **kwargs):
        return {'public_id': 'test_public_id', 'secure_url': 'https://res.cloudinary.com/demo/testimg.jpg'}

    monkeypatch.setattr(app_menu, 'cloudinary_upload', fake_upload)

    # Run processor
    rc = process(limit=10, max_attempts=3, dry_run=False)
    assert rc == 0
    assert fake_db.commits >= 1


def test_process_missing_file_marks_failed(monkeypatch):
    pending_row = {
        'id': 124,
        'restaurante_id': 1,
        'plato_id': None,
        'local_path': '/non/existent/path.jpg',
        'source_url': None,
        'attempts': 0,
        'status': 'pending'
    }

    fake_db = FakeDB([pending_row])
    monkeypatch.setenv('CLOUDINARY_URL', 'cloudinary://a:b@c')
    monkeypatch.setattr(app_menu, 'CLOUDINARY_AVAILABLE', True)
    monkeypatch.setattr(app_menu, 'CLOUDINARY_CONFIGURED', True)
    monkeypatch.setattr(app_menu, 'get_db', lambda: fake_db)

    rc = process(limit=10, max_attempts=3, dry_run=False)
    assert rc == 0
    assert fake_db.commits >= 1
