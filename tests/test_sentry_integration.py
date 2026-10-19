import json
import types
from flask import Flask

from app_menu import register_sentry_error_handler


class FakeScope:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSentry:
    def __init__(self):
        self.inited = False
        self.captured = []
        self.user = None
    def init(self, **kwargs):
        self.inited = True
    def capture_exception(self, e):
        self.captured.append(e)
    def set_user(self, u):
        self.user = u
    def push_scope(self):
        return FakeScope()


def test_sentry_capture_on_unhandled_exception(monkeypatch):
    # Create a fresh Flask app for isolation
    fake = FakeSentry()
    new_app = Flask('test_sentry_app')
    new_app.secret_key = 'test-secret'

    # Register the sentry-aware error handler with our fake sentry
    register_sentry_error_handler(new_app, sentry_module=fake)

    # Add a test route that raises
    @new_app.route('/__test_sentry_error')
    def __test_sentry_error():
        raise RuntimeError('test-sentry')

    client = new_app.test_client()

    # Set session user to be attached
    with client.session_transaction() as sess:
        sess['user_id'] = 42
        sess['restaurante_id'] = 99

    res = client.get('/__test_sentry_error')
    assert res.status_code == 500
    # Ensure sentry captured the exception
    assert len(fake.captured) == 1
    assert any('test-sentry' in str(e) for e in fake.captured)
    # Ensure user context was set
    assert fake.user and fake.user.get('id') == 42