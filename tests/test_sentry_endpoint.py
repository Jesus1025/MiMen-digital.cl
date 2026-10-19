import pytest
from app_menu import app
import io


def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['restaurante_id'] = 1
        sess['rol'] = 'admin'


def test_sentry_test_endpoint_not_configured(client):
    client.application.config['TESTING'] = True
    login_as_admin(client)

    res = client.post('/admin/sentry/test')
    assert res.status_code == 400
    j = res.get_json()
    assert j['success'] is False
    assert 'Sentry' in j['error']


def test_sentry_test_endpoint_with_sentry(monkeypatch, client):
    client.application.config['TESTING'] = True
    login_as_admin(client)

    class FakeSentry:
        def __init__(self):
            self.captured = []

        def capture_message(self, msg):
            self.captured.append(msg)

        def push_scope(self):
            class ScopeContext:
                def __init__(self, parent):
                    self.parent = parent

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def set_context(self, k, v):
                    setattr(self.parent, k, v)

            return ScopeContext(self)

    fake = FakeSentry()
    # inject fake sentry into app module
    monkeypatch.setattr('app_menu.sentry_sdk', fake, raising=False)

    res = client.post('/admin/sentry/test')
    assert res.status_code == 200
    j = res.get_json()
    assert j['success'] is True
    assert len(fake.captured) == 1
    assert 'Sentry test event' in fake.captured[0]
