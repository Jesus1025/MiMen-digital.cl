import io
import json
import pytest

from app_menu import app, CLOUDINARY_AVAILABLE


def login_as_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['restaurante_id'] = 1
        sess['rol'] = 'admin'


def test_api_upload_image_calls_cloudinary(monkeypatch, client):
    # Prepare test client and session
    client.application.config['TESTING'] = True
    login_as_admin(client)

    # Mock cloudinary_upload
    def fake_upload(file, **kwargs):
        return {'secure_url': 'https://res.cloudinary.com/demo/image/upload/v123/test.jpg', 'public_id': 'mimenudigital/test/test123'}

    monkeypatch.setattr('app_menu.cloudinary_upload', fake_upload)
    monkeypatch.setattr('app_menu.CLOUDINARY_AVAILABLE', True)
    monkeypatch.setattr('app_menu.CLOUDINARY_CONFIGURED', True)

    # Use a minimal JPEG header to pass MIME/signature validation
    data = {
        'image': (io.BytesIO(b'\xff\xd8\xff\xe0' + b'JPEGDATA'), 'test.jpg')
    }

    # Avoid DB access from before_request
    monkeypatch.setattr('app_menu.get_subscription_info', lambda rid: None)

    res = client.post('/api/upload-image', data=data, content_type='multipart/form-data')
    assert res.status_code == 200
    j = res.get_json()
    assert j['success'] is True
    assert j['url'].startswith('https://res.cloudinary.com/')


def test_admin_cloudinary_test_upload_file(monkeypatch, client):
    client.application.config['TESTING'] = True
    login_as_admin(client)

    def fake_upload(file, **kwargs):
        return {'secure_url': 'https://res.cloudinary.com/demo/image/upload/v123/test2.jpg', 'public_id': 'mimenudigital/test/test456'}

    monkeypatch.setattr('app_menu.cloudinary_upload', fake_upload)
    monkeypatch.setattr('app_menu.CLOUDINARY_AVAILABLE', True)
    monkeypatch.setattr('app_menu.CLOUDINARY_CONFIGURED', True)

    data = {
        'image': (io.BytesIO(b'fakeimagecontent2'), 'test2.jpg')
    }

    res = client.post('/admin/cloudinary/test-upload', data=data, content_type='multipart/form-data')
    assert res.status_code == 200
    j = res.get_json()
    assert j['success'] is True
    assert 'result' in j and 'public_id' in j['result']
