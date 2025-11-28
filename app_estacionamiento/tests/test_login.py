import pytest
from django.urls import reverse
from app_estacionamiento.models import Usuario

@pytest.mark.django_db
def test_login_por_email(client):
    # Crear usuario con email y password
    usuario = Usuario.objects.create_user(
        email="test@test.com",
        password="1234",
        es_conductor=True
    )

    # Hacer POST al login
    url = reverse("usuarios_login")
    response = client.post(url, {"username": "test@test.com", "password": "1234"})

    # Verificar redirección al inicio
    assert response.status_code == 302
    assert response.url == "/usuarios/inicio/"
