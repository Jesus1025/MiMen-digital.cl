import pytest
from app_menu import app as flask_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Configuración para el entorno de testing
    flask_app.config.from_object('config.TestingConfig')
    
    # Aquí podríamos pre-cargar la base de datos con datos de prueba si fuera necesario
    
    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

def test_index_redirects_or_loads(client):
    """
    Testea la página de inicio.
    Debería redirigir a /login si no hay sesión (302), 
    o cargar el dashboard si hay sesión.
    En cualquier caso, no debería dar un error 4xx o 5xx.
    """
    response = client.get('/')
    assert response.status_code in [200, 302]

def test_login_page_loads(client):
    """Testea que la página de login cargue correctamente."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Iniciar Sesión" in response.data

def test_non_existent_route(client):
    """Testea que una ruta que no existe devuelva un 404."""
    response = client.get('/una-ruta-que-no-existe')
    assert response.status_code == 404
    assert b"Página no encontrada" in response.data

def test_health_check_endpoint(client):
    """
    Testea el endpoint de health check.
    Es una buena prueba para verificar que la app está viva y que puede
    (o no) conectarse a la base de datos en el entorno de test.
    """
    response = client.get('/api/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['app'] == 'ok'
    # En un entorno de test real, probablemente la conexión a la BD de test falle
    # si no está configurada, pero el endpoint debería manejarlo.
    assert 'mysql_connection' in json_data
