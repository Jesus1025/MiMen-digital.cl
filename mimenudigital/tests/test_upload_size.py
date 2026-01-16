import io

import app_menu


def login_admin(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['restaurante_id'] = 1
        sess['rol'] = 'admin'


def test_upload_rejects_oversize_file(monkeypatch, client):
    client.application.config['TESTING'] = True
    login_admin(client)

    monkeypatch.setattr(app_menu, 'CLOUDINARY_AVAILABLE', True)
    monkeypatch.setattr(app_menu, 'CLOUDINARY_CONFIGURED', True)
    monkeypatch.setenv('CLOUDINARY_URL', 'cloudinary://a:b@c')
    # Avoid DB access from before_request
    monkeypatch.setattr('app_menu.get_subscription_info', lambda rid: None)

    # Create a file larger than MAX_CONTENT_LENGTH
    max_len = client.application.config.get('MAX_CONTENT_LENGTH', app_menu.MAX_CONTENT_LENGTH)
    big = io.BytesIO(b'a' * (max_len + 1))

    data = {
        'image': (big, 'big.jpg')
    }

    res = client.post('/api/upload-image', data=data, content_type='multipart/form-data')
    # Werkzeug may return 413 Request Entity Too Large before our handler
    assert res.status_code in (400, 413)
    if res.status_code == 400:
        assert 'Archivo demasiado grande' in res.get_json().get('error')
