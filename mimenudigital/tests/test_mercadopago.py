import json
import pytest

from app_menu import app, MERCADOPAGO_AVAILABLE, MERCADOPAGO_CLIENT


class DummyPreference:
    def __init__(self, response):
        self._response = response

    def create(self, data):
        return {"status": 201, "response": self._response}


class DummyMPClient:
    def __init__(self, pref_response):
        self._pref_response = pref_response

    def preference(self):
        return DummyPreference(self._pref_response)

    def payment(self):
        class P:
            def get(self, payment_id):
                return {"status": 200, "response": {"id": payment_id, "status": "approved", "external_reference": "rest_1_123"}}
        return P()


@pytest.fixture
def client(monkeypatch):
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['restaurante_id'] = 1
        sess['rol'] = 'admin'


def test_admin_status_without_sdk(client, monkeypatch):
    # Auth
    login_as_admin(client)
    # Force SDK unavailable
    monkeypatch.setattr('app_menu.MERCADOPAGO_AVAILABLE', False)
    res = client.get('/admin/mercadopago/status')
    assert res.status_code == 200
    data = res.get_json()
    assert 'sdk_available' in data


def test_admin_test_preference_happy_path(client, monkeypatch):
    # Auth
    login_as_admin(client)
    # Mock SDK presence and client behavior
    dummy_response = {"id": "pref_123", "init_point": "https://mercadopago.test/init"}
    dummy_client = DummyMPClient(dummy_response)

    monkeypatch.setattr('app_menu.MERCADOPAGO_AVAILABLE', True)
    monkeypatch.setattr('app_menu.MERCADOPAGO_CLIENT', dummy_client)

    res = client.post('/admin/mercadopago/test-preference', json={"price": 1500, "description": "Prueba"})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'response' in data
    assert data['response']['status'] == 201


def test_webhook_processing_approved(client, monkeypatch):
    # Mock client to return approved payment
    dummy_client = DummyMPClient({})
    monkeypatch.setattr('app_menu.MERCADOPAGO_CLIENT', dummy_client)

    # Mock DB to avoid external MySQL dependency
    class FakeCur:
        def execute(self, q, params=None):
            return None
        def fetchone(self):
            return {'fecha_vencimiento': None}
    class FakeCtx:
        def __enter__(self):
            return FakeCur()
        def __exit__(self, *a):
            pass
    class FakeDB:
        def cursor(self):
            return FakeCtx()
        def commit(self):
            return None
    monkeypatch.setattr('app_menu.get_db', lambda: FakeDB())
    # Also stub subscription info to avoid DB calls in before_request
    monkeypatch.setattr('app_menu.get_subscription_info', lambda rid: None)

    payload = {"data": {"id": "pay_1"}}
    res = client.post('/webhook/mercado-pago', json=payload)
    assert res.status_code == 200
    assert res.get_json().get('status') == 'success'
