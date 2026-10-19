import os
import hmac
import hashlib
import json

import pytest

from app_menu import app


@pytest.fixture
def client(monkeypatch):
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def sign_payload(key, payload_bytes):
    return hmac.new(key.encode(), payload_bytes, hashlib.sha256).hexdigest()


def test_webhook_signature_invalid(client, monkeypatch):
    key = 'supersecret'
    monkeypatch.setenv('MERCADO_WEBHOOK_KEY', key)

    payload = {"data": {"id": "pay_1"}}
    body = json.dumps(payload).encode('utf-8')

    headers = {'X-Hub-Signature-256': 'sha256=bad_signature'}
    res = client.post('/webhook/mercado-pago', data=body, headers=headers, content_type='application/json')
    assert res.status_code == 401
    assert res.get_json().get('status') == 'invalid_signature'


def test_webhook_signature_valid(client, monkeypatch):
    key = 'supersecret'
    monkeypatch.setenv('MERCADO_WEBHOOK_KEY', key)

    payload = {"data": {"id": "pay_2"}}
    body = json.dumps(payload).encode('utf-8')

    sig = sign_payload(key, body)
    headers = {'X-Hub-Signature-256': f'sha256={sig}'}

    # Mock MERCADOPAGO_CLIENT to avoid external call
    class DummyP:
        def get(self, pid):
            return {"status": 200, "response": {"id": pid, "status": "approved", "external_reference": "rest_1_123"}}
    class DummyMPClient:
        def payment(self):
            return DummyP()

    monkeypatch.setattr('app_menu.MERCADOPAGO_CLIENT', DummyMPClient())

    # Mock DB to avoid external MySQL dependency during approved processing
    class FakeCur:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def execute(self, q, params=None):
            self._q = q
            self._p = params
        def fetchone(self):
            return {'fecha_vencimiento': None}
    class FakeDB:
        def cursor(self):
            return FakeCur()
        def commit(self):
            return None
    monkeypatch.setattr('app_menu.get_db', lambda: FakeDB())

    res = client.post('/webhook/mercado-pago', data=body, headers=headers, content_type='application/json')
    assert res.status_code == 200
    assert res.get_json().get('status') == 'success'


def test_webhook_idempotent_when_payment_already_applied(client, monkeypatch):
    key = 'supersecret'
    monkeypatch.setenv('MERCADO_WEBHOOK_KEY', key)

    payload = {"data": {"id": "pay_3"}}
    body = json.dumps(payload).encode('utf-8')

    sig = sign_payload(key, body)
    headers = {'X-Hub-Signature-256': f'sha256={sig}'}

    # Mock payment client
    class DummyP:
        def get(self, pid):
            return {"status": 200, "response": {"id": pid, "status": "approved", "external_reference": "rest_1_123"}}
    class DummyMPClient:
        def payment(self):
            return DummyP()

    monkeypatch.setattr('app_menu.MERCADOPAGO_CLIENT', DummyMPClient())

    # Mock DB to indicate payment already applied
    class FakeCur:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def execute(self, q, params=None):
            self._q = q
            self._p = params
        def fetchone(self):
            return {'ultimo_pago_mercadopago': 'pay_3'}
    class FakeDB:
        def cursor(self):
            return FakeCur()
        def commit(self):
            return None
    monkeypatch.setattr('app_menu.get_db', lambda: FakeDB())

    res = client.post('/webhook/mercado-pago', data=body, headers=headers, content_type='application/json')
    assert res.status_code == 200
    assert res.get_json().get('status') == 'already_processed'