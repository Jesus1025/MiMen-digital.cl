import io

import app_menu


def login_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['restaurante_id'] = 1
        sess['rol'] = 'admin'


def test_upload_rejects_non_image_content(monkeypatch, client):
    client.application.config['TESTING'] = True
    login_admin(client)

    # Cloudinary available but file content is not an image
    monkeypatch.setattr(app_menu, 'CLOUDINARY_AVAILABLE', True)
    monkeypatch.setattr(app_menu, 'CLOUDINARY_CONFIGURED', True)
    monkeypatch.setenv('CLOUDINARY_URL', 'cloudinary://a:b@c')

    # Avoid DB access from before_request subscription injection
    monkeypatch.setattr('app_menu.get_subscription_info', lambda rid: None)

    data = {
        'image': (io.BytesIO(b'not-an-image-bytes'), 'fake.jpg')
    }

    res = client.post('/api/upload-image', data=data, content_type='multipart/form-data')
    assert res.status_code == 400
    j = res.get_json()
    assert j['success'] is False
    assert 'imagen' in j['error'] or 'Contenido' in j['error'] or 'Content-Type' in j['error']


def test_upload_accepts_valid_image(monkeypatch, client):
    client.application.config['TESTING'] = True
    login_admin(client)

    # Mock a fake cloudinary upload to always succeed
    def fake_upload(file, **kwargs):
        return {'secure_url': 'https://res.cloudinary.com/demo/image/upload/v123/test.jpg', 'public_id': 'mimenudigital/test/test123'}

    monkeypatch.setattr(app_menu, 'cloudinary_upload', fake_upload)
    monkeypatch.setattr(app_menu, 'CLOUDINARY_AVAILABLE', True)
    monkeypatch.setattr(app_menu, 'CLOUDINARY_CONFIGURED', True)

    data = {
        'image': (io.BytesIO(b'\xff\xd8\xff\xe0' + b'JPEGDATA'), 'ok.jpg')
    }

    res = client.post('/api/upload-image', data=data, content_type='multipart/form-data')
    assert res.status_code == 200
    j = res.get_json()
    assert j['success'] is True
    assert j['url'].startswith('https://res.cloudinary.com/')
